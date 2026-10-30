import sys
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer,QProcess
from morale import coupon_worker as worker

@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])


def test_real_worker_exports_while_gui_timer_runs(tmp_path):
    ticks=[];timer=QTimer();timer.timeout.connect(lambda:ticks.append(1));timer.start(10)
    try:report=worker.export_coupon('ripple-spacing',tmp_path/'pack')
    finally:timer.stop()
    assert len(ticks)>5
    assert report['coupon']=='ripple-spacing' and not report['physical_sewouts']
    assert not (tmp_path/'pack/INCOMPLETE.txt').exists()
    assert all(check['verified'] for check in report['export_verification'].values())


@pytest.mark.parametrize('action',['reject','close'])
def test_cancel_stops_the_running_process(monkeypatch,tmp_path,action):
    monkeypatch.setattr(worker,'worker_command',lambda *a:[sys.executable,'-c','import time; time.sleep(60)'])
    dialog=worker.CouponProgress('ripple-spacing',tmp_path/'pack')
    dialog.process.started.connect(lambda:QTimer.singleShot(20,getattr(dialog,action)))
    QTimer.singleShot(0,dialog.start)
    dialog.exec()
    assert dialog.cancelled and not dialog.completed
    assert dialog.process.state()==QProcess.ProcessState.NotRunning
    dialog.deleteLater()


def test_timeout_stops_process_and_reports_error(monkeypatch,tmp_path):
    monkeypatch.setattr(worker,'worker_command',lambda *a:[sys.executable,'-c','import time; time.sleep(60)'])
    with pytest.raises(ValueError,match='time limit'):
        worker.export_coupon('ripple-spacing',tmp_path/'pack',timeout_ms=30)


def test_launch_failure_is_reported(monkeypatch,tmp_path):
    monkeypatch.setattr(worker,'worker_command',lambda *a:[str(tmp_path/'missing-program')])
    with pytest.raises(ValueError,match='Could not start'):
        worker.export_coupon('ripple-spacing',tmp_path/'pack')


def test_worker_rejects_unknown_coupon_without_creating_folder(tmp_path):
    with pytest.raises(ValueError,match='Unknown sewout coupon'):
        worker.export_coupon('missing',tmp_path/'pack')
    assert not (tmp_path/'pack').exists()
