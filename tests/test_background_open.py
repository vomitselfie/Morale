import time
import pytest
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from morale.app import MainWindow
from morale.formats import export_machine
from morale.model import Project,DesignObject
from morale.open_worker import worker_main,read_open_result,decode


@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])


def design(tmp_path,name='rose.pes'):
    path=tmp_path/name
    export_machine(Project(objects=[DesignObject(name='Petal',kind='rectangle',width=20,height=12)]),path)
    return path


def wait(window,seconds=30):
    deadline=time.monotonic()+seconds
    while window.opening is not None and time.monotonic()<deadline:QTest.qWait(20)
    assert window.opening is None


def test_worker_decodes_machine_files_and_projects(tmp_path):
    source=design(tmp_path);output=tmp_path/'out';output.mkdir()
    assert worker_main([str(source),str(output)])==0
    project,notes=read_open_result(output,source)
    assert project.objects and notes
    morale=tmp_path/'plain.morale';morale.write_text(Project(name='Plain').dumps())
    assert decode(morale)[0].name=='Plain'


def test_result_is_rejected_if_the_file_changed_afterwards(tmp_path):
    source=design(tmp_path);output=tmp_path/'out';output.mkdir()
    assert worker_main([str(source),str(output)])==0
    source.write_bytes(source.read_bytes()+b'\0')
    with pytest.raises(ValueError,match='changed'):read_open_result(output,source)


def test_worker_reports_unreadable_files(tmp_path):
    bad=tmp_path/'bad.pes';bad.write_bytes(b'not a design');output=tmp_path/'out';output.mkdir()
    assert worker_main([str(bad),str(output)])==1 and (output/'preview.error.json').exists()


def test_window_opens_and_imports_in_the_background(tmp_path,monkeypatch):
    shown=[];monkeypatch.setattr('morale.app.QMessageBox.information',lambda *a:shown.append(a[1]))
    window=MainWindow(background_generation=True)
    try:
        window.saved=window.project.dumps()
        window.open_path(str(design(tmp_path)))
        assert window.opening is not None
        wait(window)
        assert [o.name for o in window.project.objects]!=[] and shown==['Design imported']
        count=len(window.project.objects)
        window.open_path(str(design(tmp_path,'leaf.pes')),merge=True)
        wait(window)
        assert len(window.project.objects)>count and shown==['Design imported']*2
        window.undo();assert len(window.project.objects)==count
    finally:
        window.saved=window.project.dumps();window.close()


def test_cancel_and_failure_leave_the_design_untouched(tmp_path,monkeypatch):
    errors=[];window=MainWindow(background_generation=True)
    monkeypatch.setattr(window,'error',errors.append)
    try:
        before=window.project.dumps()
        window.open_path(str(design(tmp_path)));window.cancel_opening()
        assert window.opening is None and window.open_progress is None
        QTest.qWait(300);assert window.project.dumps()==before
        bad=tmp_path/'bad.pes';bad.write_bytes(b'not a design')
        window.open_path(str(bad));wait(window)
        assert window.project.dumps()==before and errors and errors[0].startswith('Could not open this project.')
    finally:
        window.saved=window.project.dumps();window.close()
