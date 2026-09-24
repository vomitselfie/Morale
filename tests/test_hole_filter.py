from copy import deepcopy
import json
import pytest
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication
from morale.model import Project,DesignObject
from morale.trace_details import fill_small_holes
from morale.auto_digitize import outline_path,area

@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])


def square(half):return [[-half,-half],[half,-half],[half,half],[-half,half]]


def source():return Project(objects=[DesignObject(kind='compound',width=10,height=10,contours=[square(.5),square(.1)],underlay=False)])


def test_threshold_source_preservation_and_area():
    project=source();before=project.dumps()
    for threshold in (0,4):
        result,report=fill_small_holes(project,threshold)
        assert result.dumps()==before and report['filled_holes']==0
    result,report=fill_small_holes(project,4.1)
    assert project.dumps()==before and report['filled_holes']==1 and report['added_area_mm2']==pytest.approx(4)
    assert outline_path(result.objects[0].rings()).contains(QPointF(0,0))
    assert Project.loads(result.dumps()).objects==result.objects


def test_small_outer_void_does_not_erase_large_nested_hole():
    project=source();project.objects[0].contours=[square(.5),square(.4),square(.39),square(.3)]
    result,report=fill_small_holes(project,4)
    assert report['filled_holes']==1 and report['added_area_mm2']==pytest.approx(64-60.84)
    shape=outline_path(result.objects[0].rings())
    assert shape.contains(QPointF(3.95,0)) and not shape.contains(QPointF(0,0))


@pytest.mark.parametrize('field,value',[('visible',False),('stop_after',True),('group_id','g'),('stage_note','stage'),('stitch_type','running')])
def test_semantic_and_nonfill_objects_unchanged(field,value):
    project=source();setattr(project.objects[0],field,value)
    result,report=fill_small_holes(project,5)
    assert result==project and report['filled_holes']==0


@pytest.mark.parametrize('value',[-1,26,True,None,float('nan')])
def test_invalid_area_rejected(value):
    with pytest.raises(ValueError):fill_small_holes(source(),value)


def test_native_controls_presets_and_worker_report(tmp_path):
    from morale.trace_dialog import TraceDialog
    from morale.trace_presets import validate
    from morale.raster_trace import worker_main
    from morale.trace_quality import quality_text
    path=tmp_path/'hole.svg';path.write_text('<svg width="10mm" height="10mm" viewBox="0 0 10 10"><path fill-rule="evenodd" d="M0 0 H10 V10 H0Z M4 4 H6 V6 H4Z"/></svg>')
    dialog=TraceDialog(str(path))
    try:
        assert dialog.minimum_hole_area.value()==0
        settings=dialog.preset_settings();settings.pop('minimum_hole_area')
        assert validate(settings)['minimum_hole_area']==0
        dialog.minimum_hole_area.setValue(5)
        assert dialog.preset_settings()['minimum_hole_area']==5
        restored=deepcopy(dialog.preset_settings());dialog.minimum_hole_area.setValue(0);dialog.apply_preset(restored)
        assert dialog.minimum_hole_area.value()==5
    finally:dialog.close()
    out=tmp_path/'worker';out.mkdir()
    assert worker_main([str(path),str(out),json.dumps({'width':10,'minimum_hole_area':5,'stitch_mode':'fill'})])==0
    info=json.loads((out/'preview.json').read_text());project=Project.loads(info['project'])
    assert area(outline_path(project.objects[0].rings()))==pytest.approx(100,abs=.001)
    report=info['trace_stats']['quality'];assert report['hole_filter']['filled_holes']==1
    assert '4.00 mm² added' in quality_text(report)


@pytest.mark.parametrize('width',[1,2])
@pytest.mark.parametrize('above',[False,True])
def test_other_fill_occupying_hole_prevents_added_layer(width,above):
    project=source();other=DesignObject(kind='rectangle',width=width,height=width,color='#ff0000',underlay=False)
    project.objects.insert(1 if above else 0,other)
    before=project.dumps();result,report=fill_small_holes(project,5)
    assert result.dumps()==before and report['filled_holes']==0
    assert report['occupied_holes_retained']==1


def test_hidden_fill_does_not_protect_hole():
    project=source();project.objects.append(DesignObject(kind='rectangle',width=2,height=2,visible=False))
    result,report=fill_small_holes(project,5)
    assert report['filled_holes']==1 and report['occupied_holes_retained']==0


def test_hole_shared_by_two_regions_does_not_gain_two_layers():
    project=source();other=deepcopy(project.objects[0]);other.id='second';other.color='#ff0000';project.objects.append(other)
    result,report=fill_small_holes(project,5)
    assert report['filled_holes']==1 and report['occupied_holes_retained']==1
    assert len(result.objects[0].contours)==1 and len(result.objects[1].contours)==2


def test_quality_identifies_changed_region_and_keeps_legacy_reports_readable():
    from morale.trace_quality import quality_text,conversion_quality
    project=source();project.objects[0].name='Flower center'
    _,holes=fill_small_holes(project,5)
    assert holes['changes'][0]['object_id']==project.objects[0].id
    report=conversion_quality(project);report['hole_filter']=holes
    assert 'Flower center: 1 hole filled; 4.00 mm² added.' in quality_text(report)
    del holes['changes'][0]['name'];del holes['changes'][0]['object_id']
    assert 'Source region 1: 1 hole filled' in quality_text(report)
