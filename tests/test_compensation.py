import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from copy import deepcopy
import math

import pytest
from PySide6.QtWidgets import QApplication

from morale.engine import generate, preflight, fill, satin
from morale.model import DesignObject, Project
from morale.geometry import combine_outlines
from morale.formats import export_machine, import_machine


@pytest.fixture(scope="module", autouse=True)
def app():
    return QApplication.instance() or QApplication([])


def rectangle(**kwargs):
    return DesignObject(kind="rectangle", width=20, height=20, angle=0, underlay=False, **kwargs)


def extents(stitches, angle=0):
    c,s = math.cos(math.radians(angle)),math.sin(math.radians(angle))
    points = [(p.x*c+p.y*s, -p.x*s+p.y*c) for p in stitches]
    return min(x for x,y in points), max(x for x,y in points), min(y for x,y in points), max(y for x,y in points)


@pytest.mark.parametrize("angle", [0,37,90])
def test_fill_expands_along_stitch_direction_without_changing_outline(angle):
    obj = rectangle()
    obj.angle = angle
    original_outline = obj.rings()
    original = generate(Project(objects=[obj]))[0].stitches
    obj.pull_compensation = .35
    compensated = generate(Project(objects=[obj]))[0].stitches
    a,b,c,d = extents(original,angle)
    assert extents(compensated,angle) == pytest.approx((a-.35,b+.35,c,d))
    assert obj.rings() == original_outline


def test_compensation_zero_retains_default_commands():
    points = [(-10,-10),(10,-10),(10,10),(-10,10)]
    assert fill(points,.4,2,37) == fill(points,.4,2,37,compensation=0)
    rails = [(-3,-10),(3,-10),(-3,10),(3,10)]
    assert satin(rails,.4,4) == satin(rails,.4,4,compensation=0)


def test_underlay_stays_on_original_outline():
    obj = rectangle(pull_compensation=.5)
    top = generate(Project(objects=[obj]))[0].stitches
    obj.underlay = True
    together = generate(Project(objects=[obj]))[0].stitches
    underlay = together[:-len(top)]
    assert underlay and extents(underlay) == pytest.approx((-10,10,-10,10))
    assert together[-len(top):] == top


def test_hole_shrinks_but_connectors_do_not_cross_remaining_gap():
    obj = combine_outlines([rectangle(), DesignObject(kind="rectangle",width=10,height=10)],"subtract")
    obj.pull_compensation = .4
    obj.connect_fill = True
    previous = None
    for stitch in generate(Project(objects=[obj]))[0].stitches:
        if stitch.command == "stitch" and previous:
            for t in [.1,.3,.5,.7,.9]:
                x,y = previous.x+t*(stitch.x-previous.x),previous.y+t*(stitch.y-previous.y)
                assert not(abs(x)<4.59 and abs(y)<4.99)
        previous=stitch


def test_overlapping_compensated_spans_merge_without_duplicate_rows():
    outer = [(-5,-5),(5,-5),(5,5),(-5,5)]
    hole = [(-.2,-4),(.2,-4),(.2,4),(-.2,4)]
    stitches = fill(outer,1,2,0,holes=[hole],compensation=.3)
    assert sum(s.command=="jump" for s in stitches) == 10
    assert extents(stitches)[:2] == pytest.approx((-5.3,5.3))


def test_satin_expands_rails_and_still_splits_long_spans():
    points = [(-3,-10),(3,-10),(-3,10),(3,10)]
    stitches = satin(points,.4,3,compensation=.5)
    assert extents(stitches)[:2] == pytest.approx((-3.5,3.5))
    assert all(math.dist((a.x,a.y),(b.x,b.y)) <= 3.000001 for a,b in zip(stitches,stitches[1:]) if b.command=="stitch")


def test_tapered_satin_tip_remains_a_point():
    points = [(0,-10),(0,-10),(-3,10),(3,10)]
    stitches = satin(points,.4,6,compensation=.5)
    assert (stitches[0].x,stitches[0].y) == (0,-10)


def test_compensated_hoop_overflow_is_rejected(tmp_path):
    obj = rectangle(pull_compensation=.5)
    project = Project(hoop_width=20,hoop_height=20,objects=[obj])
    assert preflight(project,generate(project))
    with pytest.raises(ValueError,match="hoop"):
        export_machine(project,tmp_path/'overflow.dst')
    assert not (tmp_path/'overflow.dst').exists()


@pytest.mark.parametrize("value", [-.1,2.1,float('nan'),True])
def test_invalid_compensation_not_saved(value):
    with pytest.raises(ValueError):
        Project.loads(Project(objects=[rectangle(pull_compensation=value)]).dumps())


def test_native_property_units_undo_and_project_persistence():
    from morale.app import MainWindow
    window=MainWindow()
    try:
        obj=rectangle()
        window.replace_project(Project(objects=[obj]))
        window.select(obj.id)
        window.fields['pull_compensation'].setValue(.25)
        assert window.project.objects[0].pull_compensation == .25
        snapshot=window.project.dumps()
        window.set_unit('in')
        assert window.project.dumps()==snapshot
        window.fields['pull_compensation'].setValue(.02)
        assert window.project.objects[0].pull_compensation == pytest.approx(.508)
        window.undo()
        assert window.project.dumps()==snapshot
        assert Project.loads(snapshot).objects[0].pull_compensation==.25
    finally:
        window.saved=window.project.dumps()
        window.close()


@pytest.mark.parametrize("extension", ['dst','exp','jef','pec','pes','tbf','u01','vp3','xxx'])
def test_compensation_survives_machine_export(tmp_path,extension):
    obj=rectangle(pull_compensation=.5)
    path=tmp_path/f'compensated.{extension}'
    export_machine(Project(objects=[obj]),path)
    blocks=generate(import_machine(path).project)
    a,b,_,_=extents([s for block in blocks for s in block.stitches])
    assert (a,b)==pytest.approx((-10.5,10.5),abs=.15)
