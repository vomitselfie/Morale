import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import time
import sys
from copy import deepcopy
from pathlib import Path
import pytest
from PySide6.QtCore import Qt,QTimer,QProcess
from PySide6.QtWidgets import QApplication,QFileDialog
from PySide6.QtTest import QTest
from morale.generation import GenerationRunner,decode_blocks
from morale.model import Project,DesignObject
from morale.engine import generate
from morale.app import MainWindow


@pytest.fixture(scope='module',autouse=True)
def app(): return QApplication.instance() or QApplication([])


def wait_for(predicate,seconds=10):
    deadline=time.monotonic()+seconds
    while not predicate() and time.monotonic()<deadline: QTest.qWait(10)
    assert predicate()


def test_real_worker_retains_all_blocks_commands_and_thread_metadata():
    runner=GenerationRunner(); results=[]; errors=[]
    runner.ready.connect(lambda revision,blocks:results.append((revision,blocks)))
    runner.failed.connect(lambda revision,error:errors.append(error))
    obj=DesignObject(kind='rectangle',density_gradient=True,thread={'brand':'Test','catalog_number':'001'},stop_after=True,tie_in=True)
    project=Project(objects=[obj,DesignObject(visible=False)])
    try:
        runner.request(project,12)
        directory=Path(runner.directory.name)
        wait_for(lambda:results or errors)
        assert not errors
        assert results==[(12,generate(project))]
        assert not directory.exists()
    finally: runner.cancel()


def test_worker_replacement_and_timeout(monkeypatch):
    runner=GenerationRunner(timeout_ms=100); results=[]; errors=[]
    runner.ready.connect(lambda revision,blocks:results.append(revision))
    runner.failed.connect(lambda revision,error:errors.append((revision,error)))
    real_command=runner.command
    monkeypatch.setattr(runner,'command',lambda *args:(sys.executable,['-c','import time; time.sleep(30)']))
    try:
        runner.request(Project(),1)
        assert runner.process.waitForStarted(2000)
        old=Path(runner.directory.name)
        monkeypatch.setattr(runner,'command',real_command)
        runner.timer.setInterval(5000)
        runner.request(Project(objects=[DesignObject()]),2)
        wait_for(lambda:results or errors)
        assert results==[2] and not errors and not old.exists()
        monkeypatch.setattr(runner,'command',lambda *args:(sys.executable,['-c','import time; time.sleep(30)']))
        runner.timer.setInterval(80)
        runner.request(Project(),3)
        wait_for(lambda:errors)
        assert errors[0][0]==3 and 'timed out' in errors[0][1]
        assert runner.process.state()==QProcess.ProcessState.NotRunning and runner.directory is None
    finally: runner.cancel()


def payload():
    return [{'object_id':'id','color':'#123456','color_break':False,'thread':{},'stitches':[[0,0,'jump'],[1,2,'stitch']]}]


@pytest.mark.parametrize('mutation',[lambda d:d.clear(),lambda d:d[0].update(object_id='wrong'),lambda d:d[0]['stitches'].append([0,float('nan'),'stitch']),lambda d:d[0]['stitches'].append([True,0,'jump']),lambda d:d[0]['stitches'].append([0,0,'unknown']),lambda d:d[0].update(stitches=[[0,0,'stitch']]*250001)])
def test_invalid_worker_output_rejected(mutation):
    data=payload(); expected=[{k:v for k,v in data[0].items() if k!='stitches'}]
    mutation(data)
    with pytest.raises(ValueError): decode_blocks(data,expected)


def test_background_window_latest_edit_wins_and_exports_wait(monkeypatch):
    window=MainWindow(background_generation=True)
    called=[]
    monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *args,**kwargs:called.append(True))
    try:
        obj=DesignObject(kind='rectangle')
        window.replace_project(Project(objects=[obj])); window.select(obj.id)
        assert window.generation_pending and not window.blocks
        window.export(); window.thread_chart(); window.play()
        assert not called and not window.timer.isActive()
        old_revision=window.preview_revision
        window.update_property('spacing',.7); window.update_property('spacing',1.1)
        window.calculation_ready(old_revision,generate(Project(objects=[obj])))
        assert window.generation_pending and not window.blocks
        wait_for(lambda:not window.generation_pending)
        assert not window.generation_error
        assert window.blocks==generate(window.project)
        assert window.project.objects[0].spacing==1.1
        assert window.play_button.isEnabled()
        window.undo()
        wait_for(lambda:not window.generation_pending)
        assert window.blocks==generate(window.project)
    finally:
        window.saved=window.project.dumps(); window.close()


def test_calculation_can_be_cancelled_and_retried_without_losing_design(monkeypatch):
    window=MainWindow(background_generation=True)
    runner=window.generation_runner; real=runner.command
    monkeypatch.setattr(runner,'command',lambda *args:(sys.executable,['-c','import time; time.sleep(30)']))
    try:
        window.start_calculation()
        assert runner.process.waitForStarted(2000)
        before=window.project.dumps()
        window.toggle_calculation()
        assert not window.generation_pending and 'cancelled' in window.generation_error
        assert window.project.dumps()==before and not window.blocks
        assert runner.process.state()==QProcess.ProcessState.NotRunning
        monkeypatch.setattr(runner,'command',real)
        window.toggle_calculation()
        wait_for(lambda:not window.generation_pending)
        assert not window.generation_error and window.blocks==generate(window.project)
    finally:
        window.saved=window.project.dumps(); window.close()


def test_background_result_does_not_replace_uncommitted_text():
    window=MainWindow(background_generation=True)
    try:
        window.show(); window.activateWindow(); QApplication.processEvents(); window.select(window.project.objects[0].id)
        name=window.fields['name']
        name.setFocus(); name.selectAll(); QTest.keyClicks(name,'Uncommitted name text')
        # An arriving result updates counts and paths, not editable text fields.
        wait_for(lambda:not window.generation_pending)
        assert name.text()=='Uncommitted name text'
        assert window.project.objects[0].name!='Uncommitted name text'
        name.clearFocus()
    finally:
        window.saved=window.project.dumps(); window.close()


def test_main_window_remains_responsive_during_worker_and_close_cancels(monkeypatch):
    window=MainWindow(background_generation=True)
    runner=window.generation_runner
    monkeypatch.setattr(runner,'command',lambda *args:(sys.executable,['-c','import time; time.sleep(30)']))
    ticks=[]; timer=QTimer(); timer.setInterval(10); timer.timeout.connect(lambda:ticks.append(True))
    try:
        window.start_calculation(); assert runner.process.waitForStarted(2000)
        directory=Path(runner.directory.name)
        timer.start(); QTest.qWait(80)
        assert len(ticks)>=3
        window.saved=window.project.dumps(); window.close()
        assert runner.process.state()==QProcess.ProcessState.NotRunning and not directory.exists()
    finally:
        timer.stop(); runner.cancel()


def test_generation_error_can_be_corrected_in_same_window():
    window=MainWindow(background_generation=True)
    obj=DesignObject(kind='satin',stitch_type='satin',points=[[-.5,-.5],[.5,.5],[-.5,.5],[.5,-.5]])
    try:
        window.replace_project(Project(objects=[obj])); window.select(obj.id)
        wait_for(lambda:not window.generation_pending)
        assert window.generation_error and not window.blocks
        old_revision=window.preview_revision
        window.replace_points([(-10,-15),(10,-15),(-10,15),(10,15)])
        window.calculation_failed(old_revision,'obsolete failure')
        assert window.generation_pending and not window.generation_error
        wait_for(lambda:not window.generation_pending)
        assert not window.generation_error and window.blocks==generate(window.project)
    finally:
        window.saved=window.project.dumps(); window.close()


def test_undo_reuses_matching_cached_preview_and_cancels_obsolete_request():
    window=MainWindow(background_generation=True)
    try:
        window.select(window.project.objects[0].id)
        wait_for(lambda:not window.generation_pending)
        before=window.project.dumps(); blocks=window.blocks
        window.update_property('spacing',1.2)
        assert window.generation_pending and not window.blocks
        window.undo()
        assert window.project.dumps()==before
        assert not window.generation_pending and window.blocks==blocks
        assert not window.preview_debounce.isActive()
    finally:
        window.saved=window.project.dumps(); window.close()


def test_close_commits_pending_text_before_discard_prompt_and_stops_jobs(monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    window=MainWindow(background_generation=True)
    seen=[]
    monkeypatch.setattr(QMessageBox,'question',lambda *args,**kwargs:seen.append(window.project.objects[0].name) or QMessageBox.StandardButton.Discard)
    try:
        window.show(); window.activateWindow(); QApplication.processEvents(); window.select(window.project.objects[0].id)
        name=window.fields['name']; name.setFocus(); name.selectAll(); QTest.keyClicks(name,'Pending close edit')
        window.close(); QTest.qWait(120)
        assert seen==['Pending close edit']
        assert window.generation_runner.process.state()==QProcess.ProcessState.NotRunning
        assert not window.preview_debounce.isActive()
    finally: window.generation_runner.cancel()


def test_property_preview_never_uses_main_thread_generator(monkeypatch):
    import morale.app as app_module
    def forbidden(*args,**kwargs): raise AssertionError('Preview generation ran on the GUI thread')
    monkeypatch.setattr(app_module,'generate',forbidden)
    window=MainWindow(background_generation=True)
    try:
        window.select(window.project.objects[0].id)
        wait_for(lambda:not window.generation_pending)
        assert not window.generation_error
        window.update_property('spacing',.8)
        wait_for(lambda:not window.generation_pending)
        assert not window.generation_error and window.blocks==generate(window.project)
    finally:
        window.saved=window.project.dumps(); window.close()
