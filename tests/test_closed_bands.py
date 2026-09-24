import math
import pytest
from morale.model import Project,DesignObject
from morale.auto_digitize import choose_stitches,outline_path,difference_area
from morale.engine import generate


def band(width=2,ellipse=1,reverse=False,offset=0):
    rings=[[[math.cos(i*math.tau/96)*radius/50,math.sin(i*math.tau/96)*radius*ellipse/50]
            for i in range(96)] for radius in (10+width/2,10-width/2)]
    rings=[r[offset:]+r[:offset] for r in rings]
    if reverse: rings=[list(reversed(r)) for r in reversed(rings)]
    return DesignObject(kind='compound',width=50,height=50,contours=rings,underlay=True)


@pytest.mark.parametrize('width,kind',[(.5,'running'),(2,'satin'),(8,'fill')])
@pytest.mark.parametrize('ellipse',[1,1.5])
@pytest.mark.parametrize('reverse',[False,True])
def test_closed_band_hole_seam_and_width(width,kind,ellipse,reverse):
    obj=band(width,ellipse,reverse,13)
    source=Project(objects=[obj]); before=source.dumps()
    result,decisions=choose_stitches(source)
    assert decisions[0]['selected']==kind,decisions
    assert source.dumps()==before
    assert Project.loads(result.dumps()).objects==result.objects
    converted=result.objects[0]
    if kind=='satin':
        assert converted.points[:2]==converted.points[-2:]
        assert difference_area(outline_path(obj.rings()),outline_path(converted.rings()))<.01
    if kind=='running': assert converted.points[0]==converted.points[-1]
    sewn=[s for b in generate(result) for s in b.stitches if s.command=='stitch']
    assert sewn
    # Engine connectors and center underlay must also stay out of the hole.
    assert all(math.hypot(s.x,s.y/ellipse)>=10-width/2-.03 for s in sewn)
    if kind in {'satin','running'}:
        for block in generate(result):
            previous=None
            for stitch in block.stitches:
                point=(stitch.x,stitch.y/ellipse)
                if previous is not None and stitch.command=='stitch':
                    dx=point[0]-previous[0];dy=point[1]-previous[1]; length=dx*dx+dy*dy
                    t=max(0,min(1,-(previous[0]*dx+previous[1]*dy)/length)) if length else 0
                    assert math.hypot(previous[0]+t*dx,previous[1]+t*dy)>=10-width/2-.03
                previous=point


def test_separate_regions_and_multiple_holes_remain_fill():
    obj=band(); obj.contours=[[[x/2+offset,y/2] for x,y in ring]
                              for offset,ring in zip((-.25,.25),obj.contours)]
    multi=band();multi.contours.append([[x*.2,y*.2] for x,y in multi.contours[1]])
    _,decisions=choose_stitches(Project(objects=[obj,multi]))
    assert all(d['selected']=='fill' for d in decisions)


@pytest.mark.parametrize('extension',['dst','exp','jef','pec','pes','tbf','u01','vp3','xxx'])
def test_closed_satin_export_preserves_empty_center(tmp_path,extension):
    from morale.formats import export_machine,import_machine
    project,decisions=choose_stitches(Project(objects=[band()]))
    assert decisions[0]['selected']=='satin'
    path=tmp_path/f'band.{extension}';export_machine(project,path)
    points=[s for b in generate(import_machine(path).project) for s in b.stitches if s.command=='stitch']
    assert points and all(8.85<math.hypot(s.x,s.y)<11.15 for s in points)


def test_traced_ring_becomes_closed_satin(tmp_path):
    from PySide6.QtGui import QImage,QPainter,QColor,QTransform
    from morale.raster_trace import trace_image
    image=QImage(300,300,QImage.Format.Format_RGB32);image.fill(QColor('white'))
    transform=QTransform();transform.translate(150,150);transform.scale(10,10)
    painter=QPainter(image);painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.fillPath(transform.map(outline_path(band().rings())),QColor('red'));painter.end()
    path=tmp_path/'band.png';image.save(str(path))
    traced,_,_=trace_image(path,width=30,resolution=512,method='smooth',smoothing=.15)
    result,decisions=choose_stitches(traced)
    assert decisions[0]['selected']=='satin',decisions
    assert result.objects[0].points[:2]==result.objects[0].points[-2:]
    # Raster curves have small notches; rail fitting may smooth these within the
    # area budget. Verify both changed area and analytic radial containment.
    assert difference_area(outline_path(traced.objects[0].rings()),outline_path(result.objects[0].rings()))<1
    sewn=[s for b in generate(result) for s in b.stitches if s.command=='stitch']
    assert all(8.85<math.hypot(s.x,s.y)<11.15 for s in sewn)


@pytest.mark.parametrize('percent',[0,12.5,25,50,75,99.9])
def test_user_seam_moves_start_and_preserves_closed_geometry(percent):
    source=Project(objects=[band()]);before=source.dumps()
    result,decisions=choose_stitches(source,seams={'0':percent})
    obj=result.objects[0];assert obj.kind=='satin',decisions
    left,right=obj.transform(obj.points[:2]);angle=math.radians(percent*3.6)
    # The control measures the outer boundary, not the midpoint of the closest
    # inner projection (which can differ slightly on polygonal circles).
    assert left==pytest.approx((11*math.cos(angle),11*math.sin(angle)),abs=.02)
    assert obj.points[:2]==obj.points[-2:]
    assert source.dumps()==before and decisions[0]['seam_percent']==percent
    assert difference_area(outline_path(source.objects[0].rings()),outline_path(obj.rings()))<.01


@pytest.mark.parametrize('seams',[{'0':100},{'0':-1},{'0':True},{'0':float('nan')},{'1':50},[]])
def test_invalid_seams_rejected(seams):
    with pytest.raises(ValueError,match='seam'):choose_stitches(Project(objects=[band()]),seams=seams)


def test_native_band_seam_preview_and_persistence(tmp_path):
    import time
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QImage,QPainter,QColor,QTransform
    from PySide6.QtTest import QTest
    from morale.trace_dialog import TraceDialog
    app=QApplication.instance() or QApplication([])
    image=QImage(300,300,QImage.Format.Format_RGB32);image.fill(QColor('white'))
    transform=QTransform();transform.translate(150,150);transform.scale(10,10)
    painter=QPainter(image);painter.fillPath(transform.map(outline_path(band().rings())),QColor('red'));painter.end()
    path=tmp_path/'ring.png';image.save(str(path))
    dialog=TraceDialog(str(path));dialog.width.setValue(30);dialog.smoothing.setValue(.15)
    def preview():
        dialog.generate();deadline=time.monotonic()+10
        while dialog.project is None and time.monotonic()<deadline:QTest.qWait(10)
        assert dialog.project is not None,dialog.status.text()
    try:
        preview();first=dialog.project.objects[0]
        assert first.kind=='satin'
        original_start=first.transform(first.points[:1])[0]
        dialog.decisions.cellWidget(0,4).setValue(50)
        assert dialog.project is None and dialog.seams=={'0':50}
        preview();moved=dialog.project.objects[0]
        assert moved.kind=='satin'
        assert math.dist(original_start,moved.transform(moved.points[:1])[0])>20
        assert Project.loads(dialog.project.dumps()).objects==dialog.project.objects
        dialog.route.setChecked(True);assert dialog.seams=={'0':50}
        dialog.width.setValue(40);assert dialog.seams=={}
    finally:dialog.close()
