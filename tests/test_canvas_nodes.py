import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from morale.app import MainWindow
from morale.geometry import combine_outlines
from morale.model import Project, DesignObject


@pytest.fixture
def window():
    app = QApplication.instance() or QApplication([])
    widget = MainWindow()
    widget.show()
    app.processEvents()
    yield widget
    widget.saved = widget.project.dumps()
    widget.close()


def prepare(window, obj):
    window.replace_project(Project(objects=[obj]))
    window.select(obj.id)
    window.set_mode("nodes")
    window.canvas.scale = 8
    window.canvas.pan = QPointF()
    return window.canvas


def screen(canvas, point):
    return (QPointF(canvas.width() / 2, canvas.height() / 2) + canvas.pan + QPointF(*point) * canvas.scale).toPoint()


def drag(canvas, start, end):
    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, pos=screen(canvas, start))
    QTest.mouseMove(canvas, screen(canvas, end))
    QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, pos=screen(canvas, end))


@pytest.mark.parametrize("kind", ["polygon", "path", "satin"])
def test_drag_node_regenerates_once_and_undo_restores_source(window, kind):
    points = [[-.5, -.5], [.5, -.5], [-.5, .5], [.5, .5]] if kind == "satin" else [[-.5, -.5], [.5, -.5], [.2, .5]]
    obj = DesignObject(kind=kind, stitch_type="satin" if kind == "satin" else "running", points=points, rotation=17, flip_x=True)
    canvas = prepare(window, obj)
    original = window.project.dumps()
    before = obj.transform(obj.points)
    start = before[0]
    end = (start[0] + .5, start[1] + 1)
    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, pos=screen(canvas, start))
    QTest.mouseMove(canvas, screen(canvas, end))
    assert canvas.node_drag is not None
    assert window.project.dumps() == original
    QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, pos=screen(canvas, end))
    assert len(window.history) == 1
    after = window.project.objects[0]
    assert after.transform(after.points)[0] == pytest.approx(end, abs=.08)
    for actual, expected in zip(after.transform(after.points)[1:], before[1:]):
        assert actual == pytest.approx(expected)
    window.undo()
    assert window.project.dumps() == original


def test_compound_hole_node_moves_independently_and_snaps(window):
    obj = combine_outlines([DesignObject(kind="rectangle", width=30, height=30), DesignObject(kind="rectangle", width=10, height=10)], "subtract")
    canvas = prepare(window, obj)
    canvas.snap_grid = True
    canvas.grid_spacing = 2
    rings = obj.rings()
    ri = next(i for i, r in enumerate(rings) if max(x for x, y in r) < 10)
    drag(canvas, rings[ri][0], (-3.3, -6.6))
    result = window.project.objects[0].rings()
    assert result[ri][0] == pytest.approx((-4, -6))
    for actual, expected in zip(result[1-ri], rings[1-ri]):
        assert actual == pytest.approx(expected)


def test_escape_and_click_do_not_modify_or_snap_nodes(window):
    obj = DesignObject(kind="path", stitch_type="running", points=[[-.3, -.3], [.3, .3]])
    canvas = prepare(window, obj)
    canvas.snap_grid = True
    before = window.project.dumps()
    start = screen(canvas, obj.transform(obj.points)[0])
    QTest.mouseClick(canvas, Qt.MouseButton.LeftButton, pos=start)
    assert window.project.dumps() == before
    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(canvas, screen(canvas, (15, 15)))
    QTest.keyClick(canvas, Qt.Key.Key_Escape)
    QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, pos=screen(canvas, (15, 15)))
    assert window.project.dumps() == before and not window.history
    assert canvas.node_drag is None


def test_crossing_satin_drag_rejected_without_history(window):
    obj = DesignObject(kind="satin", stitch_type="satin", width=20, height=20,
                       points=[[-.5, -.5], [.5, -.5], [-.5, .5], [.5, .5]])
    canvas = prepare(window, obj)
    before = window.project.dumps()
    drag(canvas, (-10, -10), (15, -10))
    assert window.project.dumps() == before and not window.history
    assert "rejected" in window.statusBar().currentMessage()


def test_playback_and_multiselection_disable_node_editing(window):
    obj = DesignObject(kind="path", stitch_type="running", points=[[-.5, -.5], [.5, .5]])
    canvas = prepare(window, obj)
    before = window.project.dumps()
    canvas.playhead = 2
    drag(canvas, (-10, -15), (-8, -12))
    assert window.project.dumps() == before
    canvas.playhead = None
    window.project.objects.append(DesignObject())
    window.select_many([o.id for o in window.project.objects])
    assert canvas.node_object() is None


def test_mode_change_cancels_pending_node_drag(window):
    obj = DesignObject(kind="path", stitch_type="running", points=[[-.5, -.5], [.5, .5]])
    canvas = prepare(window, obj)
    before = window.project.dumps()
    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, pos=screen(canvas, (-10, -15)))
    QTest.mouseMove(canvas, screen(canvas, (-5, -10)))
    window.set_mode("select")
    QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, pos=screen(canvas, (-5, -10)))
    assert window.project.dumps() == before and not window.history
