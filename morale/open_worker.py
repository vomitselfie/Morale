"""Decode a design file in a separate process so the window stays responsive."""
import json
from pathlib import Path
import sys

from .model import Project

MAX_PROJECT_BYTES = 50_000_000


def decode(path):
    """A Morale project or machine file as (project, notes)."""
    path = Path(path)
    if path.suffix.lower() == ".morale":
        if path.stat().st_size > MAX_PROJECT_BYTES:
            raise ValueError("Project files are limited to 50 MB.")
        return Project.loads(path.read_text(encoding="utf-8")), []
    from .formats import import_machine
    result = import_machine(path)
    return result.project, list(result.notes)


def worker_main(args):
    if len(args) != 2:
        return 2
    source, output = Path(args[0]), Path(args[1])
    try:
        before = source.stat()
        project, notes = decode(source)
        after = source.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError("The file changed while it was being read. Try again.")
        result = {"project": project.dumps(), "notes": notes, "size": after.st_size, "mtime_ns": after.st_mtime_ns}
        (output / "open.json").write_text(json.dumps(result), encoding="utf-8")
        return 0
    except Exception as exc:
        (output / "preview.error.json").write_text(json.dumps({"error": str(exc)[:8192]}), encoding="utf-8")
        return 1


def read_open_result(root, path):
    """Validate the worker's project and confirm the file is unchanged since."""
    result_file = Path(root) / "open.json"
    if result_file.stat().st_size > 2 * MAX_PROJECT_BYTES:
        raise ValueError("Decoded design exceeds the supported size.")
    data = json.loads(result_file.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("project"), str) or not isinstance(data.get("notes"), list) \
            or any(not isinstance(note, str) for note in data["notes"]):
        raise ValueError("The open worker returned invalid data.")
    current = Path(path).stat()
    if (current.st_size, current.st_mtime_ns) != (data.get("size"), data.get("mtime_ns")):
        raise ValueError("The file changed after it was read. Open it again.")
    return Project.loads(data["project"]), data["notes"]


def make_runner(parent=None):
    from .library import PreviewRunner

    class OpenRunner(PreviewRunner):
        def command(self, path, directory):
            if getattr(sys, "frozen", False):
                return sys.executable, ["--open-worker", path, directory]
            return sys.executable, ["-m", "morale.open_worker", path, directory]

        def read_result(self, root):
            return read_open_result(root, self.opening), None

        def load(self, path):
            self.opening = str(Path(path).resolve())
            super().load(path)

        def timeout(self):
            path = self.path
            self.cancel()
            if path:
                self.failed.emit(path, "Opening timed out after 60 seconds. The file was not opened.")

    return OpenRunner(parent, timeout_ms=60_000)


if __name__ == "__main__":
    sys.exit(worker_main(sys.argv[1:]))
