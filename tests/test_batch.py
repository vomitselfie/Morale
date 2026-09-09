import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
import sys
import time

import pytest
from PySide6.QtCore import QProcess
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from morale.batch import ConversionQueue
from morale.batch_dialog import BatchDialog
from morale.formats import export_machine, import_machine
from morale.model import demo_project


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def wait_for(app, predicate, timeout=8):
    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        QTest.qWait(10)
    assert predicate(), "Native queue did not reach the expected state"


@pytest.fixture
def source(tmp_path):
    path = tmp_path / "original.pes"
    export_machine(demo_project(), path)
    return path


def test_queue_converts_and_isolates_bad_files(app, source, tmp_path):
    output = tmp_path / "output"
    output.mkdir()
    bad = tmp_path / "bad.dst"
    bad.write_bytes(b"not an embroidery file")
    before = source.read_bytes()
    queue = ConversionQueue()
    queue.start([bad, source], output, "dst")
    wait_for(app, lambda: not queue.running)
    assert [r["status"] for r in queue.results] == ["failed", "converted"]
    assert len(import_machine(output / "original.dst").project.objects) == 4
    assert source.read_bytes() == before
    assert not (output / "bad.dst").exists()
    assert not list(output.glob(".morale-batch-*"))


def test_existing_and_duplicate_names_never_overwritten(app, source, tmp_path):
    queue = ConversionQueue()
    before = source.read_bytes()
    queue.start([source], tmp_path, "pes")
    wait_for(app, lambda: not queue.running)
    assert queue.results[0]["status"] == "skipped"
    assert source.read_bytes() == before
    nested = tmp_path / "nested"
    nested.mkdir()
    second = nested / "ORIGINAL.dst"
    export_machine(demo_project(), second)
    queue.start([source, second], tmp_path, "exp")
    wait_for(app, lambda: not queue.running)
    assert [r["status"] for r in queue.results] == ["skipped", "skipped"]
    assert not (tmp_path / "original.exp").exists()


class SlowQueue(ConversionQueue):
    def worker_command(self, source, staged):
        return sys.executable, ["-c", "import time; time.sleep(30)"]


def test_cancel_kills_worker_and_cancels_pending_without_output(app, source, tmp_path):
    second = tmp_path / "second.pes"
    second.write_bytes(source.read_bytes())
    queue = SlowQueue()
    queue.start([source, second], tmp_path, "dst")
    wait_for(app, lambda: queue.process is not None and queue.process.state() == QProcess.ProcessState.Running)
    process = queue.process
    queue.cancel()
    wait_for(app, lambda: not queue.running)
    assert [r["status"] for r in queue.results] == ["cancelled", "cancelled"]
    assert queue.process is None
    assert not (tmp_path / "original.dst").exists()
    assert not (tmp_path / "second.dst").exists()
    assert not list(tmp_path.glob(".morale-batch-*"))


def test_timeout_is_reported_and_queue_finishes(app, source, tmp_path):
    queue = SlowQueue(timeout_ms=30)
    queue.start([source], tmp_path, "dst")
    wait_for(app, lambda: not queue.running)
    assert queue.results[0]["status"] == "failed"
    assert "exceeded" in queue.results[0]["message"]
    assert not (tmp_path / "original.dst").exists()
    assert not list(tmp_path.glob(".morale-batch-*"))


def test_destination_race_does_not_replace_external_file(app, source, tmp_path, monkeypatch):
    import morale.batch as batch
    original = batch.publish
    def raced(staged, target):
        Path(target).write_bytes(b"external data")
        original(staged, target)
    monkeypatch.setattr(batch, "publish", raced)
    queue = ConversionQueue()
    queue.start([source], tmp_path, "dst")
    wait_for(app, lambda: not queue.running)
    assert queue.results[0]["status"] == "skipped"
    assert (tmp_path / "original.dst").read_bytes() == b"external data"


def test_publication_failure_leaves_no_partial_target(app, source, tmp_path, monkeypatch):
    import morale.batch as batch
    def unavailable(*args):
        raise OSError("hard links unsupported")
    monkeypatch.setattr(batch, "publish", unavailable)
    queue = ConversionQueue()
    queue.start([source], tmp_path, "dst")
    wait_for(app, lambda: not queue.running)
    assert queue.results[0]["status"] == "failed"
    assert not (tmp_path / "original.dst").exists()
    assert not list(tmp_path.glob(".morale-batch-*"))


def test_native_dialog_runs_queue_and_reenables_controls(app, source, tmp_path):
    dialog = BatchDialog()
    dialog.sources = [str(source)]
    dialog.output.setText(str(tmp_path))
    dialog.format.setCurrentIndex(next(i for i in range(dialog.format.count()) if dialog.format.itemData(i)[0] == "dst"))
    dialog.start()
    assert not dialog.start_button.isEnabled()
    wait_for(app, lambda: not dialog.queue.running)
    assert dialog.start_button.isEnabled()
    assert dialog.report_button.isEnabled()
    assert "converted" in dialog.summary.text()
    assert "CONVERTED" in dialog.log.toPlainText()
    dialog.reject()


def test_invalid_start_and_reentrant_start(app, source, tmp_path):
    queue = ConversionQueue()
    with pytest.raises(ValueError, match="output folder"):
        queue.start([source], "", "dst")
    queue.start([source], tmp_path, "dst")
    with pytest.raises(ValueError, match="already"):
        queue.start([source], tmp_path, "dst")
    queue.cancel()
    wait_for(app, lambda: not queue.running)
    assert queue.results[0]["status"] == "cancelled"


def test_exclusive_rename_fallback_without_hardlinks(tmp_path, monkeypatch):
    import morale.batch as batch
    def unavailable(*args):
        raise OSError("hard links unsupported")
    monkeypatch.setattr(batch.os, "link", unavailable)
    staged, target = tmp_path / "stage", tmp_path / "target"
    staged.write_bytes(b"complete file")
    batch.publish(staged, target)
    assert target.read_bytes() == b"complete file"
    assert not staged.exists()
    staged.write_bytes(b"new data")
    with pytest.raises(FileExistsError):
        batch.publish(staged, target)
    assert target.read_bytes() == b"complete file"
    assert staged.read_bytes() == b"new data"


def test_close_dialog_waits_for_worker_shutdown(app, source, tmp_path):
    dialog = BatchDialog()
    dialog.queue.worker_command = lambda *args: (sys.executable, ["-c", "import time;time.sleep(30)"])
    dialog.queue.start([source], tmp_path, "dst")
    wait_for(app, lambda: dialog.queue.process is not None and dialog.queue.process.state() == QProcess.ProcessState.Running)
    dialog.reject()
    wait_for(app, lambda: not dialog.queue.running)
    assert dialog.queue.results[0]["status"] == "cancelled"
    assert dialog.queue.process is None


def test_worker_protocol_does_not_require_console(source, tmp_path, monkeypatch):
    import json
    from morale.batch import worker_main
    staged = tmp_path / "consoleless.dst"
    monkeypatch.setattr(sys, "stdout", None)
    assert worker_main([str(source), str(staged), "6"]) == 0
    result = json.loads(Path(str(staged) + ".result.json").read_text())
    assert result["notes"]
    assert staged.stat().st_size > 512
