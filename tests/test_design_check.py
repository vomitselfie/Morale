import pytest
from PySide6.QtWidgets import QApplication, QDialog
from morale.coupons import satin, manual_line, rectangle, ellipse
from morale.design_check import check_design, DesignIssue
from morale.engine import generate, preflight
from morale.model import Project, DesignObject, demo_project


@pytest.fixture(scope='module', autouse=True)
def app():
    return QApplication.instance() or QApplication([])


def codes(project):
    return {issue.code for issue in check_design(project, generate(project))}


def test_clean_design_reports_only_passed_checks():
    project = Project(objects=[rectangle(0, 0, 20, 20, 'Square')])
    issues = check_design(project, generate(project))
    assert {i.severity for i in issues} == {'info'} and {'FITS_HOOP', 'COMMAND_COUNT'} <= {i.code for i in issues}


def test_each_check_finds_its_problem_and_points_at_it():
    narrow = satin([(0, -20), (0, 0)], .5, 'Hairline')
    tiny = rectangle(20, 20, 1.5, 1.5, 'Speck')
    long_stitches = manual_line((-30, 30), (0, 30), 9, 'Long run')
    outside = rectangle(49, 0, 10, 10, 'Edge')
    project = Project(objects=[narrow, tiny, long_stitches, outside])
    issues = check_design(project, generate(project))
    by_code = {i.code: i for i in issues}
    assert {'SATIN_TOO_NARROW', 'FILL_TOO_SMALL', 'LONG_STITCH', 'OUTSIDE_HOOP'} <= set(by_code)
    assert by_code['SATIN_TOO_NARROW'].object_id == narrow.id and by_code['FILL_TOO_SMALL'].object_id == tiny.id
    assert by_code['OUTSIDE_HOOP'].object_id == outside.id and by_code['OUTSIDE_HOOP'].position is not None
    assert issues[0].severity == 'error'  # Errors come first.
    assert 'provisional' in by_code['SATIN_TOO_NARROW'].message


def test_long_jumps_are_flagged_unless_trimmed():
    first, second = ellipse(-30, 0, 3, 'Here'), ellipse(20, 0, 3, 'There')
    assert 'LONG_JUMP' in codes(Project(objects=[first, second]))
    first.trim_after = True
    assert 'LONG_JUMP' not in codes(Project(objects=[first, second]))


def test_stacked_layers_are_flagged_with_a_position():
    stack = [rectangle(0, 0, 10, 10, f'Layer {n}', angle=a) for n, a in enumerate([0, 45, 90, -45])]
    project = Project(objects=stack)
    issue = next(i for i in check_design(project, generate(project)) if i.code == 'HIGH_LAYER_COVERAGE')
    assert issue.position and abs(issue.position[0]) < 6 and abs(issue.position[1]) < 6


def test_checks_never_modify_the_design_and_preflight_keeps_blocking_errors():
    project = demo_project()
    before = project.dumps()
    check_design(project, generate(project))
    assert project.dumps() == before
    assert preflight(project, generate(project)) == []
    project.objects.append(rectangle(60, 0, 10, 10, 'Outside'))
    assert any('beyond' in message for message in preflight(project, generate(project)))
    assert preflight(Project(), []) == ['The design has no stitches to export.']


def test_dialog_lists_issues_and_selecting_one_shows_its_object(monkeypatch):
    from morale.app import MainWindow
    shown = []
    monkeypatch.setattr(QDialog, 'exec', lambda self: shown.append(self) or 0)
    window = MainWindow()
    try:
        narrow = satin([(0, -20), (0, 0)], .5, 'Hairline')
        window.commit(lambda: window.project.objects.append(narrow))
        window.check_design()
        dialog = shown[0]
        texts = [dialog.list.item(i).text() for i in range(dialog.list.count())]
        row = next(i for i, text in enumerate(texts) if 'Hairline' in text)
        assert texts[row].startswith('⚠')
        dialog.list.setCurrentRow(row)
        assert window.selected_id == narrow.id
    finally:
        window.saved = window.project.dumps(); window.close()
