import pytest
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox
from morale.engine import generate
from morale.export_verify import verify_export, verification_text
from morale.formats import export_machine
from morale.model import demo_project


@pytest.fixture(scope='module', autouse=True)
def app():
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize('extension', ['pes', 'dst', 'exp', 'jef', 'xxx'])
def test_reliable_formats_verify(tmp_path, extension):
    project = demo_project(); blocks = generate(project)
    path = tmp_path / f'design.{extension}'
    export_machine(project, path, blocks)
    result = verify_export(blocks, path)
    assert result['verified'] and result['problems'] == [] and result['decoded_stitches'] >= result['source_stitches']
    assert verification_text(result, path.name).startswith('Export verified')


def test_known_vp3_problem_stays_visible(tmp_path):
    # VP3 loses internal jump positions (docs/VP3_INVESTIGATION.md); verification must show it.
    project = demo_project(); blocks = generate(project)
    path = tmp_path / 'design.vp3'
    export_machine(project, path, blocks)
    result = verify_export(blocks, path)
    assert not result['verified'] and any('not in the design' in p or 'missing' in p for p in result['problems'])
    assert verification_text(result, path.name).startswith('Export check found differences')


def test_a_damaged_file_is_flagged(tmp_path, monkeypatch):
    project = demo_project(); blocks = generate(project)
    path = tmp_path / 'design.dst'
    export_machine(project, path, blocks)
    import morale.export_verify as module
    original = module.import_machine
    def shifted(p):
        result = original(p)
        for obj in result.project.objects:
            obj.x += 2
        return result
    monkeypatch.setattr(module, 'import_machine', shifted)
    result = verify_export(blocks, path)
    assert not result['verified'] and any('edge moved' in p for p in result['problems'])


@pytest.mark.parametrize('extension,title', [('pes', 'Stitches exported'), ('vp3', 'Check the exported file')])
def test_window_export_reports_verification(tmp_path, monkeypatch, extension, title):
    from morale.app import MainWindow
    shown = []
    monkeypatch.setattr(QMessageBox, 'information', lambda *a: shown.append(('info', a[1], a[2])))
    monkeypatch.setattr(QMessageBox, 'warning', lambda *a: shown.append(('warning', a[1], a[2])))
    label = {'pes': 'PES', 'vp3': 'VP3'}[extension]
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *a: (str(tmp_path / f'design.{extension}'), f'{label} (*.{extension})'))
    window = MainWindow()
    try:
        window.export()
        assert shown and shown[-1][1] == title
        assert ('Export verified' if extension == 'pes' else 'Export check found differences') in shown[-1][2]
    finally:
        window.saved = window.project.dumps(); window.close()
