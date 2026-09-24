import json
import pytest
from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
from morale.model import DesignObject,Project
from morale.stitch_edit import manual_object
from morale.formats import export_machine,export_summary
from morale.engine import generate


@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])


def project(length=30):
    return Project(objects=[manual_object(DesignObject(),[[-length/2,0,'jump'],[length/2,0,'stitch']])])


def test_report_counts_only_preparation_subdivision(tmp_path):
    source=project();before=source.dumps();result=export_machine(source,tmp_path/'long.dst')
    assert result=={'format':'.dst','source_stitches':1,'prepared_stitches':3,'subdivision_added_stitches':2,'maximum_prepared_span_mm':12}
    assert source.dumps()==before
    text=export_summary(result)
    assert 'Added 2 needle positions' in text and 'may add further' in text
    short=export_machine(project(5),tmp_path/'short.dst')
    assert short['source_stitches']==short['prepared_stitches']==1 and short['subdivision_added_stitches']==0


def test_native_export_displays_preparation_counts(tmp_path,monkeypatch):
    from morale.app import MainWindow
    window=MainWindow();window.replace_project(project());window.blocks=generate(window.project)
    before=window.project.dumps();messages=[];path=tmp_path/'long.dst'
    monkeypatch.setattr(window,'preview_available',lambda:True)
    monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *args:(str(path),'DST (*.dst)'))
    monkeypatch.setattr(QMessageBox,'information',lambda parent,title,text:messages.append(text))
    monkeypatch.setattr(window,'error',lambda message:pytest.fail(message))
    try:
        window.export()
        assert path.exists() and messages and 'Added 2 needle positions' in messages[0]
        assert '3 stitches prepared' in window.statusBar().currentMessage()
        assert window.project.dumps()==before
    finally:window.saved=window.project.dumps();window.close()


def test_batch_worker_retains_counts_in_its_report(tmp_path):
    from morale.batch import worker_main
    source=tmp_path/'source.pes';export_machine(project(),source)
    destination=tmp_path/'result.dst'
    assert worker_main([str(source),str(destination),'6'])==0
    result=json.loads((tmp_path/'result.dst.result.json').read_text())
    assert any('Added 2 needle positions' in note for note in result['notes'])
    assert any('3 prepared for DST' in note for note in result['notes'])
