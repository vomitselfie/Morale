import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import shutil
import subprocess

import pytest
from PySide6.QtCore import QPointF
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication, QDialog

from morale.model import Project, DesignObject
from morale.engine import generate
from morale.templates import template_plan, registration_marks, export_template, TemplateDialog


@pytest.fixture(scope="module", autouse=True)
def app():
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize("paper", ["A4","Letter"])
def test_large_hoop_tiles_cover_every_point_and_overlap_exactly(paper):
    project = Project(hoop_width=500,hoop_height=500)
    plan = template_plan(project,[],paper)
    tiles = [tile for c,r,tile in plan.tiles()]
    assert plan.columns == plan.rows == 3
    for x in range(-250,251,10):
        for y in range(-250,251,10):
            assert any(tile.contains(QPointF(x,y)) for tile in tiles)
    assert tiles[0].intersected(tiles[1]).width() == pytest.approx(10)
    assert tiles[0].intersected(tiles[plan.columns]).height() == pytest.approx(10)


def test_every_adjacent_tile_pair_has_two_shared_registration_marks():
    plan = template_plan(Project(hoop_width=500,hoop_height=500),[])
    marks = registration_marks(plan)
    tiles = {(c,r):tile for c,r,tile in plan.tiles()}
    for (c,r),tile in tiles.items():
        for neighbor in ((c+1,r),(c,r+1)):
            if neighbor in tiles:
                overlap = tile.intersected(tiles[neighbor])
                assert sum(overlap.contains(QPointF(x,y)) for x,y in marks) >= 2


def test_template_includes_compensated_stitches_outside_hoop_but_not_hidden_objects():
    obj = DesignObject(kind="rectangle",x=120,width=20,height=20,pull_compensation=1,angle=0)
    project = Project(objects=[obj,DesignObject(x=-900,visible=False)])
    blocks=generate(project)
    plan=template_plan(project,blocks)
    tiles=[t for c,r,t in plan.tiles()]
    assert plan.columns==2
    assert all(any(t.contains(QPointF(s.x,s.y)) for t in tiles) for b in blocks for s in b.stitches)


def test_failed_publication_preserves_existing_pdf_and_cleans_temporary(tmp_path,monkeypatch):
    import morale.templates as templates
    destination=tmp_path/'placement.pdf'
    destination.write_bytes(b'existing file')
    def fail(*args):
        raise OSError('publication failed')
    monkeypatch.setattr(templates.os,'replace',fail)
    with pytest.raises(OSError,match='publication'):
        export_template(Project(),destination)
    assert destination.read_bytes()==b'existing file'
    assert list(tmp_path.iterdir())==[destination]


@pytest.mark.parametrize("paper,pages", [("A4",1),("Letter",1)])
def test_pdf_export_keeps_project_and_produces_document(tmp_path,paper,pages):
    project=Project(objects=[DesignObject()])
    original=project.dumps()
    destination=tmp_path/'placement.pdf'
    plan=export_template(project,destination,paper)
    assert destination.read_bytes().startswith(b'%PDF-')
    assert plan.rows*plan.columns==pages
    assert project.dumps()==original


@pytest.mark.skipif(not shutil.which('pdftoppm') or not shutil.which('pdfinfo'),reason='Poppler PDF inspection tools unavailable')
def test_pdf_actual_physical_size_and_calibration_ruler(tmp_path):
    project=Project(objects=[DesignObject(kind='rectangle',width=20,height=10,color='#ff0000')])
    destination=tmp_path/'placement.pdf'
    export_template(project,destination,stitches=False)
    info=subprocess.check_output(['pdfinfo',str(destination)],text=True)
    assert '595 x 842 pts' in info
    subprocess.run(['pdftoppm','-r','254','-singlefile','-png',str(destination),str(tmp_path/'page')],check=True,capture_output=True)
    image=QImage(str(tmp_path/'page.png'))
    assert not image.isNull()
    # 254 dpi is exactly 10 pixels/mm: inspect actual rendered vector positions.
    red=[]
    for y in range(1350,1600):
        for x in range(900,1200):
            color=image.pixelColor(x,y)
            if color.red()>180 and color.green()<100 and color.blue()<100:
                red.append((x,y))
    assert red
    assert max(x for x,y in red)-min(x for x,y in red)==pytest.approx(200,abs=3)
    assert max(y for x,y in red)-min(y for x,y in red)==pytest.approx(100,abs=3)
    black=[x for y in range(2788,2793) for x in range(100,700) if image.pixelColor(x,y).lightness()<80]
    assert max(black)-min(black)==pytest.approx(500,abs=3)


@pytest.mark.skipif(not shutil.which('pdfinfo'),reason='Poppler PDF inspection tools unavailable')
def test_tiled_pdf_page_count_and_letter_dimensions(tmp_path):
    destination=tmp_path/'large.pdf'
    plan=export_template(Project(hoop_width=500,hoop_height=500),destination,'Letter')
    info=subprocess.check_output(['pdfinfo',str(destination)],text=True)
    assert '612 x 792 pts' in info
    line=next(line for line in info.splitlines() if line.startswith('Pages:'))
    assert int(line.split(':')[1])==plan.rows*plan.columns==9


def test_native_export_and_cancel_preserve_design(tmp_path,monkeypatch):
    import morale.app as module
    window=module.MainWindow()
    try:
        before=window.project.dumps()
        monkeypatch.setattr(TemplateDialog,'exec',lambda self: QDialog.DialogCode.Rejected)
        window.placement_template()
        assert not list(tmp_path.iterdir())
        monkeypatch.setattr(TemplateDialog,'exec',lambda self: QDialog.DialogCode.Accepted)
        monkeypatch.setattr(module.QFileDialog,'getSaveFileName',lambda *args: (str(tmp_path/'placement'),''))
        window.placement_template()
        assert (tmp_path/'placement.pdf').exists()
        assert window.project.dumps()==before and not window.history
    finally:
        window.saved=window.project.dumps()
        window.close()
