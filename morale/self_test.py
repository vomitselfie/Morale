"""Explicit development-bundle smoke test, isolated in a new output directory."""
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time


def run(output):
    root=Path(output).resolve()
    root.mkdir(parents=True,exist_ok=False)
    os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
    from PySide6.QtCore import qVersion
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QImage,QColor,QPainter
    from .app import MainWindow
    from .model import Project,DesignObject
    from .engine import generate
    from .formats import EXPORT_FORMATS,export_machine,import_machine
    report={'passed':False,'platform':platform.platform(),'python':sys.version,'qt':qVersion(),
            'frozen':bool(getattr(sys,'frozen',False)),'checks':[],
            'physical_sewouts':False,'external_files':False}
    app=QApplication.instance() or QApplication([])
    window=None
    def worker(kind,source,destination,options=None):
        destination.mkdir()
        command=([sys.executable] if getattr(sys,'frozen',False) else [sys.executable,'-m','morale'])
        command += [kind,str(source),str(destination)]
        if options is not None:command.append(options if isinstance(options,str) else json.dumps(options))
        result=subprocess.run(command,capture_output=True,timeout=60)
        (destination/'worker.log').write_bytes(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError(f'{kind} failed ({result.returncode}); see {destination.name}/worker.log')
    try:
        window=MainWindow()
        def fail(message):raise RuntimeError(message)
        window.error=fail
        window.show();app.processEvents()
        if window.windowIcon().isNull():raise RuntimeError('Bundled application icon is unavailable.')
        original=window.project.dumps();window.file_path=root/'saved.morale';window.save()
        if not window.file_path.exists():raise RuntimeError('Native project save failed.')
        window.replace_project(Project());window.open_path(root/'saved.morale')
        if window.project.dumps()!=original:raise RuntimeError('Native save/reopen changed the project.')
        report['checks'].append('native_window_save_reopen')
        worker('--generation-worker',root/'saved.morale',root/'generation')
        blocks=json.loads((root/'generation/blocks.json').read_text())
        if sum(len(b['stitches']) for b in blocks)!=sum(len(b.stitches) for b in generate(window.project)):
            raise RuntimeError('Bundled generation command count differs.')
        report['checks'].append('generation_subprocess')
        image=QImage(160,160,QImage.Format.Format_RGB32);image.fill(QColor('white'))
        painter=QPainter(image);painter.fillRect(30,20,20,120,QColor('red'));painter.fillRect(36,60,8,40,QColor('white'));painter.end()
        if not image.save(str(root/'source.png')):raise RuntimeError('PNG artwork creation failed.')
        (root/'source.svg').write_text('<svg width="40" height="40"><circle cx="20" cy="20" r="10" fill="none" stroke="blue" stroke-width="2"/></svg>')
        for name,options in [('raster',{'method':'smooth','resolution':256,'minimum_region':1,'palette_metric':'oklab','border_white':True,'stitch_settings':{'satin_spacing':.6,'underlay':'off'}}),('svg',{'expand_strokes':True})]:
            source=root/('source.png' if name=='raster' else 'source.svg')
            worker('--trace-worker',source,root/name,dict(width=40,stitch_mode='auto',keep_reference=True,**options))
            info=json.loads((root/name/'preview.json').read_text())
            if name=='raster' and info['trace_stats']['quality'].get('palette_reduction',{}).get('metric')!='oklab':
                raise RuntimeError('Perceptual raster palette was not applied.')
            if set(info.get('aligned_previews',{}))!={'source','vectors','stitches'}:
                raise RuntimeError('Aligned conversion previews are missing.')
            if name=='raster' and 'data-preview-contrast' not in info['inspection_svg']['stitches']:
                raise RuntimeError('White stitches have no inspection contrast.')
            quality=info['trace_stats']['quality']
            if quality.get('maximum_stitch_mm',0)<=0 or 'long_stitches' not in quality:
                raise RuntimeError('Sewn-span review measurements are missing.')
            candidate=Project.loads(info['project'])
            if name=='raster' and (not any(o.color.lower()=='#ffffff' for o in candidate.objects) or any(o.width>10 for o in candidate.objects)):
                raise RuntimeError('Enclosed white was lost or the page background was retained.')
            if name=='raster' and any(o.spacing!=.6 or o.underlay for o in candidate.objects if o.stitch_type=='satin'):
                raise RuntimeError('Custom satin settings were not retained.')
            if not candidate.reference or not candidate.objects:raise RuntimeError(f'{name} conversion returned incomplete artwork.')
            if not info.get('density_png') or not info.get('thread_density_png'):raise RuntimeError('Density review assets are missing.')
            if not any(o.stitch_type=='satin' for o in candidate.objects):raise RuntimeError(f'{name} expected satin conversion.')
            before=window.project.dumps();window.apply_raster_trace(candidate);window.undo()
            if window.project.dumps()!=before:raise RuntimeError('Artwork insertion Undo changed the source project.')
            report['checks'].append(name+'_conversion_and_undo')
        import base64
        from .artwork_compare import ArtworkCompareDialog
        inspector=ArtworkCompareDialog({key:QImage.fromData(base64.b64decode(value)) for key,value in info['aligned_previews'].items()},window,geometry=info['inspection_svg'])
        try:
            inspector.show();app.processEvents();inspector.zoom_in();view=inspector.view.transform()
            inspector.mode.setCurrentIndex(1);inspector.opacity.setValue(50)
            if not inspector.vector_layers['vectors'].isVisible() or inspector.vector_layers['vectors'].isCachingEnabled():raise RuntimeError('Scalable inspection geometry was not active.')
            if inspector.view.transform()!=view or inspector.overlay.opacity()!=.5:raise RuntimeError('Comparison changed the view or lost opacity.')
            if not inspector.grab().save(str(root/'artwork-inspector.png')):raise RuntimeError('Comparison screenshot failed.')
        finally:inspector.close()
        report['checks'].append('artwork_overlay_inspector')
        from .stitch_edit import manual_object
        from .review_panels import aligned_panels
        from .inspection_geometry import inspection_layers
        long_project=Project(objects=[manual_object(DesignObject(),[[-10,0,'jump'],[10,0,'stitch']])])
        long_info={'project':long_project.dumps(),'trace_stats':{'artwork_size_mm':[40,20]},'trace_svg':''}
        blank=QImage(640,640,QImage.Format.Format_RGB32);blank.fill(QColor('white'));long_blocks=generate(long_project)
        panels,frame=aligned_panels(long_info,blank,None,blocks=long_blocks)
        long_inspector=ArtworkCompareDialog(dict(zip(('source','vectors','stitches'),panels)),window,geometry=inspection_layers(long_info,long_blocks,frame))
        try:
            long_inspector.show();app.processEvents();long_inspector.highlight_long.setChecked(True)
            if not long_inspector.highlight_long.isEnabled() or not long_inspector.vector_layers['long_spans'].isVisible():raise RuntimeError('Long-span overlay is missing.')
            if not long_inspector.grab().save(str(root/'long-span-inspector.png')):raise RuntimeError('Long-span screenshot failed.')
        finally:long_inspector.close()
        report['checks'].append('long_span_inspector')
        from .stitch_edit import StitchDialog
        window.replace_project(long_project);window.select(long_project.objects[0].id);before=window.project.dumps()
        editor=StitchDialog(long_project.objects[0],[[-10,0,'jump'],[10,0,'stitch']],window)
        try:
            editor.split_long_stitches()
            if editor.model.rowCount()!=5:raise RuntimeError('Long stitch was not subdivided.')
            editor.undo()
            if editor.model.rowCount()!=2:raise RuntimeError('Stitch splitting Undo failed.')
            editor.redo();editor.show();app.processEvents()
            if not editor.grab().save(str(root/'split-long-stitches.png')):raise RuntimeError('Stitch splitting screenshot failed.')
            window.replace_stitches(editor.model.rows);window.undo()
            if window.project.dumps()!=before:raise RuntimeError('Applying split stitches lost main-window Undo.')
        finally:editor.close()
        import math
        split_project=Project(objects=[manual_object(DesignObject(),editor.model.rows)])
        split_exports=root/'split-exports';split_exports.mkdir()
        for extension in sorted(EXPORT_FORMATS):
            path=split_exports/('split'+extension);export_machine(split_project,path)
            previous=(0.,0.);lengths=[]
            for block in generate(import_machine(path).project):
                for stitch in block.stitches:
                    point=(stitch.x,stitch.y)
                    if stitch.command=='stitch':lengths.append(math.dist(previous,point))
                    if stitch.command in {'stitch','jump'}:previous=point
            if not lengths or max(lengths)>6.15 or abs(sum(lengths)-20)>.2:raise RuntimeError(f'{extension} lost or lengthened a split sewn span.')
        report['checks'].append('split_long_stitches_and_undo')
        oversized=Project(hoop_width=500,hoop_height=500,objects=[manual_object(DesignObject(),[[-150,-150,'jump'],[150,150,'stitch']])])
        oversized_exports=root/'oversized-exports';oversized_exports.mkdir()
        for extension in sorted(EXPORT_FORMATS):
            path=oversized_exports/('oversized'+extension);preparation=export_machine(oversized,path)
            if preparation['source_stitches']!=1 or preparation['subdivision_added_stitches']<1 or preparation['prepared_stitches']!=1+preparation['subdivision_added_stitches']:
                raise RuntimeError(f'{extension} export preparation counts are missing or inconsistent.')
            previous=(0.,0.);segments=[]
            for block in generate(import_machine(path).project):
                for stitch in block.stitches:
                    point=(stitch.x,stitch.y)
                    if stitch.command=='stitch' and math.dist(previous,point)>1e-6:segments.append((previous,point))
                    if stitch.command in {'stitch','jump'}:previous=point
            if not segments or math.dist(segments[0][0],(-150,-150))>.2 or math.dist(segments[-1][1],(150,150))>.2 or abs(sum(math.dist(a,b) for a,b in segments)-math.hypot(300,300))>.25:
                raise RuntimeError(f'{extension} did not preserve an oversized sewn path.')
        report['checks'].append('oversized_sewn_path_exports')
        hoop_source=root/'multihoop-source.morale'
        Project(objects=[manual_object(DesignObject(),[[-50,0,'jump'],[50,0,'stitch']])]).save(hoop_source)
        worker('--hoop-worker',hoop_source,root/'multihoop',dict(width=40,height=40,margin=5,registration=True,extension='.dst'))
        hoop_root=root/'multihoop/bundle';plan=json.loads((hoop_root/'plan.json').read_text())
        if not (hoop_root/'placements.csv').exists() or not any(t['export_preparation']['subdivision_added_stitches'] for t in plan['tiles']):raise RuntimeError('Multi-hoop export counts are missing.')
        if any(t['stitches']!=t['export_preparation']['source_stitches'] for t in plan['tiles']):raise RuntimeError('Multi-hoop native counts disagree.')
        for tile in plan['tiles']:
            check=tile.get('verification')
            if not isinstance(check,dict) or type(check.get('verified')) is not bool or not check.get('complete_path_comparison'):
                raise RuntimeError('Multi-hoop reopened-file verification is missing or incomplete.')
            if check['source_stitches']!=tile['stitches'] or 'controls' not in check:
                raise RuntimeError('Multi-hoop verification does not describe the native tile.')
            if not check['verified'] and not check['problems']:
                raise RuntimeError('Multi-hoop review result has no explanation.')
        report['checks'].append('multihoop_export_counts')
        from .trace_dialog import TraceDialog
        from .trace_presets import save_preset,load_preset
        preset_dialog=TraceDialog(str(root/'source.png'),window)
        try:
            preset_dialog.custom_stitches.setChecked(True);preset_dialog.stitch_settings['fill_spacing'].setValue(.7)
            for key,value in [('fill_underlay','edge_sparse'),('satin_underlay','center_zigzag')]:
                control=preset_dialog.underlay_choices[key];control.setCurrentIndex(control.findData(value))
            preset_dialog.stitch_settings['underlay_inset'].setValue(.4)
            preset_dialog.stitch_settings['underlay_spacing'].setValue(1.5)
            settings=preset_dialog.preset_settings();save_preset(root/'conversion.morale-trace.json',settings)
            preset_dialog.custom_stitches.setChecked(False);preset_dialog.width.setValue(55)
            preset_dialog.apply_preset(load_preset(root/'conversion.morale-trace.json'))
            if preset_dialog.preset_settings()!=settings or preset_dialog.width.value()!=55:raise RuntimeError('Conversion preset changed settings or artwork size.')
            preset_dialog.tabs.setCurrentIndex(1);preset_dialog.show();app.processEvents()
            if not preset_dialog.grab().save(str(root/'conversion-preset.png')):raise RuntimeError('Preset screenshot failed.')
        finally:preset_dialog.close()
        report['checks'].append('conversion_preset_round_trip')
        from .conversion_report import save_conversion_review
        save_conversion_review(root/'conversion-review.pdf','source.svg',info,QImage(str(root/'svg/preview.png')))
        if not (root/'conversion-review.pdf').read_bytes().startswith(b'%PDF-'):raise RuntimeError('Bundled conversion review PDF is missing.')
        report['checks'].append('conversion_review_pdf')
        worker('--library-search-worker',root,root/'search','trace.morale')
        search=json.loads((root/'search/search.json').read_text())
        if not search['complete'] or len(search['matches'])!=2:raise RuntimeError('Bundled recursive library search missed traced projects.')
        report['checks'].append('recursive_library_search')
        from .library import LibraryDialog
        library=LibraryDialog(window,folder=str(root))
        try:
            library.show();library.file_views.setCurrentIndex(1)
            library.results.addItems(search['matches']);library.thumbnail_button.setChecked(True)
            deadline=time.monotonic()+20
            while len(library.thumbnails.cache)<2 and time.monotonic()<deadline:
                app.processEvents();time.sleep(.01)
            if len(library.thumbnails.cache)!=2 or any('unavailable' in library.results.item(i).toolTip() for i in range(2)):
                raise RuntimeError('Bundled library thumbnails did not load.')
            report['checks'].append('visible_library_thumbnails')
            library.search.setText('obsolete')
            if library.results.count() or library.preview_path is not None:
                raise RuntimeError('Bundled library retained stale query results.')
            library.show_search(search)
            if library.results.count():raise RuntimeError('Bundled library accepted a stale search response.')
            library.thumbnail_button.setChecked(False)
            library.search.clear()
            from PySide6.QtCore import QEvent,Qt
            from PySide6.QtGui import QKeyEvent
            app.sendEvent(library.search,QKeyEvent(QEvent.Type.KeyPress,Qt.Key.Key_Return,Qt.KeyboardModifier.NoModifier))
            app.sendEvent(library.search,QKeyEvent(QEvent.Type.KeyRelease,Qt.Key.Key_Return,Qt.KeyboardModifier.NoModifier))
            deadline=time.monotonic()+20
            while library.search_runner.path is not None and time.monotonic()<deadline:
                app.processEvents();time.sleep(.01)
            paths={library.results.item(i).text() for i in range(library.results.count())}
            if not set(search['matches'])<=paths or 'saved.morale' not in paths:
                raise RuntimeError('Bundled blank keyboard search missed supported designs.')
            if not library.isVisible() or library.selected_path is not None:
                raise RuntimeError('Bundled keyboard search activated an unrelated action.')
            report['checks'].append('library_keyboard_browse_all_and_query_invalidation')
        finally:library.close()
        applique_source=DesignObject(kind='compound',width=20,height=20,
            contours=[[[-.5,-.5],[.5,-.5],[.5,.5],[-.5,.5]],[[-.2,-.2],[.2,-.2],[.2,.2],[-.2,.2]]])
        window.replace_project(Project(objects=[applique_source]));window.select(applique_source.id)
        before=window.project.dumps();window.apply_applique(2,'auto')
        if len(window.project.objects)!=4 or any(o.stitch_type!='satin' for o in window.project.objects[2:]):raise RuntimeError('Automatic appliqué borders did not become satin.')
        if sum(s.command=='stop' for b in generate(window.project) for s in b.stitches)!=2:raise RuntimeError('Appliqué operator stops changed.')
        window.project.save(root/'satin-applique.morale');window.undo()
        if window.project.dumps()!=before:raise RuntimeError('Appliqué Undo did not restore the source outline.')
        report['checks'].append('satin_applique_and_undo')
        from PySide6.QtCore import QPointF
        window.replace_project(Project(objects=[DesignObject(x=-20,width=10,height=10),DesignObject(x=0,width=10,height=10),DesignObject(x=25,width=10,height=10)]))
        window.select_many([o.id for o in window.project.objects[:2]]);window.object_snap_action.setChecked(True)
        canvas=window.canvas;canvas.scale=5;canvas.press=QPointF(0,0);before=window.project.dumps()
        canvas.drag=canvas.movement_delta(QPointF(14,0))
        if canvas.drag.x()!=15 or canvas.snap_guides[0]!=20:raise RuntimeError('Object snapping did not align the group edge.')
        if not window.grab().save(str(root/'object-snapping.png')):raise RuntimeError('Snap guide screenshot failed.')
        delta=QPointF(canvas.drag);canvas.press=None;canvas.drag=QPointF()
        canvas.moved.emit(window.selected_id,delta.x(),delta.y());window.undo()
        if window.project.dumps()!=before:raise RuntimeError('Snapped group Undo changed the source objects.')
        from .stitch_edit import manual_object
        manual=manual_object(DesignObject(),[[-10,-10,'jump'],[10,10,'stitch']]);manual.rotation=45
        window.replace_project(Project(objects=[manual,DesignObject(x=15,width=10,height=10)]));window.select(manual.id)
        canvas.press=QPointF();canvas.scale=5
        if abs(canvas.movement_delta(QPointF(9,0)).x()-10)>1e-8:raise RuntimeError('Rotated stitch snapping used selection-box corners.')
        canvas.press=None;canvas.snap_guides=(None,None)
        report['checks'].append('snap_alignment_and_undo')
        from .lettering import LetteringDialog,make_lettering
        from .embroidery_fonts import make_font_lettering,load_font,height_range
        font=load_font('califragilistic')
        if len(font['glyphs']['y']['pieces'])!=4:raise RuntimeError('Bundled Califragilistic glyph repair is missing.')
        font_obj=make_font_lettering('yAÁ','califragilistic',height_range(font)[0],layout='curved',curve=60)
        font_project=Project(objects=[font_obj]);font_snapshot=font_project.dumps()
        if generate(font_project)!=generate(Project.loads(font_snapshot)):raise RuntimeError('Curved embroidery font roundtrip failed.')
        font_dialog=LetteringDialog(obj=font_obj,parent=window)
        try:
            font_dialog.accept()
            if font_dialog.candidate!=font_obj:raise RuntimeError('Unchanged embroidery font edit changed saved geometry.')
        finally:font_dialog.close()
        (root/'curved-embroidery-font.morale').write_text(font_snapshot,encoding='utf-8')
        report['checks'].append('curved_embroidery_font_and_repaired_glyph')
        guide=DesignObject(kind='path',width=120,height=30,points=[[-.5,0],[0,-.5],[.5,0]],stitch_type='running')
        window.replace_project(Project(hoop_width=150,hoop_height=100,objects=[guide]));window.select(guide.id)
        before=window.project.dumps()
        lettering=LetteringDialog(parent=window,baseline=guide.outline())
        lettering.text.setText('Morale');lettering.height.setValue(12);lettering.accept()
        if lettering.candidate is None:raise RuntimeError('Path lettering dialog produced no outlines.')
        window.apply_lettering(lettering.candidate,hide_guide_id=guide.id)
        if window.project.objects[0].visible:raise RuntimeError('Path lettering guide was not hidden.')
        saved=window.project.dumps();obj=Project.loads(saved).objects[1]
        changed=make_lettering('MOM',obj.lettering['family'],12,previous=obj,layout='path')
        if any(math.dist(a,b)>1e-8 for a,b in zip(obj.transform(obj.lettering['baseline']),changed.transform(changed.lettering['baseline']))):
            raise RuntimeError('Editing path lettering moved the baseline.')
        window.apply_lettering(changed,replace=True);window.undo()
        if window.project.dumps()!=saved:raise RuntimeError('Path lettering edit Undo failed.')
        window.canvas.set_design(window.project,generate(window.project));app.processEvents()
        if not window.grab().save(str(root/'path-lettering.png')):raise RuntimeError('Path lettering screenshot failed.')
        (root/'path-lettering.morale').write_text(saved,encoding='utf-8')
        window.undo()
        if window.project.dumps()!=before:raise RuntimeError('Path lettering insertion Undo failed.')
        lettering.close()
        report['checks'].append('path_lettering_and_undo')
        from PySide6.QtCore import QEvent,Qt
        from PySide6.QtGui import QKeyEvent
        from .export_verify import verify_export
        def drawing_key(key):
            for event_type in (QEvent.Type.KeyPress,QEvent.Type.KeyRelease):
                app.sendEvent(window.canvas,QKeyEvent(event_type,key,Qt.KeyboardModifier.NoModifier))
        for drawing_mode in ('polygon','satin'):
            window.replace_project(Project())
            before=window.project.dumps()
            canvas=window.canvas;canvas.set_mode(drawing_mode)
            canvas.snap_grid=True;canvas.grid_spacing=2
            for key in (Qt.Key.Key_Home,Qt.Key.Key_Space,Qt.Key.Key_Right,Qt.Key.Key_Space,
                        Qt.Key.Key_Down,Qt.Key.Key_Left,Qt.Key.Key_Space):drawing_key(key)
            if drawing_mode=='satin':
                drawing_key(Qt.Key.Key_Return)
                if window.project.objects or len(canvas.vertices)!=3:
                    raise RuntimeError('Bundled keyboard satin accepted an incomplete rail pair.')
                drawing_key(Qt.Key.Key_Right);drawing_key(Qt.Key.Key_Space)
            drawing_key(Qt.Key.Key_Return)
            if len(window.project.objects)!=1 or window.project.objects[0].kind!=drawing_mode:
                raise RuntimeError('Bundled keyboard drawing did not create the requested object.')
            keyboard_saved=window.project.dumps();keyboard_blocks=generate(window.project)
            if not keyboard_blocks or generate(Project.loads(keyboard_saved))!=keyboard_blocks:
                raise RuntimeError('Bundled keyboard drawing lost stitches after project reload.')
            (root/f'keyboard-{drawing_mode}.morale').write_text(keyboard_saved,encoding='utf-8')
            for extension in ('pes','exp'):
                path=root/f'keyboard-{drawing_mode}.{extension}'
                export_machine(window.project,path,keyboard_blocks)
                verification=verify_export(keyboard_blocks,path)
                if not verification['complete_path_comparison'] or verification['bounds_delta_mm']>.3 or verification['problems']:
                    raise RuntimeError(f'Bundled keyboard {drawing_mode} {extension} export failed: {verification}')
            window.undo()
            if window.project.dumps()!=before:raise RuntimeError('Bundled keyboard drawing Undo failed.')
            window.redo()
            if window.project.dumps()!=keyboard_saved:raise RuntimeError('Bundled keyboard drawing Redo failed.')
        report['checks'].append('keyboard_drawing_roundtrip_exports_and_history')
        from PySide6.QtCore import QPointF
        from PySide6.QtGui import QMouseEvent
        window.replace_project(Project(objects=[DesignObject(kind='rectangle',width=20,height=15)]))
        canvas=window.canvas;canvas.set_mode('select');canvas.show_rulers=True;canvas.snap_grid=False
        unguided_blocks=generate(window.project)
        def guide_mouse(kind,point):
            app.sendEvent(canvas,QMouseEvent(kind,point,canvas.mapToGlobal(point),
                Qt.MouseButton.LeftButton,
                Qt.MouseButton.NoButton if kind==QEvent.Type.MouseButtonRelease else Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier))
        for axis,start in (('x',QPointF(12,100)),('y',QPointF(100,12))):
            end=QPointF(canvas.width()/2+30,canvas.height()/2+30)
            world=canvas.world(end);expected=world.x() if axis=='x' else world.y()
            guide_mouse(QEvent.Type.MouseButtonPress,start)
            if canvas.guide_draft is None or canvas.grab().isNull():
                raise RuntimeError('Bundled ruler guide preview failed.')
            guide_mouse(QEvent.Type.MouseButtonRelease,end)
            if window.project.guides[-1]!={'axis':axis,'position':expected}:
                raise RuntimeError('Bundled ruler drag produced the wrong guide.')
        guided_snapshot=window.project.dumps()
        window.file_path=root/'layout-guides.morale';window.save()
        window.open_path(window.file_path)
        if window.project.dumps()!=guided_snapshot or generate(window.project)!=unguided_blocks:
            raise RuntimeError('Bundled guide save/reopen changed guides or stitches.')
        before=window.project.dumps()
        window.add_layout_guide('x',-17.5);after=window.project.dumps()
        window.undo()
        if window.project.dumps()!=before:raise RuntimeError('Bundled guide Undo failed.')
        window.redo()
        if window.project.dumps()!=after:raise RuntimeError('Bundled guide Redo failed.')
        guide_mouse(QEvent.Type.MouseButtonPress,QPointF(12,100))
        drawing_key(Qt.Key.Key_Escape)
        guide_mouse(QEvent.Type.MouseButtonRelease,QPointF(100,100))
        if window.project.dumps()!=after or canvas.guide_draft is not None:
            raise RuntimeError('Bundled guide cancellation changed the project.')
        report['checks'].append('layout_guides_native_history_and_save')
        ripple=DesignObject(kind='compound',width=30,height=30,underlay=False,spacing=1,
            contours=[[[-.5,-.5],[.5,-.5],[.5,.5],[-.5,.5]],
                      [[-.2,-.2],[.2,-.2],[.2,.2],[-.2,.2]]])
        window.replace_project(Project(objects=[ripple]));window.select(ripple.id)
        window.stitch_type.setCurrentIndex(window.stitch_type.findData('ripple'))
        before=window.project.dumps()
        window.fields['ripple_center_x'].setValue(-60)
        changed=window.project.dumps()
        if window.project.objects[0].ripple_center_x!=-60 or changed==before:
            raise RuntimeError('Bundled ripple center control failed.')
        window.undo()
        if window.project.dumps()!=before:raise RuntimeError('Bundled ripple center Undo failed.')
        window.redo()
        if window.project.dumps()!=changed:raise RuntimeError('Bundled ripple center Redo failed.')
        ripple_blocks=generate(window.project)
        if not ripple_blocks or generate(Project.loads(changed))!=ripple_blocks:
            raise RuntimeError('Bundled ripple project reload changed stitches.')
        from .pattern_fill import RegionClip
        region=RegionClip(window.project.objects[0].rings())
        for a,b in zip(ripple_blocks[0].stitches,ripple_blocks[0].stitches[1:]):
            if b.command=='stitch':
                for t in (.1,.5,.9):
                    if not region.inside((a.x+t*(b.x-a.x),a.y+t*(b.y-a.y))):
                        raise RuntimeError('Bundled ripple stitches crossed the outline or cutout.')
        (root/'ripple.morale').write_text(changed,encoding='utf-8')
        for extension in ('pes','exp'):
            path=root/f'ripple.{extension}'
            export_machine(window.project,path,ripple_blocks)
            verification=verify_export(ripple_blocks,path)
            if not verification['complete_path_comparison'] or verification['bounds_delta_mm']>.3 or verification['problems']:
                raise RuntimeError(f'Bundled ripple {extension} export failed: {verification}')
        window.canvas.set_design(window.project,ripple_blocks);app.processEvents()
        if not window.grab().save(str(root/'ripple.png')):raise RuntimeError('Bundled ripple screenshot failed.')
        report['checks'].append('ripple_center_edit_cutout_exports_and_history')
        from .coupon_worker import export_coupon
        from PySide6.QtCore import QTimer
        ticks=[];heartbeat=QTimer();heartbeat.timeout.connect(lambda:ticks.append(1));heartbeat.start(10)
        pack_root=root/'ripple-sewout-pack'
        try:pack_report=export_coupon('ripple-spacing',pack_root,window)
        finally:heartbeat.stop()
        if not ticks or not pack_report or pack_report.get('physical_sewouts') is not False:
            raise RuntimeError('Bundled coupon worker did not complete with a responsive event loop.')
        if (pack_root/'INCOMPLETE.txt').exists():raise RuntimeError('Bundled coupon worker left an incomplete pack.')
        for filename in ('ripple-spacing.morale','placement.pdf','evaluation.pdf','metadata.json','evaluation.json','README.txt'):
            if not (pack_root/filename).is_file():raise RuntimeError(f'Bundled coupon pack omitted {filename}.')
        if not all(check.get('verified') for check in pack_report['export_verification'].values()):
            raise RuntimeError('Bundled ripple coupon exports failed software verification.')
        report['checks'].append('responsive_sewout_pack_worker')
        from .fabric_dialog import FabricDialog
        from .fabric_presets import save_preset,load_preset
        fabric=FabricDialog(window)
        try:
            fabric.profile.setCurrentText('Stretch knit')
            fabric.fields['pull_compensation'].setValue(.35)
            settings=fabric.settings()
            save_preset(root/'custom.morale-fabric.json',settings)
            restored=load_preset(root/'custom.morale-fabric.json')
            if restored!=settings:raise RuntimeError('Bundled fabric preset round-trip failed.')
            fabric_object=DesignObject(kind='rectangle',width=20,height=20)
            window.replace_project(Project(objects=[fabric_object]));window.select(fabric_object.id)
            before=window.project.dumps()
            window.apply_fabric_settings(restored)
            after=window.project.dumps()
            if after==before or window.project.objects[0].pull_compensation!=.35:
                raise RuntimeError('Bundled fabric application did not update object settings.')
            if generate(Project.loads(after))!=generate(window.project):
                raise RuntimeError('Bundled fabric project round-trip changed stitches.')
            (root/'fabric.morale').write_text(after,encoding='utf-8')
            window.undo()
            if window.project.dumps()!=before:raise RuntimeError('Bundled fabric Undo failed.')
            window.redo()
            if window.project.dumps()!=after:raise RuntimeError('Bundled fabric Redo failed.')
        finally:fabric.close()
        report['checks'].append('fabric_preset_application_and_undo')
        fabric_source=root/'fabric-art.svg'
        fabric_source.write_text('<svg width="60" height="40"><rect x="5" y="5" width="20" height="25" fill="red"/><rect x="40" y="5" width="3" height="25" fill="blue"/></svg>')
        fabric_trace=TraceDialog(str(fabric_source),window)
        try:
            fabric_trace.width.setValue(60)
            fabric_trace.apply_fabric_preset(restored)
            fabric_trace.runner.load=lambda _:None
            fabric_trace.generate()
            worker('--trace-worker',fabric_source,root/'fabric-conversion',fabric_trace.runner.options)
            converted=Project.loads(json.loads((root/'fabric-conversion/preview.json').read_text())['project'])
            if {obj.stitch_type for obj in converted.objects}!={'fill','satin'}:
                raise RuntimeError('Bundled fabric conversion lost fill/satin selection.')
            for obj in converted.objects:
                expected='edge_sparse' if obj.stitch_type=='fill' else 'center_zigzag'
                if obj.spacing!=restored['spacing'] or obj.pull_compensation!=.35 or not obj.underlay or obj.underlay_style!=expected:
                    raise RuntimeError('Bundled fabric conversion lost stitch settings.')
        finally:fabric_trace.close()
        report['checks'].append('fabric_preset_artwork_conversion')
        window.saved=window.project.dumps()
        window.load_fabric_sample()
        if window.project.name!='Morale coupon: Fabric profile comparison' or len(window.project.objects)!=9:
            raise RuntimeError('Bundled native fabric coupon loading failed.')
        coupon_blocks=generate(window.project)
        if not coupon_blocks or window.project.hoop_width!=100 or window.project.hoop_height!=100:
            raise RuntimeError('Bundled fabric coupon geometry is invalid.')
        (root/'fabric-coupon.morale').write_text(window.project.dumps(),encoding='utf-8')
        report['checks'].append('native_sewout_coupon_loading')
        from .coupons import build_project as coupon_project,evaluation_pdf
        _,coupon_tests,coupon_title,coupon_guidance=coupon_project('fabric-profiles')
        evaluation_pdf(root/'fabric-evaluation.pdf',coupon_title,coupon_tests,coupon_guidance)
        evaluation_bytes=(root/'fabric-evaluation.pdf').read_bytes()
        if not evaluation_bytes.startswith(b'%PDF-') or b'%%EOF' not in evaluation_bytes[-1024:]:
            raise RuntimeError('Bundled sewout evaluation PDF is incomplete.')
        report['checks'].append('sewout_evaluation_pdf')
        from .coupons import project_evaluation_pdf
        project_evaluation_pdf(window.project,root/'current-design-worksheet.pdf')
        worksheet=(root/'current-design-worksheet.pdf').read_bytes()
        if not worksheet.startswith(b'%PDF-') or b'%%EOF' not in worksheet[-1024:]:
            raise RuntimeError('Bundled current-design worksheet is incomplete.')
        report['checks'].append('current_design_sewout_worksheet')
        dash_source=root/'dashes.svg'
        dash_source.write_text('<svg width="40" height="40"><path d="M4 20 H36" fill="none" stroke="red" stroke-width="2" stroke-dasharray=".5 .5" pathLength="4"/><path d="M4 30 H36" fill="none" stroke="blue" stroke-width="2" stroke-dasharray="0 8" stroke-linecap="round"/></svg>')
        worker('--trace-worker',dash_source,root/'dashes',dict(width=40,expand_strokes=True,stitch_mode='fill'))
        dash_info=json.loads((root/'dashes/preview.json').read_text())
        dash_project=Project.loads(dash_info['project'])
        from .auto_digitize import outline_path
        dash_shape=outline_path([ring for obj in dash_project.objects for ring in obj.rings()])
        if not dash_shape.contains(QPointF(-15,0)) or dash_shape.contains(QPointF(-10,0)) or not dash_shape.contains(QPointF(-16,10)):
            raise RuntimeError('Bundled dashed SVG lost a dash, gap or round dot.')
        report['checks'].append('dashed_svg_conversion')
        (root/'clipped.svg').write_text('<svg width="100" height="100"><defs><clipPath id="c" clipPathUnits="objectBoundingBox"><path clip-rule="evenodd" d="M0 0H1V1H0Z M.25 .25H.75V.75H.25Z"/></clipPath></defs><rect x="20" y="20" width="60" height="60" fill="red" clip-path="url(#c)"/></svg>')
        worker('--trace-worker',root/'clipped.svg',root/'clipped',{'width':100,'stitch_mode':'fill'})
        clipped_info=json.loads((root/'clipped/preview.json').read_text())
        clipped_project=Project.loads(clipped_info['project'])
        if len(clipped_project.objects)!=1 or len(clipped_project.objects[0].contours)!=2:
            raise RuntimeError('Bundled clipping lost its fill or cutout.')
        if abs(clipped_project.objects[0].width-60)>.01:
            raise RuntimeError('Bundled clipping changed the artwork size.')
        clipped_blocks=generate(clipped_project)
        if clipped_blocks!=generate(Project.loads(clipped_project.dumps())):
            raise RuntimeError('Clipped artwork changed after save/reopen.')
        if any(-14.99<s.x<14.99 and -14.99<s.y<14.99 for block in clipped_blocks for s in block.stitches if s.command=='stitch'):
            raise RuntimeError('Bundled clipping generated needle penetrations in the cutout.')
        (root/'clipped.morale').write_text(clipped_project.dumps())
        report['checks'].append('clipped_svg_conversion_and_cutout')
        (root/'symbols.svg').write_text('<svg width="100" height="100"><defs><symbol id="s" viewBox="0 0 10 10"><defs><clipPath id="half"><rect width="50%" height="100%"/></clipPath></defs><rect width="10" height="10" clip-path="url(#half)"/></symbol></defs><use href="#s" x="10" y="10" width="20" height="20" fill="red"/><use href="#s" x="50" y="50" width="40" height="40" fill="blue"/></svg>')
        worker('--trace-worker',root/'symbols.svg',root/'symbols',{'width':100,'stitch_mode':'fill'})
        symbol_info=json.loads((root/'symbols/preview.json').read_text())
        symbol_project=Project.loads(symbol_info['project'])
        if len(symbol_project.objects)!=2 or [o.color for o in symbol_project.objects]!=['#ff0000','#0000ff']:
            raise RuntimeError('Bundled symbols lost an instance or its paint.')
        if any(abs(obj.width-width)>.01 for obj,width in zip(symbol_project.objects,(10,20))):
            raise RuntimeError('Bundled symbol clipping changed instance sizes.')
        if generate(symbol_project)!=generate(Project.loads(symbol_project.dumps())):
            raise RuntimeError('Symbol stitches changed after save/reopen.')
        (root/'symbols.morale').write_text(symbol_project.dumps())
        report['checks'].append('svg_symbols_and_local_clips')
        (root/'gradient.svg').write_text('<svg width="100" height="100"><defs><linearGradient id="g"><stop stop-color="red"/><stop offset="1" stop-color="blue"/></linearGradient><clipPath id="c"><rect width="40" height="80"/></clipPath></defs><rect width="80" height="80" fill="url(#g)" clip-path="url(#c)"/></svg>')
        worker('--trace-worker',root/'gradient.svg',root/'gradient',dict(render_svg=True,width=100,colors=3,resolution=64,method='smooth',ignore_white=False,stitch_mode='fill'))
        gradient_info=json.loads((root/'gradient/preview.json').read_text())
        gradient_project=Project.loads(gradient_info['project'])
        if gradient_info['trace_stats'].get('source_kind')!='rendered_svg' or len(gradient_project.objects)<2:
            raise RuntimeError('Bundled gradient conversion lost its editable color regions.')
        gradient_blocks=generate(gradient_project)
        if not gradient_blocks or gradient_blocks!=generate(Project.loads(gradient_project.dumps())):
            raise RuntimeError('Gradient stitches changed after save/reopen.')
        if any(s.x>-8 for block in gradient_blocks for s in block.stitches if s.command=='stitch'):
            raise RuntimeError('Bundled gradient conversion stitched outside its clip.')
        (root/'gradient.morale').write_text(gradient_project.dumps())
        report['checks'].append('svg_gradient_color_conversion')
        (root/'masked.svg').write_text('<svg width="100" height="100"><defs><mask id="m" maskContentUnits="objectBoundingBox"><rect width=".5" height="1" fill="white"/></mask></defs><rect x="10" y="10" width="80" height="80" fill="red" mask="url(#m)"/></svg>')
        worker('--trace-worker',root/'masked.svg',root/'masked',dict(render_svg=True,width=100,colors=2,resolution=128,method='smooth',ignore_white=False,stitch_mode='fill'))
        masked_info=json.loads((root/'masked/preview.json').read_text())
        masked_project=Project.loads(masked_info['project'])
        if len(masked_project.objects)!=1 or abs(masked_project.objects[0].width-40)>.5:
            raise RuntimeError('Bundled SVG mask did not retain the visible half.')
        masked_blocks=generate(masked_project)
        if not masked_blocks or any(s.x>.5 for block in masked_blocks for s in block.stitches if s.command=='stitch'):
            raise RuntimeError('Bundled SVG mask stitched into the hidden half.')
        (root/'masked.morale').write_text(masked_project.dumps())
        report['checks'].append('svg_masked_color_conversion')
        (root/'styled.svg').write_text('<svg width="100" height="100"><style>.paint {fill:blue} #art {fill:red} #m rect {fill:white}</style><defs><mask id="m" maskContentUnits="objectBoundingBox"><rect width=".5" height="1"/></mask></defs><rect id="art" class="paint" x="10" y="10" width="80" height="80" mask="url(#m)"/></svg>')
        worker('--trace-worker',root/'styled.svg',root/'styled',dict(render_svg=True,width=100,colors=2,resolution=128,method='smooth',ignore_white=False,stitch_mode='fill'))
        styled_info=json.loads((root/'styled/preview.json').read_text())
        styled_project=Project.loads(styled_info['project'])
        if len(styled_project.objects)!=1 or styled_project.objects[0].color!='#ff0000' or abs(styled_project.objects[0].width-40)>.5:
            raise RuntimeError('Bundled SVG stylesheet lost selector precedence or mask styles.')
        (root/'styled.morale').write_text(styled_project.dumps())
        report['checks'].append('svg_stylesheet_conversion')

        variable_source=root/'variables.svg'
        variable_source.write_text('<svg width="100" height="50" style="--paint:red;--edge:blue"><path fill="var(--paint)" fill-rule="evenodd" d="M5 5H35V35H5Z M15 15H25V25H15Z"/><g style="--paint:var(--edge)"><rect fill="var(--missing,var(--paint))" x="65" y="5" width="30" height="30"/></g></svg>')
        for mode in ('direct','rendered'):
            output=root/f'variables-{mode}'
            worker('--trace-worker',variable_source,output,dict(render_svg=mode=='rendered',width=100,
                colors=2,resolution=256,method='smooth',ignore_white=False,stitch_mode='fill'))
            variable_project=Project.loads(json.loads((output/'preview.json').read_text())['project'])
            objects=sorted(variable_project.objects,key=lambda obj:obj.x)
            if len(objects)!=2 or len(objects[0].rings())!=2:
                raise RuntimeError('Bundled variable artwork lost a region or cutout.')
            for obj,expected in zip(objects,((255,0,0),(0,0,255))):
                if any(abs(a-b)>(12 if mode=='rendered' else 0) for a,b in zip(QColor(obj.color).getRgb()[:3],expected)):
                    raise RuntimeError('Bundled variable artwork changed its palette.')
            variable_blocks=generate(variable_project)
            snapshot=variable_project.dumps()
            if generate(Project.loads(snapshot))!=variable_blocks:raise RuntimeError('Bundled variable project reload changed stitches.')
            (root/f'variables-{mode}.morale').write_text(snapshot)
            for extension in ('pes','exp'):
                path=root/f'variables-{mode}.{extension}'
                export_machine(variable_project,path,variable_blocks)
                check=verify_export(variable_blocks,path)
                if not check['complete_path_comparison'] or check['bounds_delta_mm']>.3 or check['problems']:
                    raise RuntimeError(f'Bundled variable artwork export failed: {check}')
        report['checks'].append('svg_variable_paints_conversion_and_exports')

        (root/'modern-colors.svg').write_text('<svg width="100" height="50"><rect width="40" height="40" style="fill:rgb(255 0 0) ! /* priority */ important;fill:blue"/><rect x="60" width="40" height="40" fill="hsl(240 100% 50%)"/></svg>')
        worker('--trace-worker',root/'modern-colors.svg',root/'modern-colors',dict(render_svg=True,width=100,colors=2,resolution=256,method='smooth',ignore_white=False,stitch_mode='fill'))
        modern_info=json.loads((root/'modern-colors/preview.json').read_text())
        modern_project=Project.loads(modern_info['project'])
        modern_objects=sorted(modern_project.objects,key=lambda obj:obj.x)
        if len(modern_objects)!=2:
            raise RuntimeError('Bundled modern SVG color conversion lost regions.')
        for obj,expected in zip(modern_objects,((255,0,0),(0,0,255))):
            if any(abs(a-b)>2 for a,b in zip(QColor(obj.color).getRgb()[:3],expected)) or abs(obj.width-40)>.5:
                raise RuntimeError('Bundled modern SVG color conversion changed colors or dimensions.')
        (root/'modern-colors.morale').write_text(modern_project.dumps())
        report['checks'].append('svg_modern_color_conversion')
        from .svg_render import render_svg_artwork
        gradient_pixels,_=render_svg_artwork('<svg width="100" height="100"><defs color="red"><linearGradient id="hard"><stop stop-color="currentColor"/><stop offset=".5" stop-color="currentColor"/><stop offset=".5" stop-color="blue"/><stop offset="1" stop-color="blue"/></linearGradient><linearGradient id="fade"><stop stop-color="red" stop-opacity="0"/><stop offset="1" stop-color="blue"/></linearGradient></defs><rect width="100" height="40" fill="url(#hard)"/><rect y="60" width="100" height="40" fill="url(#fade)"/></svg>',resolution=100)
        if gradient_pixels.pixelColor(20,20).getRgb()!=(255,0,0,255) or gradient_pixels.pixelColor(80,20).getRgb()!=(0,0,255,255):
            raise RuntimeError('Bundled gradient styles or hard transitions changed.')
        red,green,blue,alpha=gradient_pixels.pixelColor(50,80).getRgb()
        if not (124<=red<=130 and green==0 and 125<=blue<=132 and 126<=alpha<=132):
            raise RuntimeError('Bundled transparent gradient color interpolation changed.')
        if not gradient_pixels.save(str(root/'gradient-rendering.png')):
            raise RuntimeError('Could not save gradient rendering evidence.')
        report['checks'].append('svg_gradient_styles_and_interpolation')
        order_source=root/'paint-order.svg'
        order_source.write_text('<svg width="40" height="40"><rect x="10" y="10" width="20" height="20" fill="red" stroke="blue" stroke-width="4" paint-order="stroke"/></svg>')
        worker('--trace-worker',order_source,root/'paint-order',dict(width=40,expand_strokes=True,stitch_mode='fill',remove_overlap=True,overlap_allowance=0))
        order_info=json.loads((root/'paint-order/preview.json').read_text())
        order_project=Project.loads(order_info['project'])
        if [o.color for o in order_project.objects]!=['#0000ff','#ff0000']:
            raise RuntimeError('Bundled SVG paint order changed.')
        if outline_path(order_project.objects[0].rings()).contains(QPointF(-9,0)):
            raise RuntimeError('Bundled overlap removal retained covered border material.')
        before=window.project.dumps();window.apply_raster_trace(order_project);window.undo()
        if window.project.dumps()!=before:raise RuntimeError('Paint-order artwork insertion Undo failed.')
        report['checks'].append('svg_paint_order_and_undo')
        from .trace_routing import reduce_travel
        ring=DesignObject(kind='compound',width=40,height=40,stitch_type='running',underlay=False,
            contours=[[[-.5,-.5],[.5,-.5],[.5,.5],[-.5,.5]],[[-.3,-.3],[.3,-.3],[.3,.3],[-.3,.3]]])
        island=DesignObject(kind='rectangle',width=2,height=2,underlay=False)
        route_source=Project(objects=[ring,island]);routed,route_stats=reduce_travel(route_source)
        if route_stats['order']!=[1,0] or route_stats['after_mm']>=route_stats['before_mm']:
            raise RuntimeError('Routing did not recognize the independent island inside a hole.')
        if {b.object_id:b for b in generate(route_source)}!={b.object_id:b for b in generate(routed)}:
            raise RuntimeError('Routing changed sewn blocks.')
        report['checks'].append('routing_inside_holes')
        hole_source=root/'small-hole.svg'
        hole_source.write_text('<svg width="10" height="10"><path fill-rule="evenodd" d="M0 0 H10 V10 H0Z M4 4 H6 V6 H4Z M1 1 H2 V2 H1Z"/><rect x="1" y="1" width="1" height="1" fill="red"/></svg>')
        worker('--trace-worker',hole_source,root/'small-hole',dict(width=10,minimum_hole_area=5,stitch_mode='fill'))
        hole_info=json.loads((root/'small-hole/preview.json').read_text())
        if hole_info['trace_stats']['quality']['hole_filter']['filled_holes']!=1 or hole_info['trace_stats']['quality']['hole_filter']['occupied_holes_retained']!=1:
            raise RuntimeError('Bundled hole filling did not report its geometry change.')
        hole_project=Project.loads(hole_info['project'])
        if not outline_path(hole_project.objects[0].rings()).contains(QPointF(0,0)):
            raise RuntimeError('Bundled small hole was not filled.')
        before=window.project.dumps();window.apply_raster_trace(hole_project);window.undo()
        if window.project.dumps()!=before:raise RuntimeError('Hole-filter insertion Undo failed.')
        report['checks'].append('small_hole_filter_and_undo')
        from .library_catalog import CatalogDialog,save_catalog
        catalog=CatalogDialog([root/'saved.morale',root/'raster/trace.morale',root/'svg/trace.morale'],window)
        try:
            catalog.show();deadline=time.monotonic()+20
            while not catalog.save.isEnabled() and time.monotonic()<deadline:
                app.processEvents();time.sleep(.01)
            if not catalog.save.isEnabled() or any('error' in entry for entry in catalog.entries):
                raise RuntimeError('Bundled catalog previews did not complete.')
            save_catalog(root/'design-catalog.pdf',catalog.entries)
            if not (root/'design-catalog.pdf').read_bytes().startswith(b'%PDF-'):
                raise RuntimeError('Bundled catalog PDF is missing.')
        finally:catalog.reject()
        report['checks'].append('library_catalog_pdf')
        from .thread_palette_files import write_palette,read_palette
        from .catalogs import ThreadEntry
        palette_path=root/'red.edr';write_palette(palette_path,[ThreadEntry('#ff0000',{})])
        inf_path=root/'red.inf';write_palette(inf_path,[ThreadEntry('#ff0000',{'description':'Rougé','chart':'Chart α'})])
        if read_palette(inf_path)[0].metadata.get('chart')!='Chart α':raise RuntimeError('Bundled INF Unicode palette export changed metadata.')
        worker('--trace-worker',root/'source.svg',root/'palette-conversion',dict(width=40,expand_strokes=True,thread_catalog=str(palette_path),stitch_mode='auto'))
        palette_info=json.loads((root/'palette-conversion/preview.json').read_text())
        palette_project=Project.loads(palette_info['project'])
        if not palette_project.objects or any(o.color!='#ff0000' for o in palette_project.objects):
            raise RuntimeError('Bundled EDR palette was not used for artwork matching.')
        report['checks'].append('external_thread_palette_matching')
        from .catalogs import builtin_catalog
        window.replace_project(Project(objects=[DesignObject(color='#cc8833')]))
        window.select(window.project.objects[0].id);before=window.project.dumps()
        from .catalog_dialog import CatalogDialog as ThreadCatalogDialog
        matches=ThreadCatalogDialog('#cc8833',1,window,colors=['#cc8833'])
        try:
            matches.tabs.setCurrentIndex(1);matches.show();deadline=time.monotonic()+5
            while matches.match_timer.isActive() and time.monotonic()<deadline:app.processEvents()
            if not matches.match_model.rows or matches.match_model.rows[0][2].color!='#ba9800':
                raise RuntimeError('Bundled thread-match preview used the wrong proposal.')
            if not matches.grab().save(str(root/'thread-matches.png')):raise RuntimeError('Thread-match preview screenshot failed.')
        finally:matches.reject()
        window.apply_catalog_threads(builtin_catalog('PEC fixed palette'),True,'oklab')
        if window.project.objects[0].color!='#ba9800':raise RuntimeError('Native perceptual thread assignment used the wrong metric.')
        window.undo()
        if window.project.dumps()!=before:raise RuntimeError('Perceptual thread assignment Undo failed.')
        report['checks'].append('perceptual_thread_assignment_and_undo')
        boundary=Project(objects=[
            DesignObject(kind='stitches',stitch_type='manual',width=10,height=10,color='#ff0000',
                stitch_data=[[0,0,'jump'],[.2,0,'stitch']]),
            DesignObject(kind='stitches',stitch_type='manual',width=10,height=10,color='#0000ff',
                stitch_data=[[.2,0,'jump'],[.2,0,'trim'],[.3,0,'jump'],[.4,0,'stitch']])])
        boundary_blocks=generate(boundary);boundary_reports={}
        boundary_root=root/'boundary-trims';boundary_root.mkdir()
        for extension in sorted(EXPORT_FORMATS):
            path=boundary_root/('controls'+extension)
            export_machine(boundary,path,boundary_blocks)
            checked=verify_export(boundary_blocks,path);boundary_reports[extension]=checked
            if not checked['complete_path_comparison'] or checked['source_stitches']!=checked['decoded_stitches']:
                raise RuntimeError(f'Bundled {extension} boundary fixture changed stitching.')
            if extension=='.vp3':
                if checked['controls']['trim']!={'source':1,'decoded':2} or not checked['problems'] or any('Trim commands increased' not in p for p in checked['problems']):
                    raise RuntimeError('Bundled VP3 boundary-trim behavior changed; review controls.')
            elif extension=='.tbf':
                if checked['thread_control_order_matches'] is not False or checked['verified']:
                    raise RuntimeError('Bundled TBF control-order mismatch was not reported.')
            elif not checked['verified'] or checked['thread_control_order_matches'] is not True:
                raise RuntimeError(f'Bundled {extension} did not retain thread-relative trim order.')
        (boundary_root/'verification.json').write_text(json.dumps(boundary_reports,indent=2),encoding='utf-8')
        report['checks'].append('explicit_boundary_trim_exports_and_order_review')
        exports=root/'exports';exports.mkdir()
        for extension in sorted(EXPORT_FORMATS):
            path=exports/('sample'+extension);export_machine(candidate,path)
            if not any(s.command=='stitch' for b in generate(import_machine(path).project) for s in b.stitches):
                raise RuntimeError(f'{extension} decoded no sewn stitches.')
            report['checks'].append('export_reopen_'+extension)
        # Opening a design decodes it in the packaged open worker.
        worker('--open-worker',exports/'sample.pes',root/'open')
        from .open_worker import read_open_result
        opened,_=read_open_result(root/'open',exports/'sample.pes')
        if not any(s.command=='stitch' for b in generate(opened) for s in b.stitches):raise RuntimeError('Open worker decoded no sewn stitches.')
        report['checks'].append('open_worker')
        report['passed']=True
    except Exception as exc:
        report['error']=str(exc)
    finally:
        if window is not None:
            window.saved=window.project.dumps();window.close();app.processEvents()
        (root/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return 0 if report['passed'] else 1


def worker_main(args):
    if len(args)!=1:return 2
    try:return run(args[0])
    except (OSError,ValueError):return 2
