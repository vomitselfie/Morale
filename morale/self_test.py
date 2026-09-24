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
        exports=root/'exports';exports.mkdir()
        for extension in sorted(EXPORT_FORMATS):
            path=exports/('sample'+extension);export_machine(candidate,path)
            if not any(s.command=='stitch' for b in generate(import_machine(path).project) for s in b.stitches):
                raise RuntimeError(f'{extension} decoded no sewn stitches.')
            report['checks'].append('export_reopen_'+extension)
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
