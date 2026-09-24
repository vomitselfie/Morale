import math
import pytest
from morale.model import Project,DesignObject
from morale.auto_digitize import choose_stitches,outline_path,difference_area,area
from morale.branch_regions import split_branches
from morale.engine import generate


def tee(rotation=0):
    return DesignObject(kind='polygon',width=12,height=24,rotation=rotation,underlay=False,
        points=[[-.5,-.5],[.5,-.5],[.5,-.4],[.1,-.4],[.1,.5],[-.1,.5],[-.1,-.4],[-.5,-.4]])


@pytest.mark.parametrize('rotation',[0,23,90,147])
def test_tee_splits_into_editable_columns_without_area_overlap(rotation):
    source=Project(objects=[tee(rotation)]);before=source.dumps()
    split,notes=split_branches(source)
    assert notes and len(split.objects)==2
    assert source.dumps()==before
    result,decisions=choose_stitches(split)
    assert all(d['selected']=='satin' for d in decisions),decisions
    combined=outline_path([r for o in split.objects for r in o.rings()])
    original=outline_path(source.objects[0].rings())
    assert difference_area(original,combined)<.001
    assert sum(area(outline_path(o.rings())) for o in split.objects)==pytest.approx(area(original),abs=.001)
    assert Project.loads(result.dumps()).objects==result.objects


def test_ordinary_shapes_and_existing_columns_are_not_fragmented():
    source=Project(objects=[DesignObject(kind='rectangle'),DesignObject(kind='rectangle',width=2,height=30)])
    result,notes=split_branches(source)
    assert notes==[] and result.objects==source.objects


@pytest.mark.parametrize('field,value',[('stop_after',True),('color_break',True),('stage_note','Place fabric'),('group_id','group')])
def test_semantic_controls_are_not_duplicated_across_branches(field,value):
    obj=tee();setattr(obj,field,value);source=Project(objects=[obj])
    result,notes=split_branches(source)
    assert result.objects==source.objects and notes==[]


def test_forked_shape_preserves_coverage_and_has_multiple_columns():
    ring=[(-1,10),(1,10),(1,1),(8,-8),(6,-10),(0,-2),(-6,-10),(-8,-8),(-1,1)]
    source=Project(objects=[DesignObject(kind='polygon',width=20,height=20,underlay=False,
        points=[[x/20,y/20] for x,y in ring])])
    split,notes=split_branches(source)
    assert notes and len(split.objects)>=3
    result,decisions=choose_stitches(split)
    assert sum(d['selected']=='satin' for d in decisions)>=2
    assert difference_area(outline_path(source.objects[0].rings()),outline_path([r for o in split.objects for r in o.rings()]))<.01


def test_native_raster_branch_preview_and_undo(tmp_path):
    import time
    from PySide6.QtGui import QImage,QPainter,QColor,QTransform
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTest import QTest
    from morale.trace_dialog import TraceDialog
    from morale.app import MainWindow
    app=QApplication.instance() or QApplication([])
    image=QImage(300,300,QImage.Format.Format_RGB32);image.fill(QColor('white'))
    transform=QTransform();transform.translate(150,150);transform.scale(10,10)
    painter=QPainter(image);painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.fillPath(transform.map(outline_path(tee().rings())),QColor('red'));painter.end()
    path=tmp_path/'tee.png';image.save(str(path))
    dialog=TraceDialog(str(path));window=MainWindow()
    dialog.width.setValue(30);dialog.smoothing.setValue(.15);dialog.branching.setChecked(True)
    try:
        dialog.generate();deadline=time.monotonic()+10
        while dialog.project is None and time.monotonic()<deadline:QTest.qWait(10)
        assert dialog.project is not None,dialog.status.text()
        assert len(dialog.project.objects)>=2 and sum(o.kind=='satin' for o in dialog.project.objects)>=2
        assert dialog.decisions.rowCount()==len(dialog.project.objects)
        before=window.project.dumps();window.apply_raster_trace(dialog.project)
        assert sum(o.kind=='satin' for o in window.project.objects)>=2
        window.undo();assert window.project.dumps()==before
        dialog.overrides={'0':'fill'};dialog.branching.setChecked(False)
        assert dialog.project is None and not dialog.overrides
    finally:dialog.close();window.saved=window.project.dumps();window.close()


@pytest.mark.parametrize('extension',['dst','exp','jef','pec','pes','tbf','u01','vp3','xxx'])
def test_branch_export_stays_inside_silhouette(tmp_path,extension):
    from morale.formats import export_machine,import_machine
    source=Project(objects=[tee()]);split,_=split_branches(source);project,_=choose_stitches(split)
    path=tmp_path/f'branch.{extension}';export_machine(project,path)
    sewn=[s for b in generate(import_machine(path).project) for s in b.stitches if s.command=='stitch']
    assert sewn
    assert all((-6.1<=s.x<=6.1 and -12.1<=s.y<=-9.5) or (-1.3<=s.x<=1.3 and -9.7<=s.y<=12.1) for s in sewn)
