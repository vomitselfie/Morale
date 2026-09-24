import xml.etree.ElementTree as ET
import pytest
from PySide6.QtCore import QRectF,Qt
from PySide6.QtGui import QImage,QPainter,QPainterPath,QColor
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication
from morale.stitch_rendering import needs_contrast,draw_stitch_path
from morale.inspection_geometry import inspection_layers
from morale.review_panels import aligned_panels
from morale.engine import Block,Stitch


@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])


@pytest.mark.parametrize('color,expected',[('#ffffff',True),('#ffff00',True),('#eeeeee',True),('#000000',False),('#ff0000',False),('#0000ff',False)])
def test_light_colors_get_preview_contrast(color,expected):assert needs_contrast(color)==expected


def test_contrast_preserves_white_core():
    image=QImage(100,40,QImage.Format.Format_RGB32);image.fill(Qt.GlobalColor.white)
    painter=QPainter(image);path=QPainterPath();path.moveTo(10,20);path.lineTo(90,20)
    draw_stitch_path(painter,path,'#ffffff',3);painter.end()
    assert image.pixelColor(50,20)==QColor('white')
    assert image.pixelColor(50,17).red()<200
    assert image.pixelColor(50,5)==QColor('white')


def test_aligned_and_scalable_white_stitches_visible_without_sewing_across_jump():
    info={'trace_stats':{'artwork_size_mm':[20,20]},'trace_svg':''}
    blocks=[Block('white','#ffffff',[Stitch(-8,0,'jump'),Stitch(-2,0),Stitch(2,0,'jump'),Stitch(8,0)])]
    source=QImage(100,100,QImage.Format.Format_RGB32);source.fill(Qt.GlobalColor.white)
    panels,frame=aligned_panels(info,source,None,blocks=blocks)
    before=[(s.command,s.x,s.y) for s in blocks[0].stitches]
    svg=inspection_layers(info,blocks,frame)['stitches']
    root=ET.fromstring(svg);paths=root.findall('{*}path')
    assert len(paths)==2 and paths[0].get('data-preview-contrast')=='true'
    assert paths[1].get('stroke')=='#ffffff' and paths[0].get('d')==paths[1].get('d')
    renderer=QSvgRenderer(svg.encode());vector=QImage(640,640,QImage.Format.Format_RGB32);vector.fill(Qt.GlobalColor.white)
    painter=QPainter(vector);renderer.render(painter);painter.end()
    for image in (panels[2],vector):
        assert any(image.pixelColor(x,y).red()<240 for x in range(110,230) for y in range(318,323))
        assert all(image.pixelColor(x,y)==QColor('white') for x in range(310,331) for y in range(318,323))
    assert [(s.command,s.x,s.y) for s in blocks[0].stitches]==before
