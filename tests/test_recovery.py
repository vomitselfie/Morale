import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import json
from pathlib import Path
import subprocess
import sys

import pytest
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QInputDialog
from PySide6.QtTest import QTest

from morale.recovery import RecoveryStore
from morale.model import Project, demo_project
from morale.app import MainWindow


@pytest.fixture(scope="module", autouse=True)
def app():
    return QApplication.instance() or QApplication([])


def test_live_sessions_are_not_recoverable_or_discardable(tmp_path):
    first, second = RecoveryStore(tmp_path), RecoveryStore(tmp_path)
    try:
        first.write(demo_project())
        assert second.available() == []
        with pytest.raises(ValueError, match="active"):
            second.load(first.snapshot)
        with pytest.raises(ValueError, match="active"):
            second.discard(first.snapshot)
        assert first.snapshot.exists()
    finally:
        first.close()
        second.close()


def test_abandoned_snapshot_roundtrip_and_cleanup(tmp_path):
    old = RecoveryStore(tmp_path)
    project = demo_project()
    old.write(project, tmp_path / "original.morale")
    old.close(discard=False)
    current = RecoveryStore(tmp_path)
    try:
        available = current.available()
        assert len(available) == 1
        assert current.load(available[0]["path"]).dumps() == project.dumps()
        current.discard(available[0]["path"])
        assert current.available() == []
    finally:
        current.close()


def test_real_interrupted_process_leaves_recoverable_snapshot(tmp_path):
    code = "from morale.recovery import RecoveryStore; from morale.model import demo_project; import os,sys; store=RecoveryStore(sys.argv[1]); store.write(demo_project()); os._exit(0)"
    result = subprocess.run([sys.executable, "-c", code, str(tmp_path)], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    store = RecoveryStore(tmp_path)
    try:
        entries = store.available()
        assert len(entries) == 1
        assert store.load(entries[0]["path"]).name == "A little wildflower"
        store.discard(entries[0]["path"])
    finally:
        store.close()


def test_failed_write_keeps_previous_snapshot(tmp_path, monkeypatch):
    import morale.recovery as module
    store = RecoveryStore(tmp_path)
    project = demo_project()
    store.write(project)
    previous = store.snapshot.read_bytes()
    def fail(*args):
        raise OSError("disk failure")
    monkeypatch.setattr(module.os, "replace", fail)
    project.name = "Changed"
    with pytest.raises(OSError):
        store.write(project)
    assert store.snapshot.read_bytes() == previous
    assert not list(tmp_path.glob("*.tmp"))
    store.close()


def test_damaged_snapshot_is_listed_but_not_loaded(tmp_path):
    path = tmp_path / "broken.recovery.json"
    path.write_text("broken")
    store = RecoveryStore(tmp_path)
    try:
        assert store.available()[0]["error"]
        with pytest.raises(ValueError):
            store.load(path)
        assert path.exists()
        store.discard(path)
    finally:
        store.close()


def test_native_checkpoint_restore_and_save_as(tmp_path, monkeypatch):
    old = RecoveryStore(tmp_path / "recovery")
    project = demo_project()
    project.name = "Recovered work"
    source = tmp_path / "original.morale"
    source.write_text("original must not be replaced")
    old.write(project, source)
    old.close(discard=False)
    window = MainWindow(tmp_path / "recovery")
    try:
        window.restore_recovery(old.snapshot)
        assert window.project.name == "Recovered work"
        assert window.file_path is None
        assert window.project.dumps() != window.saved
        assert window.recovery.snapshot.exists()
        assert not old.snapshot.exists()
        output = tmp_path / "restored.morale"
        monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args, **kwargs: (str(output), ""))
        assert window.save()
        assert not window.recovery.snapshot.exists()
        assert Project.loads(output.read_text()).name == "Recovered work"
        assert source.read_text() == "original must not be replaced"
    finally:
        window.saved = window.project.dumps()
        window.close()


def test_recovery_write_failure_does_not_consume_source(tmp_path, monkeypatch):
    old = RecoveryStore(tmp_path)
    old.write(demo_project())
    old.close(discard=False)
    window = MainWindow(tmp_path)
    before = window.project.dumps()
    try:
        def fail(*args, **kwargs):
            raise OSError("disk failure")
        monkeypatch.setattr(window.recovery, "write", fail)
        with pytest.raises(OSError):
            window.restore_recovery(old.snapshot)
        assert window.project.dumps() == before
        assert old.snapshot.exists()
    finally:
        window.saved = window.project.dumps()
        window.close()


def test_checkpoint_and_clean_close(tmp_path):
    window = MainWindow(tmp_path)
    window.update_property("width", 22)
    assert window.recovery_idle.isActive()
    window.checkpoint()
    path = window.recovery.snapshot
    assert path.exists()
    window.saved = window.project.dumps()
    window.close()
    assert not path.exists()
    assert not window.recovery_timer.isActive()
    assert not window.recovery_idle.isActive()


def test_cancel_recovery_keeps_copy(tmp_path, monkeypatch):
    old = RecoveryStore(tmp_path)
    old.write(demo_project())
    old.close(discard=False)
    window = MainWindow(tmp_path)
    try:
        monkeypatch.setattr(QInputDialog, "getItem", lambda *args, **kwargs: ("", False))
        window.recover_session()
        assert old.snapshot.exists()
    finally:
        window.saved = window.project.dumps()
        window.close()


def test_idle_timer_really_writes_a_snapshot(tmp_path):
    window = MainWindow(tmp_path)
    try:
        window.recovery_idle.setInterval(20)
        window.update_property("width", 23)
        QTest.qWait(100)
        assert window.recovery.snapshot.exists()
        record = json.loads(window.recovery.snapshot.read_text())
        assert Project.loads(record["project"]).objects[-1].width == 23
    finally:
        window.saved = window.project.dumps()
        window.close()


def test_failed_checkpoint_is_visible_and_retains_previous(tmp_path, monkeypatch):
    window = MainWindow(tmp_path)
    try:
        window.update_property("width", 23)
        window.checkpoint()
        previous = window.recovery.snapshot.read_bytes()
        def fail(*args, **kwargs):
            raise OSError("simulated full disk")
        monkeypatch.setattr(window.recovery, "write", fail)
        window.update_property("width", 24)
        window.checkpoint()
        assert "simulated full disk" in window.recovery_error
        assert "could not be saved" in window.statusBar().currentMessage()
        assert window.recovery.snapshot.read_bytes() == previous
    finally:
        window.saved = window.project.dumps()
        window.close()


def test_deeply_nested_record_is_reported_as_damaged(tmp_path):
    path = tmp_path / "nested.recovery.json"
    path.write_text("[" * 2000 + "0" + "]" * 2000)
    store = RecoveryStore(tmp_path)
    try:
        assert store.available()[0]["error"]
        with pytest.raises(ValueError):
            store.load(path)
    finally:
        store.close()
