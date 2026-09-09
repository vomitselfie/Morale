"""Isolated, cancellable machine-file conversion with no-overwrite publication."""
import json
import ctypes
import errno
import os
from pathlib import Path
import sys

from PySide6.QtCore import QObject, QProcess, QTemporaryDir, QTimer, Signal

from .formats import EXPORT_FORMATS, export_machine, export_notes, import_machine


def worker_main(arguments):
    """Worker only writes staging data; the parent owns final publication."""
    if len(arguments) != 3:
        return 1
    source, staged, version = arguments
    try:
        imported = import_machine(source)
        export_machine(imported.project, staged, pes_version=int(version))
        result = {"notes": imported.notes + export_notes(Path(staged).suffix.lower(), int(version))}
        code = 0
    except Exception as exc:
        result = {"error": str(exc)}
        code = 1
    try:
        # Windowed Windows bundles can have sys.stdout=None, even when launched
        # as workers. A private result file keeps the protocol console-independent.
        Path(staged + ".result.json").write_text(json.dumps(result), encoding="utf-8")
    except OSError:
        return 1
    return code


def publish(staged, target):
    """Atomically publish a complete file, failing if any destination exists.

    Staging is on the destination filesystem. Use hard links where supported,
    otherwise a platform exclusive-rename operation (for removable media too).
    """
    try:
        os.link(staged, target)
    except FileExistsError:
        raise
    except OSError:
        exclusive_rename(staged, target)


def exclusive_rename(staged, target):
    if sys.platform == "win32":
        # Python's Windows rename always refuses an existing destination.
        os.rename(staged, target)
        return
    libc = ctypes.CDLL(None, use_errno=True)
    source_bytes, target_bytes = os.fsencode(staged), os.fsencode(target)
    if sys.platform.startswith("linux") and hasattr(libc, "renameat2"):
        function = libc.renameat2
        function.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        function.restype = ctypes.c_int
        result = function(-100, source_bytes, -100, target_bytes, 1)  # AT_FDCWD, RENAME_NOREPLACE
    elif sys.platform == "darwin" and hasattr(libc, "renamex_np"):
        function = libc.renamex_np
        function.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        function.restype = ctypes.c_int
        result = function(source_bytes, target_bytes, 4)  # RENAME_EXCL
    else:
        raise OSError(errno.ENOTSUP, "Exclusive rename is not available on this platform")
    if result:
        number = ctypes.get_errno()
        raise OSError(number, os.strerror(number), str(target))


class ConversionQueue(QObject):
    result = Signal(object)
    progress = Signal(int, int)
    finished = Signal()

    def __init__(self, parent=None, timeout_ms=60_000):
        super().__init__(parent)
        self.timeout_ms = timeout_ms
        self.running = False
        self.process = None
        self.scratch = None
        self.results = []
        self.jobs = []
        self.index = 0
        self.cancelled = False
        self.timed_out = False
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._timeout)

    def start(self, sources, output, extension, pes_version=6):
        if self.running:
            raise ValueError("A conversion queue is already running.")
        if not str(output).strip():
            raise ValueError("Choose an output folder.")
        output = Path(output).resolve()
        extension = "." + extension.lower().lstrip(".")
        if extension not in EXPORT_FORMATS or pes_version not in {1, 6}:
            raise ValueError("Choose a supported format/version.")
        if not output.is_dir():
            raise ValueError("Choose an existing output folder.")
        if not sources or len(sources) > 500:
            raise ValueError("Choose between 1 and 500 source files.")
        self.jobs = [{"source": str(Path(source).resolve()), "target": str(output / (Path(source).stem + extension))} for source in sources]
        counts = {}
        for job in self.jobs:
            key = job["target"].casefold()
            counts[key] = counts.get(key, 0) + 1
        for job in self.jobs:
            if counts[job["target"].casefold()] > 1:
                job["skip"] = "Multiple inputs have the same output name; rename them or convert separately."
        self.version = pes_version
        self.output = output
        self.extension = extension
        self.results = []
        self.index = 0
        self.cancelled = False
        self.running = True
        self.progress.emit(0, len(self.jobs))
        QTimer.singleShot(0, self._next)

    def _record(self, status, message="", notes=None):
        job = self.jobs[self.index]
        row = {"source": job["source"], "target": job["target"], "status": status, "message": message, "notes": notes or []}
        self.results.append(row)
        self.index += 1
        self.result.emit(row)
        self.progress.emit(self.index, len(self.jobs))

    def _next(self):
        if not self.running:
            return
        while self.index < len(self.jobs):
            job = self.jobs[self.index]
            if self.cancelled:
                self._record("cancelled", "Cancelled before conversion.")
            elif "skip" in job:
                self._record("skipped", job["skip"])
            elif os.path.lexists(job["target"]):
                self._record("skipped", "Destination already exists; no file was replaced.")
            else:
                break
        if self.index == len(self.jobs):
            self.running = False
            self.finished.emit()
            return
        self.scratch = QTemporaryDir(str(self.output / ".morale-batch-XXXXXX"))
        if not self.scratch.isValid():
            self._record("failed", "Cannot create staging files in the output folder.")
            QTimer.singleShot(0, self._next)
            return
        staged = str(Path(self.scratch.path()) / ("converted" + self.extension))
        process = QProcess(self)
        self.process = process
        self.timed_out = False
        self.staged = staged
        process.finished.connect(lambda code, status, proc=process: self._done(proc, code))
        process.errorOccurred.connect(lambda error, proc=process: self._failed_start(proc, error))
        program, arguments = self.worker_command(job["source"], staged)
        if not getattr(sys, "frozen", False):
            process.setWorkingDirectory(str(Path(__file__).resolve().parent.parent))
        process.start(program, arguments)
        self.timer.start(self.timeout_ms)

    def worker_command(self, source, staged):
        arguments = ["--batch-worker"] if getattr(sys, "frozen", False) else ["-m", "morale.batch", "--worker"]
        return sys.executable, arguments + [source, staged, str(self.version)]

    def _failed_start(self, process, error):
        if error == QProcess.ProcessError.FailedToStart:
            self._done(process, -1)

    def _timeout(self):
        if self.process:
            self.timed_out = True
            self.process.kill()

    def cancel(self):
        self.cancelled = True
        if self.process:
            self.process.kill()

    def _done(self, process, code):
        if self.process is not process:
            return
        self.timer.stop()
        self.process = None
        try:
            report = Path(self.staged + ".result.json")
            if report.stat().st_size > 1_000_000:
                raise ValueError("Worker result exceeds the size limit.")
            payload = json.loads(report.read_text(encoding="utf-8"))
        except (ValueError, UnicodeError, OSError):
            payload = {}
        if self.cancelled:
            self._record("cancelled", "Worker cancelled; no staged file was published.")
        elif self.timed_out:
            self._record("failed", f"Reader/writer exceeded {self.timeout_ms / 1000:g} seconds; worker stopped.")
        elif code != 0 or not isinstance(payload, dict) or "notes" not in payload:
            message = payload.get("error", "Worker failed or returned an invalid result.") if isinstance(payload, dict) else "Invalid worker result."
            self._record("failed", message)
        else:
            try:
                publish(self.staged, self.jobs[self.index]["target"])
                self._record("converted", notes=payload["notes"])
            except FileExistsError:
                self._record("skipped", "Destination appeared during conversion; it was not replaced.")
            except OSError as exc:
                self._record("failed", f"Could not publish safely: {exc}. Try a local output folder, then copy completed files to the machine.")
        if self.scratch:
            self.scratch.remove()
            self.scratch = None
        process.deleteLater()
        QTimer.singleShot(0, self._next)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        raise SystemExit(worker_main(sys.argv[2:]))
    import argparse
    from PySide6.QtCore import QCoreApplication
    parser = argparse.ArgumentParser(description="Convert embroidery files without replacing existing destinations.")
    parser.add_argument("sources", nargs="+")
    parser.add_argument("--output", required=True)
    parser.add_argument("--format", required=True, choices=sorted(ext[1:] for ext in EXPORT_FORMATS))
    parser.add_argument("--pes-version", type=int, choices=[1, 6], default=6)
    args = parser.parse_args()
    app = QCoreApplication([])
    queue = ConversionQueue()
    queue.result.connect(lambda row: print(json.dumps(row), flush=True))
    queue.finished.connect(app.quit)
    try:
        queue.start(args.sources, args.output, args.format, args.pes_version)
    except ValueError as exc:
        parser.error(str(exc))
    app.exec()
    raise SystemExit(any(row["status"] != "converted" for row in queue.results))


if __name__ == "__main__":
    main()
