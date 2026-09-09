import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from morale.app import MainWindow
from morale.measurements import HoopDialog, validate_hoop
from morale.model import Project


@pytest.fixture
def window():
    app = QApplication.instance() or QApplication([])
    widget = MainWindow()
    widget.show()
    app.processEvents()
    yield widget
    widget.saved = widget.project.dumps()
    widget.close()


def test_unit_switch_never_modifies_geometry_or_history(window):
    before = window.project.dumps()
    for unit in ["in", "mm", "in", "mm"]:
        window.set_unit(unit)
        assert window.project.dumps() == before
        assert not window.history


def test_inch_edits_convert_to_mm_and_undo(window):
    original = window.selected_object().width
    window.set_unit("in")
    window.fields["width"].setValue(2)
    assert window.selected_object().width == pytest.approx(50.8)
    window.undo()
    assert window.selected_object().width == original
    window.fields["width"].setValue(window.fields["width"].minimum())
    Project.loads(window.project.dumps())


def test_custom_hoop_persists_and_undoes(window):
    before = window.project.dumps()
    window.set_hoop(152.4, 203.2)
    restored = Project.loads(window.project.dumps())
    assert (restored.hoop_width, restored.hoop_height) == (152.4, 203.2)
    window.undo()
    assert window.project.dumps() == before


def test_hoop_dialog_does_not_round_unchanged_inches(window):
    dialog = HoopDialog(100, 130, "in", window)
    assert dialog.dimensions() == (100, 130)
    dialog.fields[0].setValue(6)
    assert dialog.dimensions() == pytest.approx((152.4, 130))


@pytest.mark.parametrize("dimensions", [(0, 100), (501, 100), (True, 100), (float("nan"), 100)])
def test_invalid_hoops_rejected(dimensions):
    with pytest.raises(ValueError):
        validate_hoop(*dimensions)


def test_native_measurement_tracks_world_units_without_editing(window):
    before = window.project.dumps()
    window.set_mode("measure")
    window.canvas.scale = 5
    center = window.canvas.rect().center()
    results = []
    window.canvas.measured.connect(lambda *values: results.append(values))
    QTest.mousePress(window.canvas, Qt.MouseButton.LeftButton, pos=center)
    QTest.mouseMove(window.canvas, center + QPoint(30, 40))
    QTest.mouseRelease(window.canvas, Qt.MouseButton.LeftButton, pos=center + QPoint(30, 40))
    assert results[-1] == pytest.approx((6, 8, 10))
    assert window.project.dumps() == before
    window.set_unit("in")
    assert window.canvas.measurement is not None
    assert window.project.dumps() == before
