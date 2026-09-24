import math
from copy import deepcopy
import pytest
from PySide6.QtWidgets import QApplication
from morale.stitch_edit import StitchTableModel,StitchDialog,split_sewn_splices,manual_object
from morale.model import DesignObject,Project
from morale.engine import generate


@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])


def rows():return [[0,0,'jump'],[9,12,'stitch'],[9,12,'trim'],[30,40,'jump'],[30,40,'stop'],[30,50,'stitch']]


def spans(commands):
    previous=(0,0);result=[]
    for x,y,command in commands:
        if command=='stitch':result.append((previous,(x,y)))
        if command in {'stitch','jump'}:previous=(x,y)
    return result


def test_split_preserves_paths_endpoints_and_controls_with_atomic_history():
    source=rows();before=deepcopy(source);model=StitchTableModel(source)
    assert model.split_long_stitches(6)==3 and source==before
    assert max(math.dist(a,b) for a,b in spans(model.rows))<=6
    assert sum(math.dist(a,b) for a,b in spans(model.rows))==pytest.approx(25)
    assert [r for r in model.rows if r[2]!='stitch']==[r for r in source if r[2]!='stitch']
    assert [9,12,'stitch'] in model.rows and model.rows[-1]==source[-1]
    assert len(model.history)==1
    after=deepcopy(model.rows);model.undo();assert model.rows==source
    model.redo();assert model.rows==after


def test_selection_scope_and_noop_keep_unselected_spans():
    model=StitchTableModel(rows());assert model.split_long_stitches(6,{1})==2
    assert max(math.dist(a,b) for a,b in spans(model.rows))==10
    history=len(model.history);assert model.split_long_stitches(6,[])==0 and len(model.history)==history


@pytest.mark.parametrize('maximum',[True,0,20,float('nan'),float('inf')])
def test_invalid_length_does_not_change_rows_or_history(maximum):
    model=StitchTableModel(rows());before=deepcopy(model.rows)
    with pytest.raises(ValueError):model.split_long_stitches(maximum)
    assert model.rows==before and not model.history


def test_capacity_rejection_is_atomic():
    source=[[0,0,'jump']]+[[1000 if i%2 else -1000,0,'stitch'] for i in range(100)]
    model=StitchTableModel(source)
    with pytest.raises(ValueError,match='250,000'):model.split_long_stitches(.5)
    assert model.rows==source and not model.history


def test_native_scope_apply_save_reopen_and_main_undo():
    from morale.app import MainWindow
    obj=manual_object(DesignObject(),rows());window=MainWindow();window.replace_project(Project(objects=[obj]));window.select(obj.id)
    dialog=StitchDialog(obj,rows(),window)
    try:
        before=window.project.dumps();dialog.split_maximum.setValue(4)
        dialog.split_scope.setCurrentIndex(1);dialog.table.selectRow(1);dialog.split_long_stitches()
        assert max(math.dist(a,b) for a,b in spans(dialog.model.rows))==10
        dialog.undo();dialog.split_scope.setCurrentIndex(0);dialog.split_long_stitches()
        assert dialog.model.rowCount()>len(rows())
        dialog.undo();assert dialog.model.rows==rows()
        dialog.redo();dialog.accept();assert dialog.candidate is not None
        window.replace_stitches(dialog.model.rows)
        reopened=Project.loads(window.project.dumps());blocks=generate(reopened)
        commands=[[s.x,s.y,s.command] for b in blocks for s in b.stitches]
        assert max(math.dist(a,b) for a,b in spans(commands))<=4+1e-9
        assert sum(r[2]=='trim' for r in commands)==1 and sum(r[2]=='stop' for r in commands)==1
        window.undo();assert window.project.dumps()==before
    finally:dialog.close();window.saved=window.project.dumps();window.close()


@pytest.mark.parametrize('bad',[[],[[]],[[0,0,'stitch']],[[0,0,'jump'],None]])
def test_invalid_rows_rejected(bad):
    with pytest.raises(ValueError):split_sewn_splices(bad,6)


@pytest.mark.parametrize('extension',['dst','exp','jef','pec','pes','tbf','u01','vp3','xxx'])
def test_split_continuous_run_exports_with_bounded_sewn_spans(tmp_path,extension):
    from morale.formats import export_machine,import_machine
    model=StitchTableModel([[-10,0,'jump'],[10,0,'stitch']]);model.split_long_stitches(6)
    project=Project(objects=[manual_object(DesignObject(),model.rows)])
    path=tmp_path/f'split.{extension}';export_machine(project,path)
    decoded=[[s.x,s.y,s.command] for b in generate(import_machine(path).project) for s in b.stitches]
    sewn=spans(decoded)
    assert sewn and max(math.dist(a,b) for a,b in sewn)<=5.15
    assert sum(math.dist(a,b) for a,b in sewn)==pytest.approx(20,abs=.2)
    assert sewn[-1][1]==pytest.approx((10,0),abs=.1)
