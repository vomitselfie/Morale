import xml.etree.ElementTree as ET
import pytest
from PySide6.QtCore import QRectF,Qt
from PySide6.QtGui import QImage,QPainter
from PySide6.QtWidgets import QApplication
from morale.model import DesignObject,Project
from morale.engine import Block,Stitch
from morale.inspection_geometry import inspection_layers
from morale.review_panels import frame_transform
from morale.trace_quality import conversion_quality
from morale.artwork_compare import ArtworkCompareDialog


@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])


def layers_for(stitches):
    obj=DesignObject();project=Project(objects=[obj]);blocks=[Block(obj.id,'#000000',stitches)]
    info={'project':project.dumps(),'trace_stats':{'artwork_size_mm':[40,20]},'trace_svg':''}
    frame=QRectF(-21,-11,42,22)
    return inspection_layers(info,blocks,frame),conversion_quality(project,blocks),frame


def test_highlight_count_matches_complete_report_beyond_location_cap():
    stitches=[Stitch(0,0,'jump')]+[Stitch(10 if i%2==0 else 0,0) for i in range(25)]
    layers,report,_=layers_for(stitches)
    root=ET.fromstring(layers['long_spans']);paths=root.findall('{*}path')
    assert len(paths)==1 and paths[0].get('d').count('M ')==report['long_stitches']==25
    assert len(report['regions'][0]['long_stitch_locations'])==20
    assert not root.findall('{*}rect')  # The overlay must not hide the design below it.


def test_threshold_boundary_jumps_and_controls_do_not_create_highlights():
    layers,report,_=layers_for([Stitch(-15,0,'jump'),Stitch(-9,0),Stitch(15,0,'jump'),Stitch(1000,1000,'stop'),Stitch(1000,1000,'trim')])
    assert report['long_stitches']==0 and 'long_spans' not in layers


def test_native_highlight_is_visible_on_stitches_only_and_retains_view():
    layers,report,frame=layers_for([Stitch(-8,0,'jump'),Stitch(8,0)])
    panels={key:QImage(640,640,QImage.Format.Format_RGB32) for key in ('source','vectors','stitches')}
    for image in panels.values():image.fill(Qt.GlobalColor.white)
    dialog=ArtworkCompareDialog(panels,geometry=layers)
    try:
        assert dialog.highlight_long.isEnabled() and not dialog.vector_layers['long_spans'].isVisible()
        dialog.zoom_in();view=dialog.view.transform();dialog.highlight_long.setChecked(True)
        assert dialog.vector_layers['long_spans'].isVisible() and dialog.view.transform()==view
        image=QImage(640,640,QImage.Format.Format_RGB32);image.fill(Qt.GlobalColor.white)
        painter=QPainter(image);dialog.scene.render(painter);painter.end()
        x,y=frame_transform(frame).map(0.,0.);color=image.pixelColor(round(x),round(y))
        assert color.red()>180 and 40<color.green()<150 and color.blue()<30
        dialog.mode.setCurrentIndex(0)
        assert not dialog.vector_layers['long_spans'].isVisible() and not dialog.highlight_long.isEnabled()
        dialog.mode.setCurrentIndex(2)
        assert dialog.vector_layers['long_spans'].isVisible() and dialog.view.transform()==view
    finally:dialog.close()


def test_old_snapshot_without_highlight_geometry_disables_control():
    image=QImage(640,640,QImage.Format.Format_RGB32);image.fill(Qt.GlobalColor.white)
    dialog=ArtworkCompareDialog(dict.fromkeys(('source','vectors','stitches'),image))
    try:assert not dialog.highlight_long.isEnabled()
    finally:dialog.close()
