import json
import math
import pytest
from PySide6.QtWidgets import QApplication
from morale.model import Project,DesignObject
from morale.engine import generate
from morale.trace_angles import choose_fill_angles

@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])

def measured(project):
    previous=(0,0);total=0
    for block in generate(project):
        for s in block.stitches:
            if s.command=='jump':total+=math.dist(previous,(s.x,s.y))
            if s.command in {'stitch','jump'}:previous=(s.x,s.y)
    return total

def test_long_fill_improves_actual_travel_without_changing_geometry():
    source=Project(objects=[DesignObject(kind='rectangle',width=40,height=10,underlay=False,angle=45)])
    before=source.dumps();result,report=choose_fill_angles(source)
    assert source.dumps()==before and result.objects[0].rings()==source.objects[0].rings()
    assert measured(result)<measured(source)-5
    assert report['before_mm']==pytest.approx(measured(source)) and report['after_mm']==pytest.approx(measured(result))
    assert report['changes'] and Project.loads(result.dumps()).objects==result.objects

def test_neighbor_transfers_and_underlay_are_included():
    source=Project(objects=[DesignObject(kind='rectangle',x=-30,width=8,height=30,angle=45),DesignObject(kind='rectangle',x=25,width=20,height=10,angle=45)])
    result,report=choose_fill_angles(source)
    assert report['after_mm']==pytest.approx(measured(result))
    assert measured(result)<=measured(source)+1e-6
    assert [o.id for o in source.objects]==[o.id for o in result.objects]
    assert all(o.underlay for o in result.objects)

def test_nonfills_gradients_lettering_and_groups_preserved():
    objects=[DesignObject(stitch_type='running'),DesignObject(density_gradient=True),DesignObject(group_id='group')]
    source=Project(objects=objects);result,report=choose_fill_angles(source)
    assert result==source and not report['changes']

def test_search_budget_is_explicit_and_retains_valid_result():
    source=Project(objects=[DesignObject(kind='rectangle',width=40,height=10,underlay=False)])
    result,report=choose_fill_angles(source,evaluation_limit=1)
    assert not report['complete'] and report['evaluations']==1 and measured(result)<=measured(source)

def test_angle_that_generates_no_sewing_is_not_selected():
    source=Project(objects=[DesignObject(kind='rectangle',width=10,height=.1,underlay=False,angle=45)])
    result,report=choose_fill_angles(source)
    assert any(s.command=='stitch' for b in generate(result) for s in b.stitches)

def test_hole_geometry_and_thread_metadata_preserved():
    obj=DesignObject(kind='compound',width=30,height=20,contours=[[[-.5,-.5],[.5,-.5],[.5,.5],[-.5,.5]],[[-.2,-.2],[.2,-.2],[.2,.2],[-.2,.2]]],thread={'brand':'Example'},underlay=False)
    source=Project(objects=[obj]);result,_=choose_fill_angles(source)
    assert result.objects[0].rings()==obj.rings() and result.objects[0].thread==obj.thread

@pytest.mark.parametrize('key,value',[('evaluation_limit',0),('command_limit',True)])
def test_invalid_budget(key,value):
    with pytest.raises(ValueError):choose_fill_angles(Project(),**{key:value})

def test_worker_native_option_and_undo(tmp_path):
    from morale.raster_trace import worker_main
    from morale.trace_dialog import TraceDialog
    from morale.app import MainWindow
    path=tmp_path/'fill.svg';path.write_text('<svg width="50" height="20"><rect x="5" y="5" width="40" height="10" fill="red"/></svg>')
    output=tmp_path/'output';output.mkdir()
    assert worker_main([str(path),str(output),json.dumps(dict(width=50,stitch_mode='fill',optimize_fill_angles=True))])==0
    info=json.loads((output/'preview.json').read_text());report=info['trace_stats']['quality']['fill_angles']
    assert report['after_mm']<report['before_mm']
    dialog=TraceDialog(str(path));window=MainWindow()
    try:
        assert not dialog.optimize_angles.isChecked()
        dialog.overrides={'0':'fill'};dialog.optimize_angles.setChecked(True)
        assert dialog.overrides=={'0':'fill'}
        before=window.project.dumps();window.apply_raster_trace(Project.loads(info['project']));window.undo()
        assert window.project.dumps()==before
    finally:dialog.close();window.saved=window.project.dumps();window.close()

@pytest.mark.parametrize('extension',['dst','exp','jef','pec','pes','tbf','u01','vp3','xxx'])
def test_chosen_angles_export_and_reopen_with_expected_bounds(tmp_path,extension):
    from morale.formats import export_machine,import_machine
    source=Project(objects=[DesignObject(kind='rectangle',width=40,height=10,underlay=False)])
    project,_=choose_fill_angles(source)
    path=tmp_path/f'fill.{extension}';export_machine(project,path)
    sewn=[s for b in generate(import_machine(path).project) for s in b.stitches if s.command=='stitch']
    assert sewn and all(-20.15<=s.x<=20.15 and -5.15<=s.y<=5.15 for s in sewn)

def test_candidates_exceeding_combined_command_limit_are_skipped(monkeypatch):
    import morale.trace_angles as module
    from morale.engine import Block,Stitch
    source=Project(objects=[DesignObject(angle=45),DesignObject(angle=45)])
    def fake_generate(project):
        blocks=[]
        for obj in project.objects:
            original=obj.angle==45;size=125000 if original else 130000;x=10 if original else 0
            blocks.append(Block(obj.id,obj.color,[Stitch(x,0,'jump')]+[Stitch(x,0)]*(size-1)))
        return blocks
    monkeypatch.setattr(module,'generate',fake_generate)
    result,report=choose_fill_angles(source,evaluation_limit=2)
    assert result==source and not report['changes']


@pytest.mark.parametrize('locks',[(0,),[0],iter([0])])
def test_locked_region_does_not_disable_search_for_neighbors(locks):
    source=Project(objects=[DesignObject(kind='rectangle',x=-25,width=40,height=10,underlay=False,angle=17),
                            DesignObject(kind='rectangle',x=25,width=40,height=10,underlay=False,angle=45)])
    before=source.dumps();result,report=choose_fill_angles(source,locked_regions=locks)
    assert source.dumps()==before and result.objects[0]==source.objects[0]
    assert report['evaluations']>0 and report['changes']
    assert all(change['region']==1 for change in report['changes'])
    assert measured(result)<measured(source)


@pytest.mark.parametrize('locks',[None,1,[True],[-1],[1],['0'],iter([0,False])])
def test_invalid_angle_locks_rejected_without_changing_source(locks):
    source=Project(objects=[DesignObject(angle=17)])
    before=source.dumps()
    with pytest.raises(ValueError,match='Invalid locked fill regions'):
        choose_fill_angles(source,locked_regions=locks)
    assert source.dumps()==before


def test_fine_search_reduces_real_triangle_travel_beyond_coarse_candidates():
    source=Project(objects=[DesignObject(kind='polygon',width=32,height=21,x=-20,y=20,
        points=[[-.5,-.5],[.5,-.5],[.1,.5]],underlay=False,angle=45)])
    before=source.dumps()
    coarse,limited=choose_fill_angles(source,evaluation_limit=16)
    refined,report=choose_fill_angles(source)
    assert not limited['complete'] and limited['evaluations']==16
    assert report['complete'] and report['evaluations']<=22
    assert measured(refined)<measured(coarse)-1
    assert report['after_mm']==pytest.approx(measured(refined))
    assert source.dumps()==before
    assert refined.objects[0].rings()==source.objects[0].rings()


def test_refinement_obeys_remaining_evaluation_budget():
    source=Project(objects=[DesignObject(kind='polygon',width=32,height=21,x=-20,y=20,
        points=[[-.5,-.5],[.5,-.5],[.1,.5]],underlay=False,angle=45)])
    result,report=choose_fill_angles(source,evaluation_limit=17)
    assert not report['complete'] and report['evaluations']==17
    assert measured(result)<=measured(source)
    assert report['after_mm']==pytest.approx(measured(result))


@pytest.mark.parametrize('kwargs,reason',[({'evaluation_limit':1},'evaluation_limit'),({'command_limit':1},'command_limit')])
def test_search_reports_actual_limit(kwargs,reason):
    result,report=choose_fill_angles(Project(objects=[DesignObject(kind='rectangle',width=32,height=21)]),**kwargs)
    assert not report['complete'] and report['stop_reason']==reason
    assert report['evaluation_limit']==kwargs.get('evaluation_limit',512)
    assert report['command_limit']==kwargs.get('command_limit',2_000_000)
    assert report['after_mm']==pytest.approx(measured(result))
