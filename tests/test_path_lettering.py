import math
import pytest
from PySide6.QtGui import QPainterPath, QPainterPathStroker
from PySide6.QtCore import Qt, QPointF
from PySide6.QtWidgets import QApplication
from morale.lettering import make_lettering, LetteringDialog, lettering_font
from morale.path_lettering import layout_on_path
from morale.model import Project, DesignObject
from morale.engine import generate
from morale.formats import export_machine, import_machine


@pytest.fixture(scope='module', autouse=True)
def app():
    return QApplication.instance() or QApplication([])


def letters(text='MOM', **kwargs):
    return make_lettering(text, 'DejaVu Sans', 10, layout='path', **kwargs)


def world_baseline(obj):
    return obj.transform(obj.lettering['baseline'])


@pytest.mark.parametrize('rotation,flip_x,flip_y,scale', [(0,False,False,1),(37,True,False,1),(-90,False,True,1.5)])
def test_edit_retains_world_baseline_after_transform_and_reload(rotation,flip_x,flip_y,scale):
    obj=letters(baseline=[[-60,10],[0,-5],[60,10]])
    obj.rotation=rotation;obj.flip_x=flip_x;obj.flip_y=flip_y
    obj.width*=scale;obj.height*=scale;obj.x+=7;obj.y-=3
    obj=Project.loads(Project(objects=[obj]).dumps()).objects[0]
    before=world_baseline(obj)
    edited=make_lettering('MAMA','DejaVu Sans',10*scale,previous=obj,layout='path')
    for a,b in zip(before,world_baseline(edited)):assert a==pytest.approx(b)
    assert edited.id==obj.id and edited.contours!=obj.contours
    assert (edited.rotation,edited.flip_x,edited.flip_y)==(rotation,flip_x,flip_y)


def test_replacement_baseline_uses_world_coordinates():
    obj=letters(baseline=[[-60,0],[60,0]])
    obj.rotation=31;obj.flip_x=True
    baseline=[[-50,20],[0,10],[50,20]]
    changed=letters(previous=obj,baseline=baseline)
    for a,b in zip(world_baseline(changed),baseline):assert a==pytest.approx(b)


@pytest.mark.parametrize('text', ['A\u0301ffi','مرحبا','BOB'])
def test_horizontal_baseline_preserves_shaped_outline(text):
    font,_=lettering_font(text,'DejaVu Sans',10,100)
    expected=QPainterPath();expected.setFillRule(Qt.FillRule.WindingFill);expected.addText(0,0,font,text)
    bounds=expected.boundingRect();scale=10/bounds.height()
    actual=layout_on_path(text,font,10,[[-80,0],[80,0]])
    # Compare containment across the outline, including counters and shaped ligatures.
    for ix in range(100):
        for iy in range(30):
            x=(ix+.37)/100*bounds.width()+bounds.left()
            y=(iy+.37)/30*bounds.height()+bounds.top()
            if abs(expected.contains(QPointF(x,y))-actual.contains(QPointF((x-bounds.center().x())*scale,y*scale))):
                # Ignore sub-flattening-tolerance edge samples.
                stroker=QPainterPathStroker();stroker.setWidth(.15/scale)
                assert stroker.createStroke(expected).contains(QPointF(x,y))


@pytest.mark.parametrize('baseline', [None,[],[[0,0],[0,0]],[[0,0],[1,0]],[[0,0],[math.inf,0]],[[0,0],[True,0]]])
def test_invalid_or_short_baselines_rejected(baseline):
    with pytest.raises(ValueError):letters(baseline=baseline)


def test_schema_rejects_missing_or_invalid_baseline():
    obj=letters(baseline=[[-60,0],[60,0]])
    for bad in (None,[[0,0],[0,0]],[[0,0],[float('inf'),0]]):
        obj.lettering['baseline']=bad
        with pytest.raises(ValueError):Project.loads(Project(objects=[obj]).dumps())


def test_native_add_hide_and_edit_are_atomic_and_undoable(monkeypatch):
    from morale.app import MainWindow
    guide=DesignObject(kind='path',width=120,height=20,points=[[-.5,0],[0,-.5],[.5,0]],stitch_type='running')
    window=MainWindow();window.replace_project(Project(objects=[guide]));window.select_many([guide.id])
    before=window.project.dumps()
    def accept(dialog):
        assert dialog.layout_choice.currentData()=='path'
        dialog.text.setText('MOM');dialog.height.setValue(10);dialog.accept()
        return dialog.DialogCode.Accepted
    monkeypatch.setattr(LetteringDialog,'exec',accept)
    monkeypatch.setattr(window,'error',lambda message:pytest.fail(message))
    try:
        window.add_path_lettering()
        assert len(window.project.objects)==2 and not window.project.objects[0].visible
        obj=window.project.objects[1];stored=world_baseline(obj)
        snapshot=window.project.dumps()
        edited=letters('MAMA',previous=obj)
        window.apply_lettering(edited,replace=True)
        window.undo();assert window.project.dumps()==snapshot
        window.project.objects[0].points=[[0,0],[.1,.1]]
        for a,b in zip(world_baseline(window.project.objects[1]),stored):assert a==pytest.approx(b)
        window.undo();assert window.project.dumps()==before
    finally:
        window.saved=window.project.dumps();window.close()


@pytest.mark.parametrize('extension',['dst','exp','jef','pec','pes','tbf','u01','vp3','xxx'])
def test_path_lettering_writer_bounds(tmp_path,extension):
    obj=letters(baseline=[[-60,10],[0,-10],[60,10]])
    source=Project(objects=[obj]);path=tmp_path/f'path.{extension}'
    export_machine(source,path);restored=import_machine(path).project
    before=[s for b in generate(source) for s in b.stitches if s.command=='stitch']
    after=[s for b in generate(restored) for s in b.stitches if s.command=='stitch']
    for axis in ('x','y'):
        for fn in (min,max):assert fn(getattr(s,axis) for s in before)==pytest.approx(fn(getattr(s,axis) for s in after),abs=.15)
