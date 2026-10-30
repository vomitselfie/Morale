import json
import pytest
from PySide6.QtWidgets import QApplication,QInputDialog
from morale.model import Project,DesignObject
from morale.engine import generate
from morale.project_notes import edit_notes

@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])


def test_notes_roundtrip_old_files_and_stitch_independence(tmp_path):
    project=Project(objects=[DesignObject()],notes='Fabric: linen\nStabilizer: α\n')
    blocks=generate(project);path=tmp_path/'notes.morale';project.save(path)
    assert Project.loads(path.read_text()).notes==project.notes
    data=json.loads(project.dumps());del data['notes'];old=Project.loads(json.dumps(data))
    assert old.notes=='' and generate(old)==blocks


@pytest.mark.parametrize('notes',[None,1,[],{},'x'*10001])
def test_invalid_notes_rejected(notes):
    data=json.loads(Project().dumps());data['notes']=notes
    with pytest.raises(ValueError,match='Design notes'):Project.loads(json.dumps(data))


def test_native_note_edit_undo_redo_cancel_and_limit(monkeypatch):
    from morale.app import MainWindow
    window=MainWindow();errors=[];window.error=errors.append
    try:
        before=window.project.dumps()
        monkeypatch.setattr(QInputDialog,'getMultiLineText',lambda *a:('Use woven stabilizer\nTest at low speed',True))
        edit_notes(window);after=window.project.dumps();assert after!=before
        window.undo();assert window.project.dumps()==before
        window.redo();assert window.project.dumps()==after
        for text,accepted in [('discard',False),('x'*10001,True)]:
            monkeypatch.setattr(QInputDialog,'getMultiLineText',lambda *a:(text,accepted))
            edit_notes(window);assert window.project.dumps()==after
        assert len(errors)==1
    finally:window.saved=window.project.dumps();window.close()


def test_sewout_pdf_preserves_multiline_notes_as_literal_text(tmp_path):
    # QtPdf can fail to load when a system Qt newer than PySide6's is found first.
    QPdfDocument=pytest.importorskip('PySide6.QtPdf',exc_type=ImportError).QPdfDocument
    from morale.coupons import project_evaluation_pdf
    notes=['Fabric: linen & cotton','<b>Literal note, not markup</b>']+[f'Adjustment {i:03}: inspect support and stitch tension.' for i in range(100)]
    project=Project(objects=[DesignObject(kind='rectangle',width=10,height=10)],notes='\n'.join(notes))
    before=project.dumps();path=tmp_path/'worksheet.pdf';project_evaluation_pdf(project,path)
    document=QPdfDocument();assert document.load(str(path))==QPdfDocument.Error.None_
    assert document.pageCount()>1
    text='\n'.join(document.getAllText(i).text() for i in range(document.pageCount()))
    assert 'Design notes (saved with project)' in text
    for note in notes:assert note in text
    assert project.dumps()==before
    document.close()
