import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from copy import deepcopy
import base64
import struct

import pytest
from PySide6.QtGui import QImage, QColor
from PySide6.QtWidgets import QApplication

from morale.app import MainWindow
from morale.reference import import_reference, decode_reference, validate_reference
from morale.reference_dialog import ReferenceDialog
from morale.model import Project, demo_project
from morale.engine import generate
from morale.formats import to_pattern


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def raster(tmp_path, app):
    path = tmp_path / "art.png"
    image = QImage(200, 100, QImage.Format.Format_ARGB32)
    image.fill(QColor("#da8c73"))
    assert image.save(str(path))
    return path


def test_embedded_reference_survives_source_removal(raster):
    reference = import_reference(raster, 100, 100)
    assert reference["width"] == 80
    assert reference["height"] == 40
    project = Project(reference=reference)
    saved = project.dumps()
    raster.unlink()
    loaded = Project.loads(saved)
    assert decode_reference(loaded.reference).size().width() == 200
    assert loaded.reference == reference


def test_reference_cannot_change_machine_commands(raster):
    project = demo_project()
    original = to_pattern(project).stitches
    project.reference = import_reference(raster, 100, 100)
    project.reference.update(x=999, y=999, rotation=90)
    assert to_pattern(project).stitches == original
    assert generate(Project(reference=project.reference)) == []


def test_reference_changes_undo_and_bad_replacement_is_atomic(raster, app):
    window = MainWindow()
    before = window.project.dumps()
    window.set_reference(import_reference(raster, 100, 100))
    assert window.canvas.reference_image.width() == 200
    window.undo()
    assert window.project.dumps() == before
    window.redo()
    with_reference = window.project.dumps()
    damaged = deepcopy(window.project.reference)
    damaged["png"] = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + struct.pack(">II", 20, 20)).decode()
    with pytest.raises(ValueError):
        window.replace_project(Project(reference=damaged))
    assert window.project.dumps() == with_reference
    window.saved = with_reference
    window.close()


def test_reference_dialog_precision_and_properties(raster, app):
    reference = import_reference(raster, 100, 100)
    reference["width"] = 32.123456
    dialog = ReferenceDialog(reference)
    assert dialog.result_reference() == reference
    dialog.fields["opacity"].setValue(.2)
    dialog.visible.setChecked(False)
    assert dialog.result_reference()["opacity"] == .2
    assert dialog.result_reference()["visible"] is False


@pytest.mark.parametrize("key,value", [("png", "bad encoding"), ("opacity", 2), ("width", float("nan")), ("visible", "yes")])
def test_invalid_reference_rejected(raster, key, value):
    reference = import_reference(raster, 100, 100)
    reference[key] = value
    with pytest.raises(ValueError):
        validate_reference(reference)


def test_oversized_embedded_dimensions_rejected(raster):
    reference = import_reference(raster, 100, 100)
    raw = bytearray(base64.b64decode(reference["png"]))
    raw[16:20] = struct.pack(">I", 100_000)
    reference["png"] = base64.b64encode(raw).decode()
    with pytest.raises(ValueError, match="4096"):
        validate_reference(reference)


def test_unsupported_image_type_rejected(tmp_path):
    path = tmp_path / "art.svg"
    path.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20"/>')
    with pytest.raises(ValueError, match="raster"):
        import_reference(path, 100, 100)


def test_history_has_count_and_memory_limits():
    history = ["x"] * 101
    MainWindow.limit_history(history)
    assert len(history) == 100
    history = ["x" * (17 * 1024 * 1024), "y" * (17 * 1024 * 1024)]
    MainWindow.limit_history(history)
    assert len(history) == 1


@pytest.mark.parametrize("extension", ["png", "jpg", "bmp", "webp"])
def test_supported_raster_readers(tmp_path, extension, app):
    image = QImage(80, 40, QImage.Format.Format_RGB32)
    image.fill(QColor("#32a076"))
    path = tmp_path / f"art.{extension}"
    assert image.save(str(path))
    result = import_reference(path, 100, 100)
    assert decode_reference(result).size().width() == 80
