import json
import time
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from PySide6.QtCore import QPointF
from morale.vector_artwork import vector_artwork
from morale.auto_digitize import choose_stitches,outline_path
from morale.model import Project
from morale.svg_import import import_svg_text


@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])


def artwork(tmp_path):
    path=tmp_path/'vectors.svg'
    path.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="40mm" height="20mm" viewBox="0 0 40 20"><g transform="translate(4,2)"><rect width="2" height="16" fill="red"/></g><path d="M20 2 C25 6 15 14 20 18" fill="none" stroke="blue" stroke-width=".5"/></svg>')
    return path


def test_direct_geometry_page_scaling_curves_and_source_preservation(tmp_path):
    path=artwork(tmp_path);original=path.read_bytes()
    project,image,stats=vector_artwork(path,width=80)
    assert path.read_bytes()==original and stats['method']=='svg'
    assert stats['artwork_size_mm']==[80,40]
    rect,stroke=project.objects
    assert (rect.x,rect.y,rect.width,rect.height)==pytest.approx((-30,0,4,32),abs=.001)
    assert stroke.kind=='path' and stroke.handles and stroke.stitch_type=='running'
    reopened=import_svg_text(stats['svg'],center_artwork=False)
    assert reopened.objects==project.objects or [o.rings() for o in reopened.objects]==[o.rings() for o in project.objects]
    result,decisions=choose_stitches(project)
    assert [o.stitch_type for o in result.objects]==['satin','running']
    assert result.objects[1]==stroke and decisions[1]['fixed_stitch']


def test_evenodd_hole_survives_normalization(tmp_path):
    path=tmp_path/'hole.svg';path.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40"><path fill-rule="evenodd" d="M5 5 H35 V35 H5 Z M15 15 H25 V25 H15 Z"/></svg>')
    project,_,_=vector_artwork(path,width=40)
    assert not outline_path(project.objects[0].rings()).contains(QPointF(0,0))
    assert outline_path(project.objects[0].rings()).contains(QPointF(10,0))


def test_repeated_local_use_has_unique_normalized_ids(tmp_path):
    import xml.etree.ElementTree as ET
    path=tmp_path/'instances.svg';path.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40"><defs><rect id="tile" width="2" height="10"/></defs><use href="#tile" x="5"/><use href="#tile" x="25"/></svg>')
    project,_,stats=vector_artwork(path,width=40)
    assert len(project.objects)==2
    assert sorted(o.x for o in project.objects)==pytest.approx([-14,6],abs=.001)
    ids=[node.get('id') for node in ET.fromstring(stats['svg']) if node.get('id')]
    assert len(ids)==len(set(ids))


@pytest.mark.parametrize('element',['<script>alert(1)</script>','<image href="https://example.com/a.png"/>','<rect width="5" height="5" fill="url(#gradient)"/>'])
def test_unsupported_or_external_content_rejected(tmp_path,element):
    path=tmp_path/'unsafe.svg';path.write_text(f'<svg xmlns="http://www.w3.org/2000/svg">{element}</svg>')
    with pytest.raises(ValueError):vector_artwork(path)


def test_svg_worker_bypasses_raster_tracing(tmp_path,monkeypatch):
    import morale.raster_trace as worker
    path=artwork(tmp_path);output=tmp_path/'output';output.mkdir()
    def forbidden(*args,**kwargs):raise AssertionError('SVG must not be raster-traced')
    monkeypatch.setattr(worker,'trace_image',forbidden)
    assert worker.worker_main([str(path),str(output),json.dumps({'width':80,'stitch_mode':'auto','keep_reference':True})])==0
    info=json.loads((output/'preview.json').read_text())
    assert info['trace_stats']['method']=='svg'
    project=Project.loads(info['project']);assert project.reference['width']==80
    assert project.objects[1].handles


def test_native_svg_preview_controls_and_undo(tmp_path):
    from morale.trace_dialog import TraceDialog
    from morale.app import MainWindow
    dialog=TraceDialog(str(artwork(tmp_path)));window=MainWindow()
    try:
        assert not dialog.method.isEnabled() and dialog.colors.isHidden()
        dialog.generate();deadline=time.monotonic()+10
        while dialog.project is None and time.monotonic()<deadline:QTest.qWait(10)
        assert dialog.project is not None,dialog.status.text()
        assert 'Direct SVG geometry' in dialog.status.text()
        assert not dialog.decisions.cellWidget(1,1).isEnabled()
        assert dialog.quality['artwork_notes']
        before=window.project.dumps();window.apply_raster_trace(dialog.project)
        assert window.project.reference
        window.undo();assert window.project.dumps()==before
    finally:dialog.close();window.saved=window.project.dumps();window.close()


@pytest.mark.parametrize('extension',['dst','exp','jef','pec','pes','tbf','u01','vp3','xxx'])
def test_assisted_svg_exports(tmp_path,extension):
    from morale.formats import export_machine,import_machine
    from morale.engine import generate
    source,_,_=vector_artwork(artwork(tmp_path),width=80);project,_=choose_stitches(source)
    path=tmp_path/f'vector.{extension}';export_machine(project,path)
    sewn=[s for b in generate(import_machine(path).project) for s in b.stitches if s.command=='stitch']
    assert sewn and all(-32.1<=s.x<=3 and -16.1<=s.y<=16.1 for s in sewn)
