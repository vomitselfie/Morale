import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import math
import time
import xml.etree.ElementTree as ET
import pytest
import svgelements
from PySide6.QtCore import Qt,QPointF
from PySide6.QtGui import QImage,QPainter,QColor
from PySide6.QtWidgets import QApplication,QFileDialog
from PySide6.QtTest import QTest
from morale.raster_trace import trace_image
from morale.model import Project
from morale.canvas import Canvas
from morale.engine import generate
from morale.svg_import import import_svg_text


@pytest.fixture(scope='module',autouse=True)
def app(): return QApplication.instance() or QApplication([])


def circle_image(tmp_path):
    image=QImage(256,256,QImage.Format.Format_ARGB32); image.fill(QColor('white'))
    painter=QPainter(image); painter.setRenderHint(QPainter.RenderHint.Antialiasing); painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor('#d63d79')); painter.drawEllipse(32,32,192,192)
    painter.setBrush(QColor('white')); painter.drawEllipse(96,96,64,64); painter.end()
    path=tmp_path/'ring.png'; image.save(str(path)); return path


def test_smooth_curves_preserve_holes_source_and_compact_svg(tmp_path):
    path=circle_image(tmp_path); original=path.read_bytes()
    pixel,_,_=trace_image(path,width=80,resolution=256,colors=1)
    smooth,_,stats=trace_image(path,width=80,resolution=256,colors=1,method='smooth')
    assert path.read_bytes()==original
    assert stats['palette']==1 and stats['svg']
    assert not any(Canvas.outline_path(o).contains(QPointF(0,0)) for o in smooth.objects)
    assert any(Canvas.outline_path(o).contains(QPointF(20,0)) for o in smooth.objects)
    commands=sum(len(svgelements.Path(p.get('d'))) for p in ET.fromstring(stats['svg']))
    assert commands<sum(len(r) for o in pixel.objects for r in o.contours)/4
    def circle_error(project):
        ring=max([r for o in project.objects for r in o.rings()],key=lambda r:max(math.hypot(*p) for p in r))
        error=length=0
        for a,b in zip(ring,ring[1:]+ring[:1]):
            n=math.dist(a,b); middle=((a[0]+b[0])/2,(a[1]+b[1])/2)
            error+=n*(math.hypot(*middle)-30)**2; length+=n
        return math.sqrt(error/length)
    assert circle_error(smooth)<circle_error(pixel)
    assert Project.loads(smooth.dumps()).objects==smooth.objects


def test_physical_page_size_and_asymmetric_padding_are_retained(tmp_path):
    image=QImage(64,32,QImage.Format.Format_RGB32); image.fill(QColor('white'))
    painter=QPainter(image); painter.fillRect(4,4,24,16,QColor('red')); painter.end()
    path=tmp_path/'offset.png'; image.save(str(path))
    project,_,stats=trace_image(path,width=80,colors=1,method='smooth',resolution=512,smoothing=0)
    assert len(project.objects)==1
    obj=project.objects[0]
    assert (obj.x,obj.y,obj.width,obj.height)==pytest.approx((-20,-5,30,20),abs=.05)
    root=ET.fromstring(stats['svg'])
    assert root.get('width')=='80mm' and root.get('height')=='40mm'
    reopened=import_svg_text(stats['svg'],center_artwork=False)
    assert reopened.objects[0].rings()==obj.rings()


def test_shared_color_boundary_has_no_material_overlap_or_gap(tmp_path):
    image=QImage(64,64,QImage.Format.Format_RGB32)
    for y in range(64):
        for x in range(64): image.setPixelColor(x,y,QColor('red' if x<16+y//2 else 'blue'))
    path=tmp_path/'shared.png'; image.save(str(path))
    project,_,stats=trace_image(path,width=40,colors=2,method='smooth',minimum_region=1)
    assert stats['palette']==2 and len(project.objects)==2
    paths=[Canvas.outline_path(o) for o in project.objects]
    def area(path):
        total=0
        for polygon in path.toFillPolygons():
            points=[(p.x(),p.y()) for p in polygon]
            total+=abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(points,points[1:]+points[:1])))/2
        return total
    assert area(paths[0].intersected(paths[1]))<.05
    assert area(paths[0].united(paths[1]))==pytest.approx(1600,abs=.05)


@pytest.mark.parametrize('colors',[1,2,4])
def test_thread_color_limit_with_white_background(tmp_path,colors):
    image=QImage(80,40,QImage.Format.Format_RGB32); image.fill(QColor('white'))
    painter=QPainter(image)
    for index,color in enumerate(('red','blue','green','orange','purple','cyan')):
        painter.fillRect(4+index*12,4,10,32,QColor(color))
    painter.end(); path=tmp_path/'colors.png'; image.save(str(path))
    project,_,stats=trace_image(path,colors=colors,method='smooth',minimum_region=1)
    assert 1<=stats['palette']<=colors
    assert all(min(QColor(o.color).red(),QColor(o.color).green(),QColor(o.color).blue())<245 for o in project.objects)


def test_transparency_and_detail_filter(tmp_path):
    image=QImage(32,32,QImage.Format.Format_ARGB32); image.fill(Qt.GlobalColor.transparent)
    painter=QPainter(image); painter.fillRect(4,4,8,8,QColor('red')); painter.fillRect(20,20,2,2,QColor('red')); painter.end()
    path=tmp_path/'alpha.png'; image.save(str(path))
    project,_,_=trace_image(path,method='smooth',minimum_region=4,colors=1)
    assert len(project.objects)==1
    assert not Canvas.outline_path(project.objects[0]).contains(QPointF(15,15))
    project,_,_=trace_image(path,method='smooth',minimum_region=1,colors=1)
    assert any(Canvas.outline_path(o).contains(QPointF(12.5,12.5)) for o in project.objects)


def test_native_smooth_preview_svg_save_and_invalidation(tmp_path,monkeypatch):
    from morale.trace_dialog import TraceDialog
    dialog=TraceDialog(str(circle_image(tmp_path)))
    target=tmp_path/'traced.svg'
    monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *args,**kwargs:(str(target),'SVG artwork (*.svg)'))
    try:
        assert dialog.method.currentData()=='smooth'
        dialog.generate(); deadline=time.monotonic()+10
        while dialog.project is None and time.monotonic()<deadline: QTest.qWait(10)
        assert dialog.project is not None,dialog.status.text()
        assert dialog.svg and dialog.save_svg_button.isEnabled()
        assert not dialog.vector_preview.pixmap().isNull()
        dialog.save_svg(); assert target.read_text()==dialog.svg
        dialog.smoothing.setValue(.4)
        assert dialog.project is None and not dialog.svg and not dialog.save_svg_button.isEnabled()
        dialog.method.setCurrentIndex(1)
        assert dialog.resolution.currentData()<=256 and not dialog.smoothing.isEnabled()
    finally: dialog.close()


@pytest.mark.parametrize('extension',['dst','exp','jef','pec','pes','tbf','u01','vp3','xxx'])
def test_smoothed_trace_exports_in_all_formats(tmp_path,extension):
    from morale.formats import export_machine,import_machine
    project,_,_=trace_image(circle_image(tmp_path),width=40,colors=1,method='smooth')
    path=tmp_path/f'smooth.{extension}'; export_machine(project,path)
    points=[s for b in generate(import_machine(path).project) for s in b.stitches if s.command=='stitch']
    assert points and all(math.hypot(s.x,s.y)>4.5 for s in points)
    assert all(abs(s.x)<15.5 and abs(s.y)<15.5 for s in points)
