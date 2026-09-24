import base64,json
import pytest
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication
from PySide6.QtSvg import QSvgRenderer
from morale.raster_trace import worker_main
from morale.review_panels import aligned_panels
from morale.model import Project,DesignObject
from morale.stitch_edit import manual_object

@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])

@pytest.fixture
def artwork(tmp_path):
    path=tmp_path/'offset.svg';path.write_text('<svg width="40" height="20"><rect x="2" y="4" width="8" height="8" fill="red"/></svg>')
    output=tmp_path/'output';output.mkdir()
    assert worker_main([str(path),str(output),json.dumps(dict(width=40,stitch_mode='fill'))])==0
    info=json.loads((output/'preview.json').read_text())
    return info,QImage.fromData(base64.b64decode(info['raster_png'])),QSvgRenderer(info['trace_svg'].encode())

def red_bounds(image):
    rgba=image.convertToFormat(QImage.Format.Format_RGBA8888);data=bytes(rgba.constBits());width=image.width()
    hits=[i//4 for i in range(0,len(data),4) if data[i]>150 and data[i]>data[i+1]+50 and data[i]>data[i+2]+50]
    assert hits
    return min(i%width for i in hits),min(i//width for i in hits),max(i%width for i in hits),max(i//width for i in hits)

def test_three_panels_keep_same_physical_scale_and_asymmetric_padding(artwork):
    info,source,vector=artwork;panels,frame=aligned_panels(info,source,vector)
    a,b,c=[red_bounds(image) for image in panels]
    assert b==pytest.approx(a,abs=2)
    assert c==pytest.approx(a,abs=4)
    assert a[2]<320  # Offset artwork must not be centered independently.
    assert frame.width()/frame.height()==pytest.approx(42/22)
    assert all((p.width(),p.height())==(640,640) for p in panels)

def test_commands_outside_artwork_expand_shared_frame(artwork):
    info,source,vector=artwork
    project=Project(objects=[manual_object(DesignObject(color='#ff0000'),[[0,0,'jump'],[30,0,'stitch']])])
    info['project']=project.dumps()
    panels,frame=aligned_panels(info,source,vector)
    assert frame.right()>30 and frame.left()<-20
    assert red_bounds(panels[2])[2]<639

def test_rendering_does_not_change_snapshot(artwork):
    info,source,vector=artwork;before=json.dumps(info,sort_keys=True)
    aligned_panels(info,source,vector)
    assert json.dumps(info,sort_keys=True)==before

def test_invalid_physical_frame_rejected(artwork):
    info,source,vector=artwork;info['trace_stats']['artwork_size_mm']=[0,20]
    with pytest.raises(ValueError,match='dimensions'):aligned_panels(info,source,vector)


def test_worker_and_native_preview_share_scale_without_ui_generation(artwork,monkeypatch):
    import morale.review_panels as module
    from morale.trace_dialog import TraceDialog
    info,source,vector=artwork
    panels=[QImage.fromData(base64.b64decode(info['aligned_previews'][key])) for key in ('source','vectors','stitches')]
    bounds=[red_bounds(panel) for panel in panels]
    assert bounds[1]==pytest.approx(bounds[0],abs=2)
    assert bounds[2]==pytest.approx(bounds[0],abs=4)
    monkeypatch.setattr(module,'generate',lambda *_:pytest.fail('Preview regenerated stitches on the UI thread'))
    dialog=TraceDialog('offset.svg')
    try:
        dialog.ready('offset.svg',info,panels[2])
        assert dialog.project is not None
        actual=[red_bounds(label.pixmap().toImage()) for label in (dialog.original,dialog.vector_preview,dialog.preview)]
        assert actual[1]==pytest.approx(actual[0],abs=2)
        assert actual[2]==pytest.approx(actual[0],abs=3)
        assert actual[0][2]<140
    finally:dialog.close()


def test_aligned_start_marker_and_supplied_blocks(artwork,monkeypatch):
    import morale.review_panels as module
    from morale.engine import generate
    info,source,vector=artwork;project=Project.loads(info['project']);blocks=generate(project)
    monkeypatch.setattr(module,'generate',lambda *_:pytest.fail('Supplied blocks must be reused'))
    plain,_=aligned_panels(info,source,vector,blocks=blocks)
    marked,_=aligned_panels(info,source,vector,blocks=blocks,marked_starts={project.objects[0].id})
    assert marked[0]==plain[0] and marked[1]==plain[1] and marked[2]!=plain[2]
    def blue_count(image):
        rgba=image.convertToFormat(QImage.Format.Format_RGBA8888)
        data=bytes(rgba.constBits())
        return sum(data[i+2]>150 and data[i+2]>data[i]+50 for i in range(0,len(data),4))
    assert blue_count(marked[2])>blue_count(plain[2])


def test_inspector_uses_current_snapshot_and_clears_on_invalidation(artwork,monkeypatch):
    from morale.artwork_compare import ArtworkCompareDialog
    from morale.trace_dialog import TraceDialog
    info,source,_=artwork;dialog=TraceDialog('offset.svg');seen=[]
    monkeypatch.setattr(ArtworkCompareDialog,'exec',lambda viewer:seen.append(viewer.panels['source'].copy()))
    try:
        assert not dialog.inspect_button.isEnabled()
        dialog.ready('offset.svg',info,source);assert dialog.inspect_button.isEnabled()
        dialog.inspect_artwork();assert seen and seen[0]==dialog.aligned_images['source']
        dialog.invalidate_preview();assert not dialog.aligned_images and not dialog.inspect_button.isEnabled()
        dialog.ready('offset.svg',info,source);dialog.failed('offset.svg','failed')
        assert not dialog.aligned_images and not dialog.inspect_button.isEnabled()
    finally:dialog.close()


def test_worker_inspection_geometry_matches_shared_frame(artwork):
    from PySide6.QtGui import QPainter
    from PySide6.QtCore import Qt
    info,_,_=artwork
    for key in ('vectors','stitches'):
        renderer=QSvgRenderer(info['inspection_svg'][key].encode());assert renderer.isValid()
        image=QImage(640,640,QImage.Format.Format_RGB32);image.fill(Qt.GlobalColor.white)
        painter=QPainter(image);renderer.render(painter);painter.end()
        raster=QImage.fromData(base64.b64decode(info['aligned_previews'][key]))
        assert red_bounds(image)==pytest.approx(red_bounds(raster),abs=2)
