import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import json

import pytest
from PySide6.QtCore import QMimeData
from PySide6.QtWidgets import QApplication

from morale.app import MainWindow
from morale.clipboard import MIME_TYPE, encode_objects, decode_objects
from morale.model import DesignObject, Project, satin_sample
from morale.engine import generate


@pytest.fixture
def window():
    app = QApplication.instance() or QApplication([])
    widget = MainWindow()
    widget.show()
    widget.canvas.setFocus()
    app.processEvents()
    yield widget
    QApplication.clipboard().clear()
    focused = QApplication.focusWidget()
    if focused and widget.isAncestorOf(focused):
        focused.clearFocus()
    widget.saved = widget.project.dumps()
    widget.close()


def test_payload_preserves_geometry_and_assigns_fresh_ids():
    original = satin_sample().objects
    restored = decode_objects(encode_objects(original))
    assert {o.id for o in original}.isdisjoint(o.id for o in restored)
    before = generate(Project(objects=original))
    after = generate(Project(objects=restored))
    assert [b.stitches for b in before] == [b.stitches for b in after]
    assert [o.thread for o in restored] == [o.thread for o in original]


@pytest.mark.parametrize("payload", [b"", b"not json", b"[]", b"\xff", Project().dumps().encode()])
def test_invalid_payloads_rejected(payload):
    with pytest.raises(ValueError):
        decode_objects(payload)


def test_copy_paste_cut_and_undo_in_native_window(window):
    obj = window.selected_object()
    original = window.project.dumps()
    assert window.copy_selection()
    assert QApplication.clipboard().mimeData().hasFormat(MIME_TYPE)
    window.paste_selection()
    assert len(window.project.objects) == 11
    assert window.selected_object().id != obj.id
    assert window.selected_object().outline() == obj.outline()
    window.undo()
    assert window.project.dumps() == original
    window.select(obj.id)
    window.canvas.setFocus()
    window.cut_selection()
    assert len(window.project.objects) == 9
    window.undo()
    assert window.project.dumps() == original


def test_paste_across_native_windows(window):
    source = window.selected_object()
    assert window.copy_selection()
    target = MainWindow()
    target.replace_project(Project())
    target.show()
    target.activateWindow()
    target.canvas.setFocus()
    QApplication.processEvents()
    target.paste_selection()
    assert len(target.project.objects) == 1
    assert target.project.objects[0].id != source.id
    assert target.project.objects[0].outline() == source.outline()
    target.saved = target.project.dumps()
    target.close()


def test_text_field_clipboard_does_not_cut_design_object(window):
    before = window.project.dumps()
    window.title_edit.setFocus()
    window.title_edit.selectAll()
    QApplication.processEvents()
    window.copy_selection()
    assert QApplication.clipboard().text() == window.project.name
    assert not QApplication.clipboard().mimeData().hasFormat(MIME_TYPE)
    window.cut_selection()
    assert window.title_edit.text() == ""
    assert window.project.dumps() == before


def test_invalid_and_excessive_paste_are_atomic(window):
    before = window.project.dumps()
    with pytest.raises(ValueError):
        window.paste_objects(b"bad")
    assert window.project.dumps() == before
    payload = encode_objects([DesignObject() for _ in range(500)])
    with pytest.raises(ValueError, match="500"):
        window.paste_objects(payload)
    assert window.project.dumps() == before
