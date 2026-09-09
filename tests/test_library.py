import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
import sys
import time

import pytest
from PySide6.QtCore import QProcess
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QDialog

from morale.library import PreviewRunner,LibraryDialog
from morale.model import Project,DesignObject
from morale.formats import export_machine


@pytest.fixture(scope='module',autouse=True)
def app():
    return QApplication.instance() or QApplication([])


def wait_for(predicate,timeout=8000):
    deadline=time.monotonic()+timeout/1000
    while not predicate() and time.monotonic()<deadline:
        QTest.qWait(10)
    assert predicate()


def project_file(tmp_path,name='sample.morale'):
    path=tmp_path/name
    Project(name='Preview example',objects=[DesignObject(kind='rectangle',width=10,height=10)]).save(path)
    return path


def test_real_project_worker_is_read_only_and_cleans_temporary_output(tmp_path):
    path=project_file(tmp_path)
    before=path.read_bytes()
    runner=PreviewRunner()
    results=[]
    errors=[]
    runner.ready.connect(lambda *args:results.append(args))
    runner.failed.connect(lambda *args:errors.append(args))
    try:
        runner.load(path)
        temporary=Path(runner.directory.name)
        wait_for(lambda:results or errors)
        assert not errors
        filename,info,image=results[0]
        assert filename==str(path.resolve()) and info['stitches']>0
        assert info['name']=='Preview example' and image.width()==360
        assert not temporary.exists() and runner.directory is None
        assert path.read_bytes()==before
    finally:
        runner.cancel()


@pytest.mark.parametrize('extension',['dst','exp','jef','pec','pes','tbf','u01','vp3','xxx'])
def test_real_machine_file_previews(tmp_path,extension):
    path=tmp_path/f'sample.{extension}'
    export_machine(Project(objects=[DesignObject()]),path)
    runner=PreviewRunner()
    results=[]
    errors=[]
    runner.ready.connect(lambda *args:results.append(args))
    runner.failed.connect(lambda *args:errors.append(args))
    try:
        runner.load(path)
        wait_for(lambda:results or errors)
        assert not errors and results[0][1]['stitches']>0
        assert results[0][1]['notes']
    finally:
        runner.cancel()


def test_corrupt_file_reports_failure_without_leaking_process(tmp_path):
    path=tmp_path/'broken.morale'
    path.write_text('not a project')
    runner=PreviewRunner()
    errors=[]
    runner.failed.connect(lambda *args:errors.append(args))
    try:
        runner.load(path)
        wait_for(lambda:errors)
        assert errors[0][0]==str(path.resolve())
        assert runner.process.state()==QProcess.ProcessState.NotRunning and runner.directory is None
    finally:
        runner.cancel()


def test_stalled_preview_times_out(tmp_path,monkeypatch):
    runner=PreviewRunner(timeout_ms=100)
    errors=[]
    runner.failed.connect(lambda *args:errors.append(args))
    monkeypatch.setattr(runner,'command',lambda *args:(sys.executable,['-c','import time; time.sleep(30)']))
    try:
        runner.load(project_file(tmp_path))
        wait_for(lambda:errors)
        assert 'timed out' in errors[0][1]
        assert runner.process.state()==QProcess.ProcessState.NotRunning
        assert runner.directory is None
    finally:
        runner.cancel()


def test_new_selection_cancels_old_worker_and_only_delivers_latest(tmp_path,monkeypatch):
    runner=PreviewRunner()
    command=runner.command
    first,second=project_file(tmp_path,'first.morale'),project_file(tmp_path,'second.morale')
    monkeypatch.setattr(runner,'command',lambda path,directory:(sys.executable,['-c','import time; time.sleep(30)']) if path==str(first) else command(path,directory))
    results=[]
    errors=[]
    runner.ready.connect(lambda *args:results.append(args))
    runner.failed.connect(lambda *args:errors.append(args))
    try:
        runner.load(first)
        assert runner.process.waitForStarted(2000)
        old=Path(runner.directory.name)
        runner.load(second)
        wait_for(lambda:results or errors)
        assert not errors and [r[0] for r in results]==[str(second)]
        assert not old.exists()
    finally:
        runner.cancel()


def test_browser_filters_searches_previews_and_rejects_changed_file(tmp_path):
    path=project_file(tmp_path,'Flower.MORALE')
    (tmp_path/'notes.txt').write_text('not embroidery')
    dialog=LibraryDialog(folder=tmp_path)
    try:
        dialog.show()
        wait_for(lambda:dialog.model.index(str(path)).isValid())
        source=dialog.model.index(str(path))
        wait_for(lambda:dialog.proxy.mapFromSource(source).isValid())
        dialog.search.setText('flower')
        assert dialog.proxy.mapFromSource(source).isValid()
        dialog.search.setText('no-match')
        assert not dialog.proxy.mapFromSource(source).isValid()
        dialog.search.clear()
        index=dialog.proxy.mapFromSource(source)
        dialog.tree.setCurrentIndex(index)
        wait_for(lambda:dialog.open_button.isEnabled())
        assert dialog.preview_path==str(path)
        path.write_text(path.read_text()+'\n')
        dialog.open_selected()
        assert not dialog.open_button.isEnabled()
        assert 'changed' in dialog.details.text()
    finally:
        dialog.close()


def test_closing_browser_terminates_running_preview(tmp_path,monkeypatch):
    dialog=LibraryDialog(folder=tmp_path)
    monkeypatch.setattr(dialog.runner,'command',lambda *args:(sys.executable,['-c','import time; time.sleep(30)']))
    dialog.runner.load(project_file(tmp_path))
    assert dialog.runner.process.waitForStarted(2000)
    dialog.close()
    assert dialog.runner.process.state()==QProcess.ProcessState.NotRunning
    assert dialog.runner.directory is None


def test_native_browser_open_respects_unsaved_guard(tmp_path,monkeypatch):
    import morale.app as module
    window=module.MainWindow()
    path=project_file(tmp_path)
    before=window.project.dumps()
    def accept(dialog):
        dialog.selected_path=str(path)
        return QDialog.DialogCode.Accepted
    monkeypatch.setattr(LibraryDialog,'exec',accept)
    try:
        monkeypatch.setattr(window,'confirm_discard',lambda:False)
        window.browse_designs()
        assert window.project.dumps()==before
        monkeypatch.setattr(window,'confirm_discard',lambda:True)
        window.browse_designs()
        assert window.project.name=='Preview example' and window.file_path==path
    finally:
        window.saved=window.project.dumps()
        window.close()
