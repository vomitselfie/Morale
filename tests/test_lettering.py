import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtGui import QFont, QPainterPath
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPointF

from morale.model import DesignObject, Project
from morale.engine import fill, generate, segment_inside
from morale.canvas import Canvas
from morale.lettering import make_lettering, LetteringDialog
from morale.formats import export_machine, import_machine


@pytest.fixture(scope="module", autouse=True)
def app():
    return QApplication.instance() or QApplication([])


def test_hole_fill_preserves_unstitched_center_and_safe_travel():
    outer = [(-10, -10), (10, -10), (10, 10), (-10, 10)]
    hole = [(-3, -3), (3, -3), (3, 3), (-3, 3)]
    for angle in [0, 30, 90]:
        stitches = fill(outer, .4, 2, angle, connect=True, holes=[hole])
        for a, b in zip(stitches, stitches[1:]):
            if b.command == "stitch":
                assert segment_inside((a.x, a.y), (b.x, b.y), outer, [hole])
                assert not (-2.999 < b.x < 2.999 and -2.999 < b.y < 2.999)


def test_disjoint_contours_and_nested_island():
    rings = [[(-10, -10), (10, -10), (10, 10), (-10, 10)],
             [(-5, -5), (5, -5), (5, 5), (-5, 5)],
             [(-1, -1), (1, -1), (1, 1), (-1, 1)],
             [(20, 0), (25, 0), (25, 5), (20, 5)]]
    stitches = fill(rings[0], .4, 2, 0, holes=rings[1:])
    assert any(b.command == "stitch" and abs((a.x + b.x) / 2) < 1 and abs((a.y + b.y) / 2) < 1 for a, b in zip(stitches, stitches[1:]))
    assert any(s.x > 20 for s in stitches if s.command == "stitch")
    assert not segment_inside((-4, 0), (4, 0), rings[0], rings[1:])


def test_compound_rendering_and_running_contours():
    obj = DesignObject(kind="compound", stitch_type="running", contours=[
        [[-.5, -.5], [.5, -.5], [.5, .5], [-.5, .5]],
        [[-.2, -.2], [.2, -.2], [.2, .2], [-.2, .2]]])
    path = Canvas.outline_path(obj)
    assert not path.contains(QPointF(0, 0))
    assert path.contains(QPointF(8, 0))
    assert sum(s.command == "jump" for s in generate(Project(objects=[obj]))[0].stitches) == 2


def test_lettering_is_editable_and_preserves_outlines_in_project():
    obj = make_lettering("BOB", QFont().family(), 15, 100)
    assert obj.kind == "compound"
    assert obj.height == 15
    assert len(obj.contours) >= 6
    loaded = Project.loads(Project(objects=[obj]).dumps()).objects[0]
    assert loaded.contours == obj.contours
    assert loaded.lettering["text"] == "BOB"
    changed = make_lettering("MOM", obj.lettering["family"], 20, 120, obj)
    assert changed.id == obj.id
    assert changed.height == 20
    assert changed.contours != obj.contours


def test_letter_holes_have_no_interior_stitches():
    obj = make_lettering("O", QFont().family(), 20)
    path = Canvas.outline_path(obj)
    assert not path.contains(QPointF(0, 0))
    for stitch in generate(Project(objects=[obj]))[0].stitches:
        if stitch.command == "stitch":
            assert not (abs(stitch.x) < 2 and abs(stitch.y) < 2)


@pytest.mark.parametrize("text", ["", "   ", "hello\nworld", "x" * 81])
def test_bad_lettering_text_rejected(text):
    with pytest.raises(ValueError):
        make_lettering(text, QFont().family())


@pytest.mark.parametrize("extension", ["dst", "exp", "jef", "pec", "pes", "tbf", "u01", "vp3", "xxx"])
def test_lettering_exports_to_all_machine_writers(tmp_path, extension):
    obj = make_lettering("MOM", QFont().family(), 15)
    original = Project(objects=[obj])
    path = tmp_path / f"letters.{extension}"
    export_machine(original, path)
    restored = import_machine(path).project
    expected = [s for b in generate(original) for s in b.stitches if s.command == "stitch"]
    actual = [s for b in generate(restored) for s in b.stitches if s.command == "stitch"]
    for axis in ["x", "y"]:
        assert min(getattr(s, axis) for s in actual) == pytest.approx(min(getattr(s, axis) for s in expected), abs=.15)
        assert max(getattr(s, axis) for s in actual) == pytest.approx(max(getattr(s, axis) for s in expected), abs=.15)


def test_native_lettering_dialog(app):
    dialog = LetteringDialog()
    dialog.text.setText("Hi")
    dialog.height.setValue(12)
    dialog.accept()
    assert dialog.candidate.lettering["text"] == "Hi"
    assert dialog.candidate.height == 12


@pytest.mark.parametrize("angle", [-60, 0, 60, 120])
def test_curved_layout_preserves_editable_settings_and_finite_geometry(angle):
    obj = make_lettering("MORALE", QFont().family(), 15, layout="curved", curve=angle)
    restored = Project.loads(Project(objects=[obj]).dumps()).objects[0]
    assert restored.lettering["layout"] == "curved"
    assert restored.lettering["curve"] == angle
    assert restored.contours == obj.contours
    assert generate(Project(objects=[restored]))[0].stitches
    straight = make_lettering("MORALE", QFont().family(), 15)
    if angle == 0:
        assert obj.contours == straight.contours
    else:
        assert obj.contours != straight.contours


def test_monogram_enlarges_middle_letter_and_keeps_order():
    obj = make_lettering("III", QFont().family(), 20, layout="monogram")
    rings = sorted(obj.rings(), key=lambda ring: min(x for x, y in ring))
    assert len(rings) == 3
    heights = [max(y for x, y in ring) - min(y for x, y in ring) for ring in rings]
    assert heights[1] == pytest.approx(heights[0] * 1.4, rel=.01)
    assert heights[2] == pytest.approx(heights[0])
    assert obj.lettering["text"] == "III"
    assert obj.height == pytest.approx(20)


def test_monogram_spacing_changes_width():
    tight = make_lettering("ABC", QFont().family(), 20, 50, layout="monogram")
    wide = make_lettering("ABC", QFont().family(), 20, 200, layout="monogram")
    assert wide.width > tight.width


@pytest.mark.parametrize("text", ["AB", "ABCD", "A B", "12A"])
def test_invalid_monograms_rejected(text):
    with pytest.raises(ValueError, match="three letters"):
        make_lettering(text, QFont().family(), layout="monogram")


def test_native_layout_controls_restore_saved_values(app):
    obj = make_lettering("MORALE", QFont().family(), 15, layout="curved", curve=75)
    dialog = LetteringDialog(obj)
    assert dialog.layout_choice.currentData() == "curved"
    assert dialog.curve.value() == 75
    assert dialog.height.value() == 15
    dialog.layout_choice.setCurrentIndex(dialog.layout_choice.findData("monogram"))
    assert not dialog.curve.isEnabled()
    dialog.text.setText("ABC")
    dialog.accept()
    assert dialog.candidate.lettering["layout"] == "monogram"
    assert dialog.candidate.id == obj.id


def test_resized_curved_text_restores_scaled_letter_height(app):
    obj = make_lettering("MORALE", QFont().family(), 15, layout="curved", curve=60)
    obj.height *= 1.5
    dialog = LetteringDialog(obj)
    assert dialog.height.value() == pytest.approx(22.5)


@pytest.mark.parametrize("layout", ["curved", "monogram"])
@pytest.mark.parametrize("extension", ["dst", "exp", "jef", "pec", "pes", "tbf", "u01", "vp3", "xxx"])
def test_layouts_export_to_all_writers(tmp_path, layout, extension):
    obj = make_lettering("ABC", QFont().family(), 15, layout=layout, curve=45)
    path = tmp_path / f"layout.{extension}"
    export_machine(Project(objects=[obj]), path)
    restored = import_machine(path).project
    before = [s for b in generate(Project(objects=[obj])) for s in b.stitches if s.command == "stitch"]
    after = [s for b in generate(restored) for s in b.stitches if s.command == "stitch"]
    for axis in ["x", "y"]:
        assert min(getattr(s, axis) for s in after) == pytest.approx(min(getattr(s, axis) for s in before), abs=.15)
        assert max(getattr(s, axis) for s in after) == pytest.approx(max(getattr(s, axis) for s in before), abs=.15)
