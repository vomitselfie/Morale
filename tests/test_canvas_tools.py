import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from morale.app import MainWindow
from morale.model import Project, DesignObject


@pytest.fixture
def window():
    app = QApplication.instance() or QApplication([])
    widget = MainWindow()
    widget.replace_project(Project(objects=[DesignObject(x=-20, width=10, height=10),
                                           DesignObject(x=0, width=10, height=10),
                                           DesignObject(x=25, width=10, height=10)]))
    widget.show()
    app.processEvents()
    widget.canvas.scale = 5
    widget.canvas.setFocus()
    yield widget
    widget.saved = widget.project.dumps()
    widget.close()


def drag(canvas, start, end, modifiers=Qt.KeyboardModifier.NoModifier):
    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, modifiers, start)
    QTest.mouseMove(canvas, end)
    QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, modifiers, end)


def test_marquee_selects_enclosed_shapes_without_editing(window):
    before = window.project.dumps()
    center = window.canvas.rect().center()
    drag(window.canvas, center + QPoint(-140, -40), center + QPoint(40, 40))
    assert window.selected_ids == {obj.id for obj in window.project.objects[:2]}
    assert window.project.dumps() == before


def test_additive_marquee_excludes_hidden_shapes(window):
    window.select(window.project.objects[2].id)
    window.project.objects[1].visible = False
    window.refresh()
    center = window.canvas.rect().center()
    drag(window.canvas, center + QPoint(-140, -40), center + QPoint(40, 40), Qt.KeyboardModifier.ShiftModifier)
    assert window.selected_ids == {window.project.objects[0].id, window.project.objects[2].id}


def test_escape_cancels_marquee(window):
    center = window.canvas.rect().center()
    QTest.mousePress(window.canvas, Qt.MouseButton.LeftButton, pos=center + QPoint(-180, -60))
    QTest.mouseMove(window.canvas, center + QPoint(180, 60))
    QTest.keyClick(window.canvas, Qt.Key.Key_Escape)
    QTest.mouseRelease(window.canvas, Qt.MouseButton.LeftButton, pos=center + QPoint(180, 60))
    assert window.selected_ids == set()
    assert window.canvas.marquee_start is None


def test_grid_snaps_creation_but_not_measurement(window):
    window.set_snap(True)
    window.set_mode("rectangle")
    center = window.canvas.rect().center()
    drag(window.canvas, center + QPoint(33, 33), center + QPoint(122, 122))
    obj = window.selected_object()
    assert (obj.x, obj.y, obj.width, obj.height) == (15, 15, 10, 10)
    window.set_mode("measure")
    measured = []
    window.canvas.measured.connect(lambda *values: measured.append(values))
    drag(window.canvas, center, center + QPoint(30, 40))
    assert measured[-1] == pytest.approx((6, 8, 10))


def test_snapped_group_drag_keeps_relative_positions(window):
    window.project.objects[0].x = -17
    window.project.objects[1].x = 3
    window.refresh()
    window.select_many([obj.id for obj in window.project.objects[:2]])
    window.set_snap(True)
    center = window.canvas.rect().center()
    drag(window.canvas, center + QPoint(15, 0), center + QPoint(38, 0))
    assert [obj.x for obj in window.project.objects[:2]] == [-10, 10]


def test_inch_grid_uses_quarter_inch(window):
    window.set_unit("in")
    window.set_snap(True)
    snapped = window.canvas.snapped(QPointF(7, 12))
    assert (snapped.x(), snapped.y()) == pytest.approx((6.35, 12.7))


def test_custom_grid_is_physical_and_does_not_edit_project(window):
    before = window.project.dumps()
    window.set_grid_spacing(.5)
    window.set_snap(True)
    result = window.canvas.snapped(QPointF(1.2, -2.3))
    assert (result.x(), result.y()) == (1., -2.5)
    window.set_unit("in")
    assert window.canvas.grid_step() == .5
    assert window.project.dumps() == before
    with pytest.raises(ValueError):
        window.set_grid_spacing(0)


def test_marquee_can_select_a_zero_width_running_path(window):
    obj = DesignObject(kind="path", stitch_type="running", width=10, height=10, points=[[0, -.5], [0, .5]])
    window.replace_project(Project(objects=[obj]))
    window.canvas.scale = 5
    center = window.canvas.rect().center()
    drag(window.canvas, center + QPoint(-50, -50), center + QPoint(50, 50))
    assert window.selected_ids == {obj.id}
