import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import math

import pytest
from PySide6.QtWidgets import QApplication

from morale.engine import generate, generate_underlay, running
from morale.model import DesignObject, Project
from morale.geometry import combine_outlines
from morale.formats import export_machine, import_machine
from morale.underlay import inset_rings


@pytest.fixture(scope="module",autouse=True)
def app():
    return QApplication.instance() or QApplication([])


def rectangle(**kwargs):
    return DesignObject(kind='rectangle',width=30,height=20,angle=0,**kwargs)


def rails(**kwargs):
    return DesignObject(kind='satin',stitch_type='satin',width=10,height=20,
                        points=[[-.5,-.5],[.5,-.5],[-.5,.5],[.5,.5]],**kwargs)


def test_default_underlay_retains_original_sequences():
    obj=rectangle()
    assert generate_underlay(obj)==running(obj.outline(),obj.stitch_length)
    obj=rails()
    assert generate_underlay(obj)==running([(0,-10),(0,10)],obj.stitch_length,closed=False)


def test_inset_edge_run_is_set_back_from_all_sides():
    obj=rectangle(underlay_inset=1.5)
    stitches=generate_underlay(obj)
    assert (min(s.x for s in stitches),max(s.x for s in stitches))==pytest.approx((-13.5,13.5))
    assert (min(s.y for s in stitches),max(s.y for s in stitches))==pytest.approx((-8.5,8.5))


@pytest.mark.parametrize('style',['edge','sparse','edge_sparse'])
def test_underlay_respects_holes_and_inset(style):
    obj=combine_outlines([rectangle(),DesignObject(kind='rectangle',width=8,height=8)],'subtract')
    obj.underlay_style=style
    obj.underlay_inset=1
    stitches=generate_underlay(obj)
    assert stitches
    previous=None
    for s in stitches:
        assert abs(s.x)<=14.001 and abs(s.y)<=9.001
        if s.command=='stitch' and previous:
            for t in [.1,.3,.5,.7,.9]:
                x,y=previous.x+t*(s.x-previous.x),previous.y+t*(s.y-previous.y)
                assert not(abs(x)<4.7 and abs(y)<4.7)
                assert math.hypot(max(0,abs(x)-4),max(0,abs(y)-4)) >= .97
        previous=s


def test_sparse_fill_is_perpendicular_to_cover_and_uses_requested_spacing():
    obj=rectangle(underlay_style='sparse',underlay_spacing=3)
    stitches=generate_underlay(obj)
    starts=[s for s in stitches if s.command=='jump']
    assert len(starts)==10
    assert all(abs(a.x-b.x)==pytest.approx(3) for a,b in zip(starts,starts[1:]))
    assert all(abs(a.x-b.x)<1e-8 for a,b in zip(stitches,stitches[1:]) if b.command=='stitch')


def test_narrow_inset_omits_underlay_without_losing_cover():
    obj=DesignObject(kind='rectangle',width=1,height=10,underlay_inset=1)
    assert generate_underlay(obj)==[]
    assert any(s.command=='stitch' for b in generate(Project(objects=[obj])) for s in b.stitches)


@pytest.mark.parametrize('style',['zigzag','center_zigzag'])
def test_satin_zigzag_setback_and_length_limits(style):
    obj=rails(underlay_style=style,underlay_inset=1,underlay_spacing=2,satin_max=3)
    stitches=generate_underlay(obj)
    assert min(s.x for s in stitches)==pytest.approx(-4)
    assert max(s.x for s in stitches)==pytest.approx(4)
    assert all(math.dist((a.x,a.y),(b.x,b.y))<=3.000001 for a,b in zip(stitches,stitches[1:]) if b.command=='stitch')
    if style=='center_zigzag':
        assert stitches[:len(running([(0,-10),(0,10)],obj.stitch_length,False))]==running([(0,-10),(0,10)],obj.stitch_length,False)


def test_collapsed_satin_underlay_falls_back_to_center_run():
    obj=rails(underlay_style='zigzag',underlay_inset=3)
    obj.width=2
    stitches=generate_underlay(obj)
    assert stitches and all(s.x==0 for s in stitches)


def test_compensation_only_changes_cover():
    obj=rectangle(underlay_style='edge_sparse',underlay_inset=1)
    before=generate_underlay(obj)
    obj.pull_compensation=.5
    assert generate_underlay(obj)==before


@pytest.mark.parametrize('key,value',[('underlay_inset',-1),('underlay_inset',4),('underlay_spacing',0),('underlay_style',[]),('underlay_style','unknown')])
def test_invalid_underlay_settings_rejected(key,value):
    obj=rectangle()
    setattr(obj,key,value)
    with pytest.raises(ValueError):
        Project.loads(Project(objects=[obj]).dumps())


def test_native_underlay_edit_units_undo_and_persistence():
    from morale.app import MainWindow
    window=MainWindow()
    try:
        obj=rectangle()
        window.replace_project(Project(objects=[obj]))
        window.select(obj.id)
        window.underlay_style.setCurrentIndex(window.underlay_style.findData('edge_sparse'))
        window.fields['underlay_inset'].setValue(1)
        snapshot=window.project.dumps()
        window.set_unit('in')
        assert window.project.dumps()==snapshot
        assert window.fields['underlay_inset'].value()==pytest.approx(1/25.4,abs=.0001)
        window.undo()
        assert window.project.objects[0].underlay_inset==0
        restored=Project.loads(snapshot).objects[0]
        assert restored.underlay_inset==1 and restored.underlay_style=='edge_sparse'
    finally:
        window.saved=window.project.dumps()
        window.close()


@pytest.mark.parametrize('extension',['dst','exp','jef','pec','pes','tbf','u01','vp3','xxx'])
def test_underlay_and_cover_export_in_all_formats(tmp_path,extension):
    obj=rectangle(underlay_style='edge_sparse',underlay_inset=1)
    path=tmp_path/f'underlay.{extension}'
    export_machine(Project(objects=[obj]),path)
    result=generate(import_machine(path).project)
    sewn=[s for b in result for s in b.stitches if s.command=='stitch']
    assert sewn
    assert any(abs(abs(s.x)-14)<.15 for s in sewn)
    assert any(abs(abs(s.x)-15)<.15 for s in sewn)
