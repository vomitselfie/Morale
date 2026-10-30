import math
import pytest
from PySide6.QtWidgets import QApplication
from morale.model import Project,DesignObject
from morale.engine import generate
from morale.ripple_fill import ripple_paths
from morale.formats import export_machine
from morale.export_verify import verify_export

@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])

def shape(**kwargs):
    return DesignObject(**dict(dict(kind='rectangle',width=20,height=20,stitch_type='ripple',spacing=1,underlay=False),**kwargs))

def test_concentric_rows_spacing_length_and_roundtrip():
    obj=shape();paths=list(ripple_paths(obj))
    closed=[p for p in paths if math.dist(p[0],p[-1])<1e-8]
    assert len(closed)==10
    assert [math.hypot(*p[0]) for p in closed]==pytest.approx([i+.5 for i in range(10)])
    for path in paths:
        assert all(math.dist(a,b)<=obj.stitch_length+1e-8 for a,b in zip(path,path[1:]))
    project=Project(objects=[obj]);assert generate(project)==generate(Project.loads(project.dumps()))
    original=len(paths);obj.spacing=2
    assert len(list(ripple_paths(obj)))<original

def test_sewn_segments_stay_inside_holes_islands_and_disconnected_regions():
    from morale.pattern_fill import RegionClip
    obj=shape();obj.kind='compound'
    obj.contours=[[[-.5,-.5],[.1,-.5],[.1,.5],[-.5,.5]],
                  [[-.4,-.2],[-.1,-.2],[-.1,.2],[-.4,.2]],
                  [[-.3,-.1],[-.2,-.1],[-.2,.1],[-.3,.1]],
                  [[.3,-.5],[.5,-.5],[.5,.5],[.3,.5]]]
    region=RegionClip(obj.rings());stitches=generate(Project(objects=[obj]))[0].stitches
    assert sum(s.command=='jump' for s in stitches)>10
    for a,b in zip(stitches,stitches[1:]):
        if b.command=='stitch':
            for t in (.01,.25,.5,.75,.99):
                assert region.inside((a.x+t*(b.x-a.x),a.y+t*(b.y-a.y)))

def test_translation_and_rotation_keep_circular_rows():
    a=list(ripple_paths(shape()))
    b=list(ripple_paths(shape(x=40,y=-30)))
    assert len(a)==len(b)
    for first,second in zip(a,b):
        for p,q in zip(first,second):assert q==pytest.approx((p[0]+40,p[1]-30))
    rotated=shape(rotation=37)
    assert list(ripple_paths(rotated))

def test_generation_limit(monkeypatch):
    import morale.engine as engine
    monkeypatch.setattr(engine,'MAX_STITCHES',20)
    with pytest.raises(ValueError,match='command limit'):generate(Project(objects=[shape()]))

def test_native_choice_and_undo():
    from morale.app import MainWindow
    window=MainWindow()
    try:
        obj=DesignObject();window.replace_project(Project(objects=[obj]));window.select(obj.id)
        before=window.project.dumps()
        window.stitch_type.setCurrentIndex(window.stitch_type.findData('ripple'))
        assert window.project.objects[0].stitch_type=='ripple'
        assert window.fields['spacing'].isEnabled() and window.underlay.isEnabled()
        assert not window.fields['pull_compensation'].isEnabled()
        after=window.project.dumps();assert generate(Project.loads(after))
        window.undo();assert window.project.dumps()==before
        window.redo();assert window.project.dumps()==after
    finally:window.saved=window.project.dumps();window.close()

@pytest.mark.parametrize('extension',['dst','exp','jef','pec','pes','tbf','u01','vp3','xxx'])
def test_exports(tmp_path,extension):
    project=Project(objects=[shape()]);blocks=generate(project)
    path=tmp_path/f'ripple.{extension}';export_machine(project,path,blocks)
    result=verify_export(blocks,path)
    assert result['complete_path_comparison'] and result['bounds_delta_mm']<=.3
    if extension=='vp3':
        assert all(issue.startswith('Trim commands increased:') for issue in result['problems']),result
    else:assert not result['problems'],result


@pytest.mark.parametrize('kind',['path','satin','stitches'])
def test_reject_nonclosed_objects(kind):
    with pytest.raises(ValueError,match='closed outline'):list(ripple_paths(shape(kind=kind)))


def test_clipping_budget(monkeypatch):
    from morale.pattern_fill import RegionClip
    original=RegionClip.__init__
    def almost_exhausted(self,rings):
        original(self,rings);self.work=30_000_000
    monkeypatch.setattr(RegionClip,'__init__',almost_exhausted)
    with pytest.raises(ValueError,match='too complex'):list(ripple_paths(shape()))


def test_underlay_and_finishing_retained():
    obj=shape(tie_in=True,tie_off=True,trim_after=True,stop_after=True)
    obj.underlay=True;obj.underlay_style='edge_sparse'
    stitches=generate(Project(objects=[obj]))[0].stitches
    assert stitches[-1].command=='stop' and stitches[-2].command=='trim'
    obj.underlay=False
    assert len(generate(Project(objects=[obj]))[0].stitches)<len(stitches)


def test_offset_center_follows_rotation_and_reflection():
    from copy import deepcopy
    obj=shape(ripple_center_x=25,ripple_center_y=-15)
    original=list(ripple_paths(obj));changed=deepcopy(obj)
    changed.x=30;changed.y=-20;changed.rotation=37;changed.flip_x=True
    transformed=list(ripple_paths(changed))
    assert len(original)==len(transformed)
    c,s=math.cos(math.radians(37)),math.sin(math.radians(37))
    for first,second in zip(original,transformed):
        assert len(first)==len(second)
        for (x,y),point in zip(first,second):
            assert point==pytest.approx((30-x*c-y*s,-20-x*s+y*c),abs=1e-8)
    assert math.dist(original[0][0],(5,-3))==pytest.approx(.5)


@pytest.mark.parametrize('value',[True,float('nan'),float('inf'),101,-101,'25'])
def test_invalid_center_rejected_on_load_and_generation(value):
    obj=shape(ripple_center_x=value)
    with pytest.raises(ValueError):Project.loads(Project(objects=[obj]).dumps())
    with pytest.raises(ValueError):list(ripple_paths(obj))


def test_older_project_defaults_to_center():
    import json
    project=Project(objects=[shape()]);raw=json.loads(project.dumps())
    for key in ('ripple_center_x','ripple_center_y'):raw['objects'][0].pop(key)
    assert generate(Project.loads(json.dumps(raw)))==generate(project)


def test_native_center_edit_roundtrip_and_undo():
    from morale.app import MainWindow
    window=MainWindow()
    try:
        obj=shape();window.replace_project(Project(objects=[obj]));window.select(obj.id)
        before=window.project.dumps()
        assert window.fields['ripple_center_x'].isEnabled()
        window.fields['ripple_center_x'].setValue(35)
        assert window.project.objects[0].ripple_center_x==35
        assert Project.loads(window.project.dumps()).objects[0].ripple_center_x==35
        assert generate(window.project)!=generate(Project.loads(before))
        window.undo();assert window.project.dumps()==before
    finally:window.saved=window.project.dumps();window.close()


@pytest.mark.parametrize('extension',['pes','exp'])
def test_external_center_export_with_hole(tmp_path,extension):
    obj=shape(kind='compound',ripple_center_x=75,ripple_center_y=-50,
              contours=[[[-.5,-.5],[.5,-.5],[.5,.5],[-.5,.5]],
                        [[-.2,-.2],[.2,-.2],[.2,.2],[-.2,.2]]])
    project=Project(objects=[obj]);blocks=generate(project)
    assert blocks[0].stitches
    path=tmp_path/f'offset.{extension}';export_machine(project,path,blocks)
    result=verify_export(blocks,path)
    assert result['complete_path_comparison'] and not result['problems'],result


def center(obj):return obj.transform([(obj.ripple_center_x/100,obj.ripple_center_y/100)])[0]


def test_contour_edit_preserves_world_center():
    from morale.geometry import replace_contours
    obj=shape(kind='compound',contours=[[[-.5,-.5],[.5,-.5],[.5,.5],[-.5,.5]]],
              rotation=37,flip_x=True,ripple_center_x=25,ripple_center_y=-15)
    rings=obj.rings();rings[0][0]=(rings[0][0][0]-2,rings[0][0][1]-1)
    edited=replace_contours(obj,rings)
    assert center(edited)==pytest.approx(center(obj))
    assert generate(Project(objects=[edited]))


def test_boolean_result_keeps_first_objects_center():
    from morale.geometry import combine_outlines
    obj=shape(ripple_center_x=25,ripple_center_y=-15)
    result=combine_outlines([obj,DesignObject(kind='rectangle',width=20,height=20,x=15)],'union')
    assert result.width>obj.width
    assert center(result)==pytest.approx(center(obj))


def test_nonuniform_transform_applies_same_affine_to_center():
    from morale.arrange import transform_selection
    obj=shape(rotation=31,flip_y=True,ripple_center_x=25,ripple_center_y=-15)
    old=center(obj)
    result=transform_selection([obj],scale=2,scale_y=.7,rotation=20,origin='hoop')[0]
    c,s=math.cos(math.radians(20)),math.sin(math.radians(20))
    assert center(result)==pytest.approx((2*old[0]*c-.7*old[1]*s,2*old[0]*s+.7*old[1]*c))


def test_bezier_conversion_keeps_center():
    from morale.bezier import enable_handles,edit_controls
    obj=shape(kind='polygon',points=[[-.5,-.5],[.5,-.5],[.5,.5],[-.5,.5]],
              rotation=23,ripple_center_x=25,ripple_center_y=-15)
    result=enable_handles(obj);assert center(result)==pytest.approx(center(obj))
    controls=result.control_points();controls[0]=(controls[0][0]-1,controls[0][1]-1)
    edited=edit_controls(result,controls)
    assert center(edited)==pytest.approx(center(obj))


def test_point_edit_and_undo_keep_center_and_reject_out_of_range_atomically():
    from morale.app import MainWindow
    window=MainWindow()
    try:
        obj=shape(kind='polygon',points=[[-.5,-.5],[.5,-.5],[.5,.5],[-.5,.5]],ripple_center_x=25)
        window.replace_project(Project(objects=[obj]));window.select(obj.id)
        before=window.project.dumps();points=obj.control_points();points[0]=(-12,-11)
        window.replace_points(points)
        assert center(window.project.objects[0])==pytest.approx(center(obj))
        window.undo();assert window.project.dumps()==before
        with pytest.raises(ValueError,match='ripple center'):
            window.replace_points([(90,90),(91,90),(91,91)])
        assert window.project.dumps()==before
    finally:window.saved=window.project.dumps();window.close()


def test_cleanup_preserves_clipped_ripple_detour(monkeypatch):
    import morale.ripple_fill as module
    # Isolate the cleanup integration from the circle sampler using an already
    # clipped short path around a hole smaller than cleanup's error tolerance.
    obj=shape(kind='compound',minimum_stitch=.2,
        contours=[[[-.5,-.5],[.5,-.5],[.5,.5],[-.5,.5]],
                  [[.00475,-.00005],[.00525,-.00005],[.00525,.00005],[.00475,.00005]]])
    path=[(-.1,0),(0,0),(.1,.005),(.2,0)]
    monkeypatch.setattr(module,'ripple_paths',lambda _:iter([path]))
    stitches=generate(Project(objects=[obj]))[0].stitches
    assert [(s.x,s.y) for s in stitches]==path


@pytest.mark.parametrize('minimum',[.1,.5,1])
@pytest.mark.parametrize('offset',[-60,0,45])
def test_real_ripple_cleanup_keeps_sewn_segments_in_region(minimum,offset):
    from morale.pattern_fill import RegionClip
    obj=shape(kind='compound',minimum_stitch=minimum,ripple_center_x=offset,
              contours=[[[-.5,-.5],[.5,-.5],[.5,.5],[-.5,.5]],
                        [[-.3,-.1],[.2,-.1],[.2,.2],[-.3,.2]]])
    stitches=generate(Project(objects=[obj]))[0].stitches
    region=RegionClip(obj.rings())
    for a,b in zip(stitches,stitches[1:]):
        if b.command=='stitch':
            start,end=(a.x,a.y),(b.x,b.y)
            covered=sum(math.dist(p,q) for p,q in region.segment(start,end))
            assert covered==pytest.approx(math.dist(start,end),abs=1e-8)
