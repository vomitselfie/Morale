import pytest
from PySide6.QtWidgets import QApplication
from morale.applique import applique_stages,AppliqueDialog
from morale.model import Project,DesignObject
from morale.engine import generate
from morale.auto_digitize import outline_path,area,difference_area

@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])

def cutout():return DesignObject(kind='compound',width=20,height=20,contours=[[[-.5,-.5],[.5,-.5],[.5,.5],[-.5,.5]],[[-.2,-.2],[.2,-.2],[.2,.2],[-.2,.2]]])

@pytest.mark.parametrize('source',[DesignObject(kind='ellipse',width=20,height=30),DesignObject(kind='rectangle',width=20,height=30),cutout()])
def test_satin_borders_preserve_band_coverage_and_two_stops(source):
    before=Project(objects=[source]).dumps()
    baseline=applique_stages(source,2,'fill');stages=applique_stages(source,2,'auto')
    assert all(o.stitch_type=='satin' for o in stages[2:])
    expected=outline_path(baseline[-1].rings());actual=outline_path([ring for o in stages[2:] for ring in o.rings()])
    assert difference_area(expected,actual)<=max(.02,area(expected)*.01)
    assert sum(s.command=='stop' for b in generate(Project(objects=stages)) for s in b.stitches)==2
    assert Project(objects=[source]).dumps()==before
    assert Project.loads(Project(objects=stages).dumps()).objects==stages

def test_cutout_produces_distinct_cover_objects():
    stages=applique_stages(cutout(),2,'auto')
    assert len(stages)==4 and len({o.id for o in stages})==4
    assert all('Satin cover' in o.name for o in stages[2:])
    assert all(not o.stop_after and o.trim_after for o in stages[2:])

def test_unsuitable_band_keeps_named_tatami_fallback():
    stages=applique_stages(DesignObject(width=1,height=1),6,'auto')
    assert stages[-1].stitch_type=='fill'
    assert 'Tatami' in stages[-1].name and 'fallback' in stages[-1].stage_note

def test_hidden_and_thread_metadata_preserved():
    source=DesignObject(visible=False,thread={'brand':'Example','catalog_number':'123'})
    stages=applique_stages(source,2,'auto')
    assert not generate(Project(objects=stages))
    assert all(o.thread==source.thread for o in stages)

@pytest.mark.parametrize('mode',[None,[],True,'satin'])
def test_invalid_mode_rejected(mode):
    with pytest.raises(ValueError):applique_stages(DesignObject(),2,mode)

@pytest.mark.parametrize('extension',['dst','exp','jef','pec','pes','tbf','u01','vp3','xxx'])
def test_satin_applique_export_preserves_pauses(tmp_path,extension):
    from morale.formats import export_machine,import_machine
    project=Project(objects=applique_stages(cutout(),2,'auto'))
    path=tmp_path/f'applique.{extension}';export_machine(project,path)
    blocks=generate(import_machine(path).project)
    assert len(blocks)-1+sum(s.command=='stop' for b in blocks for s in b.stitches)==2
    assert any(s.command=='stitch' for b in blocks for s in b.stitches)

def test_native_auto_cover_and_undo():
    from morale.app import MainWindow
    window=MainWindow();dialog=AppliqueDialog(window)
    try:
        assert dialog.cover_mode.currentData()=='auto'
        source=cutout();window.replace_project(Project(objects=[source]));window.select(source.id)
        before=window.project.dumps();window.apply_applique(2,'auto')
        assert len(window.project.objects)==4 and window.project.objects[-1].stitch_type=='satin'
        window.undo();assert window.project.dumps()==before
    finally:dialog.close();window.saved=window.project.dumps();window.close()

def test_multiple_cover_object_limit_rejected_atomically():
    from morale.app import MainWindow
    window=MainWindow()
    try:
        source=cutout();window.replace_project(Project(objects=[source,*[DesignObject(visible=False) for _ in range(497)]]));window.select(source.id)
        before=window.project.dumps()
        with pytest.raises(ValueError,match='500-object'):window.apply_applique(2,'auto')
        assert window.project.dumps()==before
    finally:window.saved=window.project.dumps();window.close()
