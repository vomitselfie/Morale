import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from morale.canvas import Canvas
from morale.model import Project

@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])

@pytest.mark.parametrize('mode',['rectangle','ellipse','leaf'])
def test_keyboard_shape_corners(mode):
    canvas=Canvas();canvas.set_design(Project(),[]);canvas.set_mode(mode);drawn=[]
    canvas.drawn.connect(lambda kind,points:drawn.append((kind,points)))
    QTest.keyClick(canvas,Qt.Key.Key_Home);QTest.keyClick(canvas,Qt.Key.Key_Space)
    QTest.keyClick(canvas,Qt.Key.Key_Right,Qt.KeyboardModifier.ShiftModifier)
    QTest.keyClick(canvas,Qt.Key.Key_Down,Qt.KeyboardModifier.ShiftModifier)
    QTest.keyClick(canvas,Qt.Key.Key_Space)
    assert drawn==[(mode,[(0.,0.),(10.,10.)])]
    assert canvas.press is None
    canvas.close()


def test_keyboard_path_points_backspace_finish_and_cancel():
    canvas=Canvas();canvas.set_design(Project(),[]);canvas.set_mode('path');drawn=[]
    canvas.drawn.connect(lambda *args:drawn.append(args))
    QTest.keyClick(canvas,Qt.Key.Key_Home);QTest.keyClick(canvas,Qt.Key.Key_Space)
    QTest.keyClick(canvas,Qt.Key.Key_Right);QTest.keyClick(canvas,Qt.Key.Key_Space)
    QTest.keyClick(canvas,Qt.Key.Key_Backspace)
    assert len(canvas.vertices)==1
    QTest.keyClick(canvas,Qt.Key.Key_Down);QTest.keyClick(canvas,Qt.Key.Key_Space)
    QTest.keyClick(canvas,Qt.Key.Key_Return)
    assert drawn[0][1]==[(0.,0.),(1.,1.)]
    QTest.keyClick(canvas,Qt.Key.Key_Escape)
    assert not canvas.vertices and canvas.press is None
    canvas.close()


def test_native_keyboard_drawing_creates_editable_object_and_undo():
    from morale.app import MainWindow
    window=MainWindow()
    try:
        window.replace_project(Project());before=window.project.dumps()
        canvas=window.canvas;canvas.set_mode('rectangle')
        for key,modifier in [(Qt.Key.Key_Home,Qt.KeyboardModifier.NoModifier),(Qt.Key.Key_Space,Qt.KeyboardModifier.NoModifier),
                             (Qt.Key.Key_Right,Qt.KeyboardModifier.ShiftModifier),(Qt.Key.Key_Down,Qt.KeyboardModifier.ShiftModifier),
                             (Qt.Key.Key_Space,Qt.KeyboardModifier.NoModifier)]:QTest.keyClick(canvas,key,modifier)
        assert len(window.project.objects)==1
        obj=window.project.objects[0]
        assert obj.kind=='rectangle' and obj.width==obj.height==10
        window.undo();assert window.project.dumps()==before
    finally:window.saved=window.project.dumps();window.close()


@pytest.mark.parametrize('mode',['polygon','satin'])
def test_native_keyboard_polygon_and_satin_export(tmp_path,mode):
    from morale.app import MainWindow
    from morale.engine import generate
    from morale.formats import export_machine
    from morale.export_verify import verify_export
    window=MainWindow()
    try:
        window.replace_project(Project());canvas=window.canvas;canvas.set_mode(mode)
        canvas.snap_grid=True;canvas.grid_spacing=2
        QTest.keyClick(canvas,Qt.Key.Key_Home);QTest.keyClick(canvas,Qt.Key.Key_Space)
        QTest.keyClick(canvas,Qt.Key.Key_Right);QTest.keyClick(canvas,Qt.Key.Key_Space)
        QTest.keyClick(canvas,Qt.Key.Key_Down);QTest.keyClick(canvas,Qt.Key.Key_Left);QTest.keyClick(canvas,Qt.Key.Key_Space)
        if mode=='satin':
            QTest.keyClick(canvas,Qt.Key.Key_Return)
            assert not window.project.objects and len(canvas.vertices)==3
            QTest.keyClick(canvas,Qt.Key.Key_Right);QTest.keyClick(canvas,Qt.Key.Key_Space)
        QTest.keyClick(canvas,Qt.Key.Key_Return)
        assert len(window.project.objects)==1
        obj=window.project.objects[0];assert obj.kind==mode
        assert obj.width==obj.height==2
        blocks=generate(window.project);assert blocks
        for extension in ('pes','exp'):
            path=tmp_path/f'keyboard.{extension}'
            export_machine(window.project,path,blocks)
            result=verify_export(blocks,path)
            assert result['complete_path_comparison'] and result['bounds_delta_mm']<=.3
            assert not result['problems'],result
        window.undo();assert not window.project.objects
    finally:window.saved=window.project.dumps();window.close()


def test_keyboard_drawing_is_blocked_during_playback():
    canvas=Canvas();canvas.set_design(Project(),[]);canvas.set_mode('path');canvas.playhead=0
    QTest.keyClick(canvas,Qt.Key.Key_Space);QTest.keyClick(canvas,Qt.Key.Key_Right)
    assert not canvas.vertices and canvas.cursor_point.x()==0
    canvas.close()


def test_playback_cannot_commit_an_existing_keyboard_draft():
    from PySide6.QtCore import QPointF
    canvas=Canvas();canvas.set_design(Project(),[]);canvas.set_mode('path')
    canvas.vertices=[QPointF(0,0),QPointF(10,0)];canvas.playhead=0;drawn=[]
    canvas.drawn.connect(lambda *args:drawn.append(args))
    QTest.keyClick(canvas,Qt.Key.Key_Return)
    assert not drawn and len(canvas.vertices)==2
    canvas.close()


def test_keyboard_cursor_pans_into_view_without_moving_draft_points():
    from PySide6.QtCore import QPointF
    canvas=Canvas();canvas.resize(240,180);canvas.set_design(Project(),[]);canvas.set_mode('path')
    canvas.scale=40
    QTest.keyClick(canvas,Qt.Key.Key_Space)
    QTest.keyClick(canvas,Qt.Key.Key_Right,Qt.KeyboardModifier.ShiftModifier)
    screen=QPointF(canvas.width()/2,canvas.height()/2)+canvas.pan+canvas.cursor_point*canvas.scale
    assert 40<=screen.x()<=canvas.width()-40 and 40<=screen.y()<=canvas.height()-40
    assert canvas.pan.x()<0 and canvas.vertices==[QPointF(0,0)]
    assert canvas.cursor_point==QPointF(10,0)
    QTest.keyClick(canvas,Qt.Key.Key_Home)
    screen=QPointF(canvas.width()/2,canvas.height()/2)+canvas.pan
    assert 40<=screen.x()<=canvas.width()-40
    canvas.close()


@pytest.mark.parametrize('direction,coordinate',[(Qt.Key.Key_Right,999),(Qt.Key.Key_Left,-999)])
def test_keyboard_grid_limit_stays_inside_editable_coordinate_range(direction,coordinate):
    from PySide6.QtCore import QPointF
    canvas=Canvas();canvas.set_design(Project(),[]);canvas.set_mode('path')
    canvas.snap_grid=True;canvas.grid_spacing=3;canvas.cursor_point=QPointF(coordinate,0)
    QTest.keyClick(canvas,direction)
    assert canvas.cursor_point.x()==coordinate
    assert abs(canvas.cursor_point.x())<=1000
    canvas.close()


def test_keyboard_tools_menu_enters_canvas_and_creates_rectangle():
    from morale.app import MainWindow
    window=MainWindow()
    try:
        window.replace_project(Project());window.show();window.activateWindow();QApplication.processEvents()
        action=window.mode_actions['rectangle']
        assert action in window.tools_menu.actions()
        window.tools_menu.popup(window.mapToGlobal(window.rect().center()))
        window.tools_menu.setActiveAction(action)
        QTest.keyClick(window.tools_menu,Qt.Key.Key_Return);QApplication.processEvents()
        assert window.canvas.mode=='rectangle' and window.focusWidget() is window.canvas
        # Offscreen Qt leaves the hidden popup active; emulate the window manager's restoration.
        window.activateWindow();QApplication.processEvents()
        assert window.canvas.hasFocus()
        QTest.keyClick(window.canvas,Qt.Key.Key_Home);QTest.keyClick(window.canvas,Qt.Key.Key_Space)
        QTest.keyClick(window.canvas,Qt.Key.Key_Right,Qt.KeyboardModifier.ShiftModifier)
        QTest.keyClick(window.canvas,Qt.Key.Key_Down,Qt.KeyboardModifier.ShiftModifier)
        QTest.keyClick(window.canvas,Qt.Key.Key_Space)
        assert len(window.project.objects)==1 and window.project.objects[0].kind=='rectangle'
        window.undo();assert not window.project.objects
    finally:window.saved=window.project.dumps();window.close()


@pytest.mark.parametrize('modifier',[Qt.KeyboardModifier.ControlModifier,Qt.KeyboardModifier.MetaModifier])
@pytest.mark.parametrize('key',[Qt.Key.Key_Backspace,Qt.Key.Key_Space,Qt.Key.Key_Home,Qt.Key.Key_Right])
def test_drawing_does_not_consume_control_or_command_combinations(key,modifier):
    from PySide6.QtCore import QEvent,QPointF
    from PySide6.QtGui import QKeyEvent
    canvas=Canvas();canvas.set_design(Project(),[]);canvas.set_mode('path')
    canvas.cursor_point=QPointF(4,5);canvas.vertices=[QPointF(1,2)]
    before_pan=QPointF(canvas.pan)
    assert not canvas.drawing_key(QKeyEvent(QEvent.Type.KeyPress,key,modifier))
    assert canvas.cursor_point==QPointF(4,5) and canvas.vertices==[QPointF(1,2)]
    assert canvas.pan==before_pan and not canvas.keyboard_cursor
    canvas.close()


@pytest.mark.parametrize('modifier',[Qt.KeyboardModifier.ControlModifier,Qt.KeyboardModifier.MetaModifier])
def test_modified_enter_does_not_finish_path_and_arrow_does_not_nudge(modifier):
    from PySide6.QtCore import QPointF
    canvas=Canvas();canvas.set_design(Project(),[]);canvas.set_mode('path')
    canvas.vertices=[QPointF(0,0),QPointF(10,0)];drawn=[];moved=[]
    canvas.drawn.connect(lambda *args:drawn.append(args));canvas.moved.connect(lambda *args:moved.append(args))
    QTest.keyClick(canvas,Qt.Key.Key_Return,modifier)
    assert not drawn and len(canvas.vertices)==2
    canvas.set_mode('select');canvas.selected_id='object'
    QTest.keyClick(canvas,Qt.Key.Key_Right,modifier)
    assert not moved
    QTest.keyClick(canvas,Qt.Key.Key_Right)
    assert moved==[('object',.1,0.)]
    canvas.close()
