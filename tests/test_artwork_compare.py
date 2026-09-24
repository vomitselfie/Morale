import pytest
from PySide6.QtGui import QImage,QColor,QPainter
from PySide6.QtWidgets import QApplication
from morale.artwork_compare import ArtworkCompareDialog


@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])


def panels():
    result={}
    for key,color in [('source','red'),('vectors','green'),('stitches','blue')]:
        result[key]=QImage(640,640,QImage.Format.Format_RGB32);result[key].fill(QColor(color))
    return result


def test_overlay_blends_same_coordinates_and_preserves_zoom():
    dialog=ArtworkCompareDialog(panels());dialog.show();QApplication.processEvents()
    try:
        before=dialog.view.transform().m11();dialog.zoom_in()
        assert dialog.view.transform().m11()>before
        zoom=dialog.view.transform();dialog.mode.setCurrentIndex(1);dialog.opacity.setValue(50)
        assert dialog.view.transform()==zoom
        image=QImage(640,640,QImage.Format.Format_RGB32);image.fill(QColor('white'))
        painter=QPainter(image);dialog.scene.render(painter);painter.end()
        c=image.pixelColor(320,320)
        assert c.red()==pytest.approx(128,abs=2) and c.green()==pytest.approx(64,abs=2) and c.blue()==0
        dialog.mode.setCurrentIndex(0)
        assert not dialog.overlay.isVisible() and not dialog.opacity.isEnabled()
        assert dialog.view.transform()==zoom
        dialog.fit()
        assert dialog.view.transform().m11()<zoom.m11()
        assert dialog.view.viewport().rect().contains(dialog.view.mapFromScene(dialog.scene.sceneRect()).boundingRect())
    finally:dialog.close()


def test_comparison_owns_snapshot():
    original=panels();dialog=ArtworkCompareDialog(original)
    try:
        original['source'].fill(QColor('black'))
        assert dialog.panels['source'].pixelColor(0,0)==QColor('red')
    finally:dialog.close()


@pytest.mark.parametrize('bad',[{}, {'source':QImage()},dict(source=QImage(1,1,QImage.Format.Format_RGB32),vectors=QImage(),stitches=QImage())])
def test_missing_or_wrong_sized_images_rejected(bad):
    with pytest.raises(ValueError):ArtworkCompareDialog(bad)
