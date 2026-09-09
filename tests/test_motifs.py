import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import math

import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPointF,Qt
from PySide6.QtTest import QTest

from morale.motifs import motif_paths
from morale.model import Project,DesignObject
from morale.engine import generate,preflight
from morale.formats import export_machine,import_machine


@pytest.fixture(scope='module',autouse=True)
def app():
    return QApplication.instance() or QApplication([])


def guide(**kwargs):
    return DesignObject(kind='path',stitch_type='motif',width=20,height=1,points=[[-.5,0],[.5,0]],**kwargs)


def center(path):
    return ((min(x for x,y in path)+max(x for x,y in path))/2,(min(y for x,y in path)+max(y for x,y in path))/2)


def test_open_guide_centers_repeats_with_requested_size_and_spacing():
    paths=list(motif_paths(guide()))
    assert len(paths)==4
    assert [center(path)[0] for path in paths]==pytest.approx([-7.5,-2.5,2.5,7.5])
    assert all(max(x for x,y in p)-min(x for x,y in p)==pytest.approx(4) for p in paths)
    assert all(max(y for x,y in p)-min(y for x,y in p)==pytest.approx(3) for p in paths)


@pytest.mark.parametrize('pattern,paths_per_repeat',[('diamond',1),('box',1),('cross',2)])
def test_motifs_have_explicit_travel_breaks_and_bounded_stitches(pattern,paths_per_repeat):
    obj=guide(motif_pattern=pattern,stitch_length=.5)
    stitches=generate(Project(objects=[obj]))[0].stitches
    assert sum(s.command=='jump' for s in stitches)==4*paths_per_repeat
    assert all(math.dist((a.x,a.y),(b.x,b.y))<=.50000001 for a,b in zip(stitches,stitches[1:]) if b.command=='stitch')


def test_rotated_guide_rotates_motifs_without_changing_their_size():
    original=list(motif_paths(guide()))
    rotated=list(motif_paths(guide(rotation=90)))
    for a,b in zip(original,rotated):
        for (x,y),point in zip(a,b):
            assert point==pytest.approx((-y,x))


def test_closed_guide_distributes_repeats_without_duplicate_seam():
    obj=DesignObject(kind='rectangle',width=10,height=10,stitch_type='motif',motif_spacing=6)
    paths=list(motif_paths(obj))
    assert len(paths)==6
    assert len({tuple(round(v,6) for v in center(p)) for p in paths})==6


def test_short_guide_produces_no_partial_motif():
    obj=guide()
    obj.width=2
    assert list(motif_paths(obj))==[]


def test_repeat_limit_is_enforced_for_complex_guides():
    obj=guide(motif_spacing=.5,motif_width=.5)
    obj.width=500
    obj.points=[[-.5,0],[.5,0]]*10
    with pytest.raises(ValueError,match='5,000'):
        list(motif_paths(obj))


def test_bounds_check_includes_motif_extensions():
    obj=guide(motif_height=10,y=9)
    project=Project(hoop_width=20,hoop_height=20,objects=[obj])
    assert preflight(project,generate(project))


@pytest.mark.parametrize('key,value',[('motif_pattern','unknown'),('motif_width',0),('motif_height',31),('motif_spacing',float('nan'))])
def test_invalid_motif_settings_rejected(key,value):
    obj=guide()
    setattr(obj,key,value)
    with pytest.raises(ValueError):
        Project.loads(Project(objects=[obj]).dumps())


def test_native_motif_settings_units_undo_and_persistence():
    from morale.app import MainWindow
    window=MainWindow()
    try:
        obj=guide()
        obj.stitch_type='running'
        window.replace_project(Project(objects=[obj]))
        window.select(obj.id)
        before=window.project.dumps()
        window.stitch_type.setCurrentIndex(window.stitch_type.findData('motif'))
        assert window.project.objects[0].stitch_type=='motif'
        assert window.fields['motif_width'].isEnabled()
        window.motif_pattern.setCurrentIndex(window.motif_pattern.findData('cross'))
        window.fields['motif_height'].setValue(5)
        saved=window.project.dumps()
        window.set_unit('in')
        assert window.project.dumps()==saved
        assert window.fields['motif_height'].value()==pytest.approx(5/25.4,abs=.0001)
        assert Project.loads(saved).objects[0].motif_pattern=='cross'
        window.undo(); window.undo(); window.undo()
        assert window.project.dumps()==before
    finally:
        window.saved=window.project.dumps()
        window.close()


def test_motif_can_be_selected_by_its_stitches_away_from_guide():
    from morale.app import MainWindow
    window=MainWindow()
    try:
        obj=guide()
        window.replace_project(Project(objects=[obj]))
        window.show()
        QApplication.processEvents()
        canvas=window.canvas
        canvas.scale=8
        point=(QPointF(canvas.width()/2,canvas.height()/2)+QPointF(-7.5,-1.5)*canvas.scale).toPoint()
        QTest.mouseClick(canvas,Qt.MouseButton.LeftButton,pos=point)
        assert window.selected_id==obj.id and not window.history
    finally:
        window.saved=window.project.dumps()
        window.close()


@pytest.mark.parametrize('extension',['dst','exp','jef','pec','pes','tbf','u01','vp3','xxx'])
def test_motifs_export_through_all_writers(tmp_path,extension):
    path=tmp_path/f'motifs.{extension}'
    export_machine(Project(objects=[guide()]),path)
    stitches=[s for b in generate(import_machine(path).project) for s in b.stitches if s.command=='stitch']
    assert stitches
    assert (min(s.x for s in stitches),max(s.x for s in stitches),min(s.y for s in stitches),max(s.y for s in stitches))==pytest.approx((-9.5,9.5,-1.5,1.5),abs=.15)
