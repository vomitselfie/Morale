import math
import pytest
from morale.model import Project,DesignObject
from morale.auto_digitize import choose_stitches,column_pairs,difference_area,outline_path
from morale.engine import generate


def ribbon(width=2,rotation=0):
    outer=[]; inner=[]
    for i in range(97):
        a=math.radians(-135+270*i/96)
        outer.append(((10+width/2)*math.cos(a),(10+width/2)*math.sin(a)))
        inner.append(((10-width/2)*math.cos(a),(10-width/2)*math.sin(a)))
    ring=outer+list(reversed(inner))
    return DesignObject(kind='compound',width=30,height=30,rotation=rotation,
        contours=[[[x/30,y/30] for x,y in ring]],underlay=False)


@pytest.mark.parametrize('rotation',[0,23,90,181])
@pytest.mark.parametrize('width,selected',[(.5,'running'),(2,'satin'),(8,'fill')])
def test_bending_ribbon_stitch_selection(rotation,width,selected):
    obj=ribbon(width,rotation); source=Project(objects=[obj]); before=source.dumps()
    assert column_pairs(obj)[0] is None
    result,decisions=choose_stitches(source)
    assert decisions[0]['selected']==selected,decisions
    assert source.dumps()==before
    assert Project.loads(result.dumps()).objects==result.objects
    if selected=='satin':
        assert difference_area(outline_path(obj.rings()),outline_path(result.objects[0].rings()))<.01
    sewn=[s for b in generate(result) for s in b.stitches if s.command=='stitch']
    assert sewn
    if selected in {'running','satin'}:
        assert all(10-width/2-.02<=math.hypot(s.x,s.y)<=10+width/2+.02 for s in sewn)


def test_closed_ring_becomes_satin_and_true_branch_stays_fill():
    ring=DesignObject(kind='compound',width=20,height=20,contours=[
        [[math.cos(i*math.tau/96)*r,math.sin(i*math.tau/96)*r] for i in range(96)] for r in (.5,.4)])
    branch=DesignObject(kind='polygon',width=10,height=20,points=[
        [-.5,-.5],[.5,-.5],[.5,-.4],[.1,-.4],[.1,.5],[-.1,.5],[-.1,-.4],[-.5,-.4]])
    result,decisions=choose_stitches(Project(objects=[ring,branch]))
    assert [d['selected'] for d in decisions]==['satin','fill']


@pytest.mark.parametrize('extension',['dst','exp','jef','pec','pes','tbf','u01','vp3','xxx'])
def test_curved_satin_machine_roundtrip(tmp_path,extension):
    from morale.formats import export_machine,import_machine
    project,decisions=choose_stitches(Project(objects=[ribbon()]))
    assert decisions[0]['selected']=='satin'
    path=tmp_path/f'curved.{extension}'; export_machine(project,path)
    sewn=[s for b in generate(import_machine(path).project) for s in b.stitches if s.command=='stitch']
    assert sewn and all(8.85<math.hypot(s.x,s.y)<11.15 for s in sewn)


def test_rasterized_curved_artwork_gets_editable_satin(tmp_path):
    from PySide6.QtGui import QImage,QPainter,QColor,QTransform
    from morale.raster_trace import trace_image
    image=QImage(300,300,QImage.Format.Format_RGB32); image.fill(QColor('white'))
    transform=QTransform(); transform.translate(150,150); transform.scale(10,10)
    painter=QPainter(image); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.fillPath(transform.map(outline_path(ribbon().rings())),QColor('red')); painter.end()
    path=tmp_path/'curved.png'; image.save(str(path))
    traced,_,_=trace_image(path,width=30,resolution=512,method='smooth',smoothing=.15)
    result,decisions=choose_stitches(traced)
    assert decisions[0]['selected']=='satin',decisions
    assert difference_area(outline_path(traced.objects[0].rings()),outline_path(result.objects[0].rings()))<.5
    assert result.objects[0].kind=='satin' and result.objects[0].points
