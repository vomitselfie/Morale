import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import math

import pytest

from morale.engine import Stitch, generate, generate_object, generate_underlay, satin
from morale.generated import GeneratedRun, plan_column
from morale.model import DesignObject, Project


def rails(**kwargs):
    return DesignObject(kind='satin', stitch_type='satin', width=10, height=40,
                        points=[[-.5, -.5], [.5, -.5], [-.5, .5], [.5, .5]], **kwargs)


def longest_move(stitches, command):
    return max((math.dist((a.x, a.y), (b.x, b.y)) for a, b in zip(stitches, stitches[1:]) if b.command == command), default=0)


def test_reversed_run_sews_same_segments_backwards():
    run = GeneratedRun([Stitch(0, 0, "jump"), Stitch(1, 0, "stitch"), Stitch(5, 0, "jump"), Stitch(6, 0, "stitch")], "underlay", True)
    back = run.reversed()
    assert [(s.x, s.y, s.command) for s in back.stitches] == [(6, 0, "jump"), (5, 0, "stitch"), (1, 0, "jump"), (0, 0, "stitch")]
    assert back.reversed() == run


def test_only_reversible_motion_runs_can_be_reversed():
    with pytest.raises(ValueError):
        GeneratedRun([Stitch(0, 0, "jump"), Stitch(1, 0, "stitch")], "top").reversed()
    with pytest.raises(ValueError):
        GeneratedRun([Stitch(0, 0, "jump"), Stitch(0, 0, "trim")], "top", True).reversed()


@pytest.mark.parametrize("style", ["auto", "zigzag", "center_zigzag"])
def test_satin_column_starts_and_ends_at_top_start_without_jump_back(style):
    obj = rails(underlay_style=style)
    planned = generate_object(obj)
    top = planned.runs[-1]
    assert top.kind == "top" and all(run.kind == "underlay" for run in planned.runs[:-1])
    # The top pass keeps the direction the user drew.
    assert top.stitches == satin(obj.transform(obj.points), obj.spacing, obj.satin_max, obj.pull_compensation)
    # Each pass starts at the end of the column where the previous one finished.
    assert math.dist(planned.entry, top.entry) <= obj.width / 2 + 1e-6
    for previous, run in zip(planned.runs, planned.runs[1:]):
        assert math.dist(previous.exit, run.entry) <= obj.width / 2 + 1e-6
    # No jump runs the length of the column back to its start.
    stitches = generate(Project(objects=[obj]))[0].stitches
    assert longest_move(stitches, "jump") <= obj.width / 2 + 1e-6


def test_flat_underlay_keeps_natural_pass_order():
    obj = rails(underlay_style="center_zigzag")
    flat = generate_underlay(obj)
    assert (flat[0].x, flat[0].y) == pytest.approx((0, -20))
    planned = [s for run in generate_object(obj).runs[:-1] for s in run.stitches]
    # Planning only reorients passes: the same needle positions, no extra pass.
    assert sorted((s.x, s.y) for s in planned) == sorted((s.x, s.y) for s in flat)


def test_satin_without_underlay_is_only_top():
    obj = rails(underlay=False)
    assert [run.kind for run in generate_object(obj).runs] == ["top"]


def test_plan_without_return_pass_keeps_jump():
    top = GeneratedRun([Stitch(0, 0, "jump"), Stitch(0, 10, "stitch")], "top", True)
    under = GeneratedRun([Stitch(0, 0, "jump"), Stitch(0, 10, "stitch")], "underlay", True)
    assert plan_column([under], top) == [under, top]
    out, back = plan_column([under], top, center=under)[:2]
    assert out.exit == back.entry and back.exit == top.entry


def test_plan_omits_return_when_underlay_already_ends_at_start():
    top = GeneratedRun([Stitch(-5, 0, "jump"), Stitch(5, 1, "stitch"), Stitch(-5, 20, "stitch")], "top", True)
    center = GeneratedRun([Stitch(0, 0, "jump"), Stitch(0, 20, "stitch")], "underlay", True)
    zigzag = GeneratedRun([Stitch(-4, 0, "jump"), Stitch(4, 20, "stitch")], "underlay", True)
    planned = plan_column([center, zigzag], top, center)
    assert len(planned) == 3 and planned[1].exit == (-4, 0)


def test_fill_objects_lower_unchanged():
    obj = DesignObject(kind='rectangle', width=30, height=20, angle=0)
    planned = generate_object(obj)
    assert [run.kind for run in planned.runs] == ["underlay", "top"]
    assert planned.runs[0].stitches == generate_underlay(obj)
    assert not any(run.reversible for run in planned.runs)
