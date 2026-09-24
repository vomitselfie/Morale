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
    assert notes and len(split.objects)>=2
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


def _stroked(segments,width,rotation=0,rounded=False):
    """Union of stroked centerlines, as flattened artwork outlines would arrive."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QPainterPath,QPainterPathStroker
    path=QPainterPath()
    for segment in segments:
        line=QPainterPath();line.moveTo(*segment[0])
        for point in segment[1:]:line.lineTo(*point)
        stroker=QPainterPathStroker();stroker.setWidth(width)
        stroker.setCapStyle(Qt.PenCapStyle.RoundCap if rounded else Qt.PenCapStyle.FlatCap)
        stroker.setJoinStyle(Qt.PenJoinStyle.RoundJoin if rounded else Qt.PenJoinStyle.MiterJoin)
        path=path.united(stroker.createStroke(line))
    return _polygon(path,rotation)


def _polygon(path,rotation):
    ring=[(p.x(),p.y()) for p in path.simplified().toFillPolygons()[0]]
    if ring[0]==ring[-1]:ring.pop()
    c,s=math.cos(math.radians(rotation)),math.sin(math.radians(rotation))
    ring=[(x*c-y*s,x*s+y*c) for x,y in ring]
    xs,ys=zip(*ring);cx,cy=(min(xs)+max(xs))/2,(min(ys)+max(ys))/2;w,h=max(xs)-min(xs),max(ys)-min(ys)
    return DesignObject(kind='polygon',x=cx,y=cy,width=w,height=h,underlay=False,points=[[(x-cx)/w,(y-cy)/h] for x,y in ring])


def _radial(count,length=10,offset=0):
    return [[(0,0),(length*math.cos(2*math.pi*k/count+offset),length*math.sin(2*math.pi*k/count+offset))] for k in range(count)]


@pytest.mark.parametrize('name,segments,width,rounded',[
    ('Y',_radial(3,offset=math.pi/2),3,False),
    ('rounded Y',_radial(3,offset=math.pi/2),3,True),
    ('X',_radial(4,offset=math.pi/5),3,False),
    ('star',_radial(5,length=9),2.5,False),
    ('K',[[(0,-10),(0,10)],[(0,1),(7,-9)],[(2,-1),(7,9)]],2.2,False)])
@pytest.mark.parametrize('rotation',[0,17,40])
def test_obliquely_branching_shapes_become_satin_columns(name,segments,width,rounded,rotation):
    # Straight horizontal/vertical/principal cuts cannot separate these arms at
    # every rotation; crotch-to-crotch chords can.
    source=Project(objects=[_stroked(segments,width,rotation,rounded)])
    split,notes=split_branches(source)
    assert notes and 2<=len(split.objects)<=len(segments)+1
    _,decisions=choose_stitches(split)
    assert all(d['selected']=='satin' for d in decisions),(name,decisions)
    original=outline_path(source.objects[0].rings())
    assert difference_area(original,outline_path([r for o in split.objects for r in o.rings()]))<.001
    assert sum(area(outline_path(o.rings())) for o in split.objects)==pytest.approx(area(original),abs=.001)


@pytest.mark.parametrize('rotation',[0,17,40])
def test_stem_is_cut_from_broad_fill_without_slivers(rotation):
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QPainterPath,QPainterPathStroker
    leaf=QPainterPath();leaf.addEllipse(QPointF(0,-7),5,8)
    stem=QPainterPath();stem.moveTo(0,0);stem.lineTo(0,9)
    stroker=QPainterPathStroker();stroker.setWidth(1.6)
    source=Project(objects=[_polygon(leaf.united(stroker.createStroke(stem)),rotation)])
    split,notes=split_branches(source)
    assert notes and len(split.objects)==2
    _,decisions=choose_stitches(split)
    assert sorted(d['selected'] for d in decisions)==['fill','satin']


def _on_or_inside(ring,point):
    from morale.branch_regions import _contains
    for a,b in zip(ring,ring[1:]+ring[:1]):
        dx,dy=b[0]-a[0],b[1]-a[1];length=dx*dx+dy*dy
        t=max(0,min(1,((point[0]-a[0])*dx+(point[1]-a[1])*dy)/length)) if length else 0
        if math.hypot(a[0]+t*dx-point[0],a[1]+t*dy-point[1])<1e-6:return True
    return _contains(ring,point)


@pytest.mark.parametrize('name,segments,width',[
    ('Y',_radial(3,offset=math.pi/2),3),('X',_radial(4,offset=math.pi/5),3),
    ('star',_radial(5,length=9),2.5),('K',[[(0,-10),(0,10)],[(0,1),(7,-9)],[(2,-1),(7,9)]],2.2)])
@pytest.mark.parametrize('rotation',[0,17,40])
def test_branch_joins_overlap_inside_the_artwork(name,segments,width,rotation):
    source=Project(objects=[_stroked(segments,width,rotation)])
    exact,exact_notes=split_branches(source)
    overlapped,notes=split_branches(source,.3)
    assert exact_notes[0]['overlapped_joins']==0 and exact_notes[0]['joins']==notes[0]['joins']>=1
    assert notes[0]['overlapped_joins']==notes[0]['joins']
    outline=source.objects[0].rings()[0]
    assert all(_on_or_inside(outline,p) for o in overlapped.objects for p in o.rings()[0])
    extra=sum(area(outline_path(o.rings())) for o in overlapped.objects)-sum(area(outline_path(o.rings())) for o in exact.objects)
    assert 0<extra<=.3*9*notes[0]['joins']
    _,decisions=choose_stitches(overlapped)
    assert all(d['selected']=='satin' for d in decisions),decisions


def test_overlapped_stem_export_stays_inside_silhouette(tmp_path):
    from morale.formats import export_machine,import_machine
    source=Project(objects=[tee()]);split,notes=split_branches(source,.5)
    assert notes[0]['overlapped_joins']==1
    project,_=choose_stitches(split);path=tmp_path/'branch.dst';export_machine(project,path)
    sewn=[s for b in generate(import_machine(path).project) for s in b.stitches if s.command=='stitch']
    assert sewn and all((-6.1<=s.x<=6.1 and -12.1<=s.y<=-9.5) or (-1.3<=s.x<=1.3 and -9.7<=s.y<=12.1) for s in sewn)


@pytest.mark.parametrize('value',[-.1,1.5,True,'0.3',float('nan')])
def test_invalid_join_overlap_is_rejected(value):
    with pytest.raises(ValueError):split_branches(Project(objects=[tee()]),value)
