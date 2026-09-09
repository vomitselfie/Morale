import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import math

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from morale.bezier import enable_handles, edit_controls, flatten_cubics
from morale.model import DesignObject, Project
from morale.engine import generate
from morale.formats import export_machine, import_machine
from morale.geometry import combine_outlines
from morale.stitch_edit import manual_object
from morale.canvas import Canvas
from morale.nodes import PointDialog


@pytest.fixture(scope="module", autouse=True)
def app():
    return QApplication.instance() or QApplication([])


def curve():
    source = DesignObject(kind="path", stitch_type="running", points=[[-.5, 0], [.5, 0]], underlay=False, stitch_length=.5)
    return edit_controls(source, [(-10, 0), (-10, 0), (-10, -20), (10, -20), (10, 0), (10, 0)])


def test_cubic_tracks_analytic_curve_and_includes_endpoints():
    obj = curve()
    points = obj.outline()
    assert points[0] == (-10, 0) and points[-1] == (10, 0)
    assert min(y for x, y in points) == pytest.approx(-15)
    def distance(p, a, b):
        dx, dy = b[0]-a[0], b[1]-a[1]
        t = max(0, min(1, ((p[0]-a[0])*dx + (p[1]-a[1])*dy)/(dx*dx+dy*dy)))
        return math.dist(p, (a[0]+t*dx, a[1]+t*dy))
    for i in range(101):
        t = i/100
        exact = (-10*(1-t)**3 - 30*(1-t)**2*t + 30*(1-t)*t*t + 10*t**3, -60*t*(1-t))
        assert min(distance(exact, a, b) for a, b in zip(points, points[1:])) < .031


def test_collinear_reversal_is_not_flattened_to_zero_length():
    controls = [(0, 0), (0, 0), (20, 0), (-20, 0), (0, 0), (0, 0)]
    result = flatten_cubics(controls, False)
    assert max(x for x, y in result) > 5 and min(x for x, y in result) < -5


@pytest.mark.parametrize("kind", ["path", "polygon"])
def test_enable_handles_preserves_straight_geometry_and_roundtrip(kind):
    source = DesignObject(kind=kind, stitch_type="running", rotation=29, flip_y=True,
                          points=[[-.5, -.5], [.5, -.5], [.1, .5]])
    obj = enable_handles(source)
    for actual, expected in zip(obj.outline(), source.outline()):
        assert actual == pytest.approx(expected)
    restored = Project.loads(Project(objects=[obj]).dumps()).objects[0]
    assert restored == obj
    assert len(obj.handles) == 3


@pytest.mark.parametrize("bad", [[], [(0, 0)]*7, [(float('nan'), 0)]*6, [(1001, 0)]*6])
def test_invalid_controls_rejected(bad):
    with pytest.raises(ValueError):
        edit_controls(curve(), bad)


def test_schema_rejects_mismatched_handles():
    obj = curve()
    obj.handles.pop()
    with pytest.raises(ValueError, match="handles"):
        Project.loads(Project(objects=[obj]).dumps())


def test_closed_cubic_fill_uses_curved_boundary():
    source = DesignObject(kind="polygon", points=[[-.5, 0], [.5, 0], [0, .5]], underlay=False)
    obj = enable_handles(source)
    controls = obj.control_points()
    controls[2], controls[3] = (-10, -20), (10, -20)
    obj = edit_controls(obj, controls)
    path = Canvas.outline_path(obj)
    assert path.contains(QPointF(0, -10))
    assert not path.contains(QPointF(0, -16))
    stitches = generate(Project(objects=[obj]))[0].stitches
    assert any(s.command == "stitch" and s.y < -12 for s in stitches)


def test_numeric_handle_editor_retains_precision_and_triples():
    obj = curve()
    dialog = PointDialog(obj)
    assert dialog.table.rowCount() == 6
    assert dialog.points() == obj.control_points()
    dialog.table.item(2, 0).setText("-11.1234567")
    result = edit_controls(obj, dialog.points())
    assert result.control_points()[2][0] == pytest.approx(-11.1234567)
    dialog.close()


def test_native_enable_handles_is_undoable_and_repeat_is_noop():
    from morale.app import MainWindow
    window = MainWindow()
    try:
        obj = DesignObject(kind="path", stitch_type="running", points=[[-.5, 0], [.5, 0]])
        window.replace_project(Project(objects=[obj]))
        window.select(obj.id)
        original = window.project.dumps()
        window.enable_bezier()
        assert window.project.objects[0].handles and window.canvas.mode == "nodes"
        window.enable_bezier()
        assert len(window.history) == 1
        window.undo()
        assert window.project.dumps() == original
    finally:
        window.saved = window.project.dumps()
        window.close()


def test_boolean_conversion_flattens_curves_to_compound():
    source = DesignObject(kind="polygon", points=[[-.5, -.5], [.5, -.5], [0, .5]])
    source = enable_handles(source)
    result = combine_outlines([source, DesignObject(kind="rectangle", x=10)], "union")
    assert result.kind == "compound" and not result.handles
    generate(Project(objects=[result]))


def test_manual_conversion_clears_curve_handles():
    obj = curve()
    manual = manual_object(obj, [(0, 0, "jump"), (1, 1, "stitch")])
    assert not manual.handles
    Project.loads(Project(objects=[manual]).dumps())


def test_native_handle_and_anchor_drags_and_undo():
    from morale.app import MainWindow
    window = MainWindow()
    try:
        window.show()
        QApplication.processEvents()
        obj = curve()
        window.replace_project(Project(objects=[obj]))
        window.select(obj.id)
        window.set_mode("nodes")
        canvas = window.canvas
        canvas.scale = 8
        canvas.pan = QPointF()
        def screen(point):
            return (QPointF(canvas.width()/2, canvas.height()/2) + QPointF(*point)*canvas.scale).toPoint()
        def drag(a, b):
            QTest.mousePress(canvas, Qt.MouseButton.LeftButton, pos=screen(a))
            QTest.mouseMove(canvas, screen(b))
            QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, pos=screen(b))
        original = window.project.dumps()
        drag((-10, -20), (-15, -25))
        controls = window.project.objects[0].control_points()
        assert controls[2] == pytest.approx((-15, -25), abs=.08)
        assert controls[1] == pytest.approx((-10, 0))
        previous_anchor, previous_handle = controls[1], controls[2]
        drag((-10, 0), (-8, 2))
        controls = window.project.objects[0].control_points()
        assert controls[1] == pytest.approx((-8, 2), abs=.08)
        assert controls[2] == pytest.approx(tuple(h + a - old for h, a, old in zip(previous_handle, controls[1], previous_anchor)))
        window.undo()
        window.undo()
        assert window.project.dumps() == original
    finally:
        window.saved = window.project.dumps()
        window.close()


@pytest.mark.parametrize("extension", ["dst", "exp", "jef", "pec", "pes", "tbf", "u01", "vp3", "xxx"])
def test_curved_running_path_exports_in_all_formats(tmp_path, extension):
    path = tmp_path / f"curve.{extension}"
    export_machine(Project(objects=[curve()]), path)
    stitches = [s for b in generate(import_machine(path).project) for s in b.stitches if s.command == "stitch"]
    assert min(s.y for s in stitches) == pytest.approx(-15, abs=.15)
    assert max(s.x for s in stitches) == pytest.approx(10, abs=.15)
    assert min(s.x for s in stitches) < -9.8


@pytest.mark.parametrize('mode,length', [('free',5),('smooth',5),('symmetric',10)])
def test_coupled_handle_drag_geometry(mode,length):
    from morale.bezier import move_control
    controls=[(-3,-4),(0,0),(3,0),(10,0),(12,0),(14,0)]
    result=move_control(controls,2,(0,10),mode)
    assert result[2]==(0,10) and result[1]==(0,0)
    assert math.dist(result[0],result[1])==pytest.approx(length)
    assert result[0]==pytest.approx((-3,-4) if mode=='free' else (0,-length))
    assert result[3:]==controls[3:]
    assert controls[2]==(3,0)
    # Incoming handles couple in the opposite direction as well.
    if mode!='free':
        reverse=move_control(result,0,(6,0),mode)
        assert reverse[2]==pytest.approx((-10 if mode=='smooth' else -6,0))


def test_collapsed_handles_are_finite_and_anchor_moves_preserve_vectors():
    from morale.bezier import move_control
    controls=[(-3,-4),(0,0),(3,0)]
    assert move_control(controls,2,(0,0),'smooth')[0]==(-3,-4)
    assert move_control(controls,2,(0,0),'symmetric')[0]==(0,0)
    for mode in ('free','smooth','symmetric'):
        assert move_control(controls,1,(10,20),mode)==[(7,16),(10,20),(13,20)]


@pytest.mark.parametrize('mode', ['smooth','symmetric'])
def test_native_coupled_drag_menu_save_and_undo(mode):
    from morale.app import MainWindow
    window=MainWindow()
    try:
        window.show()
        QApplication.processEvents()
        source=DesignObject(kind='path',stitch_type='running',underlay=False)
        obj=edit_controls(source,[(-20,0),(-15,0),(-10,0),(-4,0),(0,0),(4,0),(10,0),(15,0),(20,0)])
        window.replace_project(Project(objects=[obj]))
        window.select(obj.id)
        window.set_mode('nodes')
        original=window.project.dumps()
        action=next(a for a in window.handle_drag_actions.actions() if a.data()==mode)
        action.trigger()
        assert window.canvas.handle_drag_mode==mode
        assert sum(a.isChecked() for a in window.handle_drag_actions.actions())==1
        canvas=window.canvas
        canvas.scale=8
        canvas.pan=QPointF()
        def screen(p):
            return (QPointF(canvas.width()/2,canvas.height()/2)+QPointF(*p)*canvas.scale).toPoint()
        QTest.mousePress(canvas,Qt.MouseButton.LeftButton,pos=screen((4,0)))
        QTest.mouseMove(canvas,screen((0,8)))
        QTest.mouseRelease(canvas,Qt.MouseButton.LeftButton,pos=screen((0,8)))
        restored=Project.loads(window.project.dumps())
        controls=restored.objects[0].control_points()
        assert controls[5]==pytest.approx((0,8),abs=.08)
        assert controls[3]==pytest.approx((0,-4 if mode=='smooth' else -8),abs=.08)
        window.undo()
        assert window.project.dumps()==original
    finally:
        window.saved=window.project.dumps()
        window.close()
