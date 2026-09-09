import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import math

import pytest
from PySide6.QtWidgets import QApplication

from morale.engine import generate,contour_fill
from morale.model import Project,DesignObject
from morale.geometry import combine_outlines
from morale.formats import export_machine,import_machine


@pytest.fixture(scope='module',autouse=True)
def app():
    return QApplication.instance() or QApplication([])


def rectangle(**kwargs):
    return DesignObject(kind='rectangle',width=10,height=10,stitch_type='contour',underlay=False,spacing=1,**kwargs)


def runs(stitches):
    result=[]
    for stitch in stitches:
        if stitch.command=='jump':
            result.append([stitch])
        elif stitch.command=='stitch':
            result[-1].append(stitch)
    return result


def test_rectangular_layers_are_closed_and_spaced_inward():
    obj=rectangle()
    layers=runs(generate(Project(objects=[obj]))[0].stitches)
    assert len(layers)==5
    widths=[]
    for layer in layers:
        assert (layer[0].x,layer[0].y)==pytest.approx((layer[-1].x,layer[-1].y))
        widths.append(max(s.x for s in layer)-min(s.x for s in layer))
        assert all(math.dist((a.x,a.y),(b.x,b.y))<=obj.stitch_length+1e-8 for a,b in zip(layer,layer[1:]))
    assert widths==pytest.approx([9,7,5,3,1])


def test_rotation_keeps_physical_offset_distance():
    obj=rectangle(rotation=37)
    a=math.radians(37)
    first=runs(generate(Project(objects=[obj]))[0].stitches)[0]
    x=[s.x*math.cos(a)+s.y*math.sin(a) for s in first]
    y=[-s.x*math.sin(a)+s.y*math.cos(a) for s in first]
    assert (min(x),max(x),min(y),max(y))==pytest.approx((-4.5,4.5,-4.5,4.5),abs=.01)


def test_holes_and_disjoint_components_are_not_sewn_across():
    outer=DesignObject(kind='rectangle',width=20,height=20,underlay=False)
    hole=DesignObject(kind='rectangle',width=8,height=8)
    obj=combine_outlines([outer,hole],'subtract')
    obj=combine_outlines([obj,DesignObject(kind='rectangle',width=10,height=10,x=30)],'union')
    obj.stitch_type='contour'
    obj.spacing=1
    stitches=generate(Project(objects=[obj]))[0].stitches
    assert len(runs(stitches))>5
    previous=None
    for s in stitches:
        if s.command=='stitch' and previous:
            for t in [.1,.3,.5,.7,.9]:
                x,y=previous.x+t*(s.x-previous.x),previous.y+t*(s.y-previous.y)
                assert not(abs(x)<3.99 and abs(y)<3.99)
                assert not 10.01<x<24.99
        previous=s


def test_increasing_spacing_reduces_layers_and_ignores_tatami_compensation():
    obj=rectangle()
    original=generate(Project(objects=[obj]))
    obj.pull_compensation=1
    obj.connect_fill=True
    assert generate(Project(objects=[obj]))==original
    obj.spacing=2
    assert len(runs(generate(Project(objects=[obj]))[0].stitches))==2


def test_command_limit_is_enforced(monkeypatch):
    import morale.engine as engine
    monkeypatch.setattr(engine,'MAX_STITCHES',20)
    with pytest.raises(ValueError,match='command limit'):
        contour_fill(rectangle().rings(),.2,.5)


def test_native_contour_choice_controls_undo_and_persistence():
    from morale.app import MainWindow
    window=MainWindow()
    try:
        obj=DesignObject(kind='rectangle')
        window.replace_project(Project(objects=[obj]))
        window.select(obj.id)
        before=window.project.dumps()
        window.stitch_type.setCurrentIndex(window.stitch_type.findData('contour'))
        assert window.project.objects[0].stitch_type=='contour'
        assert window.fields['spacing'].isEnabled()
        assert not window.fields['pull_compensation'].isEnabled()
        assert not window.finishing['connect_fill'].isEnabled()
        assert Project.loads(window.project.dumps()).objects[0].stitch_type=='contour'
        window.undo()
        assert window.project.dumps()==before
    finally:
        window.saved=window.project.dumps()
        window.close()


@pytest.mark.parametrize('extension',['dst','exp','jef','pec','pes','tbf','u01','vp3','xxx'])
def test_contour_fill_exports_in_all_formats(tmp_path,extension):
    path=tmp_path/f'contour.{extension}'
    export_machine(Project(objects=[rectangle()]),path)
    stitches=[s for b in generate(import_machine(path).project) for s in b.stitches if s.command=='stitch']
    assert stitches
    assert (min(s.x for s in stitches),max(s.x for s in stitches),min(s.y for s in stitches),max(s.y for s in stitches))==pytest.approx((-4.5,4.5,-4.5,4.5),abs=.15)
