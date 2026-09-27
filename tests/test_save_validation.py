from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication
from morale.model import Project, DesignObject, demo_project, satin_sample
from morale.lettering import make_lettering

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module', autouse=True)
def app():
    return QApplication.instance() or QApplication([])


def test_save_refuses_a_project_the_loader_would_reject(tmp_path):
    path = tmp_path / 'design.morale'
    good = demo_project()
    good.save(path)
    before = path.read_bytes()
    bad = demo_project()
    bad.objects[0].stitch_type = 'no-such-stitch'
    with pytest.raises(ValueError):
        bad.save(path)
    # The previous file is untouched and no temporary file is left behind.
    assert path.read_bytes() == before and [p.name for p in tmp_path.iterdir()] == ['design.morale']
    with pytest.raises(ValueError):
        bad.save(tmp_path / 'new.morale')
    assert not (tmp_path / 'new.morale').exists()


BUILT_IN = ['demo', 'satin sample', 'satin lettering', 'rectangle']
EXAMPLES = sorted(str(p.relative_to(ROOT)) for p in (ROOT / 'examples').rglob('*.morale'))


def build(name):
    # Built inside the test: Qt font lookups need the application, which does not
    # exist yet when pytest collects parameters.
    from PySide6.QtGui import QFont
    if name == 'demo':
        return demo_project()
    if name == 'satin sample':
        return satin_sample()
    if name == 'satin lettering':
        return Project(objects=[make_lettering('Morale', QFont().family(), 15, stitch_type='satin')])
    if name == 'rectangle':
        return Project(objects=[DesignObject(kind='rectangle')])
    return Project.loads((ROOT / name).read_text(encoding='utf-8'))


@pytest.mark.parametrize('name', BUILT_IN + EXAMPLES)
def test_everything_saved_reopens_with_the_same_content(tmp_path, name):
    project = build(name)
    path = tmp_path / 'saved.morale'
    project.save(path)
    reopened = Project.loads(path.read_text(encoding='utf-8'))
    assert [o.id for o in reopened.objects] == [o.id for o in project.objects]
    assert reopened.dumps() == project.dumps()
