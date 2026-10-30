import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from morale.engine import generate
from morale.model import DesignObject, Project, demo_project
from morale.swatches import build_swatches, swatch_values


@pytest.fixture(scope="module", autouse=True)
def app():
    return QApplication.instance() or QApplication([])


def bounds(project, names):
    points = [(s.x, s.y) for block in generate(project) for s in block.stitches
              if s.command == "stitch" and next(o for o in project.objects if o.id == block.object_id).name in names]
    xs, ys = zip(*points)
    return min(xs), min(ys), max(xs), max(ys)


def test_values_step_evenly_between_the_ends():
    assert swatch_values(.35, .6, 6) == [.35, .4, .45, .5, .55, .6]
    assert swatch_values(90, 0, 3) == [90, 45, 0]
    for count in (1, 10, 2.5):
        with pytest.raises(ValueError):
            swatch_values(0, 1, count)


def test_swatches_copy_the_selection_with_one_setting_stepped():
    source = demo_project()
    leaf = source.objects[1]
    stem = DesignObject("Stem", "path", -10, 5, 6, 8, stitch_type="running", points=[[-.5, .5], [.5, -.5]])
    source.objects.append(stem)
    original = source.dumps()
    result = build_swatches(source, {leaf.id, stem.id}, "spacing", .35, .6, 6)
    assert result.name == "Test swatches: Row spacing" and source.dumps() == original
    leaves = [o for o in result.objects if o.name.startswith("Left leaf")]
    stems = [o for o in result.objects if o.name.startswith("Stem")]
    labels = [o for o in result.objects if o.name.startswith("Label")]
    assert [o.spacing for o in leaves] == [.35, .4, .45, .5, .55, .6]
    # Running stitches do not use row spacing and keep their own.
    assert all(o.spacing == stem.spacing for o in stems)
    assert [o.lettering["text"] for o in labels] == ["0.35", "0.4", "0.45", "0.5", "0.55", "0.6"]
    assert len({o.id for o in result.objects}) == len(result.objects)
    assert all(o.color == leaf.color or o in stems for o in result.objects)
    # Each swatch and its label share a group, and swatches do not overlap.
    for value in ("0.35", "0.6"):
        group = {o.group_id for o in result.objects if o.name.endswith(value)}
        assert len(group) == 1
    boxes = [bounds(result, {f"Left leaf · {v}", f"Stem · {v}", f"Label {v}"}) for v in ("0.35", "0.4", "0.45", "0.5", "0.55", "0.6")]
    for i, a in enumerate(boxes):
        assert -50 < a[0] and a[2] < 50 and -50 < a[1] and a[3] < 50
        for b in boxes[i + 1:]:
            assert a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1]
    assert "1. 0.35" in result.notes and "6. 0.6" in result.notes


def test_swatches_without_labels_and_with_angles():
    source = Project(objects=[DesignObject(kind="rectangle", width=15, height=10, angle=0)])
    result = build_swatches(source, {source.objects[0].id}, "angle", 0, 90, 4, labels=False)
    assert [o.angle for o in result.objects] == [0, 30, 60, 90]


@pytest.mark.parametrize("ids,key,start,stop,count,message", [
    ("none", "spacing", .4, .5, 3, "Select the parts"),
    ("stem", "spacing", .4, .5, 3, "None of the selected parts uses row spacing"),
    ("leaf", "spacing", .1, .5, 3, "between 0.2 and 5"),
    ("leaf", "colour", .4, .5, 3, "Choose a setting"),
    ("stem", "stitch_length", 2, 3, 9, "Choose fewer swatches"),
])
def test_unusable_requests_explain_what_to_change(ids, key, start, stop, count, message):
    source = demo_project()
    chosen = {"leaf": {source.objects[1].id}, "stem": {source.objects[0].id}, "none": set()}[ids]
    with pytest.raises(ValueError, match=message):
        build_swatches(source, chosen, key, start, stop, count)


def test_native_swatches_open_as_new_design_after_confirmation(monkeypatch):
    from morale.app import MainWindow
    from morale.swatch_dialog import SwatchDialog
    window = MainWindow()
    try:
        leaf = window.project.objects[1]
        window.select(leaf.id)
        dialog = SwatchDialog(window.selected_objects(), window)
        assert (dialog.start.value(), dialog.stop.value()) == pytest.approx((leaf.spacing - .1, leaf.spacing + .1))
        dialog.setting.setCurrentIndex(3)
        assert (dialog.start.value(), dialog.stop.value()) == (0, 90)
        dialog.deleteLater()
        def accept(self):
            self.setting.setCurrentIndex(1); self.count.setValue(3)
            return SwatchDialog.DialogCode.Accepted
        monkeypatch.setattr(SwatchDialog, "exec", accept)
        asked = []
        monkeypatch.setattr(window, "confirm_discard", lambda: asked.append(True) or True)
        window.test_swatches()
        assert asked and window.project.name == "Test swatches: Pull compensation"
        assert sorted(o.pull_compensation for o in window.project.objects if o.name.startswith("Left leaf")) == [0, .2, .4]
    finally:
        window.saved = window.project.dumps(); window.close()


def test_refused_layout_never_discards_the_design(monkeypatch):
    from morale.app import MainWindow
    from morale.swatch_dialog import SwatchDialog
    window = MainWindow()
    try:
        window.select(window.project.objects[0].id)
        before = window.project.dumps()
        def accept(self):
            self.setting.setCurrentIndex(2); self.count.setValue(9)
            return SwatchDialog.DialogCode.Accepted
        monkeypatch.setattr(SwatchDialog, "exec", accept)
        errors = []
        monkeypatch.setattr(window, "error", errors.append)
        asked = []
        monkeypatch.setattr(window, "confirm_discard", lambda: asked.append(True) or True)
        window.test_swatches()
        assert errors and "Choose fewer swatches" in errors[0] and window.project.dumps() == before
        assert not asked
    finally:
        window.saved = window.project.dumps(); window.close()
