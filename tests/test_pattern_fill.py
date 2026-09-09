import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import math
from copy import deepcopy
import pytest
from PySide6.QtWidgets import QApplication
from morale.model import Project,DesignObject
from morale.pattern_fill import RegionClip,pattern_fill_paths
from morale.engine import generate,segment_inside
from morale.arrange import mirror,transform_selection


@pytest.fixture(scope='module',autouse=True)
def app():
    return QApplication.instance() or QApplication([])


def shape():
    return DesignObject(kind='compound',stitch_type='pattern',width=30,height=30,angle=0,motif_width=4,motif_height=3,motif_spacing=5,motif_row_spacing=5,
        contours=[[[-.5,-.5],[.5,-.5],[.5,.5],[-.5,.5]],[[-.15,-.15],[.15,-.15],[.15,.15],[-.15,.15]]])


def test_segment_clipping_holes_tangencies_and_collinear_edges():
    clip=RegionClip([[(0,0),(10,0),(10,10),(0,10)],[(4,4),(6,4),(6,6),(4,6)]])
    assert clip.segment((-2,5),(12,5))==[((0,5),(4,5)),((6,5),(10,5))]
    assert clip.segment((-2,0),(12,0))==[((0,0),(10,0))]
    assert not clip.segment((-1,-1),(0,0))
    assert not clip.segment((5,5),(5,5))


@pytest.mark.parametrize('pattern',['diamond','box','cross','custom'])
@pytest.mark.parametrize('angle',[0,37])
def test_area_motifs_never_sew_across_holes_or_outside(pattern,angle):
    obj=shape(); obj.motif_pattern=pattern; obj.angle=angle
    if pattern=='custom': obj.custom_motif_paths=[[[-.5,-.5],[.5,-.5],[.2,.5]],[[0,-.3],[0,.3]]]
    stitches=generate(Project(objects=[obj]))[0].stitches
    assert stitches
    rings=obj.rings()
    for a,b in zip(stitches,stitches[1:]):
        if b.command=='stitch':
            assert segment_inside((a.x,a.y),(b.x,b.y),rings[0],rings[1:])
            assert math.dist((a.x,a.y),(b.x,b.y))<=obj.stitch_length+1e-8
    assert Project.loads(Project(objects=[obj]).dumps()).objects[0]==obj


def test_clipped_fragments_have_jumps_and_do_not_bridge_hole():
    obj=shape(); obj.motif_pattern='custom'; obj.custom_motif_paths=[[[-.5,0],[.5,0]]]
    obj.motif_width=30; obj.motif_spacing=30; obj.motif_row_spacing=30
    paths=list(pattern_fill_paths(obj))
    assert paths==[[(-15,0),(-4.5,0)],[(4.5,0),(15,0)]]
    assert sum(s.command=='jump' for s in generate(Project(objects=[obj]))[0].stitches)==2


def test_nested_island_and_separate_regions():
    obj=shape(); obj.contours.append([[-.05,-.05],[.05,-.05],[.05,.05],[-.05,.05]])
    obj.motif_pattern='custom'; obj.custom_motif_paths=[[[-.5,0],[.5,0]]]; obj.motif_width=30; obj.motif_spacing=30; obj.motif_row_spacing=30
    paths=list(pattern_fill_paths(obj))
    assert len(paths)==3 and paths[1]==[(-1.5,0),(1.5,0)]


@pytest.mark.parametrize('axis',['horizontal','vertical'])
def test_asymmetric_custom_pattern_mirrors_with_shape(axis):
    obj=shape(); obj.angle=23; obj.rotation=17; obj.motif_pattern='custom'
    obj.custom_motif_paths=[[[-.5,-.5],[.5,-.3],[.1,.5]]]
    def segments(obj):
        return [tuple(sorted((a,b))) for path in pattern_fill_paths(obj) for a,b in zip(path,path[1:])]
    expected=[]
    for pair in segments(obj):
        expected.append(tuple(sorted(((-x,y) if axis=='horizontal' else (x,-y)) for x,y in pair)))
    def key(pair): return tuple(round(v,7) for p in pair for v in p)
    actual=segments(mirror(obj,axis))
    assert len(actual)==len(expected)
    for a,b in zip(sorted(actual,key=key),sorted(expected,key=key)):
        for p,q in zip(a,b): assert p==pytest.approx(q,abs=1e-8)


def test_no_tatami_underlay_compensation_or_gradient_is_added():
    obj=shape(); original=generate(Project(objects=[obj]))
    obj.underlay=False; obj.pull_compensation=1; obj.density_gradient=True
    assert generate(Project(objects=[obj]))==original
    rotated=transform_selection([obj],1,90,'hoop')[0]
    for a,b in zip(list(pattern_fill_paths(obj)),list(pattern_fill_paths(rotated))):
        for p,q in zip(a,b): assert q==pytest.approx((-p[1],p[0]))


def test_pattern_complexity_limits_and_schema():
    obj=shape(); obj.width=obj.height=500; obj.motif_spacing=obj.motif_row_spacing=.5
    with pytest.raises(ValueError,match='5,000'): list(pattern_fill_paths(obj))
    obj=shape(); obj.motif_row_spacing=0
    with pytest.raises(ValueError): Project.loads(Project(objects=[obj]).dumps())
    obj=DesignObject(kind='path',stitch_type='pattern',points=[[-.5,-.5],[.5,.5]])
    with pytest.raises(ValueError): Project.loads(Project(objects=[obj]).dumps())


def test_native_custom_area_pattern_apply_and_undo():
    from morale.app import MainWindow
    window=MainWindow(); obj=shape()
    try:
        window.replace_project(Project(objects=[obj])); window.select(obj.id)
        assert window.fields['motif_row_spacing'].isEnabled()
        before=window.project.dumps()
        window.captured_motif={'format':'morale-motif','version':1,'name':'Corner','paths':[[[-.5,-.5],[.5,-.5],[.5,.5]]]}
        window.apply_custom_motif()
        assert window.project.objects[0].stitch_type=='pattern'
        assert window.project.objects[0].motif_pattern=='custom'
        window.undo(); assert window.project.dumps()==before
        window.fields['motif_row_spacing'].setValue(7)
        assert window.project.objects[0].motif_row_spacing==7
        window.undo(); assert window.project.dumps()==before
    finally:
        window.saved=window.project.dumps(); window.close()


@pytest.mark.parametrize('extension',['dst','exp','jef','pec','pes','tbf','u01','vp3','xxx'])
def test_pattern_fill_export_sewn_bounds_and_hole_points(tmp_path,extension):
    from morale.formats import export_machine,import_machine
    obj=shape(); obj.angle=23
    project=Project(objects=[obj]); path=tmp_path/f'pattern.{extension}'
    export_machine(project,path)
    decoded=import_machine(path).project
    def sewn(project): return [s for b in generate(project) for s in b.stitches if s.command=='stitch']
    def bounds(points): return min(s.x for s in points),min(s.y for s in points),max(s.x for s in points),max(s.y for s in points)
    points=sewn(decoded)
    assert points and bounds(points)==pytest.approx(bounds(sewn(project)),abs=.15)
    assert all(not(abs(s.x)<4.3 and abs(s.y)<4.3) for s in points)


def test_clipping_budget_rejects_excessively_complex_custom_fill():
    obj=shape(); obj.motif_pattern='custom'
    obj.custom_motif_paths=[[[(-.5 if i%2 else .5),i/1999-0.5] for i in range(2000)]]
    obj.motif_spacing=obj.motif_row_spacing=1
    with pytest.raises(ValueError,match='complex'): list(pattern_fill_paths(obj))


def test_legacy_project_has_no_pattern_setting_requirement():
    import json
    obj=DesignObject()
    packet=json.loads(Project(objects=[obj]).dumps())
    for key in ('motif_row_spacing','pattern_flip_x','pattern_flip_y'): packet['objects'][0].pop(key)
    restored=Project.loads(json.dumps(packet))
    assert generate(restored)==generate(Project(objects=[obj]))
