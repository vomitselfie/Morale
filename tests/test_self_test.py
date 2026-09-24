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
    assert len(report['checks'])==32 and not report['physical_sewouts'] and not report['external_files']
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
