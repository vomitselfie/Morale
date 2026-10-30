import pytest
from morale.model import Project,DesignObject
from morale.engine import generate
from morale.trace_routing import reduce_travel


def objects():
    return [DesignObject(name=f'Region {i}',kind='rectangle',x=x,width=2,height=2,underlay=False)
            for i,x in enumerate((30,5,20,10))]


def test_route_reduces_measured_travel_without_changing_stitches():
    source=Project(objects=objects());before=source.dumps()
    result,stats=reduce_travel(source)
    assert source.dumps()==before
    assert stats['after_mm']<stats['before_mm']-15
    assert stats['moved_regions']>0
    assert {b.object_id:b for b in generate(source)}=={b.object_id:b for b in generate(result)}
    assert Project.loads(result.dumps()).objects==result.objects


@pytest.mark.parametrize('barrier',['stop_after','color_break','group_id','stage_note','color','thread'])
def test_semantic_and_thread_boundaries_keep_their_place(barrier):
    source=Project(objects=objects())
    value={'group_id':'group','stage_note':'Applique placement','color':'#ff0000','thread':{'brand':'Test','catalog_number':'1','description':'Red'}}.get(barrier,True)
    setattr(source.objects[1],barrier,value)
    result,_=reduce_travel(source)
    assert [o.id for o in result.objects[:2]]==[o.id for o in source.objects[:2]]


def test_overlapping_geometry_keeps_original_layering():
    items=objects();items[0].width=60
    source=Project(objects=items)
    result,stats=reduce_travel(source)
    assert result.objects[0].id==source.objects[0].id
    assert stats['after_mm']<=stats['before_mm']


def test_already_short_route_is_not_worsened():
    items=sorted(objects(),key=lambda o:o.x)
    source=Project(objects=items);result,stats=reduce_travel(source)
    assert result.objects==source.objects and stats['moved_regions']==0


@pytest.mark.parametrize('extension',['dst','exp','jef','pec','pes','tbf','u01','vp3','xxx'])
def test_reordered_regions_export_in_each_format(tmp_path,extension):
    from morale.formats import export_machine,import_machine
    project,stats=reduce_travel(Project(objects=objects()))
    path=tmp_path/f'route.{extension}';export_machine(project,path)
    sewn=[s for b in generate(import_machine(path).project) for s in b.stitches if s.command=='stitch']
    assert sewn and all(abs(s.y)<=1.1 for s in sewn)
    assert all(any(abs(s.x-x)<=1.1 for x in (5,10,20,30)) for s in sewn)


def test_island_inside_hole_can_move_before_ring():
    ring=DesignObject(kind='compound',width=40,height=40,stitch_type='running',underlay=False,
        contours=[[[-.5,-.5],[.5,-.5],[.5,.5],[-.5,.5]],[[-.3,-.3],[.3,-.3],[.3,.3],[-.3,.3]]])
    island=DesignObject(kind='rectangle',width=2,height=2,underlay=False)
    source=Project(objects=[ring,island]);before=source.dumps()
    result,stats=reduce_travel(source)
    assert stats['order']==[1,0] and stats['after_mm']<stats['before_mm']
    assert source.dumps()==before
    assert {b.object_id:b for b in generate(source)}=={b.object_id:b for b in generate(result)}


def test_actual_crossing_running_paths_keep_order():
    a=DesignObject(kind='path',width=30,height=30,points=[[-.5,-.5],[.5,.5]],stitch_type='running',underlay=False)
    b=DesignObject(kind='path',width=30,height=30,points=[[0,0],[-.5,.5]],stitch_type='running',underlay=False)
    result,stats=reduce_travel(Project(objects=[a,b]))
    assert stats['order']==[0,1]


def test_compensated_sewn_geometry_keeps_overlap_locked():
    a=DesignObject(kind='rectangle',x=10,width=10,height=10,pull_compensation=1,underlay=False)
    b=DesignObject(kind='rectangle',width=9,height=10,pull_compensation=1,underlay=False)
    _,stats=reduce_travel(Project(objects=[a,b]))
    assert stats['order']==[0,1]


def test_complex_regions_keep_conservative_bbox_lock():
    ring=DesignObject(kind='compound',width=100,height=100,spacing=.2,stitch_length=.5,underlay=False,
        contours=[[[-.5,-.5],[.5,-.5],[.5,.5],[-.5,.5]],[[-.3,-.3],[.3,-.3],[.3,.3],[-.3,.3]]])
    island=DesignObject(kind='rectangle',width=2,height=2,underlay=False)
    source=Project(objects=[ring,island])
    assert len(generate(source)[0].stitches)>2000
    _,stats=reduce_travel(source)
    assert stats['order']==[0,1]


def test_adjacent_refinement_improves_on_nearest_neighbor_route():
    import math
    positions=[(-10,30),(-20,-10),(0,10),(20,30),(-30,0)]
    source=Project(objects=[DesignObject(kind='rectangle',x=x,y=y,width=2,height=2,underlay=False) for x,y in positions])
    before=source.dumps();blocks=generate(source)
    ends=[[(s.x,s.y) for s in b.stitches if s.command in {'stitch','jump'}] for b in blocks]
    pending=set(range(len(ends)));previous=(0,0);greedy=0
    while pending:
        chosen=min(pending,key=lambda i:(math.dist(previous,ends[i][0]),i))
        greedy+=math.dist(previous,ends[chosen][0]);previous=ends[chosen][-1];pending.remove(chosen)
    result,report=reduce_travel(source)
    assert report['after_mm']<greedy-10
    assert 0<report['refinement_evaluations']<=2048
    assert source.dumps()==before
    assert {b.object_id:b for b in generate(result)}=={b.object_id:b for b in blocks}
    previous=(0,0);measured=0
    for block in generate(result):
        points=[(s.x,s.y) for s in block.stitches if s.command in {'stitch','jump'}]
        measured+=math.dist(previous,points[0]);previous=points[-1]
    assert measured==pytest.approx(report['after_mm'])
