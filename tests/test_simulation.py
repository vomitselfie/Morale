import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QPointF
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication

from morale.simulation import Timeline
from morale.engine import Stitch, Block
from morale.model import Project, DesignObject
from morale.stitch_edit import manual_object
from morale.canvas import Canvas


@pytest.fixture(scope="module",autouse=True)
def app():
    return QApplication.instance() or QApplication([])


def blocks():
    return [Block('a','#ff0000',[Stitch(-10,0,'jump'),Stitch(0,0),Stitch(0,0,'trim'),Stitch(10,0,'jump'),Stitch(20,0),Stitch(20,0,'stop')]),
            Block('b','#0000ff',[Stitch(20,10,'jump'),Stitch(30,10)])]


def test_event_positions_and_playback_prefix_are_exact():
    timeline=Timeline(blocks())
    assert [(e[0],e[1]) for e in timeline.events]==[(1,'jump'),(3,'trim'),(4,'jump'),(6,'stop'),(7,'thread'),(7,'jump')]
    assert list(timeline.visible_events(0))==[]
    assert [e[1] for e in timeline.visible_events(3)]==['jump','trim']
    event=next(e for e in timeline.events if e[0]==7 and e[1]=='jump')
    assert event[2:4]==((20,0),(20,10))
    assert [e[1] for e in timeline.visible_events(None,{'b'})]==['thread','jump']


def test_thread_identity_and_forced_repeats_match_sewing_runs():
    source=blocks()[0]
    same=Block('same',source.color,[Stitch(30,0)])
    forced=Block('forced',source.color,[Stitch(40,0)],color_break=True)
    catalog=Block('catalog',source.color,[Stitch(50,0)],thread={'catalog_number':'different'})
    empty=Block('empty','#123456',[])
    timeline=Timeline([source,same,empty,forced,catalog])
    assert [r['ids'] for r in timeline.runs]==[{'a','same'},{'forced'},{'catalog'}]
    assert [(r['start'],r['end']) for r in timeline.runs]==[(0,7),(7,8),(8,9)]


def test_control_navigation_respects_range_and_does_not_loop_on_duplicate_indices():
    timeline=Timeline(blocks())
    assert timeline.next_control(0,1)==3
    assert timeline.next_control(3,1)==6
    assert timeline.next_control(7,1)==8
    assert timeline.next_control(7,-1)==6
    assert timeline.next_control(7,-1,6,8)==6
    assert timeline.next_control(6,-1,6,8)==6


def test_control_coordinates_do_not_move_the_travel_origin():
    timeline=Timeline([Block('a','#123456',[Stitch(10,10),Stitch(99,99,'trim'),Stitch(20,20,'jump')])])
    jump=timeline.events[-1]
    assert jump[2:4]==((10,10),(20,20))


def overlay_image(canvas,playhead):
    image=QImage(400,300,QImage.Format.Format_RGB32)
    image.fill(0xffffffff)
    painter=QPainter(image)
    painter.translate(150,100)
    painter.scale(5,5)
    canvas.playhead=playhead
    canvas.paint_command_overlays(painter)
    painter.end()
    return image


def test_rendered_travel_is_separate_from_stitches_and_respects_playhead():
    canvas=Canvas()
    canvas.timeline=Timeline(blocks())
    canvas.scale=5
    canvas.show_travel=True
    canvas.show_controls=True
    before=overlay_image(canvas,0)
    partial=overlay_image(canvas,3)
    complete=overlay_image(canvas,None)
    assert before.pixelColor(150,100).name()=='#ffffff'
    assert partial.pixelColor(150,100).name()!='#ffffff'  # Trim at origin.
    assert partial.pixelColor(250,100).name()=='#ffffff'  # Stop has not happened.
    assert complete.pixelColor(254,100).name()!='#ffffff'  # Stop square edge.
    canvas.close()


def test_native_thread_inspection_playback_reset_and_overlays_do_not_edit_project():
    from morale.app import MainWindow
    window=MainWindow()
    try:
        a=manual_object(DesignObject(color='#ff0000'),[(-10,0,'jump'),(0,0,'stitch'),(0,0,'trim'),(10,0,'jump'),(20,0,'stitch'),(20,0,'stop')])
        b=manual_object(DesignObject(color='#0000ff'),[(20,10,'jump'),(30,10,'stitch')])
        window.replace_project(Project(objects=[a,b]))
        before=window.project.dumps()
        assert window.thread_run.count()==3
        window.toggle_overlay('show_travel',True)
        window.toggle_overlay('show_controls',True)
        window.thread_run.setCurrentIndex(2)
        assert window.canvas.inspection_ids=={b.id}
        assert (window.slider.minimum(),window.slider.maximum())==(6,8)
        assert window.canvas.playhead==6
        window.jump_control(1)
        assert window.canvas.playhead==7
        assert 'jump' in window.counter.text()
        window.tick()
        assert window.canvas.playhead==8
        window.play()
        window.timer.stop()
        assert window.canvas.playhead==6
        window.reset_playback()
        assert window.canvas.inspection_ids is None and window.canvas.playhead is None
        assert window.thread_run.currentIndex()==0 and window.slider.minimum()==0
        assert window.project.dumps()==before and not window.history
    finally:
        window.saved=window.project.dumps()
        window.close()


def test_canvas_thread_inspection_hides_other_runs_in_rendered_view():
    from morale.app import MainWindow
    window=MainWindow()
    try:
        a=manual_object(DesignObject(color='#ff0000'),[(-20,-10,'jump'),(-10,-10,'stitch')])
        b=manual_object(DesignObject(color='#0000ff'),[(10,10,'jump'),(20,10,'stitch')])
        window.replace_project(Project(objects=[a,b]))
        window.show()
        QApplication.processEvents()
        window.canvas.scale=8
        def red_pixels():
            image=window.canvas.grab().toImage()
            cx,cy=window.canvas.width()/2,window.canvas.height()/2
            return sum(1 for y in range(int(cy-83),int(cy-77)) for x in range(int(cx-155),int(cx-85))
                       if (c:=image.pixelColor(x,y)).red()>c.blue()+80)
        assert red_pixels()>0
        window.thread_run.setCurrentIndex(2)
        window.slider.setValue(window.slider.maximum())
        assert red_pixels()==0
        window.reset_playback()
        assert red_pixels()>0
    finally:
        window.saved=window.project.dumps()
        window.close()
