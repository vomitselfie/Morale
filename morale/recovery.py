"""Per-window recovery snapshots guarded against concurrent live sessions."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import uuid

from PySide6.QtCore import QLockFile

from .model import Project


class RecoveryStore:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.snapshot = self.root / f"{uuid.uuid4().hex}.recovery.json"
        self.lock = self._lock(self.snapshot)
        if not self.lock.tryLock(0):
            raise OSError("Could not reserve a recovery session.")
        self.closed = False

    @staticmethod
    def _lock(path):
        lock = QLockFile(str(path) + ".lock")
        lock.setStaleLockTime(0)  # Age alone must never invalidate a live session.
        return lock

    def write(self, project, source_path=None):
        if self.closed:
            raise OSError("Recovery session is closed.")
        record = {"version": 1, "name": project.name, "updated": datetime.now(timezone.utc).isoformat(),
                  "source_path": str(source_path) if source_path else None, "project": project.dumps()}
        payload = json.dumps(record, ensure_ascii=False).encode("utf-8")
        if len(payload) > 64_000_000:
            raise ValueError("Recovery snapshot exceeds 64 MB; save the project explicitly.")
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="wb", dir=self.root, suffix=".tmp", delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.snapshot)
        finally:
            if temporary:
                temporary.unlink(missing_ok=True)

    def clear(self):
        self.snapshot.unlink(missing_ok=True)

    def close(self, discard=True):
        if self.closed:
            return
        try:
            if discard:
                self.clear()
        finally:
            self.lock.unlock()
            self.closed = True

    def _path(self, path):
        path = Path(path)
        if path.parent.resolve() != self.root.resolve() or not path.name.endswith(".recovery.json") or path.is_symlink():
            raise ValueError("Invalid recovery location.")
        return path

    def _read(self, path):
        if path.stat().st_size > 64_000_000:
            raise ValueError("Recovery file exceeds 64 MB.")
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except RecursionError as exc:
            raise ValueError("Recovery record nesting exceeds the supported limit.") from exc
        if not isinstance(record, dict) or type(record.get("version")) is not int or record.get("version") != 1 or not isinstance(record.get("project"), str) or not isinstance(record.get("name"), str) or not isinstance(record.get("updated"), str):
            raise ValueError("Invalid recovery record.")
        if len(record["name"]) > 200 or len(record["updated"]) > 100:
            raise ValueError("Invalid recovery metadata.")
        return record

    def available(self):
        entries = []
        for path in sorted(self.root.glob("*.recovery.json")):
            if path == self.snapshot or path.is_symlink():
                continue
            lock = self._lock(path)
            if not lock.tryLock(0):
                continue
            try:
                try:
                    record = self._read(path)
                    entries.append({"path": path, "name": record["name"], "updated": record["updated"], "error": ""})
                except (OSError, ValueError) as exc:
                    entries.append({"path": path, "name": path.name, "updated": "", "error": str(exc)})
            finally:
                lock.unlock()
        return entries

    def load(self, path):
        path = self._path(path)
        lock = self._lock(path)
        if not lock.tryLock(0):
            raise ValueError("That recovery belongs to an active session.")
        try:
            try:
                return Project.loads(self._read(path)["project"])
            except RecursionError as exc:
                raise ValueError("Recovery project nesting exceeds the supported limit.") from exc
        finally:
            lock.unlock()

    def discard(self, path):
        path = self._path(path)
        lock = self._lock(path)
        if not lock.tryLock(0):
            raise ValueError("Cannot discard another active session's recovery.")
        try:
            path.unlink(missing_ok=True)
        finally:
            lock.unlock()
