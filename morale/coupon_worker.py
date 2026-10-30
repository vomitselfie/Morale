"""Isolated standard-coupon generation with a cancellable native progress dialog."""
import json
import sys
from pathlib import Path
from PySide6.QtCore import QProcess,QTimer
from PySide6.QtWidgets import QDialog,QVBoxLayout,QLabel,QProgressBar,QPushButton


def worker_main(args):
    from PySide6.QtWidgets import QApplication
    from .coupons import build_coupon
    app=QApplication.instance() or QApplication([])
    try:
        if len(args)!=2:raise ValueError('Expected coupon name and destination.')
        build_coupon(args[0],args[1])
        return 0
    except Exception as exc:
        print(str(exc),file=sys.stderr)
        return 1


def worker_command(name,destination):
    return ([sys.executable] if getattr(sys,'frozen',False) else [sys.executable,'-m','morale'])+['--coupon-worker',name,str(destination)]


class CouponProgress(QDialog):
    def __init__(self,name,destination,parent=None,timeout_ms=60000):
        super().__init__(parent)
        self.setWindowTitle('Exporting sewout pack')
        self.cancelled=False;self.failure='';self.log=b'';self.completed=False
        layout=QVBoxLayout(self)
        label=QLabel('Generating machine files, placement and evaluation forms…');label.setWordWrap(True)
        layout.addWidget(label)
        bar=QProgressBar();bar.setRange(0,0);bar.setAccessibleName('Sewout pack export progress');layout.addWidget(bar)
        self.cancel_button=QPushButton('Cancel');self.cancel_button.clicked.connect(self.reject);layout.addWidget(self.cancel_button)
        self.process=QProcess(self);self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.read_output)
        self.process.finished.connect(self.finished_process)
        self.process.errorOccurred.connect(self.process_error)
        self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.timeout.connect(self.timed_out)
        self.command=worker_command(name,destination);self.timeout_ms=timeout_ms

    def start(self):
        if self.cancelled:return
        self.timer.start(self.timeout_ms)
        self.process.start(self.command[0],self.command[1:])

    def read_output(self):
        self.log=(self.log+bytes(self.process.readAllStandardOutput()))[-8192:]

    def process_error(self,error):
        if error==QProcess.ProcessError.FailedToStart:
            self.failure='Could not start the sewout export worker.';self.timer.stop();super().reject()

    def timed_out(self):
        self.failure='Sewout export exceeded its time limit.'
        self.process.kill()

    def reject(self):
        self.cancelled=True;self.cancel_button.setEnabled(False)
        if self.process.state()!=QProcess.ProcessState.NotRunning:self.process.kill()
        else:self.timer.stop();super().reject()

    def finished_process(self,code,status):
        self.timer.stop();self.read_output()
        if self.cancelled or self.failure:super().reject()
        elif code or status!=QProcess.ExitStatus.NormalExit:
            self.failure=self.log.decode('utf-8',errors='replace').strip() or 'Sewout export worker failed.'
            super().reject()
        else:self.completed=True;super().accept()


def export_coupon(name,destination,parent=None,timeout_ms=60000):
    destination=Path(destination)
    if destination.exists():raise FileExistsError(str(destination))
    dialog=CouponProgress(name,destination,parent,timeout_ms)
    try:
        QTimer.singleShot(0,dialog.start)
        dialog.exec()
        if dialog.failure:raise ValueError(dialog.failure)
        if dialog.cancelled:return None
        if not dialog.completed:raise ValueError('Sewout export did not complete.')
        if (destination/'INCOMPLETE.txt').exists():raise ValueError('Sewout pack is incomplete.')
        with (destination/'report.json').open('rb') as stream:raw=stream.read(1_000_001)
        if len(raw)>1_000_000:raise ValueError('Sewout export report is too large.')
        report=json.loads(raw)
        if not isinstance(report,dict) or report.get('coupon')!=name or not isinstance(report.get('export_verification'),dict):
            raise ValueError('Invalid sewout export report.')
        return report
    finally:dialog.deleteLater()
