import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from copy import deepcopy

import pytest
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication, QDialog

from morale.app import MainWindow
from morale.canvas import Canvas
from morale.geometry import combine_outlines, replace_contours
from morale.model import DesignObject, Project
from morale.nodes import ContourDialog, PointDialog


@pytest.fixture(scope="module", autouse=True)
def app():
    return QApplication.instance() or QApplication([])


def ring_object():
    return combine_outlines([DesignObject(kind="rectangle", width=30, height=30),
                             DesignObject(kind="rectangle", width=10, height=10)], "subtract")


def test_move_hole_without_moving_outer_contour():
    obj = ring_object()
    rings = obj.rings()
    hole = next(i for i, r in enumerate(rings) if max(x for x, y in r) < 10)
    rings[hole] = [(x + 5, y) for x, y in rings[hole]]
    result = replace_contours(obj, rings)
    path = Canvas.outline_path(result)
    assert path.contains(QPointF(-3, 0))
    assert not path.contains(QPointF(7, 0))
    assert result.width == obj.width and result.height == obj.height
    assert result.id == obj.id
    assert Project.loads(Project(objects=[result]).dumps()).objects[0] == result


def test_unchanged_transformed_contours_retain_exact_source():
    obj = ring_object()
    obj.rotation = 37
    obj.flip_y = True
    obj.x = 1 / 7
    dialog = ContourDialog(obj)
    try:
        dialog.selector.setCurrentIndex(1)
        dialog.selector.setCurrentIndex(0)
        dialog.accept()
        assert dialog.result() == QDialog.DialogCode.Accepted
        assert dialog.candidate == obj
    finally:
        dialog.close()


def test_edited_transformed_contours_rebase_once():
    obj = ring_object()
    obj.rotation = 37
    obj.flip_x = True
    rings = obj.rings()
    rings[0][0] = (rings[0][0][0] + 1, rings[0][0][1] - .5)
    result = replace_contours(obj, rings)
    assert result.rotation == 0 and not result.flip_x
    for actual, expected in zip(result.rings(), rings):
        for point, original in zip(actual, expected):
            assert point == pytest.approx(original)


@pytest.mark.parametrize("rings", [[], [[(0, 0), (1, 1)]], [[(0, 0), (1, 1), (float('nan'), 0)]],
                                   [[(0, 0), (1, 1), (1001, 0)]], [[(0, 0), (1, 1), (0,)]]])
def test_invalid_contours_rejected(rings):
    with pytest.raises(ValueError):
        replace_contours(ring_object(), rings)


def test_dialog_bad_cell_keeps_current_contour_and_can_be_corrected():
    dialog = ContourDialog(ring_object())
    try:
        original = dialog.table.item(0, 0).text()
        dialog.table.item(0, 0).setText("oops")
        dialog.selector.setCurrentIndex(1)
        assert dialog.current == dialog.selector.currentIndex() == 0
        assert "numeric" in dialog.message.text()
        dialog.accept()
        assert dialog.result() != QDialog.DialogCode.Accepted
        dialog.table.item(0, 0).setText(original)
        dialog.selector.setCurrentIndex(1)
        assert dialog.current == 1
        dialog.accept()
        assert dialog.result() == QDialog.DialogCode.Accepted
    finally:
        dialog.close()


def test_add_remove_contours_and_cancel_preserves_source():
    obj = ring_object()
    original = deepcopy(obj)
    dialog = ContourDialog(obj)
    dialog.add_contour()
    assert len(dialog.rings) == 3 and dialog.table.rowCount() == 3
    dialog.remove_contour()
    dialog.remove_contour()
    dialog.remove_contour()
    assert len(dialog.rings) == 1 and "at least one" in dialog.message.text()
    dialog.reject()
    assert obj == original


def test_native_apply_undo_noop_and_failure_are_atomic():
    window = MainWindow()
    try:
        obj = ring_object()
        window.replace_project(Project(objects=[obj]))
        window.selected_id = obj.id
        original = window.project.dumps()
        window.apply_contours(obj.rings())
        assert not window.history
        window.apply_contours([obj.rings()[0]])
        assert len(window.project.objects[0].contours) == 1
        window.undo()
        assert window.project.dumps() == original
        window.selected_id = obj.id
        with pytest.raises(ValueError):
            window.apply_contours([])
        assert window.project.dumps() == original
    finally:
        window.saved = window.project.dumps()
        window.close()


def test_point_dialog_does_not_round_untouched_coordinates():
    obj = DesignObject(kind="path", stitch_type="running", rotation=23, points=[[-.5, -.5], [.5, .5]])
    dialog = PointDialog(obj)
    assert dialog.points() == obj.transform(obj.points)
    dialog.table.item(0, 0).setText("1.2345")
    assert dialog.points()[0][0] == 1.2345
    dialog.close()
