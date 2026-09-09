import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import time
import sys

import pytest
from PySide6.QtCore import QPointF,QProcess
from PySide6.QtGui import QImage,QColor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QDialogButtonBox

from morale.raster_trace import trace_image
from morale.trace_dialog import TraceDialog
from morale.canvas import Canvas
from morale.model import Project,DesignObject
from morale.engine import generate
from morale.formats import export_machine,import_machine


@pytest.fixture(scope='module',autouse=True)
def app():
    return QApplication.instance() or QApplication([])


def fixture_image(tmp_path):
    image=QImage(32,32,QImage.Format.Format_ARGB32)
    image.fill(QColor('white'))
    for y in range(4,28):
        for x in range(4,28):
            if not(12<=x<20 and 12<=y<20):
                image.setPixelColor(x,y,QColor('red'))
    path=tmp_path/'art.png'
    assert image.save(str(path))
    return path


def wait_for(predicate):
    deadline=time.monotonic()+8
    while not predicate() and time.monotonic()<deadline:
        QTest.qWait(10)
    assert predicate()


def test_tracing_preserves_hole_physical_dimensions_and_source_file(tmp_path):
    path=fixture_image(tmp_path)
    data=path.read_bytes()
    project,_,stats=trace_image(path,width=40,colors=2)
    assert path.read_bytes()==data
    assert len(project.objects)==1 and stats['palette']==1
    obj=project.objects[0]
    assert (obj.width,obj.height)==pytest.approx((30,30))
    assert not Canvas.outline_path(obj).contains(QPointF(0,0))
    assert Canvas.outline_path(obj).contains(QPointF(10,0))
    assert obj.color=='#ff0000'
    for block in generate(project):
        assert all(not(abs(s.x)<4.9 and abs(s.y)<4.9) for s in block.stitches if s.command=='stitch')
    assert Project.loads(project.dumps()).objects[0].contours==obj.contours


def test_palette_limit_and_white_background_option(tmp_path):
    path=fixture_image(tmp_path)
    project,_,_=trace_image(path,colors=2,ignore_white=False)
    assert {o.color for o in project.objects}=={'#ffffff','#ff0000'}
    project,_,_=trace_image(path,colors=1,ignore_white=False)
    assert len(project.objects)==1


def test_transparency_and_small_regions(tmp_path):
    image=QImage(8,8,QImage.Format.Format_ARGB32)
    image.fill(QColor(0,0,0,0))
    for y in range(2,4):
        for x in range(2,4): image.setPixelColor(x,y,QColor(255,0,0,128))
    image.setPixelColor(7,7,QColor(255,0,0,128))
    path=tmp_path/'alpha.png'
    image.save(str(path))
    project,_,stats=trace_image(path,width=40,minimum_region=2)
    assert stats['omitted_pixels']==1
    assert len(project.objects)==1 and project.objects[0].color=='#ff7f7f'
    assert project.objects[0].width==pytest.approx(10)


@pytest.mark.parametrize('settings',[{'width':0},{'colors':17},{'resolution':512},{'minimum_region':0},{'ignore_white':'yes'}])
def test_invalid_settings_rejected(tmp_path,settings):
    with pytest.raises(ValueError): trace_image(fixture_image(tmp_path),**settings)


def test_excessively_fragmented_trace_rejected(tmp_path):
    image=QImage(64,64,QImage.Format.Format_RGB32)
    for y in range(64):
        for x in range(64):
            image.setPixelColor(x,y,QColor('red' if x%2==0 and y%2==0 else 'white'))
    path=tmp_path/'fragmented.png'
    image.save(str(path))
    with pytest.raises(ValueError,match='limits'):
        trace_image(path,minimum_region=1)


def test_real_trace_worker_preview_invalidation_and_application(tmp_path):
    from morale.app import MainWindow
    path=fixture_image(tmp_path)
    dialog=TraceDialog(str(path))
    window=MainWindow()
    try:
        dialog.generate()
        wait_for(lambda:dialog.project is not None or dialog.runner.path is None)
        assert dialog.project is not None,dialog.status.text()
        before=window.project.dumps()
        count=len(window.project.objects)
        window.apply_raster_trace(dialog.project)
        assert len(window.project.objects)>count
        window.undo()
        assert window.project.dumps()==before
        dialog.colors.setValue(2)
        assert dialog.project is None
        assert not dialog.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled()
    finally:
        dialog.close()
        window.saved=window.project.dumps()
        window.close()


def test_closing_trace_dialog_kills_worker(tmp_path,monkeypatch):
    dialog=TraceDialog(str(fixture_image(tmp_path)))
    monkeypatch.setattr(dialog.runner,'command',lambda *args:(sys.executable,['-c','import time; time.sleep(30)']))
    try:
        dialog.generate()
        assert dialog.runner.process.waitForStarted(2000)
        dialog.close()
        assert dialog.runner.process.state()==QProcess.ProcessState.NotRunning
    finally:
        dialog.runner.cancel()


@pytest.mark.parametrize('extension',['dst','exp','jef','pec','pes','tbf','u01','vp3','xxx'])
def test_traced_artwork_exports_in_all_formats(tmp_path,extension):
    project,_,_=trace_image(fixture_image(tmp_path),width=40)
    path=tmp_path/f'trace.{extension}'
    export_machine(project,path)
    stitches=[s for b in generate(import_machine(path).project) for s in b.stitches if s.command=='stitch']
    assert stitches
    assert all(not(abs(s.x)<4.8 and abs(s.y)<4.8) for s in stitches)
