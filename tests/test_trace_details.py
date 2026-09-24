import json
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPointF
from morale.model import Project,DesignObject
from morale.geometry import replace_contours
from morale.auto_digitize import outline_path,area
from morale.trace_details import filter_small_fills

@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])

def square(x,y,size):return [(x,y),(x+size,y),(x+size,y+size),(x,y+size)]

def compound(rings):
    obj=DesignObject(kind='compound');return replace_contours(obj,rings)

def test_disabled_preserves_every_object_and_metadata():
    project=Project(objects=[compound([square(0,0,.1)])]);before=project.dumps()
    result,report=filter_small_fills(project,0)
    assert result.dumps()==before and project.dumps()==before and not report['changes']

def test_disconnected_islands_filtered_independently():
    obj=compound([square(0,0,5),square(10,0,.5)])
    project=Project(objects=[obj]);before=project.dumps()
    result,report=filter_small_fills(project,1)
    assert project.dumps()==before and result.objects[0].id==obj.id
    assert area(outline_path(result.objects[0].rings()))==pytest.approx(25)
    assert report['removed_components']==1 and report['removed_area_mm2']==pytest.approx(.25)
    assert not outline_path(result.objects[0].rings()).contains(QPointF(10.2,.2))

def test_holes_subtracted_when_measuring_component_area():
    obj=compound([square(0,0,10),square(.1,.1,9.8)])
    result,report=filter_small_fills(Project(objects=[obj]),4)
    assert not result.objects and report['removed_area_mm2']==pytest.approx(3.96)

def test_holes_of_retained_component_are_not_filled():
    obj=compound([square(0,0,10),square(1,1,8),square(20,0,.2)])
    result,_=filter_small_fills(Project(objects=[obj]),1)
    region=outline_path(result.objects[0].rings())
    assert area(region)==pytest.approx(36)
    assert not region.contains(QPointF(5,5)) and region.contains(QPointF(.5,.5))

def test_island_nested_in_hole_is_separate_component():
    obj=compound([square(0,0,10),square(1,1,8),square(4,4,.5)])
    result,report=filter_small_fills(Project(objects=[obj]),1)
    assert report['removed_components']==1 and report['removed_area_mm2']==pytest.approx(.25)
    assert area(outline_path(result.objects[0].rings()))==pytest.approx(36)

def test_nesting_independent_of_order_and_winding():
    rings=[square(4,4,.5),list(reversed(square(1,1,8))),square(0,0,10)]
    result,_=filter_small_fills(Project(objects=[compound(rings)]),1)
    assert area(outline_path(result.objects[0].rings()))==pytest.approx(36)

@pytest.mark.parametrize('scale,retained',[(1,False),(2,True)])
def test_physical_size_controls_threshold(scale,retained):
    obj=DesignObject(kind='rectangle',width=.5*scale,height=.5*scale)
    result,_=filter_small_fills(Project(objects=[obj]),.5)
    assert bool(result.objects)==retained

@pytest.mark.parametrize('field,value',[('visible',False),('stop_after',True),('color_break',True),('group_id','group'),('stage_note','Placement'),('stitch_type','running')])
def test_protected_semantics_and_outlines_retained(field,value):
    obj=DesignObject(kind='rectangle',width=.2,height=.2);setattr(obj,field,value)
    project=Project(objects=[obj]);result,report=filter_small_fills(project,1)
    assert result==project and not report['changes']

@pytest.mark.parametrize('value',[-1,26,True,None,float('nan')])
def test_invalid_threshold_rejected(value):
    with pytest.raises(ValueError,match='area'):filter_small_fills(Project(),value)

def test_overlap_remnant_filtered_in_worker_and_undo(tmp_path):
    from morale.raster_trace import worker_main
    from morale.app import MainWindow
    path=tmp_path/'sliver.svg';path.write_text('<svg width="40" height="40"><rect x="10" y="10" width="10" height="10" fill="red"/><rect x="10.01" y="10" width="10" height="10" fill="blue"/></svg>')
    output=tmp_path/'output';output.mkdir()
    assert worker_main([str(path),str(output),json.dumps(dict(width=40,remove_overlap=True,overlap_allowance=0,minimum_fill_area=.2,stitch_mode='fill',keep_reference=True))])==0
    info=json.loads((output/'preview.json').read_text());project=Project.loads(info['project'])
    assert len(project.objects)==1 and project.objects[0].color.lower()=='#0000ff'
    assert info['trace_stats']['quality']['detail_filter']['removed_area_mm2']==pytest.approx(.1,abs=.001)
    window=MainWindow()
    try:
        before=window.project.dumps();window.apply_raster_trace(project);window.undo()
        assert window.project.dumps()==before
    finally:window.saved=window.project.dumps();window.close()

def test_native_threshold_change_clears_region_choices(tmp_path):
    from morale.trace_dialog import TraceDialog
    dialog=TraceDialog(str(tmp_path/'image.svg'))
    try:
        assert dialog.minimum_fill_area.value()==0
        dialog.overrides={'0':'satin'};dialog.seams={'0':10}
        dialog.minimum_fill_area.setValue(.25)
        assert not dialog.overrides and not dialog.seams
    finally:dialog.close()


def test_review_names_removed_regions():
    from morale.trace_quality import conversion_quality,quality_text
    obj=DesignObject(kind='rectangle',width=.2,height=.2,name='Tiny accent',underlay=False)
    project=Project(objects=[obj]);_,detail=filter_small_fills(project,1)
    assert detail['changes'][0]['object_id']==obj.id
    report=conversion_quality(project);report['detail_filter']=detail
    assert 'Tiny accent: 1 filled island omitted; 0.04 mm² removed. Entire region omitted.' in quality_text(report)
