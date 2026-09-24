import json
import pytest
from PySide6.QtCore import QPointF
from PySide6.QtGui import QImage,QColor
from PySide6.QtWidgets import QApplication
from morale.background_removal import remove_border_white
from morale.raster_trace import trace_image,worker_main
from morale.canvas import Canvas


@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])


def artwork():
    image=QImage(32,32,QImage.Format.Format_RGBA8888);image.fill(QColor('white'))
    for y in range(4,28):
        for x in range(4,28):image.setPixelColor(x,y,QColor('red'))
    for y in range(10,22):
        for x in range(10,22):image.setPixelColor(x,y,QColor('white'))
    return image


def test_enclosed_white_kept_and_source_untouched():
    source=artwork();before=source.copy();result,report=remove_border_white(source)
    assert source==before and result.pixelColor(0,0).alpha()==0
    assert result.pixelColor(15,15)==QColor('white') and result.pixelColor(5,5)==QColor('red')
    assert report['removed_pixels']==32*32-24*24


def test_transparent_channel_connects_white_to_page_edge():
    source=artwork()
    for y in range(16):source.setPixelColor(15,y,QColor('transparent'))
    result,_=remove_border_white(source)
    assert result.pixelColor(16,16).alpha()==0


def test_diagonal_contact_does_not_open_enclosed_detail():
    source=QImage(3,3,QImage.Format.Format_RGBA8888);source.fill(QColor('red'))
    source.setPixelColor(0,0,QColor('white'));source.setPixelColor(1,1,QColor('white'))
    result,_=remove_border_white(source)
    assert result.pixelColor(0,0).alpha()==0 and result.pixelColor(1,1)==QColor('white')


@pytest.mark.parametrize('method',['pixels','smooth'])
def test_conversion_keeps_enclosed_white_object_and_original_reference(tmp_path,method):
    source=artwork();path=tmp_path/'white-detail.png';source.save(str(path))
    ordinary,_,_=trace_image(path,width=32,colors=2,resolution=64,minimum_region=1,method=method,palette_metric='oklab')
    result,reference,stats=trace_image(path,width=32,colors=2,resolution=64,minimum_region=1,method=method,palette_metric='oklab',border_white=True,smoothing=0)
    assert not any(o.color.lower()=='#ffffff' for o in ordinary.objects)
    white=[o for o in result.objects if o.color.lower()=='#ffffff']
    assert white and any(Canvas.outline_path(o).contains(QPointF(0,0)) for o in white)
    assert all(not Canvas.outline_path(o).contains(QPointF(-15,-15)) for o in result.objects)
    assert reference.pixelColor(0,0).alpha()==255 and reference.pixelColor(15,15)==QColor('white')
    assert stats['background_removal']['mode']=='border_white'


def test_native_option_worker_report_and_legacy_presets(tmp_path):
    from morale.trace_dialog import TraceDialog
    from morale.trace_quality import quality_text
    from morale.trace_presets import validate
    path=tmp_path/'white.png';artwork().save(str(path));output=tmp_path/'out';output.mkdir()
    assert worker_main([str(path),str(output),json.dumps(dict(width=32,colors=2,resolution=64,minimum_region=1,method='smooth',border_white=True))])==0
    info=json.loads((output/'preview.json').read_text())
    assert 'Page-edge background removal' in quality_text(info['trace_stats']['quality'])
    dialog=TraceDialog(str(path))
    try:
        old=dialog.preset_settings();old.pop('border_white')
        assert validate(old)['border_white'] is False
        dialog.overrides={'0':'fill'};dialog.border_white.setChecked(True)
        assert not dialog.overrides and dialog.preset_settings()['border_white']
        dialog.runner.load=lambda _:None;dialog.generate();assert dialog.runner.options['border_white']
        dialog.white.setChecked(False);assert not dialog.border_white.isEnabled()
    finally:dialog.close()


def test_invalid_setting_rejected_before_reading_file(tmp_path):
    with pytest.raises(ValueError):trace_image(tmp_path/'missing.png',border_white=1)
