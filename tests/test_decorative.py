import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import math

import pytest
from PySide6.QtWidgets import QApplication

from morale.decorative import blanket_paths, cross_paths
from morale.engine import generate, satin
from morale.model import DesignObject, Project
from morale.pattern_fill import RegionClip


@pytest.fixture(scope="module", autouse=True)
def app():
    return QApplication.instance() or QApplication([])


def stitches(obj):
    return generate(Project.loads(Project(objects=[obj]).dumps()))[0].stitches


def square(**settings):
    return DesignObject(kind="rectangle", width=20, height=20, angle=0, underlay=False, **settings)


def test_blanket_prongs_point_into_closed_shapes_and_left_of_paths():
    ring = [(0, 0), (20, 0), (20, 20), (0, 20)]
    region = RegionClip([ring])
    for winding in (ring, ring[::-1]):
        path = blanket_paths([winding], 4, 3, True, region.inside)[0]
        assert all(-1e-9 <= x <= 20 + 1e-9 and -1e-9 <= y <= 20 + 1e-9 for x, y in path)
        # Corners stay on the outline between prongs.
        assert all(corner in path for corner in winding)
    line = blanket_paths([[(0, 0), (10, 0)]], 2, 1, False, None)[0]
    assert line[0] == (0, 0) and line[-2:] == [(10, 1), (10, 0)]
    assert max(y for _, y in line) == pytest.approx(1)


def test_blanket_meander_and_cross_generate_inside_their_shapes():
    for kind in ("blanket", "meander", "cross"):
        obj = square(stitch_type=kind)
        points = [(s.x, s.y) for s in stitches(obj) if s.command == "stitch"]
        assert points
        assert all(-10 - 1e-6 <= x <= 10 + 1e-6 and -10 - 1e-6 <= y <= 10 + 1e-6 for x, y in points), kind


def test_meander_avoids_holes_and_repeats_exactly():
    obj = DesignObject(kind="compound", width=30, height=30, stitch_type="meander", underlay=False,
                       contours=[[[-.5, -.5], [.5, -.5], [.5, .5], [-.5, .5]], [[-.2, -.2], [.2, -.2], [.2, .2], [-.2, .2]]])
    first = stitches(obj)
    assert first == stitches(obj)
    sewn = [(a, b) for a, b in zip(first, first[1:]) if b.command == "stitch"]
    # No sewn segment enters the 12 mm hole.
    for a, b in sewn:
        for t in (0, .5, 1):
            x, y = a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t
            assert not (abs(x) < 6 - 1e-6 and abs(y) < 6 - 1e-6)
    with pytest.raises(ValueError):
        Project.loads(Project(objects=[DesignObject(kind="path", stitch_type="meander", points=[[-.5, 0], [.5, 0]])]).dumps())


def test_cross_stitch_sews_both_diagonals_of_every_cell_with_one_edge_turn():
    paths = cross_paths([[(0, 0), (7.5, 0), (7.5, 2.5), (0, 2.5)]], 2.5, lambda p: 0 < p[0] < 7.5 and 0 < p[1] < 2.5)
    assert len(paths) == 1
    segments = list(zip(paths[0], paths[0][1:]))
    diagonals = {frozenset(s) for s in segments if s[0][0] != s[1][0]}
    edges = [s for s in segments if s[0][0] == s[1][0]]
    assert len(diagonals) == 6 and len(edges) == 1
    # Cells sit on a grid shared by every object.
    obj = square(stitch_type="cross", x=1.3)
    xs = {round(s.x / 2.5, 6) for s in stitches(obj) if s.command == "stitch"}
    assert all(x == int(x) for x in xs)


@pytest.mark.parametrize("style", ["s", "zigzag"])
def test_satin_styles(style):
    rails = [(0, 0), (6, 0), (0, 20), (6, 20)]
    plain = satin(rails, .4, 6)
    if style == "s":
        bent = satin(rails, .4, 6, style="s")
        assert len(bent) > len(plain) * 1.4
        assert all(-1e-9 <= s.x <= 6 + 1e-9 and -.8 <= s.y <= 20.8 for s in bent)
        assert (bent[1].x, bent[1].y) == (plain[1].x, plain[1].y)
    obj = DesignObject(kind="satin", stitch_type="satin", width=6, height=20, satin_style=style, underlay=False,
                       points=[[-.5, -.5], [.5, -.5], [-.5, .5], [.5, .5]])
    sewn = stitches(obj)
    if style == "zigzag":
        assert len(sewn) < len(plain) / 2
    with pytest.raises(ValueError):
        obj.satin_style = "wavy"
        Project.loads(Project(objects=[obj]).dumps())


def test_new_settings_round_trip_and_reject_bad_values():
    obj = square(stitch_type="blanket", blanket_spacing=4, blanket_width=2, meander_spacing=5, cross_cell=3)
    assert Project.loads(Project(objects=[obj]).dumps()).objects[0] == obj
    for key, value in (("blanket_spacing", .5), ("blanket_width", 11), ("meander_spacing", 0), ("cross_cell", 20)):
        bad = square(**{key: value})
        with pytest.raises(ValueError):
            Project.loads(Project(objects=[bad]).dumps())


def test_panel_offers_new_types_for_matching_shapes():
    from morale.app import MainWindow
    window = MainWindow()
    try:
        obj = window.project.objects[1]
        window.select(obj.id)
        window.stitch_type.setCurrentIndex(window.stitch_type.findData("cross"))
        assert window.project.objects[1].stitch_type == "cross"
        assert not window.property_form.isRowVisible(window.fields["meander_spacing"])
        assert window.property_form.isRowVisible(window.fields["cross_cell"])
        window.select(window.project.objects[0].id)  # Open stem path
        model = window.stitch_type.model()
        enabled = {window.stitch_type.itemData(i) for i in range(window.stitch_type.count()) if model.item(i).isEnabled()}
        assert "blanket" in enabled and "meander" not in enabled and "cross" not in enabled
    finally:
        window.saved = window.project.dumps(); window.close()
