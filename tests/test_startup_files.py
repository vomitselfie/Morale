from PySide6.QtCore import QEvent
from PySide6.QtGui import QFileOpenEvent
from PySide6.QtWidgets import QApplication
from morale.app import MainWindow,FileOpenFilter,startup_file
from morale.model import Project,DesignObject


def test_startup_file_ignores_flags_and_missing_paths(tmp_path):
    design=tmp_path/'rose.morale';design.write_text(Project().dumps())
    assert startup_file(['Morale'])is None
    assert startup_file(['Morale','--self-test',str(tmp_path/'missing.morale')])is None
    assert startup_file(['Morale','-psn_0_12345',str(design)])==str(design)


def test_file_open_event_opens_the_design(tmp_path,monkeypatch):
    app=QApplication.instance() or QApplication([])
    design=tmp_path/'rose.morale'
    design.write_text(Project(name='Rose',objects=[DesignObject(name='Petal')]).dumps())
    window=MainWindow()
    try:
        opener=FileOpenFilter(window)
        window.saved=window.project.dumps()
        event=QFileOpenEvent(str(design))
        assert event.type()==QEvent.Type.FileOpen and opener.eventFilter(app,event)
        assert window.project.name=='Rose' and window.file_path==design
        # Unsaved work is protected by the usual prompt.
        monkeypatch.setattr(window,'confirm_discard',lambda:False)
        other=tmp_path/'other.morale';other.write_text(Project(name='Other').dumps())
        assert opener.eventFilter(app,QFileOpenEvent(str(other))) and window.project.name=='Rose'
    finally:
        window.saved=window.project.dumps();window.close()
