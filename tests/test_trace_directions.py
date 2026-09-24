import itertools
import math
import pytest
from morale.model import Project,DesignObject
from morale.engine import generate
from morale.routing import route_object
from morale.trace_routing import reduce_travel
from morale.auto_digitize import outline_path,difference_area


def travel(project):
    previous=(0,0);total=0
    for block in generate(project):
        points=[(s.x,s.y) for s in block.stitches if s.command in {'jump','stitch'}]
        if points:total+=math.dist(previous,points[0]);previous=points[-1]
    return total


def test_direction_plan_matches_exhaustive_fixed_order_search():
    objects=[DesignObject(kind='path',stitch_type='running',x=x,width=20,height=2,color=color,
        points=[[-.5,0],[.5,0]],underlay=False) for x,color in ((20,'#ff0000'),(0,'#00ff00'),(-20,'#0000ff'))]
    source=Project(objects=objects);before=source.dumps()
    optimum=min(travel(Project(objects=[route_object(obj,[(0,0,reverse)]) for obj,reverse in zip(objects,choices)]))
                for choices in itertools.product((False,True),repeat=3))
    result,stats=reduce_travel(source,reverse=True)
    assert stats['after_mm']==pytest.approx(optimum)
    assert stats['after_mm']==pytest.approx(travel(result)) and stats['after_mm']<stats['before_mm']
    assert stats['order']==[0,1,2] and stats['reversed_regions']
    assert source.dumps()==before and Project.loads(result.dumps()).objects==result.objects


def satin():
    return Project(objects=[DesignObject(kind='satin',stitch_type='satin',y=20,width=4,height=20,
        points=[[-.5,.5],[.5,.5],[-.5,-.5],[.5,-.5]],underlay=False)])


def test_satin_direction_shortens_entry_without_changing_outline():
    source=satin();result,stats=reduce_travel(source,reverse=True)
    assert stats['reversed_regions']==[0] and stats['after_mm']<stats['before_mm']-15
    assert difference_area(outline_path(source.objects[0].rings()),outline_path(result.objects[0].rings()))<.001
    assert all(abs(s.x)<=2 and 10<=s.y<=30 for b in generate(result) for s in b.stitches if s.command=='stitch')


@pytest.mark.parametrize('field,value',[('group_id','g'),('stop_after',True),('color_break',True),('stage_note','Placement')])
def test_explicit_boundaries_do_not_reverse(field,value):
    source=satin();setattr(source.objects[0],field,value)
    result,stats=reduce_travel(source,reverse=True)
    assert result.objects==source.objects and stats['reversed_regions']==[]


def test_closed_start_is_preserved():
    source=Project(objects=[DesignObject(kind='path',stitch_type='running',x=20,width=10,height=10,
        points=[[.5,.5],[-.5,.5],[-.5,-.5],[.5,-.5],[.5,.5]])])
    result,stats=reduce_travel(source,reverse=True)
    assert result.objects==source.objects and not stats['reversed_regions']


@pytest.mark.parametrize('extension',['dst','exp','jef','pec','pes','tbf','u01','vp3','xxx'])
def test_reversed_satin_export_bounds(tmp_path,extension):
    from morale.formats import export_machine,import_machine
    result,_=reduce_travel(satin(),reverse=True);path=tmp_path/f'direction.{extension}';export_machine(result,path)
    sewn=[s for b in generate(import_machine(path).project) for s in b.stitches if s.command=='stitch']
    assert sewn and all(abs(s.x)<=2.1 and 9.9<=s.y<=30.1 for s in sewn)


def test_final_layer_validation_rejects_inverted_crossing_paths():
    from morale.trace_routing import layering_valid
    a=DesignObject(kind='path',stitch_type='running',width=20,height=20,points=[[-.5,-.5],[.5,.5]],underlay=False)
    b=DesignObject(kind='path',stitch_type='running',width=20,height=20,points=[[-.5,.5],[.5,-.5]],underlay=False)
    blocks={b.object_id:b for b in generate(Project(objects=[a,b]))}
    assert layering_valid([a,b],blocks,[0,1])
    assert not layering_valid([a,b],blocks,[1,0])


def test_final_layer_validation_failure_restores_source(monkeypatch):
    import morale.trace_routing as routing
    source=Project(objects=[DesignObject(kind='path',stitch_type='running',x=x,width=10,height=2,points=[[.5,0],[-.5,0]],underlay=False) for x in (30,5)])
    result,stats=routing.reduce_travel(source,True)
    assert stats['order']==[1,0] and stats['reversed_regions']
    checked=[]
    def reject(objects,blocks,order):
        checked.append(order)
        assert len(blocks)==2
        return False
    monkeypatch.setattr(routing,'layering_valid',reject)
    before=source.dumps();result,stats=routing.reduce_travel(source,True)
    assert stats['status']=='rejected' and 'layer order' in stats['reason']
    assert checked==[[1,0]] and source.dumps()==before and result.dumps()==before
    assert stats['order']==[0,1] and stats['reversed_regions']==[] and stats['after_mm']==stats['before_mm']
