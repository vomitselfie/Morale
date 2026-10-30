import json
import pytest
from PySide6.QtWidgets import QApplication
from morale import embroidery_fonts,font_audit


@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])


@pytest.mark.parametrize('damaged',[False,True])
def test_missing_or_damaged_font_library_cannot_pass(tmp_path,monkeypatch,damaged):
    fonts=tmp_path/'fonts';fonts.mkdir()
    if damaged:
        folder=fonts/'damaged';folder.mkdir();(folder/'font.json.gz').write_bytes(b'not gzip')
    monkeypatch.setattr(embroidery_fonts,'FONT_DIR',fonts)
    destination=tmp_path/'report'
    try:
        assert font_audit.run(destination)==1
        report=json.loads((destination/'report.json').read_text())
        assert not report['passed'] and not report['physical_sewouts']
        if damaged:
            assert report['results'][0]['font']=='damaged'
            assert all(not item['passed'] and 'Font loading failed' in item['error'] for item in report['results'][0]['layouts'])
        else:assert report['results']==[]
        before=(destination/'report.json').read_bytes()
        with pytest.raises(FileExistsError):font_audit.run(destination)
        assert (destination/'report.json').read_bytes()==before
    finally:embroidery_fonts.load_font.cache_clear()
