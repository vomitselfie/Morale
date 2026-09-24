import pytest
from PySide6.QtCore import QPointF,Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from morale.app import MainWindow
from morale.model import Project,DesignObject
from morale.engine import generate
from morale.stitch_edit import manual_object

@pytest.fixture
def window():
    app=QApplication.instance() or QApplication([])
    window=MainWindow();window.show();app.processEvents()
    obj=manual_object(DesignObject(),[[-5,0,'jump'],[0,0,'stitch'],[0,0,'trim'],[0,0,'stop'],[5,0,'jump'],[5,5,'stitch']])
    window.replace_project(Project(objects=[obj]));window.select(obj.id);window.set_mode('stitch_nodes');window.canvas.scale=8
    yield window
    window.saved=window.project.dumps();window.close()

def screen(canvas,x,y):return (QPointF(canvas.width()/2,canvas.height()/2)+canvas.pan+QPointF(x,y)*canvas.scale).toPoint()

def click(canvas,x,y,modifier=Qt.KeyboardModifier.NoModifier):
    QTest.mouseClick(canvas,Qt.MouseButton.LeftButton,modifier,screen(canvas,x,y))

def test_toggle_range_and_keyboard_extension(window):
    c=window.canvas;before=window.project.dumps()
    click(c,0,0);click(c,5,5,Qt.KeyboardModifier.ControlModifier)
    assert c.selected_stitch_indices()=={1,5}
    click(c,5,5,Qt.KeyboardModifier.ControlModifier)
    assert c.selected_stitch_indices()=={1}
    click(c,5,5,Qt.KeyboardModifier.ShiftModifier)
    assert c.selected_stitch_indices()=={1,4,5}
    QTest.keyClick(c,Qt.Key.Key_BracketLeft,Qt.KeyboardModifier.ShiftModifier)
    assert c.selected_stitch_indices()=={1,4,5}
    assert window.project.dumps()==before

def test_drag_group_preserves_spacing_controls_and_one_undo(window):
    c=window.canvas;before=window.project.dumps();history=len(window.history)
    click(c,0,0);click(c,5,5,Qt.KeyboardModifier.ControlModifier)
    QTest.mousePress(c,Qt.MouseButton.LeftButton,pos=screen(c,0,0))
    QTest.mouseMove(c,screen(c,2,3));QTest.mouseRelease(c,Qt.MouseButton.LeftButton,pos=screen(c,2,3))
    rows=generate(window.project)[0].stitches
    target=c.world(QPointF(screen(c,2,3)))
    for i in [1,2,3]:assert (rows[i].x,rows[i].y)==pytest.approx((target.x(),target.y()))
    assert (rows[5].x,rows[5].y)==pytest.approx((target.x()+5,target.y()+5))
    assert (rows[0].x,rows[0].y)==pytest.approx((-5,0))
    assert (rows[4].x,rows[4].y)==pytest.approx((5,0))
    assert len(window.history)==history+1 and c.selected_stitch_indices()=={1,5}
    window.undo();assert window.project.dumps()==before

def test_group_nudge_and_snap_preserve_relative_offsets(window):
    c=window.canvas;click(c,0,0);click(c,5,5,Qt.KeyboardModifier.ControlModifier)
    QTest.keyClick(c,Qt.Key.Key_Right,Qt.KeyboardModifier.ShiftModifier)
    rows=window.blocks[0].stitches
    assert rows[1].x==pytest.approx(1) and rows[5].x==pytest.approx(6)
    c.snap_grid=True;c.grid_spacing=2
    QTest.keyClick(c,Qt.Key.Key_Down)
    rows=window.blocks[0].stitches
    assert rows[5].y-rows[1].y==pytest.approx(5)

def test_cancel_group_drag_is_nonmutating(window):
    c=window.canvas;click(c,0,0);click(c,5,5,Qt.KeyboardModifier.ControlModifier)
    before=window.project.dumps()
    QTest.mousePress(c,Qt.MouseButton.LeftButton,pos=screen(c,0,0));QTest.mouseMove(c,screen(c,2,2))
    QTest.keyClick(c,Qt.Key.Key_Escape);QTest.mouseRelease(c,Qt.MouseButton.LeftButton,pos=screen(c,2,2))
    assert window.project.dumps()==before

def test_invalid_bulk_move_rejected_atomically(window):
    before=window.project.dumps();obj=window.project.objects[0]
    window.edit_canvas_stitches(obj.id,[1,5],1000,0)
    assert window.project.dumps()==before and 'rejected' in window.statusBar().currentMessage()

def test_generated_group_move_converts_once_and_undo_restores(window):
    obj=DesignObject(kind='path',stitch_type='running',points=[[-.5,0],[.5,0]],underlay=False)
    window.replace_project(Project(objects=[obj]));window.select(obj.id)
    before=window.project.dumps();original=generate(window.project)[0].stitches
    window.edit_canvas_stitches(obj.id,[1,2],1,2)
    assert window.project.objects[0].kind=='stitches'
    actual=generate(window.project)[0].stitches
    assert len(actual)==len(original)
    for i in [1,2]:assert (actual[i].x,actual[i].y)==pytest.approx((original[i].x+1,original[i].y+2))
    window.undo();assert window.project.dumps()==before

def box(canvas,start,end,modifier=Qt.KeyboardModifier.NoModifier,cancel=False):
    QTest.mousePress(canvas,Qt.MouseButton.LeftButton,modifier,screen(canvas,*start))
    QTest.mouseMove(canvas,screen(canvas,*end))
    if cancel:QTest.keyClick(canvas,Qt.Key.Key_Escape)
    QTest.mouseRelease(canvas,Qt.MouseButton.LeftButton,modifier,screen(canvas,*end))

@pytest.mark.parametrize('reverse',[False,True])
def test_box_selects_motion_points_in_both_directions_without_mutation(window,reverse):
    c=window.canvas;before=window.project.dumps();history=len(window.history)
    start,end=(-2,-2),(7,7)
    box(c,end if reverse else start,start if reverse else end)
    assert c.selected_stitch_indices()=={1,4,5}
    assert window.project.dumps()==before and len(window.history)==history
    assert c.stitch_marquee is None and window.selected_ids=={window.project.objects[0].id}

def test_additive_and_subtractive_boxes(window):
    c=window.canvas;click(c,-5,0)
    box(c,(-2,-2),(2,2),Qt.KeyboardModifier.ControlModifier)
    assert c.selected_stitch_indices()=={0,1}
    box(c,(-2,-2),(2,2),Qt.KeyboardModifier.AltModifier)
    assert c.selected_stitch_indices()=={0}
    box(c,(3,3),(7,7),Qt.KeyboardModifier.ShiftModifier)
    assert c.selected_stitch_indices()=={0,5}

def test_box_cancel_preserves_selection_and_prevents_nudge(window):
    c=window.canvas;click(c,0,0);before=window.project.dumps()
    QTest.mousePress(c,Qt.MouseButton.LeftButton,pos=screen(c,-2,-2))
    QTest.mouseMove(c,screen(c,7,7));QTest.keyClick(c,Qt.Key.Key_Right)
    QTest.keyClick(c,Qt.Key.Key_Escape);QTest.mouseRelease(c,Qt.MouseButton.LeftButton,pos=screen(c,7,7))
    assert c.selected_stitch_indices()=={1} and window.project.dumps()==before

def test_empty_box_clears_and_tool_change_cancels(window):
    c=window.canvas;click(c,0,0)
    box(c,(10,10),(15,15));assert not c.selected_stitch_indices()
    click(c,0,0);QTest.mousePress(c,Qt.MouseButton.LeftButton,pos=screen(c,-2,-2))
    assert c.stitch_marquee is not None
    window.set_mode('select');QTest.mouseRelease(c,Qt.MouseButton.LeftButton,pos=screen(c,7,7))
    assert c.stitch_marquee is None

def test_box_selection_can_be_moved_and_undone(window):
    c=window.canvas;before=window.project.dumps()
    box(c,(-2,-2),(7,7));QTest.keyClick(c,Qt.Key.Key_Right)
    rows=generate(window.project)[0].stitches
    assert rows[0].x==pytest.approx(-5)
    for i,x in [(1,.1),(4,5.1),(5,5.1)]:assert rows[i].x==pytest.approx(x)
    window.undo();assert window.project.dumps()==before

def test_delete_selection_preserves_controls_and_undo(window):
    c=window.canvas;before=window.project.dumps();history=len(window.history)
    click(c,0,0);QTest.keyClick(c,Qt.Key.Key_Delete)
    rows=generate(window.project)[0].stitches
    assert [s.command for s in rows]==['jump','trim','stop','jump','stitch']
    for i in [1,2]:assert (rows[i].x,rows[i].y)==pytest.approx((-5,0))
    assert len(window.project.objects)==1 and len(window.history)==history+1
    assert c.selected_stitch() is not None
    window.undo();assert window.project.dumps()==before

def test_select_all_is_canvas_scoped_and_delete_all_is_rejected(window):
    c=window.canvas;c.setFocus();before=window.project.dumps()
    QTest.keyClick(c,Qt.Key.Key_A,Qt.KeyboardModifier.ControlModifier)
    assert c.selected_stitch_indices()=={0,1,4,5}
    QTest.keyClick(c,Qt.Key.Key_Delete)
    assert window.project.dumps()==before and 'Keep at least one' in window.statusBar().currentMessage()

def test_delete_first_jump_adds_entry_without_losing_next_stitch(window):
    c=window.canvas;before=window.project.dumps();click(c,-5,0)
    QTest.keyClick(c,Qt.Key.Key_Delete)
    rows=generate(window.project)[0].stitches
    assert [s.command for s in rows]==['jump','stitch','trim','stop','jump','stitch']
    assert (rows[0].x,rows[0].y)==pytest.approx((0,0))
    assert 'entry jump' in window.statusBar().currentMessage()
    window.undo();assert window.project.dumps()==before

def test_delete_generated_positions_converts_and_restores(window):
    obj=DesignObject(kind='path',stitch_type='running',points=[[-.5,0],[.5,0]],underlay=False)
    window.replace_project(Project(objects=[obj]));window.select(obj.id)
    before=window.project.dumps();count=len(window.blocks[0].stitches)
    window.delete_canvas_stitches(obj.id,[1,2])
    assert window.project.objects[0].kind=='stitches' and len(window.blocks[0].stitches)==count-2
    window.undo();assert window.project.dumps()==before
