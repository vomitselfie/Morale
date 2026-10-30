import json
import pytest
from PySide6.QtWidgets import QApplication,QInputDialog
from morale.model import Project
from morale.guides import validate_guides,edit_guides
from morale.engine import generate

@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])


def test_guides_roundtrip_legacy_and_no_sewn_geometry():
    p=Project(guides=[{'axis':'x','position':12.5},{'axis':'y','position':-5}])
    assert Project.loads(p.dumps()).guides==p.guides and generate(p)==[]
    old=json.loads(p.dumps());old.pop('guides');assert Project.loads(json.dumps(old)).guides==[]

@pytest.mark.parametrize('guides',[None,[{}],[{'axis':'z','position':0}],[{'axis':'x','position':True}],
                                  [{'axis':'x','position':1001}],[{'axis':'x','position':float('nan')}],
                                  [{'axis':'x','position':0}]*101])
def test_invalid_guides(guides):
    with pytest.raises(ValueError):validate_guides(guides)


def test_native_edit_undo_cancel_and_invalid_input(monkeypatch):
    from morale.app import MainWindow
    w=MainWindow();errors=[]
    try:
        w.replace_project(Project());before=w.project.dumps();monkeypatch.setattr(w,'error',errors.append)
        monkeypatch.setattr(QInputDialog,'getMultiLineText',lambda *a:('x 10\ny -20',True))
        edit_guides(w);assert len(w.project.guides)==2
        assert not w.canvas.grab().isNull()
        after=w.project.dumps();w.undo();assert w.project.dumps()==before
        w.redo();assert w.project.dumps()==after
        monkeypatch.setattr(QInputDialog,'getMultiLineText',lambda *a:('invalid',True))
        edit_guides(w);assert errors and w.project.dumps()==after
        monkeypatch.setattr(QInputDialog,'getMultiLineText',lambda *a:('',False))
        edit_guides(w);assert w.project.dumps()==after
    finally:w.saved=w.project.dumps();w.close()


def test_guides_snap_raw_position_before_grid_and_respect_zoom_and_visibility():
    from morale.canvas import Canvas
    from PySide6.QtCore import QPointF
    canvas=Canvas();canvas.set_design(Project(guides=[{'axis':'x','position':3},{'axis':'y','position':-2}]),[])
    canvas.scale=5;canvas.snap_layout_guides=True;canvas.snap_grid=True;canvas.grid_spacing=10
    assert canvas.snapped(QPointF(3.5,-2.5))==QPointF(3,-2)
    canvas.scale=40;assert canvas.snapped(QPointF(3.5,-2.5))==QPointF(0,0)
    canvas.scale=5;canvas.show_layout_guides=False
    assert canvas.snapped(QPointF(3.5,-2.5))==QPointF(0,0)
    canvas.close()


def test_object_center_snaps_without_grid_and_keyboard_can_leave_guide():
    from morale.canvas import Canvas
    from morale.model import DesignObject
    from PySide6.QtCore import QPointF,Qt
    from PySide6.QtTest import QTest
    obj=DesignObject(x=0,y=0)
    canvas=Canvas();canvas.set_design(Project(objects=[obj],guides=[{'axis':'x','position':10}]),[])
    canvas.selected_id=obj.id;canvas.press=QPointF();canvas.snap_layout_guides=True
    assert canvas.movement_delta(QPointF(9,4))==QPointF(10,4)
    canvas.set_mode('path');canvas.cursor_point=QPointF(10,0)
    QTest.keyClick(canvas,Qt.Key.Key_Right);assert canvas.cursor_point==QPointF(11,0)
    canvas.close()


def test_selection_union_edge_snaps_to_guide_as_one_rigid_group():
    from morale.canvas import Canvas
    from morale.model import DesignObject
    from PySide6.QtCore import QPointF
    objects=[DesignObject(kind='rectangle',x=-10,width=10,height=10),DesignObject(kind='rectangle',x=10,width=10,height=10)]
    canvas=Canvas();canvas.set_design(Project(objects=objects,guides=[{'axis':'x','position':30}]),[])
    canvas.selected_id=objects[0].id;canvas.selected_ids={o.id for o in objects};canvas.press=QPointF()
    canvas.snap_layout_guides=True
    assert canvas.movement_delta(QPointF(14,2))==QPointF(15,2)
    assert canvas.snap_guides==(30,None)
    canvas.show_layout_guides=False
    assert canvas.movement_delta(QPointF(14,2))==QPointF(14,2)
    canvas.close()


def test_object_snapping_precedence_keeps_unmatched_layout_axis():
    from morale.canvas import Canvas
    from morale.model import DesignObject
    from PySide6.QtCore import QPointF
    moving=DesignObject(kind='rectangle',width=10,height=10)
    target=DesignObject(kind='rectangle',x=22,width=10,height=10,y=40)
    canvas=Canvas();canvas.set_design(Project(objects=[moving,target],guides=[{'axis':'x','position':18},{'axis':'y','position':8}]),[])
    canvas.selected_id=moving.id;canvas.press=QPointF();canvas.snap_layout_guides=True;canvas.snap_objects=True
    delta=canvas.movement_delta(QPointF(12.5,2.5))
    assert delta==QPointF(12,3) and canvas.snap_guides==(17,8)
    canvas.close()


@pytest.mark.parametrize('axis',['x','y'])
def test_ruler_drag_adds_guide_with_undo(axis):
    from morale.app import MainWindow
    from PySide6.QtCore import QPoint,QPointF,Qt
    from PySide6.QtTest import QTest
    w=MainWindow()
    try:
        w.replace_project(Project());canvas=w.canvas;canvas.resize(600,600);canvas.scale=5
        before=w.project.dumps();start=QPoint(12,200) if axis=='x' else QPoint(200,12);end=QPoint(350,350)
        QTest.mousePress(canvas,Qt.MouseButton.LeftButton,pos=start)
        assert canvas.guide_draft is not None and not w.project.guides
        assert not canvas.grab().isNull()
        assert canvas.guide_draft is not None and not w.project.guides
        expected=canvas.world(QPointF(end)).x() if axis=='x' else canvas.world(QPointF(end)).y()
        QTest.mouseMove(canvas,end);QTest.mouseRelease(canvas,Qt.MouseButton.LeftButton,pos=end)
        assert w.project.guides==[{'axis':axis,'position':expected}]
        w.undo();assert w.project.dumps()==before
        w.redo();assert w.project.guides==[{'axis':axis,'position':expected}]
    finally:w.saved=w.project.dumps();w.close()


def test_ruler_drag_escape_and_release_on_ruler_cancel():
    from morale.canvas import Canvas
    from PySide6.QtCore import QPoint,QPointF,Qt
    from PySide6.QtTest import QTest
    canvas=Canvas();canvas.set_design(Project(),[]);added=[];canvas.guide_added.connect(lambda *a:added.append(a))
    QTest.mousePress(canvas,Qt.MouseButton.LeftButton,pos=QPoint(12,100))
    QTest.keyClick(canvas,Qt.Key.Key_Escape)
    QTest.mouseRelease(canvas,Qt.MouseButton.LeftButton,pos=QPoint(200,200))
    assert not added and canvas.guide_draft is None
    QTest.mousePress(canvas,Qt.MouseButton.LeftButton,pos=QPoint(12,100))
    QTest.mouseRelease(canvas,Qt.MouseButton.LeftButton,pos=QPoint(12,150))
    assert not added
    canvas.close()
