import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from copy import deepcopy
import math

import pytest
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication
from morale.auto_digitize import choose_stitches,outline_path,difference_area
from morale.model import Project,DesignObject
from morale.engine import generate


@pytest.fixture(scope='module',autouse=True)
def app(): return QApplication.instance() or QApplication([])


@pytest.mark.parametrize('rotation',[0,17,45,90,137])
@pytest.mark.parametrize('width,expected',[(.5,'running'),(3,'satin'),(9,'fill')])
def test_physical_width_selects_stitches_at_any_rotation(rotation,width,expected):
    source=Project(objects=[DesignObject(kind='rectangle',width=width,height=30,rotation=rotation,x=12,y=-7)])
    before=source.dumps(); result,decisions=choose_stitches(source)
    assert source.dumps()==before
    obj=result.objects[0]
    assert obj.stitch_type==expected,decisions
    assert obj.id==source.objects[0].id and obj.color==source.objects[0].color
    assert Project.loads(result.dumps()).objects==result.objects
    path=outline_path(source.objects[0].rings())
    points=[s for block in generate(result) for s in block.stitches if s.command=='stitch']
    assert points
    # Rounded rail endpoints can lie on a boundary; allow a micron around it.
    from PySide6.QtGui import QPainterPathStroker
    stroker=QPainterPathStroker(); stroker.setWidth(.002)
    allowed=path.united(stroker.createStroke(path))
    assert all(allowed.contains(QPointF(s.x,s.y)) for s in points)
    if expected=='satin':
        actual=outline_path(obj.rings())
        assert difference_area(path,actual)<.01


def test_holes_branches_and_compact_shapes_remain_fill():
    shapes=[DesignObject(kind='ellipse',width=5,height=5),
        DesignObject(kind='compound',width=4,height=30,contours=[
            [[-.5,-.5],[.5,-.5],[.5,.5],[-.5,.5]],
            [[-.2,-.3],[.2,-.3],[.2,.3],[-.2,.3]]]),
        DesignObject(kind='polygon',width=5,height=30,points=[
            [-.5,-.5],[-.2,-.5],[-.2,.2],[.2,.2],[.2,-.5],[.5,-.5],[.5,.5],[-.5,.5]])]
    source=Project(objects=shapes); result,decisions=choose_stitches(source)
    assert all(d['selected']=='fill' for d in decisions)
    assert result.objects==source.objects


def test_curved_monotone_column_reconstructs_outline():
    left=[(-1+math.sin(i/20*math.pi)*2,-10+i) for i in range(21)]
    right=[(x+2,y) for x,y in left]
    obj=DesignObject(kind='compound',x=1,width=4,height=20,contours=[[
        [(x-1)/4,y/20] for x,y in left+list(reversed(right))]])
    result,decisions=choose_stitches(Project(objects=[obj]))
    assert decisions[0]['selected']=='satin',decisions
    before=outline_path(obj.rings()); after=outline_path(result.objects[0].rings())
    assert difference_area(before,after)<.1


def test_overrides_and_size_changes():
    obj=DesignObject(kind='rectangle',width=3,height=25)
    source=Project(objects=[obj])
    assert choose_stitches(source,'fill')[1][0]['selected']=='fill'
    result,decisions=choose_stitches(source,'auto',{'0':'running'})
    assert result.objects[0].stitch_type=='running' and 'replace' in decisions[0]['reason']
    enlarged=deepcopy(source); enlarged.objects[0].width=12
    result,decisions=choose_stitches(enlarged,'auto',{'0':'satin'})
    assert result.objects[0].stitch_type=='fill' and '6 mm' in decisions[0]['reason']


@pytest.mark.parametrize('overrides',[[],{'2':'fill'},{'0':'unknown'},{'-1':'auto'},{'x':'fill'}])
def test_bad_overrides_rejected(overrides):
    with pytest.raises(ValueError): choose_stitches(Project(objects=[DesignObject()]),overrides=overrides)


@pytest.mark.parametrize('extension',['dst','exp','jef','pec','pes','tbf','u01','vp3','xxx'])
def test_automatic_satin_machine_exports(tmp_path,extension):
    from morale.formats import export_machine,import_machine
    project,_=choose_stitches(Project(objects=[DesignObject(kind='rectangle',width=3,height=20,underlay=False)]))
    path=tmp_path/f'column.{extension}'; export_machine(project,path)
    sewn=[s for b in generate(import_machine(path).project) for s in b.stitches if s.command=='stitch']
    assert sewn and all(abs(s.x)<=1.6 and abs(s.y)<=10.1 for s in sewn)
    assert max(s.x for s in sewn)>1.3 and min(s.x for s in sewn)<-1.3


def test_image_worker_region_overrides_and_undo(tmp_path):
    import time
    from PySide6.QtGui import QImage,QPainter,QColor
    from PySide6.QtTest import QTest
    from morale.trace_dialog import TraceDialog
    from morale.app import MainWindow
    image=QImage(200,200,QImage.Format.Format_RGB32); image.fill(QColor('white'))
    painter=QPainter(image)
    for x,width,color in ((20,10,'red'),(50,3,'blue'),(90,50,'green')):
        painter.fillRect(x,20,width,150,QColor(color))
    painter.end(); path=tmp_path/'columns.png'; image.save(str(path))
    dialog=TraceDialog(str(path)); window=MainWindow()
    def preview():
        dialog.generate(); deadline=time.monotonic()+10
        while dialog.project is None and time.monotonic()<deadline: QTest.qWait(10)
        assert dialog.project is not None,dialog.status.text()
    try:
        dialog.width.setValue(40); dialog.minimum.setValue(1)
        preview()
        types={o.stitch_type for o in dialog.project.objects}
        assert types=={'running','satin','fill'}
        satin=next(i for i,o in enumerate(dialog.project.objects) if o.stitch_type=='satin')
        choice=dialog.decisions.cellWidget(satin,1)
        choice.setCurrentIndex(choice.findData('fill'))
        assert dialog.project is None and dialog.overrides=={str(satin):'fill'}
        preview()
        assert dialog.project.objects[satin].stitch_type=='fill'
        dialog.route.setChecked(True)
        assert dialog.project is None and dialog.overrides=={str(satin):'fill'}
        preview()
        assert 'Travel from artwork origin:' in dialog.status.text()
        assert dialog.quality is not None and dialog.quality_button.isEnabled()
        assert [r['object_id'] for r in dialog.quality['regions']]==[o.id for o in dialog.project.objects]
        assert '(sew ' in dialog.decisions.item(0,0).text()
        assert any(o.name.endswith(f'region {satin+1}') and o.stitch_type=='fill' for o in dialog.project.objects)
        dialog.thread_catalog.setCurrentIndex(1)
        assert dialog.project is None and dialog.overrides=={str(satin):'fill'}
        preview()
        assert all(o.thread for o in dialog.project.objects)
        assert dialog.quality['thread_matches']
        assert all(m['metric']=='oklab' for m in dialog.quality['thread_matches'])
        dialog.color_metric.setCurrentIndex(1)
        assert dialog.project is None and dialog.overrides=={str(satin):'fill'}
        preview()
        assert all(m['metric']=='rgb' for m in dialog.quality['thread_matches'])
        dialog.finishing.setChecked(True)
        assert dialog.project is None and dialog.overrides=={str(satin):'fill'}
        preview()
        assert dialog.quality['finishing']['trim_objects']>=1
        assert dialog.project.objects[0].tie_in and dialog.project.objects[-1].trim_after
        dialog.internal_trims.setChecked(True);preview()
        assert all(o.jump_trim==5 for o in dialog.project.objects)
        assert dialog.quality['finishing']['internal_trims']
        dialog.reverse_travel.setChecked(True);assert dialog.project is None
        preview();assert 'Travel from artwork origin:' in dialog.status.text()
        dialog.stitch_mode.setCurrentIndex(1)
        assert dialog.quality is None and not dialog.quality_button.isEnabled()
        assert not dialog.overrides and dialog.decisions.rowCount()==0
        dialog.stitch_mode.setCurrentIndex(0); preview()
        before=window.project.dumps()
        window.apply_raster_trace(dialog.project)
        assert any(o.kind=='satin' for o in window.project.objects)
        window.undo(); assert window.project.dumps()==before
    finally:
        dialog.close(); window.saved=window.project.dumps(); window.close()
