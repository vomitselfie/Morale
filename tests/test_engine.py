import math

import pytest

from morale.engine import fill, generate, preflight, running
from morale.model import DesignObject, Project, demo_project


def test_demo_is_inside_hoop_and_has_four_threads():
    project = demo_project()
    blocks = generate(project)
    assert len(blocks) == 10
    assert len({b.color for b in blocks}) == 4
    assert not preflight(project, blocks)
    assert sum(len(b.stitches) for b in blocks) > 1000


@pytest.mark.parametrize("angle", [0, 31, 90, 165])
def test_fill_spacing_bounds_and_max_length(angle):
    obj = DesignObject(kind="rectangle", width=18, height=24, angle=angle, underlay=False)
    stitches = generate(Project(objects=[obj]))[0].stitches
    assert stitches
    for previous, current in zip(stitches, stitches[1:]):
        assert abs(current.x) <= 9 + 1e-6
        assert abs(current.y) <= 12 + 1e-6
        if current.command == "stitch":
            assert math.dist((previous.x, previous.y), (current.x, current.y)) <= obj.stitch_length + 1e-6


def test_concave_fill_jumps_across_gap():
    # U-shaped polygon: the middle of the upper rows must never be sewn across.
    polygon = [(0, 0), (2, 0), (2, 7), (8, 7), (8, 0), (10, 0), (10, 10), (0, 10)]
    stitches = fill(polygon, .5, 2, 0)
    for a, b in zip(stitches, stitches[1:]):
        if b.command == "stitch" and b.y < 7:
            assert max(a.x, b.x) <= 2 or min(a.x, b.x) >= 8


def test_running_path_is_open_and_resampled():
    stitches = running([(0, 0), (10, 0)], 2.5, closed=False)
    assert [(s.x, s.y) for s in stitches] == [(0, 0), (2.5, 0), (5, 0), (7.5, 0), (10, 0)]
    assert stitches[0].command == "jump"


def test_running_stitch_preserves_sharp_corners():
    stitches = running([(0, 0), (3, 0), (3, 3)], 2.5, closed=False)
    assert (3, 0) in [(s.x, s.y) for s in stitches]
    assert all(s.x == 3 or s.y == 0 for s in stitches)


def test_resize_regenerates_stitches():
    obj = DesignObject(width=10, height=10)
    project = Project(objects=[obj])
    small = len(generate(project)[0].stitches)
    obj.width = obj.height = 30
    assert len(generate(project)[0].stitches) > small * 4


def test_preflight_and_visibility():
    obj = DesignObject(x=60)
    project = Project(objects=[obj])
    assert "beyond" in preflight(project, generate(project))[0]
    obj.visible = False
    assert generate(project) == []
    assert "no stitches" in preflight(project, [])[0]


def test_fill_budget():
    with pytest.raises(ValueError, match="limit"):
        generate(Project(objects=[DesignObject(kind="rectangle", width=500, height=500, spacing=.2, stitch_length=.5)]))
