import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import pytest
from PySide6.QtCore import QPointF,Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from morale.app import MainWindow
from morale.model import Project,DesignObject
from morale.engine import generate


@pytest.fixture
def window():
    app=QApplication.instance() or QApplication([])
    window=MainWindow(); window.show(); app.processEvents()
    yield window
    window.saved=window.project.dumps(); window.close()


def setup(window,obj):
    window.replace_project(Project(objects=[obj])); window.select(obj.id); window.set_mode('stitch_nodes')
    window.canvas.scale=8; window.canvas.pan=QPointF()
    QApplication.processEvents()
    return window.canvas


def screen(canvas,point):
    return (QPointF(canvas.width()/2,canvas.height()/2)+canvas.pan+QPointF(*point)*canvas.scale).toPoint()


def drag(canvas,start,end,cancel=False):
    QTest.mousePress(canvas,Qt.MouseButton.LeftButton,pos=screen(canvas,start))
    QTest.mouseMove(canvas,screen(canvas,end))
    if cancel: QTest.keyClick(canvas,Qt.Key.Key_Escape)
    QTest.mouseRelease(canvas,Qt.MouseButton.LeftButton,pos=screen(canvas,end))


def manual():
    return DesignObject(kind='stitches',stitch_type='manual',rotation=31,flip_x=True,
        stitch_data=[[-.5,-.5,'jump'],[0,0,'stitch'],[0,0,'trim'],[0,0,'stop'],[.5,.5,'jump'],[.5,0,'stitch']])


def test_drag_manual_stitch_updates_controls_preserves_commands_and_undo(window):
    obj=manual(); canvas=setup(window,obj)
    before=window.project.dumps(); history=len(window.history)
    drag(canvas,(0,0),(3,4))
    rows=generate(window.project)[0].stitches
    assert [s.command for s in rows]==[row[2] for row in obj.stitch_data]
    for s in rows[1:4]: assert (s.x,s.y)==pytest.approx((3,4),abs=.08)
    original=generate(Project(objects=[obj]))[0].stitches
    for a,b in zip(original[4:],rows[4:]): assert (a.x,a.y)==pytest.approx((b.x,b.y))
    assert len(window.history)==history+1
    assert canvas.selected_stitch()[1]==1
    window.undo(); assert window.project.dumps()==before


def test_generated_stitch_click_is_nonmutating_move_converts_and_undo_restores(window):
    obj=DesignObject(kind='path',stitch_type='running',points=[[-.5,-.5],[0,.2],[.5,.5]],underlay=False)
    canvas=setup(window,obj)
    before=window.project.dumps()
    s=window.blocks[0].stitches[3]; point=(s.x,s.y)
    QTest.mouseClick(canvas,Qt.MouseButton.LeftButton,pos=screen(canvas,point))
    assert window.project.dumps()==before
    drag(canvas,point,(s.x+2,s.y-2))
    assert window.project.objects[0].kind=='stitches'
    assert len(window.blocks[0].stitches)==len(generate(Project(objects=[obj]))[0].stitches)
    window.undo(); assert window.project.dumps()==before


def test_drag_escape_snap_and_invalid_move(window):
    obj=manual(); canvas=setup(window,obj)
    before=window.project.dumps()
    drag(canvas,(0,0),(3,4),cancel=True)
    assert window.project.dumps()==before and canvas.stitch_drag is None
    canvas.snap_grid=True; canvas.grid_spacing=2
    drag(canvas,(0,0),(3.2,4.3))
    s=window.blocks[0].stitches[1]
    assert (s.x,s.y)==pytest.approx((4,4))
    before=window.project.dumps(); count=len(window.history)
    window.edit_canvas_stitch(obj.id,1,1001,0)
    assert window.project.dumps()==before and len(window.history)==count
    assert 'rejected' in window.statusBar().currentMessage()


def test_coincident_positions_cycle_and_keyboard_skips_controls(window):
    obj=DesignObject(kind='stitches',stitch_type='manual',stitch_data=[[-.5,0,'jump'],[0,0,'stitch'],[0,0,'trim'],[0,0,'stitch'],[0,0,'stop'],[.5,0,'stitch']])
    canvas=setup(window,obj)
    for index in (1,3,1):
        QTest.mouseClick(canvas,Qt.MouseButton.LeftButton,pos=screen(canvas,(0,0)))
        assert canvas.selected_stitch()[1]==index
    QTest.keyClick(canvas,Qt.Key.Key_BracketRight)
    assert canvas.selected_stitch()[1]==3
    QTest.keyClick(canvas,Qt.Key.Key_Right)
    rows=window.blocks[0].stitches
    assert rows[1].x==pytest.approx(0)
    assert rows[3].x==pytest.approx(.1) and rows[4].x==pytest.approx(.1)
    QTest.keyClick(canvas,Qt.Key.Key_Down,Qt.KeyboardModifier.ShiftModifier)
    assert window.blocks[0].stitches[3].y==pytest.approx(1)


def test_playback_and_multiselection_prevent_stitch_edits(window):
    obj=manual(); canvas=setup(window,obj)
    before=window.project.dumps()
    canvas.playhead=1
    drag(canvas,(0,0),(3,4))
    QTest.keyClick(canvas,Qt.Key.Key_Right)
    assert window.project.dumps()==before
    canvas.playhead=None; canvas.selected_ids={obj.id,'another'}
    drag(canvas,(0,0),(3,4))
    assert window.project.dumps()==before


def test_switching_tool_cancels_preview(window):
    obj=manual(); canvas=setup(window,obj)
    before=window.project.dumps()
    QTest.mousePress(canvas,Qt.MouseButton.LeftButton,pos=screen(canvas,(0,0)))
    QTest.mouseMove(canvas,screen(canvas,(3,4)))
    assert canvas.stitch_drag is not None
    window.set_mode('select')
    QTest.mouseRelease(canvas,Qt.MouseButton.LeftButton,pos=screen(canvas,(3,4)))
    assert canvas.stitch_drag is None and window.project.dumps()==before


@pytest.mark.parametrize('extension',['dst','exp','jef','pec','pes','tbf','u01','vp3','xxx'])
def test_canvas_moved_stitch_persists_and_exports(window,tmp_path,extension):
    from morale.formats import export_machine,import_machine
    obj=DesignObject(kind='stitches',stitch_type='manual',stitch_data=[[-.5,0,'jump'],[0,0,'stitch'],[.5,.5,'stitch']])
    setup(window,obj)
    window.edit_canvas_stitch(obj.id,1,3.4,-2.7)
    project=Project.loads(window.project.dumps())
    assert (generate(project)[0].stitches[1].x,generate(project)[0].stitches[1].y)==pytest.approx((3.4,-2.7))
    path=tmp_path/f'moved.{extension}'; export_machine(project,path)
    stitches=[s for b in generate(import_machine(path).project) for s in b.stitches if s.command=='stitch']
    assert any(abs(s.x-3.4)<.15 and abs(s.y+2.7)<.15 for s in stitches)


def test_manual_rebasing_after_precise_moves():
    from morale.stitch_edit import manual_object
    import random
    randomizer=random.Random(236)
    for _ in range(100):
        rows=[[randomizer.uniform(-40,40),randomizer.uniform(-40,40),'jump']]+[[randomizer.uniform(-40,40),randomizer.uniform(-40,40),'stitch'] for _ in range(3)]
        result=manual_object(DesignObject(),rows)
        actual=generate(Project(objects=[result]))[0].stitches
        for row,stitch in zip(rows,actual): assert (stitch.x,stitch.y)==pytest.approx(row[:2],abs=1e-10)
