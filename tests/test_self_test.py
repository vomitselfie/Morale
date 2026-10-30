import json
import os
import subprocess
import sys
import pytest
from PySide6.QtWidgets import QApplication
from morale.self_test import run,worker_main

@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])

def test_explicit_self_test_exercises_workers_native_project_and_exports(tmp_path):
    root=tmp_path/'smoke'
    result=subprocess.run([sys.executable,'-m','morale','--self-test',str(root)],capture_output=True,text=True,
                          env={**os.environ,'QT_QPA_PLATFORM':'offscreen'},timeout=60)
    assert result.returncode==0,result.stderr
    report=json.loads((root/'report.json').read_text())
    assert report['passed'] and not report['frozen']
    assert len(report['checks'])==53 and 'open_worker' in report['checks'] and not report['physical_sewouts'] and not report['external_files']
    assert 'explicit_boundary_trim_exports_and_order_review' in report['checks']
    assert (root/'boundary-trims/verification.json').is_file()
    assert 'library_keyboard_browse_all_and_query_invalidation' in report['checks']
    assert 'layout_guides_native_history_and_save' in report['checks']
    assert (root/'layout-guides.morale').is_file()
    assert 'keyboard_drawing_roundtrip_exports_and_history' in report['checks']
    assert 'ripple_center_edit_cutout_exports_and_history' in report['checks']
    assert 'responsive_sewout_pack_worker' in report['checks']
    assert 'svg_variable_paints_conversion_and_exports' in report['checks']
    for mode in ('direct','rendered'):
        assert (root/f'variables-{mode}.morale').is_file()
    assert (root/'ripple-sewout-pack/evaluation.pdf').is_file()
    for extension in ('morale','pes','exp','png'):
        assert (root/f'ripple.{extension}').is_file()
    for mode in ('polygon','satin'):
        for extension in ('morale','pes','exp'):
            assert (root/f'keyboard-{mode}.{extension}').is_file()
    assert 'svg_symbols_and_local_clips' in report['checks']
    assert 'svg_gradient_color_conversion' in report['checks']
    assert (root/'gradient.morale').is_file()
    assert (root/'symbols.morale').is_file()
    assert 'clipped_svg_conversion_and_cutout' in report['checks']
    assert (root/'clipped.morale').is_file()
    assert 'curved_embroidery_font_and_repaired_glyph' in report['checks']
    assert (root/'curved-embroidery-font.morale').is_file()
    assert (root/'raster/preview.json').exists() and (root/'svg/preview.json').exists()
    assert len(list((root/'exports').iterdir()))==9

def test_existing_directory_never_overwritten(tmp_path):
    path=tmp_path/'report.json';path.write_text('keep me')
    assert worker_main([str(tmp_path)])==2
    assert path.read_text()=='keep me'

def test_worker_failure_is_recorded_with_logs(tmp_path,monkeypatch):
    import morale.self_test as module
    monkeypatch.setattr(module.subprocess,'run',lambda *args,**kwargs:subprocess.CompletedProcess(args[0],1,b'',b'worker failed'))
    root=tmp_path/'failed';assert run(root)==1
    report=json.loads((root/'report.json').read_text())
    assert not report['passed'] and 'generation-worker failed' in report['error']
    assert (root/'generation/worker.log').read_text()=='worker failed'
