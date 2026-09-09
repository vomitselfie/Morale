import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from morale.app import MainWindow
from morale.model import Project
from morale.formats import export_machine


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(app):
    widget = MainWindow()
    widget.show()
    app.processEvents()
    yield widget
    widget.saved = widget.project.dumps()
    widget.close()


def test_edit_undo_redo_and_duplicate(window):
    obj = window.selected_object()
    original_width = obj.width
    window.fields["width"].setValue(22)
    assert window.selected_object().width == 22
    window.undo()
    assert window.selected_object().width == original_width
    window.redo()
    assert window.selected_object().width == 22
    before = len(window.project.objects)
    window.duplicate()
    assert len(window.project.objects) == before + 1
    window.delete()
    assert len(window.project.objects) == before


def test_draw_on_native_canvas_and_playback(window, app):
    window.replace_project(Project())
    window.set_mode("rectangle")
    canvas = window.canvas
    center = canvas.rect().center()
    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, pos=center - QPoint(50, 50))
    QTest.mouseMove(canvas, center + QPoint(50, 50))
    QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, pos=center + QPoint(50, 50))
    app.processEvents()
    assert len(window.project.objects) == 1
    assert window.project.objects[0].kind == "rectangle"
    assert window.blocks[0].stitches
    window.play()
    window.tick()
    assert window.canvas.playhead == 25
    window.reset_playback()
    assert window.canvas.playhead is None


def test_project_save_open_and_cancel(window, tmp_path, monkeypatch):
    path = tmp_path / "native.morale"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **kw: (str(path), "Morale project (*.morale)"))
    assert window.save()
    window.update_property("width", 42)
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **kw: QMessageBox.StandardButton.Cancel)
    assert not window.confirm_discard()
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **kw: QMessageBox.StandardButton.Discard)
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **kw: (str(path), ""))
    window.open()
    assert window.project.dumps() == path.read_text()
    assert not window.history


def test_selection_does_not_modify_project(window):
    before = window.project.dumps()
    for obj in window.project.objects:
        window.select(obj.id)
    assert window.project.dumps() == before
    assert not window.history


def test_reorder_and_hidden_objects(window):
    first = window.project.objects[0]
    window.select(first.id)
    window.reorder(1)
    assert window.project.objects[1].id == first.id
    window.update_property("visible", False)
    assert first.id not in {b.object_id for b in window.blocks}
    window.undo()
    assert first.id in {b.object_id for b in window.blocks}


def test_corrected_extension_does_not_overwrite_without_confirmation(window, tmp_path, monkeypatch):
    existing = tmp_path / "keep.morale"
    existing.write_text("Keep this file")
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **kw: (str(tmp_path / "keep.txt"), ""))
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **kw: QMessageBox.StandardButton.No)
    assert window.save() is False
    assert existing.read_text() == "Keep this file"


def test_native_import_merge_undo_and_manual_controls(window, tmp_path, monkeypatch):
    path = tmp_path / "merge.pes"
    export_machine(window.project, path)
    count = len(window.project.objects)
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **kw: (str(path), ""))
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **kw: None)
    window.import_design()
    assert len(window.project.objects) == count + 4
    assert window.selected_object().kind == "stitches"
    assert not window.stitch_type.isEnabled()
    assert not window.fields["stitch_length"].isEnabled()
    window.undo()
    assert len(window.project.objects) == count
    window.redo()
    assert len(window.project.objects) == count + 4


def test_open_machine_file_never_saves_over_original(window, tmp_path, monkeypatch):
    path = tmp_path / "original.dst"
    export_machine(window.project, path)
    original = path.read_bytes()
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **kw: (str(path), ""))
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **kw: None)
    window.open()
    assert window.file_path is None
    assert window.project.dumps() != window.saved
    assert all(o.kind == "stitches" for o in window.project.objects)
    assert path.read_bytes() == original


def test_native_satin_drawing_point_edit_and_undo(window, app):
    window.replace_project(Project())
    window.set_mode("satin")
    center = window.canvas.rect().center()
    for offset in [QPoint(-20, -60), QPoint(20, -60), QPoint(-35, 60), QPoint(35, 60)]:
        QTest.mouseClick(window.canvas, Qt.MouseButton.LeftButton, pos=center + offset)
    QTest.keyClick(window.canvas, Qt.Key.Key_Return)
    app.processEvents()
    obj = window.selected_object()
    assert obj.kind == "satin"
    assert obj.stitch_type == "satin"
    assert window.fields["satin_max"].isEnabled()
    assert not window.fields["angle"].isEnabled()
    before = window.project.dumps()
    window.replace_points([(-2, -10), (2, -10), (-3, 10), (3, 10)])
    assert window.selected_object().width == 6
    window.undo()
    assert window.project.dumps() == before


def test_invalid_point_edit_does_not_mutate_project(window):
    window.add_shape("satin", [(-2, -10), (2, -10), (-2, 10), (2, 10)])
    before = window.project.dumps()
    with pytest.raises(ValueError):
        window.replace_points([(-2, -10), (2, -10), (2, 10), (-2, 10)])
    assert window.project.dumps() == before


def test_triple_run_and_finishing_controls_work_in_native_ui(window):
    window.select(window.project.objects[0].id)
    count = len(window.blocks[0].stitches)
    window.stitch_type.setCurrentIndex(window.stitch_type.findData("triple"))
    assert window.selected_object().stitch_type == "triple"
    assert len(window.blocks[0].stitches) > count * 2
    window.finishing["trim_after"].setChecked(True)
    assert window.blocks[0].stitches[-1].command == "trim"


def test_stitch_edit_conversion_undo_and_validation(window):
    before = window.project.dumps()
    window.replace_stitches([[0, 0, "jump"], [10, 5, "stitch"], [10, 5, "trim"], [10, 5, "stop"]])
    assert window.selected_object().kind == "stitches"
    assert window.blocks[-1].stitches[-1].command == "stop"
    modified = window.project.dumps()
    window.undo()
    assert window.project.dumps() == before
    window.redo()
    assert window.project.dumps() == modified
    with pytest.raises(ValueError):
        window.replace_stitches([[1, 2, "stitch"]])
    assert window.project.dumps() == modified


def test_thread_metadata_edits_and_recolor_undo(window):
    window.update_thread("brand", "Example")
    window.update_thread("catalog_number", "0012")
    assert window.selected_object().thread["catalog_number"] == "0012"
    window.update_property("color", "#abcdef")
    assert window.selected_object().thread == {}
    window.undo()
    assert window.selected_object().thread == {"brand": "Example", "catalog_number": "0012"}


def test_lettering_add_edit_and_undo(window):
    from morale.lettering import make_lettering
    from PySide6.QtGui import QFont
    before = window.project.dumps()
    obj = make_lettering("MOM", QFont().family(), 15)
    window.apply_lettering(obj)
    assert window.selected_object().lettering["text"] == "MOM"
    changed = make_lettering("MUM", obj.lettering["family"], 18, previous=obj)
    window.apply_lettering(changed, replace=True)
    assert window.selected_object().lettering["text"] == "MUM"
    window.undo()
    assert window.selected_object().lettering["text"] == "MOM"
    window.undo()
    assert window.project.dumps() == before


def test_arrange_undo_and_point_edit_after_mirroring(window):
    before = window.project.dumps()
    window.arrange_object("mirror", "horizontal")
    assert window.selected_object().flip_x
    window.undo()
    assert window.project.dumps() == before
    obj = window.project.objects[0]
    window.select(obj.id)
    window.arrange_object("mirror", "vertical")
    window.replace_points([(0, 0), (5, 10)])
    assert window.selected_object().outline() == [(0, 0), (5, 10)]


def test_native_applique_creation_and_undo(window):
    before = window.project.dumps()
    window.apply_applique(2)
    assert len(window.project.objects) == 12
    assert window.selected_object().name.startswith("Placement")
    assert window.selected_object().stop_after
    assert "place" in window.layers.currentItem().toolTip()
    window.undo()
    assert window.project.dumps() == before
