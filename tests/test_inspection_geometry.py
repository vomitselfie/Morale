import xml.etree.ElementTree as ET
import pytest
from PySide6.QtCore import QRectF,Qt
from PySide6.QtGui import QImage,QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication
from morale.inspection_geometry import inspection_layers
from morale.engine import Block,Stitch
from morale.review_panels import frame_transform
from morale.artwork_compare import ArtworkCompareDialog


@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])


def data():
    info={'trace_stats':{'artwork_size_mm':[40,20]},'trace_svg':'<svg viewBox="0 0 40 20"><path fill="red" d="M2 4 C2 1 10 1 10 4 L10 12 L2 12 Z"/></svg>'}
    blocks=[Block('one','#ff0000',[Stitch(-18,-6,'jump'),Stitch(-10,-6),Stitch(10,6,'jump'),Stitch(18,6)])]
    frame=QRectF(-21,-11,42,22)
    return info,blocks,frame


def test_scalable_stitches_preserve_travel_gaps_and_curves():
    info,blocks,frame=data();layers=inspection_layers(info,blocks,frame,{'one'})
    assert 'C2 1 10 1 10 4' in layers['vectors']
    root=ET.fromstring(layers['stitches']);paths=root.findall('{*}path')
    assert len(paths)==1 and paths[0].get('d').count('M ')==2
    assert len(root.findall('{*}circle'))==1
    renderer=QSvgRenderer(layers['stitches'].encode());assert renderer.isValid()
    image=QImage(1280,1280,QImage.Format.Format_RGB32);image.fill(Qt.GlobalColor.white)
    painter=QPainter(image);renderer.render(painter);painter.end()
    transform=frame_transform(frame)
    # A lost jump would sew straight through the design center.
    x,y=transform.map(0.,0.);assert image.pixelColor(round(x*2),round(y*2)).red()>240
    assert image.pixelColor(round(x*2),round(y*2)).green()>240
    x,y=transform.map(14.,6.);color=image.pixelColor(round(x*2),round(y*2))
    assert color.red()>150 and color.green()<100


def test_inspector_uses_uncached_geometry_and_preserves_view():
    info,blocks,frame=data();layers=inspection_layers(info,blocks,frame)
    panels={key:QImage(640,640,QImage.Format.Format_RGB32) for key in ('source','vectors','stitches')}
    for image in panels.values():image.fill(Qt.GlobalColor.white)
    dialog=ArtworkCompareDialog(panels,geometry=layers);dialog.show();QApplication.processEvents()
    try:
        assert dialog.vector_layers['stitches'].isVisible() and not dialog.overlay.isVisible()
        assert all(not item.isCachingEnabled() for item in dialog.vector_layers.values())
        dialog.zoom_in();view=dialog.view.transform();dialog.mode.setCurrentIndex(1);dialog.opacity.setValue(35)
        assert dialog.view.transform()==view and dialog.vector_layers['vectors'].graphicsEffect().opacity()==.35
        assert dialog.vector_layers['vectors'].isVisible() and not dialog.vector_layers['stitches'].isVisible()
        dialog.mode.setCurrentIndex(0);assert not any(item.isVisible() for item in dialog.vector_layers.values())
    finally:dialog.close()


def test_pixel_mode_still_has_scalable_sewn_geometry():
    info,blocks,frame=data();info['trace_svg']=''
    assert set(inspection_layers(info,blocks,frame))=={'stitches','long_spans'}


def test_geometry_blends_as_one_layer_instead_of_per_svg_primitive():
    panels={key:QImage(640,640,QImage.Format.Format_RGB32) for key in ('source','vectors','stitches')}
    for image in panels.values():image.fill(Qt.GlobalColor.red)
    svg='<svg xmlns="http://www.w3.org/2000/svg" width="640" height="640" viewBox="0 0 640 640"><rect width="640" height="640" fill="white"/><rect x="100" y="100" width="440" height="440" fill="red"/></svg>'
    dialog=ArtworkCompareDialog(panels,geometry={'stitches':svg})
    try:
        dialog.opacity.setValue(50)
        image=QImage(640,640,QImage.Format.Format_RGB32);image.fill(Qt.GlobalColor.white)
        painter=QPainter(image);dialog.scene.render(painter);painter.end()
        center=image.pixelColor(320,320);edge=image.pixelColor(20,20)
        assert center.red()>250 and center.green()<3 and center.blue()<3
        assert edge.red()>250 and edge.green()==pytest.approx(128,abs=2)
    finally:dialog.close()
