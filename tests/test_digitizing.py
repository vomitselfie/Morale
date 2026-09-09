import math

import pytest

from morale.engine import Stitch, fill, finish_stitches, generate, running, satin, triple_run, segment_inside
from morale.model import DesignObject, Project


def test_triple_running_retraces_each_segment_and_keeps_endpoint():
    basic = running([(0, 0), (6, 0)], 2, closed=False)
    triple = triple_run(basic)
    assert [s.x for s in triple] == [0, 2, 0, 2, 4, 2, 4, 6, 4, 6]
    assert triple[0].command == "jump"
    assert all(s.command == "stitch" for s in triple[1:])


@pytest.mark.parametrize("maximum", [1, 3, 6, 12])
def test_satin_follows_variable_width_rails_and_splits_long_stitches(maximum):
    points = [(-2, 0), (2, 0), (-4, 10), (4, 10), (-1, 20), (1, 20)]
    result = satin(points, .4, maximum)
    assert result[0].command == "jump"
    assert max(s.y for s in result) == pytest.approx(20)
    assert min(s.x for s in result) < -3.8
    assert max(s.x for s in result) > 3.8
    for previous, current in zip(result, result[1:]):
        assert math.dist((previous.x, previous.y), (current.x, current.y)) <= maximum + 1e-8
        width = 2 + .2 * current.y if current.y <= 10 else 4 - .3 * (current.y - 10)
        assert abs(current.x) <= width + 1e-8


def test_satin_spacing_controls_density():
    points = [(-2, 0), (2, 0), (-2, 20), (2, 20)]
    fine = satin(points, .3, 12)
    coarse = satin(points, .6, 12)
    assert len(fine) == pytest.approx(2 * len(coarse), abs=2)


@pytest.mark.parametrize("points", [
    [(-2, 0), (2, 0), (2, 10), (-2, 10)],
    [(0, 0), (0, 0), (0, 10), (0, 10)],
    [(-2, 0), (2, 0), (-2, 10)],
    [(-2, 0), (2, 0), (-2, 10), (2, 10), (-2, 5), (2, 5)],
])
def test_invalid_satin_rails_are_rejected(points):
    with pytest.raises(ValueError, match="Satin"):
        satin(points, .4, 6)


def test_tapered_satin_tip_is_supported():
    result = satin([(0, 0), (0, 0), (-3, 10), (3, 10)], .4, 6)
    assert len(result) > 40
    assert all(abs(s.x) <= .3 * s.y + 1e-8 for s in result)


def test_finishing_locks_each_run_without_sewing_across_travel():
    original = [Stitch(0, 0, "jump"), Stitch(3, 0), Stitch(20, 0, "jump"), Stitch(23, 0)]
    finished = finish_stitches(original, tie_in=True, tie_off=True, trim_after=True)
    assert sum(s.command == "stitch" for s in finished) == 18
    assert sum(s.command == "jump" for s in finished) == 2
    assert finished[-1] == Stitch(23, 0, "trim")
    for a, b in zip(finished, finished[1:]):
        if b.command == "stitch":
            assert math.dist((a.x, a.y), (b.x, b.y)) <= 3
            assert max(a.x, b.x) <= 3 or min(a.x, b.x) >= 20


def test_finishing_defaults_preserve_existing_designs():
    original = [Stitch(0, 0, "jump"), Stitch(3, 0), Stitch(8, 0, "jump"), Stitch(9, 0)]
    assert finish_stitches(original) == original


def test_imported_stitches_are_not_modified_by_finishing_controls():
    obj = DesignObject(kind="stitches", stitch_type="manual", stitch_data=[[-.5, 0, "jump"], [.5, 0, "stitch"]], tie_in=True, tie_off=True, trim_after=True)
    assert len(generate(Project(objects=[obj]))[0].stitches) == 2


def test_satin_project_roundtrip_includes_settings_and_center_underlay():
    obj = DesignObject(kind="satin", stitch_type="satin", width=6, height=20,
                       points=[[-.5, -.5], [.5, -.5], [-.5, .5], [.5, .5]],
                       tie_in=True, tie_off=True, trim_after=True, satin_max=4)
    project = Project.loads(Project(objects=[obj]).dumps())
    stitches = generate(project)[0].stitches
    assert stitches[0] == Stitch(0, -10, "jump")
    assert stitches[-1].command == "trim"
    assert project.objects[0].satin_max == 4


@pytest.mark.parametrize("key,value", [("tie_in", "true"), ("tie_off", 1), ("trim_after", []), ("satin_max", 0)])
def test_invalid_finishing_settings_rejected(key, value):
    obj = DesignObject()
    setattr(obj, key, value)
    with pytest.raises(ValueError):
        Project.loads(Project(objects=[obj]).dumps())


def test_convex_fill_connects_rows_without_jumps():
    points = [(0, 0), (10, 0), (10, 10), (0, 10)]
    stitches = fill(points, .4, 2, 0, connect=True)
    assert sum(s.command == "jump" for s in stitches) == 1
    assert sum(s.command == "jump" for s in fill(points, .4, 2, 0)) == 25


def test_connected_fill_never_sews_across_a_concave_gap():
    polygon = [(0, 0), (2, 0), (2, 7), (8, 7), (8, 0), (10, 0), (10, 10), (0, 10)]
    stitches = fill(polygon, .4, 6, 0, connect=True)
    assert sum(s.command == "jump" for s in stitches) > 1
    for a, b in zip(stitches, stitches[1:]):
        if b.command == "stitch":
            assert segment_inside((a.x, a.y), (b.x, b.y), polygon)


def test_connector_checks_narrow_notch_between_sampling_points():
    polygon = [(0, 0), (1.01, 0), (1.01, 5), (1.02, 5), (1.02, 0), (10, 0), (10, 10), (0, 10)]
    assert not segment_inside((0, 2), (10, 2), polygon)
    assert segment_inside((0, 6), (10, 6), polygon)


@pytest.mark.parametrize("extension", ["dst", "exp", "jef", "pec", "pes", "tbf", "u01", "vp3", "xxx"])
def test_digitizing_sampler_roundtrips_through_machine_formats(tmp_path, extension):
    from morale.model import satin_sample
    from morale.formats import export_machine, import_machine
    project = satin_sample()
    expected = [s for b in generate(project) for s in b.stitches if s.command == "stitch"]
    path = tmp_path / f"sampler.{extension}"
    export_machine(project, path)
    restored = generate(import_machine(path).project)
    actual = [s for b in restored for s in b.stitches if s.command == "stitch"]
    assert len(restored) == 3
    assert any(s.command == "trim" for b in restored for s in b.stitches)
    for axis in ["x", "y"]:
        assert min(getattr(s, axis) for s in actual) == pytest.approx(min(getattr(s, axis) for s in expected), abs=.15)
        assert max(getattr(s, axis) for s in actual) == pytest.approx(max(getattr(s, axis) for s in expected), abs=.15)
