import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import math
from copy import deepcopy
import pytest
from PySide6.QtWidgets import QApplication
from morale.density import fill_rows
from morale.model import Project,DesignObject
from morale.engine import generate,generate_underlay,segment_inside
from morale.arrange import mirror,transform_selection


@pytest.fixture(scope='module',autouse=True)
def app():
    return QApplication.instance() or QApplication([])


def shape():
    return DesignObject(kind='rectangle',width=30,height=40,angle=0,spacing=.4,density_gradient=True,gradient_end_spacing=2,underlay=False)


def test_uniform_rows_and_equal_endpoints_are_unchanged():
    assert fill_rows(-10,10,.45)==[-10+.45*(i+.5) for i in range(45) if -10+.45*(i+.5)<10]
    obj=shape(); obj.gradient_end_spacing=obj.spacing
    legacy=deepcopy(obj); legacy.density_gradient=False
    assert generate(Project(objects=[obj]))==generate(Project(objects=[legacy]))


@pytest.mark.parametrize('start,end',[(.2,5),(5,.2),(.45,1.5),(.45,.4500000000000001)])
def test_rows_integrate_linear_spacing_and_stay_inside(start,end):
    rows=fill_rows(-20,20,start,end)
    assert rows and all(-20<y<20 for y in rows)
    assert all(a<b for a,b in zip(rows,rows[1:]))
    slope=(end-start)/40
    def density(y): return math.log1p(slope*(y+20)/start)/slope
    for a,b in zip(rows,rows[1:]): assert density(b)-density(a)==pytest.approx(1,abs=1e-10)
    gaps=[b-a for a,b in zip(rows,rows[1:])]
    if end>start: assert gaps[0]<=gaps[-1]
    else: assert gaps[0]>=gaps[-1]


def test_reverse_gradient_is_exact_geometric_reflection():
    rows=fill_rows(-20,20,.4,2)
    reverse=fill_rows(-20,20,.4,2,True)
    assert reverse==pytest.approx([-y for y in reversed(rows)],abs=1e-12)


def test_gradient_holes_and_connectors_respect_material():
    obj=shape(); obj.kind='compound'; obj.connect_fill=True
    obj.contours=[[[-.5,-.5],[.5,-.5],[.5,.5],[-.5,.5]],[[-.2,-.2],[.2,-.2],[.2,.2],[-.2,.2]]]
    rings=obj.rings()
    stitches=generate(Project(objects=[obj]))[0].stitches
    for a,b in zip(stitches,stitches[1:]):
        if b.command=='stitch': assert segment_inside((a.x,a.y),(b.x,b.y),rings[0],rings[1:])


def test_underlay_not_changed_and_spacing_settings_persist():
    obj=shape(); obj.underlay=True; obj.underlay_style='edge_sparse'
    original=deepcopy(obj); original.density_gradient=False
    assert generate_underlay(obj)==generate_underlay(original)
    assert generate(Project(objects=[obj]))!=generate(Project(objects=[original]))
    assert Project.loads(Project(objects=[obj]).dumps()).objects[0]==obj


@pytest.mark.parametrize('axis',['horizontal','vertical'])
@pytest.mark.parametrize('rotation',[0,37])
def test_mirror_keeps_density_on_corresponding_side(axis,rotation):
    obj=shape(); obj.angle=31; obj.rotation=rotation
    mirrored=mirror(obj,axis)
    # Row order can reverse, so compare the complete set of row spans.
    def endpoints(source):
        stitches=generate(Project(objects=[source]))[0].stitches
        starts=[(s.x,s.y) for s in stitches if s.command=='jump']
        ends=[(a.x,a.y) for a,b in zip(stitches,stitches[1:]) if b.command=='jump']+[(stitches[-1].x,stitches[-1].y)]
        return [tuple(sorted((a,b),key=lambda p:(round(p[0],8),round(p[1],8)))) for a,b in zip(starts,ends)]
    expected=[]
    for span in endpoints(obj):
        expected.append(tuple(sorted((((-x,y) if axis=='horizontal' else (x,-y)) for x,y in span),key=lambda p:(round(p[0],8),round(p[1],8)))))
    key=lambda span:tuple(round(v,8) for p in span for v in p)
    assert len(endpoints(mirrored))==len(expected)
    for actual,target in zip(sorted(endpoints(mirrored),key=key),sorted(expected,key=key)):
        for a,b in zip(actual,target): assert a==pytest.approx(b,abs=1e-9)
    assert mirror(mirrored,axis)==obj


def test_rotation_carries_gradient_axis():
    obj=shape()
    rotated=transform_selection([obj],1,90,'hoop')[0]
    original=generate(Project(objects=[obj]))[0].stitches
    result=generate(Project(objects=[rotated]))[0].stitches
    assert len(original)==len(result)
    for a,b in zip(original,result): assert (b.x,b.y)==pytest.approx((-a.y,a.x),abs=1e-10)


@pytest.mark.parametrize('key,value',[('density_gradient',1),('gradient_reverse','yes'),('gradient_end_spacing',0),('gradient_end_spacing',6),('gradient_end_spacing',float('inf'))])
def test_invalid_gradient_project_rejected(key,value):
    obj=shape(); setattr(obj,key,value)
    with pytest.raises(ValueError): Project.loads(Project(objects=[obj]).dumps())


def test_native_gradient_controls_and_undo():
    from morale.app import MainWindow
    window=MainWindow(); obj=shape(); obj.density_gradient=False
    try:
        window.replace_project(Project(objects=[obj])); window.select(obj.id)
        before=window.project.dumps()
        window.density_gradient.setChecked(True)
        window.fields['gradient_end_spacing'].setValue(1.25)
        assert window.project.objects[0].density_gradient
        assert window.project.objects[0].gradient_end_spacing==1.25
        window.undo(); window.undo(); assert window.project.dumps()==before
    finally:
        window.saved=window.project.dumps(); window.close()


@pytest.mark.parametrize('extension',['dst','exp','jef','pec','pes','tbf','u01','vp3','xxx'])
def test_gradient_exports_with_retained_sewn_bounds(tmp_path,extension):
    from morale.formats import export_machine,import_machine
    obj=shape(); obj.angle=23
    project=Project(objects=[obj])
    path=tmp_path/f'gradient.{extension}'; export_machine(project,path)
    def sewn_bounds(project):
        sewn=[s for b in generate(project) for s in b.stitches if s.command=='stitch']
        return min(s.x for s in sewn),min(s.y for s in sewn),max(s.x for s in sewn),max(s.y for s in sewn)
    assert sewn_bounds(import_machine(path).project)==pytest.approx(sewn_bounds(project),abs=.15)


@pytest.mark.parametrize('args',[(0,10,0),(0,10,float('nan')),(0,10,.4,6),(0,10,.4,True),(-1e308,1e308,.4,1.5),(0,10,.4,1.5,'yes')])
def test_invalid_row_generator_settings(args):
    with pytest.raises(ValueError): fill_rows(*args)


def test_legacy_project_without_gradient_fields_keeps_default_fill():
    import json
    obj=shape(); obj.density_gradient=False
    data=json.loads(Project(objects=[obj]).dumps())
    for key in ('density_gradient','gradient_end_spacing','gradient_reverse'): data['objects'][0].pop(key)
    restored=Project.loads(json.dumps(data))
    assert not restored.objects[0].density_gradient
    assert generate(restored)==generate(Project(objects=[obj]))
