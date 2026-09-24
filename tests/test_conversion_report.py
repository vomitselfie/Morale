import json
import re
import shutil
import subprocess
from copy import deepcopy
import pytest
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication
from morale.raster_trace import worker_main
from morale.conversion_report import save_conversion_review

@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])

@pytest.fixture
def preview(tmp_path):
    source=tmp_path/'art.svg';source.write_text('<svg width="40" height="40"><rect x="5" y="5" width="30" height="30" fill="red"/></svg>')
    output=tmp_path/'worker';output.mkdir()
    assert worker_main([str(source),str(output),'{}'])==0
    return json.loads((output/'preview.json').read_text()),QImage(str(output/'preview.png'))

def test_pdf_contains_visual_pages_and_measurements_without_changing_project(tmp_path,preview):
    info,image=preview;before=deepcopy(info);path=tmp_path/'review.pdf'
    save_conversion_review(path,'private/folder/art.svg',info,image)
    data=path.read_bytes();assert data.startswith(b'%PDF-')
    assert len(re.findall(rb'/Type /Page\b',data))>=4
    assert info==before
    if shutil.which('pdftotext'):
        text=subprocess.check_output(['pdftotext',str(path),'-'],text=True)
        assert 'art.svg' in text and 'private/folder' not in text
        assert 'Conversion measurements' in text and 'Needle-penetration review' in text
        assert 'not an actual-size' in text and 'share one physical frame' in text

def test_long_measurements_paginate_without_losing_last_line(tmp_path,preview):
    info,image=preview;info['trace_stats']['quality']['artwork_notes']=[f'Review detail {i}: inspect this generated region.' for i in range(250)]
    path=tmp_path/'long.pdf';save_conversion_review(path,'art.svg',info,image)
    assert len(re.findall(rb'/Type /Page\b',path.read_bytes()))>4
    if shutil.which('pdftotext'):
        text=subprocess.check_output(['pdftotext',str(path),'-'],text=True)
        assert 'Review detail 249' in text

def test_write_failure_preserves_existing_pdf_and_removes_temporary_file(tmp_path,preview,monkeypatch):
    import morale.conversion_report as module
    info,image=preview;path=tmp_path/'review.pdf';path.write_bytes(b'original')
    def fail(*args):raise OSError('simulated PDF failure')
    monkeypatch.setattr(module,'_write',fail)
    before=set(tmp_path.iterdir())
    with pytest.raises(OSError):save_conversion_review(path,'art.svg',info,image)
    assert path.read_bytes()==b'original' and set(tmp_path.iterdir())==before

def test_pixel_mode_without_prepared_svg_can_be_reviewed(tmp_path,preview):
    info,image=preview;info['trace_svg']=''
    path=tmp_path/'pixels.pdf';save_conversion_review(path,'pixels.png',info,image)
    assert path.read_bytes().startswith(b'%PDF-')

def test_native_save_and_invalidation(tmp_path,preview,monkeypatch):
    import morale.trace_dialog as module
    info,image=preview;dialog=module.TraceDialog(str(tmp_path/'art.svg'))
    try:
        dialog.ready('preview.png',info,image)
        assert dialog.review_button.isEnabled()
        path=tmp_path/'native.pdf';monkeypatch.setattr(module.QFileDialog,'getSaveFileName',lambda *args:(str(path),''))
        dialog.save_review();assert path.read_bytes().startswith(b'%PDF-')
        dialog.invalidate_preview();assert dialog.review_snapshot is None and not dialog.review_button.isEnabled()
        dialog.ready('preview.png',info,image);dialog.failed('preview.png','failed')
        assert dialog.review_snapshot is None and not dialog.review_button.isEnabled() and not dialog.density_button.isEnabled()
    finally:dialog.close()


def test_underlay_settings_survive_worker_and_pdf(tmp_path):
    source=tmp_path/'supports.svg'
    source.write_text('<svg width="40" height="40"><rect x="5" y="5" width="30" height="30" fill="red"/></svg>')
    output=tmp_path/'support-worker';output.mkdir()
    options={'stitch_settings':{'fill_underlay':'edge_sparse','underlay_inset':.4,'underlay_spacing':1.5}}
    assert worker_main([str(source),str(output),json.dumps(options)])==0
    info=json.loads((output/'preview.json').read_text())
    region=info['trace_stats']['quality']['regions'][0]
    assert region['underlay']['style']=='edge_sparse' and region['underlay']['inset_mm']==.4
    path=tmp_path/'supports.pdf'
    save_conversion_review(path,'supports.svg',info,QImage(str(output/'preview.png')))
    if shutil.which('pdftotext'):
        text=subprocess.check_output(['pdftotext','-layout',str(path),'-'],text=True)
        import unicodedata
        text=unicodedata.normalize('NFKC',text)
        assert 'Fill underlay: Edge run and sparse fill' in text
        assert 'support spacing 1.5 mm' in text and 'inset 0.4 mm' in text
