import json
import pytest
from PySide6.QtWidgets import QApplication
from morale.model import Project,DesignObject
from morale.engine import generate
from morale.trace_stitch_settings import apply_stitch_settings


@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])


def test_spacing_changes_sewing_without_changing_artwork():
    source=Project(objects=[DesignObject(kind='rectangle',width=20,height=20,underlay=False)])
    snapshot=source.dumps()
    result,report=apply_stitch_settings(source,{'fill_spacing':1,'stitch_length':4})
    assert source.dumps()==snapshot and result.objects[0].rings()==source.objects[0].rings()
    assert result.objects[0].id==source.objects[0].id and report['changed_objects']==1
    assert sum(len(b.stitches) for b in generate(result))<sum(len(b.stitches) for b in generate(source))
    assert Project.loads(result.dumps()).objects==result.objects


def test_type_specific_settings_and_underlay():
    from morale.auto_digitize import choose_stitches
    satin,_=choose_stitches(Project(objects=[DesignObject(kind='rectangle',width=3,height=20)]))
    assert satin.objects[0].stitch_type=='satin'
    running=DesignObject(stitch_type='running',underlay=False)
    source=Project(objects=[*satin.objects,running])
    result,_=apply_stitch_settings(source,{'fill_spacing':1,'satin_spacing':.6,'underlay':'auto','pull_compensation':.2})
    assert result.objects[0].spacing==.6 and result.objects[0].underlay
    assert result.objects[0].pull_compensation==.2
    assert result.objects[1]==running
    disabled,_=apply_stitch_settings(result,{'underlay':'off'})
    assert not any(o.underlay for o in disabled.objects)
    assert generate(disabled)


@pytest.mark.parametrize('settings',[None,[],{'unknown':1},{'fill_spacing':True},{'satin_spacing':.1},
    {'stitch_length':float('nan')},{'pull_compensation':float('inf')},{'underlay':True},{'underlay':'edge'}])
def test_invalid_settings_are_rejected(settings):
    with pytest.raises(ValueError):apply_stitch_settings(Project(),settings)


@pytest.mark.parametrize('fill_underlay',['off','edge_sparse'])
def test_worker_native_preview_and_undo(tmp_path,fill_underlay):
    from morale.raster_trace import worker_main
    from morale.trace_dialog import TraceDialog
    from morale.app import MainWindow
    from morale.trace_quality import quality_text
    path=tmp_path/'fill.svg';path.write_text('<svg width="30" height="30"><rect x="5" y="5" width="20" height="20" fill="red"/></svg>')
    output=tmp_path/'out';output.mkdir()
    options=dict(width=30,stitch_settings={'fill_spacing':.9,'underlay':'off','fill_underlay':fill_underlay,'underlay_inset':.4,'underlay_spacing':1.5,'pull_compensation':.2},optimize_fill_angles=True)
    assert worker_main([str(path),str(output),json.dumps(options)])==0
    info=json.loads((output/'preview.json').read_text());result=Project.loads(info['project']);obj=result.objects[0]
    assert obj.spacing==.9 and obj.underlay==(fill_underlay!='off') and obj.pull_compensation==.2
    assert obj.underlay_inset==.4 and obj.underlay_spacing==1.5
    if obj.underlay:assert obj.underlay_style==fill_underlay
    assert 'Custom stitch settings: 1 objects changed' in quality_text(info['trace_stats']['quality'])
    assert info['trace_stats']['quality']['density']['penetrations']==sum(s.command=='stitch' for b in generate(result) for s in b.stitches)
    dialog=TraceDialog(str(path));window=MainWindow()
    try:
        assert not dialog.custom_stitches.isChecked()
        dialog.overrides={'0':'fill'};dialog.custom_stitches.setChecked(True)
        dialog.stitch_settings['fill_spacing'].setValue(.9)
        assert dialog.overrides=={'0':'fill'} and dialog.project is None
        dialog.runner.load=lambda path:None
        dialog.generate();assert dialog.runner.options['stitch_settings']['fill_spacing']==.9
        before=window.project.dumps();window.apply_raster_trace(result);window.undo()
        assert window.project.dumps()==before
        dialog.custom_stitches.setChecked(False);dialog.generate()
        assert 'stitch_settings' not in dialog.runner.options
    finally:dialog.close();window.saved=window.project.dumps();window.close()


def test_mixed_underlay_supports_preserve_artwork_and_use_engine_geometry():
    from morale.auto_digitize import choose_stitches
    from morale.engine import generate_underlay
    satin,_=choose_stitches(Project(objects=[DesignObject(kind='rectangle',width=3,height=20)]))
    fill=DesignObject(kind='rectangle',width=20,height=20)
    running=DesignObject(stitch_type='running',underlay=False)
    source=Project(objects=[fill,*satin.objects,running]);snapshot=source.dumps()
    result,_=apply_stitch_settings(source,{'underlay':'off','fill_underlay':'edge_sparse',
        'satin_underlay':'center_zigzag','underlay_inset':.4,'underlay_spacing':1.5})
    assert source.dumps()==snapshot and result.objects[-1]==running
    for original,converted,style in zip(source.objects,result.objects,['edge_sparse','center_zigzag']):
        assert converted.rings()==original.rings() and converted.id==original.id
        assert converted.underlay and converted.underlay_style==style
        assert converted.underlay_inset==.4 and converted.underlay_spacing==1.5
        assert generate_underlay(converted)!=generate_underlay(original)
    assert generate(result)
    assert Project.loads(result.dumps()).objects==result.objects


@pytest.mark.parametrize('settings',[{'fill_underlay':'zigzag'},{'satin_underlay':'edge'},
    {'underlay_inset':3.1},{'underlay_spacing':0},{'underlay_inset':True}])
def test_invalid_type_specific_underlay_rejected(settings):
    with pytest.raises(ValueError):apply_stitch_settings(Project(),settings)


def test_region_spacing_overrides_global_without_source_changes():
    from morale.trace_stitch_settings import apply_region_spacing
    source=Project(objects=[DesignObject(width=20,height=20),DesignObject(width=20,height=20)])
    global_project,_=apply_stitch_settings(source,{'fill_spacing':.6})
    snapshot=global_project.dumps();result=apply_region_spacing(global_project,{'1':1.2})
    assert [o.spacing for o in result.objects]==[.6,1.2]
    assert global_project.dumps()==snapshot
    assert len(generate(result)[1].stitches)<len(generate(global_project)[1].stitches)


@pytest.mark.parametrize('values',[{'2':.5},{'01':.5},{'0':True},{'0':.1},{'0':float('nan')},[]])
def test_invalid_region_spacing_is_rejected(values):
    from morale.trace_stitch_settings import apply_region_spacing
    with pytest.raises(ValueError):apply_region_spacing(Project(objects=[DesignObject()]),values)


def test_region_spacing_worker_and_native_invalidation(tmp_path):
    from PySide6.QtGui import QImage
    from morale.raster_trace import worker_main
    from morale.trace_dialog import TraceDialog
    path=tmp_path/'region.svg';path.write_text('<svg width="40" height="40"><rect x="5" y="5" width="30" height="30" fill="red"/></svg>')
    output=tmp_path/'preview';output.mkdir()
    options={'width':40,'stitch_mode':'fill','stitch_settings':{'fill_spacing':.5},'region_spacing':{'0':.9},'reduce_travel':True}
    assert worker_main([str(path),str(output),json.dumps(options)])==0
    info=json.loads((output/'preview.json').read_text())
    project=Project.loads(info['project']);assert project.objects[0].spacing==.9
    dialog=TraceDialog(str(path))
    try:
        dialog.ready(str(path),info,QImage(str(output/'preview.png')))
        control=dialog.decisions.cellWidget(0,5);assert control.value()==.9
        control.setValue(1.1)
        assert dialog.project is None and dialog.region_spacing=={'0':1.1}
        dialog.runner.load=lambda _:None;dialog.generate()
        assert dialog.runner.options['region_spacing']=={'0':1.1}
        dialog.invalidate();assert dialog.region_spacing=={}
    finally:dialog.close()


def test_region_spacing_follows_artwork_through_reordering(tmp_path):
    from morale.raster_trace import worker_main
    path=tmp_path/'ordered.svg'
    path.write_text('<svg width="100" height="40"><rect id="far" x="5" y="10" width="20" height="20" fill="red"/><rect id="near" x="45" y="10" width="20" height="20" fill="red"/></svg>')
    output=tmp_path/'routed';output.mkdir()
    options={'width':100,'stitch_mode':'fill','region_spacing':{'0':1.2,'1':.4},'reduce_travel':True}
    assert worker_main([str(path),str(output),json.dumps(options)])==0
    info=json.loads((output/'preview.json').read_text());project=Project.loads(info['project'])
    stats=info['trace_stats'];order=stats['sewing_order']
    assert order!=[0,1],stats.get('routing')
    for source_index,obj in zip(order,project.objects):
        assert obj.spacing==options['region_spacing'][str(source_index)]
        assert ('far' if source_index==0 else 'near') in obj.name
    assert [d['spacing_mm'] for d in stats['stitch_decisions']]==[1.2,.4]


def test_reset_region_spacing_retains_other_region_choices():
    from morale.trace_dialog import TraceDialog
    dialog=TraceDialog('art.svg')
    try:
        dialog.region_spacing={'0':.9};dialog.overrides={'0':'satin'};dialog.seams={'0':25}
        dialog.reset_region_spacing()
        assert dialog.region_spacing=={} and dialog.overrides=={'0':'satin'} and dialog.seams=={'0':25}
        assert dialog.project is None
    finally:dialog.close()


def test_region_angle_lock_survives_automatic_search_and_native_edit(tmp_path):
    from PySide6.QtGui import QImage
    from morale.raster_trace import worker_main
    from morale.trace_dialog import TraceDialog
    path=tmp_path/'angle.svg';path.write_text('<svg width="40" height="40"><rect x="5" y="5" width="30" height="20" fill="red"/></svg>')
    output=tmp_path/'angle';output.mkdir()
    options={'width':40,'stitch_mode':'fill','region_angles':{'0':17},'optimize_fill_angles':True}
    assert worker_main([str(path),str(output),json.dumps(options)])==0
    info=json.loads((output/'preview.json').read_text());project=Project.loads(info['project'])
    assert project.objects[0].angle==17
    assert not info['trace_stats']['fill_angles']['changes']
    dialog=TraceDialog(str(path))
    try:
        dialog.ready(str(path),info,QImage(str(output/'preview.png')))
        control=dialog.decisions.cellWidget(0,6);assert control.value()==17
        control.setValue(33)
        assert dialog.region_angles=={'0':33} and dialog.project is None
        dialog.runner.load=lambda _:None;dialog.generate()
        assert dialog.runner.options['region_angles']=={'0':33}
        dialog.region_spacing={'0':.9};dialog.reset_region_angles()
        assert dialog.region_angles=={} and dialog.region_spacing=={'0':.9}
    finally:dialog.close()


@pytest.mark.parametrize('values',[{'1':30},{'00':30},{'0':True},{'0':360},{'0':float('nan')},[]])
def test_invalid_region_angles_are_rejected(values):
    from morale.trace_stitch_settings import apply_region_angles
    with pytest.raises(ValueError):apply_region_angles(Project(objects=[DesignObject()]),values)


def test_reset_selected_region_keeps_neighbor_corrections_after_reordering(tmp_path):
    from PySide6.QtGui import QImage
    from PySide6.QtWidgets import QDialogButtonBox
    from morale.raster_trace import worker_main
    from morale.trace_dialog import TraceDialog
    path=tmp_path/'corrections.svg'
    path.write_text('<svg width="100" height="40"><rect id="far" x="5" y="10" width="20" height="20" fill="red"/><rect id="near" x="45" y="10" width="20" height="20" fill="red"/></svg>')
    output=tmp_path/'before';output.mkdir()
    options={'width':100,'stitch_mode':'fill','region_spacing':{'0':1.2,'1':.4},
             'region_angles':{'0':17,'1':90},'reduce_travel':True}
    assert worker_main([str(path),str(output),json.dumps(options)])==0
    info=json.loads((output/'preview.json').read_text())
    assert info['trace_stats']['sewing_order']==[1,0]
    dialog=TraceDialog(str(path))
    try:
        assert not dialog.reset_selected_region.isEnabled()
        dialog.region_spacing=dict(options['region_spacing']);dialog.region_angles=dict(options['region_angles'])
        dialog.overrides={'0':'fill','1':'fill'};dialog.seams={'0':25,'1':50}
        dialog.ready(str(path),info,QImage(str(output/'preview.png')))
        dialog.decisions.setCurrentCell(0,0)
        dialog.reset_selected_region.click()
        assert dialog.overrides=={'1':'fill'} and dialog.seams=={'1':50}
        assert dialog.region_spacing=={'1':.4} and dialog.region_angles=={'1':90}
        assert dialog.project is None and dialog.review_snapshot is None
        assert not dialog.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled()
        assert dialog.decisions.item(0,2).text()=='Pending'
        assert dialog.decisions.cellWidget(0,6) is None
        assert dialog.decisions.cellWidget(1,6).value()==90
        dialog.runner.load=lambda _:None;dialog.generate()
        assert dialog.runner.options['region_angles']=={'1':90}
        options.update(region_angles=dialog.runner.options['region_angles'],
                       region_spacing=dialog.runner.options['region_spacing'])
        after=tmp_path/'after';after.mkdir()
        assert worker_main([str(path),str(after),json.dumps(options)])==0
        decisions=json.loads((after/'preview.json').read_text())['trace_stats']['stitch_decisions']
        assert decisions[0]['angle_degrees']==45 and decisions[0]['spacing_mm']==.45
        assert decisions[1]['angle_degrees']==90 and decisions[1]['spacing_mm']==.4
        dialog.invalidate()
        assert not dialog.reset_selected_region.isEnabled()
    finally:dialog.close()


@pytest.mark.parametrize('column,label',[(1,'stitch type'),(5,'stitch spacing'),(6,'fill angle')])
def test_focused_region_control_selects_reset_target(tmp_path,column,label):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QImage
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTest import QTest
    from morale.raster_trace import worker_main
    from morale.trace_dialog import TraceDialog
    path=tmp_path/'focus.svg'
    path.write_text('<svg width="60" height="30"><rect x="2" y="2" width="20" height="20" fill="red"/><rect x="32" y="2" width="20" height="20" fill="blue"/></svg>')
    output=tmp_path/'preview';output.mkdir()
    assert worker_main([str(path),str(output),json.dumps({'width':60,'stitch_mode':'fill'})])==0
    info=json.loads((output/'preview.json').read_text())
    dialog=TraceDialog(str(path))
    try:
        dialog.ready(str(path),info,QImage(str(output/'preview.png')))
        dialog.region_spacing={'0':.8,'1':1.2};dialog.region_angles={'0':17,'1':33}
        dialog.tabs.setCurrentIndex(3);dialog.show();QApplication.processEvents()
        dialog.decisions.setCurrentCell(0,0)
        control=dialog.decisions.cellWidget(1,column)
        assert control.accessibleName()==f'Region 2 {label}'
        control.setFocus(Qt.FocusReason.TabFocusReason);QApplication.processEvents()
        assert dialog.decisions.currentRow()==1
        dialog.reset_selected_region.setFocus(Qt.FocusReason.TabFocusReason)
        QTest.keyClick(dialog.reset_selected_region,Qt.Key.Key_Space)
        assert dialog.region_spacing=={'0':.8} and dialog.region_angles=={'0':17}
        assert dialog.decisions.item(1,2).text()=='Pending'
        assert dialog.decisions.cellWidget(0,column) is not None
        assert dialog.project is None
    finally:dialog.close()


def test_preview_scrolls_on_short_screen_with_actions_visible():
    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QApplication,QDialogButtonBox
    from morale.trace_dialog import TraceDialog
    dialog=TraceDialog('art.svg')
    try:
        dialog.resize(1000,600);dialog.show();QApplication.processEvents()
        dialog.runner.load=lambda _:None;dialog.generate();QApplication.processEvents()
        assert dialog.tabs.currentWidget() is dialog.preview_scroll
        assert dialog.height()<=600
        assert dialog.preview_scroll.verticalScrollBar().maximum()>0
        for button in dialog.buttons.buttons():
            position=button.mapTo(dialog,QPoint(0,0))
            assert dialog.rect().contains(position)
            assert dialog.rect().contains(position+QPoint(button.width()-1,button.height()-1))
        dialog.preview_scroll.ensureWidgetVisible(dialog.review_button)
        QApplication.processEvents()
        center=dialog.review_button.mapTo(dialog.preview_scroll.viewport(),dialog.review_button.rect().center())
        assert dialog.preview_scroll.viewport().rect().contains(center)
        assert not dialog.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled()
    finally:dialog.close()


def test_fixed_svg_outline_ignores_fill_overrides_and_disables_controls(tmp_path):
    from PySide6.QtGui import QImage
    from morale.raster_trace import worker_main
    from morale.trace_dialog import TraceDialog
    path=tmp_path/'mixed.svg'
    path.write_text('<svg width="60" height="30"><path d="M2 4 L22 4 L22 24" fill="none" stroke="blue"/><rect x="32" y="4" width="20" height="20" fill="red"/></svg>')
    baseline=tmp_path/'baseline';baseline.mkdir()
    options={'width':60,'stitch_mode':'fill','expand_strokes':False}
    assert worker_main([str(path),str(baseline),json.dumps(options)])==0
    before=json.loads((baseline/'preview.json').read_text())
    decisions=before['trace_stats']['stitch_decisions']
    outline=next(d['region'] for d in decisions if d['fixed_stitch'])
    fill=next(d['region'] for d in decisions if not d['fixed_stitch'])
    options.update(region_spacing={str(outline):1.2,str(fill):.8},region_angles={str(outline):17,str(fill):33})
    output=tmp_path/'edited';output.mkdir()
    assert worker_main([str(path),str(output),json.dumps(options)])==0
    info=json.loads((output/'preview.json').read_text())
    original=Project.loads(before['project']);project=Project.loads(info['project'])
    assert generate(project)[outline].stitches==generate(original)[outline].stitches
    assert project.objects[fill].spacing==.8 and project.objects[fill].angle==33
    dialog=TraceDialog(str(path))
    try:
        dialog.ready(str(path),info,QImage(str(output/'preview.png')))
        for column in (1,5,6):assert not dialog.decisions.cellWidget(outline,column).isEnabled()
        for column in (1,5,6):assert dialog.decisions.cellWidget(fill,column).isEnabled()
        assert dialog.decisions.item(outline,2).text()=='Running'
    finally:dialog.close()


def test_changed_artwork_clears_native_corrections_and_rejects_stale_worker(tmp_path):
    from PySide6.QtGui import QImage
    from morale.raster_trace import worker_main
    from morale.trace_dialog import TraceDialog
    path=tmp_path/'changed.svg';path.write_text('<svg width="40" height="40"><rect width="20" height="20"/></svg>')
    output=tmp_path/'first';output.mkdir()
    assert worker_main([str(path),str(output),'{}'])==0
    info=json.loads((output/'preview.json').read_text())
    fingerprint=info['source_fingerprint']
    dialog=TraceDialog(str(path))
    try:
        dialog.ready(str(path),info,QImage(str(output/'preview.png')))
        dialog.region_angles={'0':17};dialog.region_spacing={'0':1.2}
        dialog.overrides={'0':'satin'};dialog.seams={'0':25}
        path.write_text('<svg width="40" height="40"><circle cx="20" cy="20" r="15" fill="red"/></svg>')
        stale=tmp_path/'stale';stale.mkdir()
        assert worker_main([str(path),str(stale),json.dumps({'expected_source':fingerprint,'region_angles':{'0':17}})])==1
        assert not (stale/'preview.json').exists()
        assert 'Artwork changed' in json.loads((stale/'preview.error.json').read_text())['error']
        dialog.runner.load=lambda _:None;dialog.generate()
        for key in ('region_angles','region_spacing','stitch_overrides','band_seams'):
            assert dialog.runner.options[key]=={}
        assert dialog.decisions.rowCount()==0 and dialog.project is None
    finally:dialog.close()


def test_source_content_change_with_same_size_and_timestamp_rejects_overrides(tmp_path):
    import os
    from PySide6.QtGui import QImage
    from morale.raster_trace import worker_main
    from morale.trace_dialog import TraceDialog
    source=tmp_path/'same.svg'
    source.write_text('<svg width="40" height="40"><rect width="20" height="20" fill="red"/></svg>')
    initial=source.stat();first=tmp_path/'first';first.mkdir()
    assert worker_main([str(source),str(first),'{}'])==0
    info=json.loads((first/'preview.json').read_text())
    source.write_text(source.read_text().replace('red','tan'))
    os.utime(source,ns=(initial.st_atime_ns,initial.st_mtime_ns))
    assert source.stat().st_size==initial.st_size
    dialog=TraceDialog(str(source))
    try:
        dialog.ready(str(source),info,QImage(str(first/'preview.png')))
        dialog.region_angles={'0':17};dialog.runner.load=lambda _:None;dialog.generate()
        assert dialog.runner.options['expected_source_digest']==info['source_digest']
        second=tmp_path/'second';second.mkdir()
        assert worker_main([str(source),str(second),json.dumps(dialog.runner.options)])==1
        error=json.loads((second/'preview.error.json').read_text())['error']
        dialog.failed(str(source),error)
        assert dialog.region_angles=={} and dialog.project is None and dialog.source_digest is None
    finally:dialog.close()


@pytest.mark.parametrize('preserve_metadata',[False,True])
def test_worker_rejects_artwork_changed_during_conversion(tmp_path,monkeypatch,preserve_metadata):
    import os
    import morale.inspection_geometry as inspection
    from morale.raster_trace import worker_main
    source=tmp_path/'midtrace.svg'
    source.write_text('<svg width="40" height="40"><rect width="20" height="20" fill="red"/></svg>')
    before=source.stat();original=inspection.inspection_layers
    def change_after_render(*args,**kwargs):
        result=original(*args,**kwargs)
        source.write_text(source.read_text().replace('red','tan'))
        if preserve_metadata:os.utime(source,ns=(before.st_atime_ns,before.st_mtime_ns))
        return result
    monkeypatch.setattr(inspection,'inspection_layers',change_after_render)
    output=tmp_path/'worker';output.mkdir()
    assert worker_main([str(source),str(output),'{}'])==1
    message=json.loads((output/'preview.error.json').read_text())['error']
    assert message.startswith('Artwork changed during tracing.')


@pytest.mark.parametrize('style',['edge','edge_sparse','sparse'])
def test_fabric_preset_native_conversion_generates_persistent_support(tmp_path,style):
    from morale.trace_dialog import TraceDialog
    from morale.raster_trace import worker_main
    from morale.fabric_presets import save_preset,load_preset
    from morale.formats import export_machine
    from morale.export_verify import verify_export
    source=tmp_path/'fabric-art.svg'
    source.write_text('<svg width="60" height="40"><rect x="5" y="5" width="20" height="25" fill="red"/><rect x="40" y="5" width="3" height="25" fill="blue"/></svg>')
    original=source.read_bytes()
    preset=tmp_path/'fabric.morale-fabric.json'
    save_preset(preset,dict(spacing=.65,pull_compensation=.25,underlay_inset=.4,underlay_spacing=1.8,underlay_style=style))
    dialog=TraceDialog(str(source))
    try:
        dialog.width.setValue(60)
        dialog.apply_fabric_preset(load_preset(preset))
        dialog.runner.load=lambda _:None
        dialog.generate()
        output=tmp_path/'converted';output.mkdir()
        assert worker_main([str(source),str(output),json.dumps(dialog.runner.options)])==0
        assert source.read_bytes()==original
        info=json.loads((output/'preview.json').read_text())
        project=Project.loads(info['project'])
        assert {obj.stitch_type for obj in project.objects}=={'fill','satin'}
        for obj in project.objects:
            assert obj.spacing==.65 and obj.pull_compensation==.25
            assert obj.underlay and obj.underlay_inset==.4 and obj.underlay_spacing==1.8
            expected=style if obj.stitch_type=='fill' else 'auto' if style=='edge' else 'center_zigzag'
            assert obj.underlay_style==expected
        blocks=generate(project)
        assert blocks==generate(Project.loads(project.dumps()))
        for extension in ('pes','exp'):
            target=tmp_path/f'fabric.{extension}'
            export_machine(project,target,blocks)
            report=verify_export(blocks,target)
            assert report['complete_path_comparison'] and report['bounds_delta_mm']<=.3
            assert not report['problems'],report
    finally:dialog.close()


def test_region_corrections_survive_fabric_load_through_worker(tmp_path):
    from morale.trace_dialog import TraceDialog
    from morale.raster_trace import worker_main
    path=tmp_path/'corrected.svg'
    path.write_text('<svg width="60" height="40"><rect x="5" y="5" width="20" height="25" fill="red"/><rect x="35" y="5" width="20" height="25" fill="blue"/></svg>')
    dialog=TraceDialog(str(path))
    try:
        dialog.width.setValue(60)
        dialog.overrides={'0':'fill','1':'fill'}
        dialog.region_spacing={'0':.9};dialog.region_angles={'0':17}
        dialog.apply_fabric_preset(dict(spacing=.6,pull_compensation=.2,underlay_inset=.5,underlay_spacing=2,underlay_style='edge_sparse'))
        dialog.runner.load=lambda _:None;dialog.generate()
        output=tmp_path/'worker';output.mkdir()
        assert worker_main([str(path),str(output),json.dumps(dialog.runner.options)])==0
        info=json.loads((output/'preview.json').read_text())
        project=Project.loads(info['project'])
        assert len(project.objects)==2
        assert [obj.spacing for obj in project.objects]==[.9,.6]
        assert project.objects[0].angle==17
        assert all(obj.underlay_style=='edge_sparse' and obj.pull_compensation==.2 for obj in project.objects)
        assert info['trace_stats']['stitch_decisions'][0]['spacing_mm']==.9
        assert generate(Project.loads(project.dumps()))==generate(project)
    finally:dialog.close()


def test_region_explanation_refreshes_and_does_not_revive_stale_results(tmp_path):
    from copy import deepcopy
    from PySide6.QtGui import QImage
    from morale.raster_trace import worker_main
    from morale.trace_dialog import TraceDialog
    path=tmp_path/'explanation.svg'
    path.write_text('<svg width="40" height="40"><rect width="20" height="20" fill="red"/></svg>')
    output=tmp_path/'result';output.mkdir()
    assert worker_main([str(path),str(output),json.dumps({'width':40,'stitch_mode':'fill'})])==0
    info=json.loads((output/'preview.json').read_text());image=QImage(str(output/'preview.png'))
    dialog=TraceDialog(str(path))
    try:
        dialog.ready(str(path),info,image);dialog.decisions.setCurrentCell(0,0)
        assert dialog.region_reason.text()==dialog.decisions.item(0,3).text()
        updated=deepcopy(info)
        updated['trace_stats']['stitch_decisions'][0]['reason']='Updated decision after regeneration.'
        dialog.ready(str(path),updated,image)
        assert dialog.region_reason.text()=='Updated decision after regeneration.'
        dialog.invalidate_preview()
        dialog.decisions.setCurrentCell(0,2)
        assert dialog.region_reason.text().startswith('Generate a new preview')
        assert dialog.project is None
    finally:dialog.close()


def test_underlay_off_fabric_preset_removes_generated_support(tmp_path):
    from morale.trace_dialog import TraceDialog
    from morale.raster_trace import worker_main
    from morale.engine import generate_underlay
    path=tmp_path/'support.svg'
    path.write_text('<svg width="60" height="40"><rect x="5" y="5" width="20" height="25" fill="red"/><rect x="40" y="5" width="3" height="25" fill="blue"/></svg>')
    dialog=TraceDialog(str(path));projects=[]
    try:
        dialog.width.setValue(60);dialog.runner.load=lambda _:None
        for enabled in (True,False):
            dialog.apply_fabric_preset(dict(spacing=.6,pull_compensation=.2,underlay_inset=.4,underlay_spacing=2,underlay_style='edge_sparse',underlay=enabled))
            dialog.generate();output=tmp_path/str(enabled);output.mkdir()
            assert worker_main([str(path),str(output),json.dumps(dialog.runner.options)])==0
            projects.append(Project.loads(json.loads((output/'preview.json').read_text())['project']))
        supported,bare=projects
        assert {obj.stitch_type for obj in bare.objects}=={'fill','satin'}
        for a,b in zip(supported.objects,bare.objects):
            assert a.rings()==b.rings() and a.spacing==b.spacing==.6
            assert a.pull_compensation==b.pull_compensation==.2
            assert a.underlay and not b.underlay
            assert generate_underlay(a) and not generate_underlay(b)
        assert sum(len(block.stitches) for block in generate(bare))<sum(len(block.stitches) for block in generate(supported))
        assert generate(Project.loads(bare.dumps()))==generate(bare)
    finally:dialog.close()


def test_lock_displayed_angle_without_changing_value_survives_search(tmp_path):
    from PySide6.QtGui import QImage
    from morale.raster_trace import worker_main
    from morale.trace_dialog import TraceDialog
    path=tmp_path/'angle.svg';path.write_text('<svg width="40" height="20"><rect width="40" height="20" fill="red"/></svg>')
    out=tmp_path/'initial';out.mkdir()
    assert worker_main([str(path),str(out),json.dumps({'width':40,'stitch_mode':'fill'})])==0
    info=json.loads((out/'preview.json').read_text());dialog=TraceDialog(str(path))
    try:
        dialog.lock_selected_angle.click();assert not dialog.region_angles
        dialog.ready(str(path),info,QImage(str(out/'preview.png')))
        dialog.decisions.setCurrentCell(0,0)
        angle=dialog.decisions.cellWidget(0,6).value()
        assert dialog.decisions.cellWidget(0,6).suffix()=='°'
        dialog.lock_selected_angle.click()
        assert dialog.region_angles=={'0':angle} and 'locked at' in dialog.status.text()
        assert 'locked' in dialog.decisions.cellWidget(0,6).suffix()
        assert 'preserves this direction' in dialog.decisions.cellWidget(0,6).accessibleDescription()
        revised=tmp_path/'locked';revised.mkdir()
        assert worker_main([str(path),str(revised),json.dumps({'width':40,'stitch_mode':'fill',
            'optimize_fill_angles':True,'region_angles':dialog.region_angles})])==0
        result=json.loads((revised/'preview.json').read_text())
        assert Project.loads(result['project']).objects[0].angle==angle
        assert not result['trace_stats']['quality']['fill_angles']['changes']
        dialog.ready(str(path),result,QImage(str(revised/'preview.png')))
        assert 'locked' in dialog.decisions.cellWidget(0,6).suffix()
        dialog.decisions.setCurrentCell(0,0);dialog.unlock_selected_angle.click()
        assert dialog.decisions.cellWidget(0,6).suffix()=='°'
        assert 'may change' in dialog.decisions.cellWidget(0,6).accessibleDescription()
    finally:dialog.close()


def test_unlock_selected_angle_preserves_other_region_corrections(tmp_path):
    from morale.trace_dialog import TraceDialog
    dialog=TraceDialog(str(tmp_path/'source.svg'))
    try:
        dialog.region_angles={'0':17,'1':90}
        dialog.region_spacing={'0':.7,'1':.5};dialog.overrides={'0':'fill'};dialog.seams={'0':25}
        dialog.unlock_selected_angle.click()
        assert dialog.region_angles=={'0':17,'1':90}
        dialog.decisions.setRowCount(2);dialog.decisions.setCurrentCell(0,0)
        dialog.unlock_selected_angle.click()
        assert dialog.region_angles=={'1':90}
        assert dialog.region_spacing=={'0':.7,'1':.5}
        assert dialog.overrides=={'0':'fill'} and dialog.seams=={'0':25}
        assert 'Other corrections are retained' in dialog.status.text()
        dialog.unlock_selected_angle.click()
        assert dialog.region_angles=={'1':90}
    finally:dialog.close()


@pytest.mark.parametrize('requested',['auto','satin'])
def test_worker_keeps_fill_when_requested_compensation_folds_satin(tmp_path,requested):
    import math
    from morale.raster_trace import worker_main
    from morale.formats import export_machine
    from morale.export_verify import verify_export
    rings=['M '+' L '.join(f'{2+r*math.cos(i*math.tau/64):.9f},{2+r*math.sin(i*math.tau/64):.9f}' for i in range(64))+' Z' for r in (2,1)]
    path=tmp_path/'band.svg'
    path.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="4mm" height="4mm" viewBox="0 0 4 4"><path fill="blue" fill-rule="evenodd" d="'+' '.join(rings)+'"/></svg>')
    before=path.read_bytes()
    options={'width':4,'stitch_mode':'auto','stitch_overrides':{'0':requested},'stitch_settings':{'underlay':'off','pull_compensation':0}}
    baseline=tmp_path/'baseline';baseline.mkdir()
    assert worker_main([str(path),str(baseline),json.dumps(options)])==0
    initial=json.loads((baseline/'preview.json').read_text())
    assert initial['trace_stats']['stitch_decisions'][0]['selected']=='satin'
    options['stitch_settings']['pull_compensation']=1.5
    output=tmp_path/'compensated';output.mkdir()
    assert worker_main([str(path),str(output),json.dumps(options)])==0
    info=json.loads((output/'preview.json').read_text())
    decision=info['trace_stats']['stitch_decisions'][0]
    assert decision['requested']==requested and decision['selected']=='fill'
    assert 'Pull compensation produces invalid satin rails' in decision['reason']
    result=Project.loads(info['project'])
    assert result.objects[0].pull_compensation==1.5 and result.objects[0].stitch_type=='fill'
    blocks=generate(result)
    for extension in ('pes','exp'):
        machine=tmp_path/f'fallback.{extension}';export_machine(result,machine,blocks)
        assert verify_export(blocks,machine)['verified']
    assert path.read_bytes()==before
    from PySide6.QtGui import QImage
    from morale.trace_dialog import TraceDialog
    assert decision['fallback'] and not initial['trace_stats']['stitch_decisions'][0]['fallback']
    dialog=TraceDialog(str(path))
    try:
        dialog.ready(str(path),info,QImage(str(output/'preview.png')))
        assert dialog.project is not None
        assert 'Fill retained for 1 unsuitable column regions' in dialog.status.text()
        dialog.decisions.setCurrentCell(0,2)
        assert 'Pull compensation produces invalid satin rails' in dialog.region_reason.text()
    finally:dialog.close()
