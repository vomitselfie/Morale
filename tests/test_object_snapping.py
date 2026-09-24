import pytest
from PySide6.QtCore import QRectF,QPointF,QPoint,Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from morale.object_snapping import snap_bounds
from morale.model import Project,DesignObject
from morale.app import MainWindow


@pytest.fixture
def window():
    app=QApplication.instance() or QApplication([])
    window=MainWindow();window.replace_project(Project(objects=[DesignObject(x=-20,width=10,height=10),DesignObject(x=0,width=10,height=10),DesignObject(x=25,width=10,height=10)]))
    window.show();app.processEvents();window.canvas.scale=5
    yield window
    window.saved=window.project.dumps();window.close()


def test_group_bounds_snap_nearest_edge_and_keep_unmatched_axis():
    delta,guides=snap_bounds([QRectF(-25,-5,10,10),QRectF(-5,-5,10,10)],[QRectF(20,-5,10,10)],QPointF(14,2.5),1.6)
    assert (delta.x(),delta.y())==(15,2.5) and guides==(20,None)


def test_zero_width_path_and_center_alignment():
    delta,guides=snap_bounds([QRectF(0,-5,0,10)],[QRectF(9,-10,2,20)],QPointF(10.1,.1),.5)
    assert (delta.x(),delta.y())==(10,0) and guides==(10,0)


def test_no_targets_and_outside_threshold_do_not_snap():
    moving=[QRectF(0,0,2,2)]
    for targets in ([],[QRectF(20,20,2,2)]):
        delta,guides=snap_bounds(moving,targets,QPointF(3,4),1)
        assert delta==QPointF(3,4) and guides==(None,None)


def test_native_group_drag_object_priority_over_grid_and_undo(window):
    canvas=window.canvas;window.select_many([obj.id for obj in window.project.objects[:2]])
    window.set_snap(True);window.object_snap_action.setChecked(True)
    before=window.project.dumps();start=canvas.rect().center();end=start+QPoint(70,0)
    QTest.mousePress(canvas,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,start)
    QTest.mouseMove(canvas,end,10)
    assert canvas.snap_guides[0]==20
    QTest.mouseRelease(canvas,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,end)
    assert [obj.x for obj in window.project.objects]==[-5,15,25]
    assert canvas.snap_guides==(None,None)
    window.undo();assert window.project.dumps()==before


def test_hidden_and_inspection_filtered_objects_do_not_attract(window):
    canvas=window.canvas;window.select_many([obj.id for obj in window.project.objects[:2]])
    canvas.snap_objects=True;canvas.press=QPointF(0,0)
    window.project.objects[2].visible=False
    assert canvas.movement_delta(QPointF(14,0))==QPointF(14,0)
    window.project.objects[2].visible=True;canvas.inspection_ids={obj.id for obj in window.project.objects[:2]}
    assert canvas.movement_delta(QPointF(14,0))==QPointF(14,0)


def test_screen_tolerance_changes_with_zoom_and_escape_clears_guides(window):
    canvas=window.canvas;window.select_many([obj.id for obj in window.project.objects[:2]])
    canvas.snap_objects=True;canvas.press=QPointF(0,0);canvas.scale=5
    assert canvas.movement_delta(QPointF(13.5,0)).x()==15
    canvas.scale=10;assert canvas.movement_delta(QPointF(13.5,0)).x()==13.5
    before=window.project.dumps();QTest.keyClick(canvas,Qt.Key.Key_Escape)
    assert canvas.snap_guides==(None,None) and window.project.dumps()==before


def test_rotated_manual_design_uses_needle_bounds_instead_of_box_corners():
    from morale.stitch_edit import manual_object
    from morale.object_snapping import object_bounds
    import math
    obj=manual_object(DesignObject(),[[-10,-10,'jump'],[10,10,'stitch']]);obj.rotation=45
    bounds=object_bounds(obj)
    assert bounds.width()==pytest.approx(0,abs=1e-10)
    assert bounds.height()==pytest.approx(20*math.sqrt(2))
    # A transformed rectangular selection box would incorrectly be 28 mm wide.
    delta,guides=snap_bounds([bounds],[QRectF(10,-20,4,40)],QPointF(9,0),1.6)
    assert delta.x()==pytest.approx(10) and guides[0]==10


def test_rotated_reflected_shape_bounds_follow_artwork():
    from morale.object_snapping import object_bounds
    from morale.canvas import Canvas
    obj=DesignObject(kind='polygon',points=[[-.5,-.5],[.5,-.5],[-.5,.5]],width=20,height=10,rotation=37,flip_x=True,x=3,y=-7)
    assert object_bounds(obj)==Canvas.outline_path(obj).boundingRect()


def test_manual_controls_do_not_contribute_false_snap_bounds():
    from morale.object_snapping import object_bounds
    obj=DesignObject(kind='stitches',width=20,height=20,stitch_data=[[-.2,0,'jump'],[.2,0,'stitch'],[.5,.5,'trim']])
    bounds=object_bounds(obj)
    assert bounds==QRectF(-4,0,8,0)


def test_drag_bounds_cache_is_replaced_on_design_refresh(window):
    from morale.object_snapping import object_bounds
    from morale.engine import generate
    window.project.objects[-1].kind='rectangle'
    canvas=window.canvas;window.select_many([window.project.objects[0].id]);canvas.snap_objects=True;canvas.press=QPointF()
    canvas.movement_delta(QPointF(1,0));old=canvas.snap_bounds_cache[window.project.objects[-1].id]
    window.project.objects[-1].rotation=45
    canvas.set_design(window.project,generate(window.project))
    canvas.movement_delta(QPointF(1,0));new=canvas.snap_bounds_cache[window.project.objects[-1].id]
    assert new!=old and new==object_bounds(window.project.objects[-1])
