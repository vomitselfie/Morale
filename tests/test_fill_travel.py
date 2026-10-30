import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import math

import pytest
from PySide6.QtWidgets import QApplication

from morale.engine import Stitch, generate, segment_inside
from morale.fill_travel import FillTravel, TRAVEL_INSET, travel_inside
from morale.model import DesignObject, Project
from morale.routing import fill_anchors, route_fill


@pytest.fixture(scope="module", autouse=True)
def app():
    return QApplication.instance() or QApplication([])


def frame(**settings):
    """30 mm square with a 12 mm square hole."""
    return DesignObject(kind='compound', width=30, height=30, angle=0, underlay=False,
                        contours=[[[-.5, -.5], [.5, -.5], [.5, .5], [-.5, .5]], [[-.2, -.2], [.2, -.2], [.2, .2], [-.2, .2]]],
                        **settings)


def sewn_outside(obj, stitches):
    rings = obj.rings()
    return [(a, b) for a, b in zip(stitches, stitches[1:])
            if b.command == 'stitch' and not segment_inside((a.x, a.y), (b.x, b.y), rings[0], rings[1:])]


def long_jumps(obj, stitches):
    return [b for a, b in zip(stitches, stitches[1:]) if b.command == 'jump' and math.dist((a.x, a.y), (b.x, b.y)) > obj.stitch_length]


def test_routed_connected_fill_travels_inside_instead_of_jumping():
    routed = frame(route_fill=True)
    connected = frame(route_fill=True, connect_fill=True)
    before = generate(Project(objects=[routed]))[0].stitches
    after = generate(Project(objects=[connected]))[0].stitches
    assert long_jumps(routed, before) and not long_jumps(connected, after)
    assert not sewn_outside(connected, after)
    # Travel adds a little thread, not a pass round the hole on every row.
    assert len(after) < len(before) * 1.1


@pytest.mark.parametrize("settings", [{}, {"connect_fill": True}, {"route_fill": True}])
def test_each_setting_alone_keeps_previous_output(settings):
    from morale.engine import fill
    obj = frame(**settings)
    rings = obj.rings()
    rows = fill(rings[0], obj.spacing, obj.stitch_length, obj.angle, obj.connect_fill, rings[1:])
    if obj.route_fill:
        from morale.fill_routing import route_fill_runs
        rows = route_fill_runs(rows)
    assert generate(Project(objects=[obj]))[0].stitches[:len(rows)] == rows


def test_travel_walks_the_shorter_way_inside_the_outline():
    obj = frame()
    travel = FillTravel(obj.rings())
    # A straight line clips the hole; the walk turns the outer corner instead.
    assert travel.path((-15, -3), (-3, -15)) == [(-3, -15)]
    route = travel.path((-15, 5), (5, -15))
    assert route is not None and route[-1] == (5, -15)
    points = [(-15, 5)] + route
    length = sum(math.dist(a, b) for a, b in zip(points, points[1:]))
    assert length < 41  # 19.5 mm each way along the 0.5 mm inset ring, plus short legs.
    rings = obj.rings()
    assert all(segment_inside(a, b, rings[0], rings[1:]) for a, b in zip(points[1:-1], points[2:-1]))
    assert all(abs(abs(x) - (15 - TRAVEL_INSET)) < 1e-6 or abs(abs(y) - (15 - TRAVEL_INSET)) < 1e-6 for x, y in route[:-1])


def test_travel_too_long_or_between_rings_stays_a_jump():
    obj = frame()
    assert FillTravel(obj.rings(), limit=30).path((-15, 5), (5, -15)) is None
    # Half way round the square exceeds the 50 mm limit.
    assert FillTravel(obj.rings()).path((-15, 0), (15, 0)) is None
    # Outer edge to hole edge: nearest different rings.
    assert FillTravel(obj.rings()).path((-15, -15), (6, 6)) is None
    stitches = [Stitch(-15, -15, 'jump'), Stitch(-14, -15), Stitch(6, 6, 'jump'), Stitch(5, 6)]
    assert travel_inside(stitches, FillTravel(obj.rings()), 2.5) == stitches


def test_fill_starts_and_ends_at_chosen_outline_points():
    source = frame(connect_fill=True, route_fill=True)
    anchors = fill_anchors(source)
    assert anchors == source.contours[0]
    for start, end in [(0, 2), (1, 3), (2, 0), (3, 1)]:
        obj = route_fill(source, start, end)
        stitches = generate(Project(objects=[obj]))[0].stitches
        motion = [s for s in stitches if s.command in {'stitch', 'jump'}]
        first, last = obj.transform([anchors[start], anchors[end]])
        assert (motion[0].x, motion[0].y) == pytest.approx(first)
        assert (motion[-1].x, motion[-1].y) == pytest.approx(last)
        assert not sewn_outside(obj, stitches)


def test_fill_start_picks_the_nearest_row_order_without_travel_when_blocked():
    source = DesignObject(kind='rectangle', width=20, height=10, angle=0, underlay=False)
    for corner in range(4):
        obj = route_fill(source, corner, None)
        stitches = generate(Project(objects=[obj]))[0].stitches
        target = obj.transform([fill_anchors(source)[corner]])[0]
        assert math.dist((stitches[0].x, stitches[0].y), target) < 1e-6


def test_fill_points_round_trip_survive_other_stitch_types_and_reject_bad_values():
    obj = route_fill(frame(), 0, 2)
    restored = Project.loads(Project(objects=[obj]).dumps()).objects[0]
    assert restored.fill_start == obj.fill_start and restored.fill_end == obj.fill_end
    obj.stitch_type = 'contour'
    assert Project.loads(Project(objects=[obj]).dumps()).objects[0].fill_start == obj.fill_start
    for bad in ([1], [0, 2], ['a', 0]):
        obj.fill_start = bad
        with pytest.raises(ValueError):
            Project.loads(Project(objects=[obj]).dumps())
    with pytest.raises(ValueError):
        route_fill(frame(), 9, None)
    with pytest.raises(ValueError):
        route_fill(DesignObject(kind='satin', stitch_type='satin', points=[[-.5, -.5], [.5, -.5], [-.5, .5], [.5, .5]]))


def test_native_fill_start_dialog_applies_with_undo():
    from morale.app import MainWindow
    from morale.routing_dialog import RoutingDialog
    window = MainWindow()
    try:
        obj = frame(connect_fill=True, route_fill=True)
        window.replace_project(Project(objects=[obj])); window.select(obj.id)
        before = window.project.dumps()
        dialog = RoutingDialog(window.selected_object(), window)
        try:
            assert dialog.windowTitle() == 'Fill start and end'
            dialog.fill_start.setCurrentIndex(2); dialog.fill_end.setCurrentIndex(4)
            assert dialog.candidate is not None and dialog.preview.stitches
            assert 'Entry: 15.00, -15.00 mm' in dialog.status.text()
            window.apply_routing(dialog.plan)
        finally:
            dialog.deleteLater()
        assert window.project.objects[0].fill_start == obj.contours[0][1]
        assert window.project.objects[0].fill_end == obj.contours[0][3]
        window.undo()
        assert window.project.dumps() == before
    finally:
        window.saved = window.project.dumps(); window.close()
