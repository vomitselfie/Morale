from copy import deepcopy
import time
import pytest
from PySide6.QtGui import QImage,QPainter,QColor
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from morale.app import MainWindow
from morale.trace_dialog import TraceDialog
from morale.model import Project
from morale.reference import decode_reference,import_reference
from morale.engine import generate


@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])


def artwork(tmp_path):
    image=QImage(127,63,QImage.Format.Format_RGB32);image.fill(QColor('white'))
    painter=QPainter(image);painter.fillRect(10,8,20,40,QColor('red'));painter.end()
    path=tmp_path/'offset.png';image.save(str(path));return path


def preview(dialog):
    dialog.generate();deadline=time.monotonic()+10
    while dialog.project is None and time.monotonic()<deadline:QTest.qWait(10)
    assert dialog.project is not None,dialog.status.text()


def test_sampled_reference_uses_original_physical_page_size_and_survives_source_move(tmp_path):
    path=artwork(tmp_path);original=path.read_bytes();dialog=TraceDialog(str(path));window=MainWindow()
    try:
        dialog.width.setValue(40);dialog.resolution.setCurrentIndex(0)
        assert dialog.keep_reference.isChecked();preview(dialog)
        ref=dialog.project.reference
        assert (ref['x'],ref['y'],ref['width'],ref['height'])==pytest.approx((0,0,40,40*63/127))
        assert decode_reference(ref).size().width()==64
        assert path.read_bytes()==original
        unreferenced=deepcopy(dialog.project);unreferenced.reference={}
        assert generate(unreferenced)==generate(dialog.project)
        before=window.project.dumps();window.apply_raster_trace(dialog.project)
        assert window.project.reference==ref and not window.canvas.reference_image.isNull()
        saved=tmp_path/'with-source.morale';window.project.save(saved)
        path.rename(tmp_path/'moved-source.png')
        reopened=Project.loads(saved.read_text());assert not decode_reference(reopened.reference).isNull()
        window.undo();assert window.project.dumps()==before
    finally:dialog.close();window.saved=window.project.dumps();window.close()


def test_existing_reference_is_kept_unless_replacement_is_selected(tmp_path):
    path=artwork(tmp_path);window=MainWindow()
    window.set_reference(import_reference(path,100,100));before=window.project.dumps()
    dialog=TraceDialog(str(path),window)
    try:
        assert not dialog.keep_reference.isChecked() and 'Replace existing' in dialog.keep_reference.text()
        preview(dialog);assert dialog.project.reference=={}
        window.apply_raster_trace(dialog.project)
        assert window.project.reference==Project.loads(before).reference
        window.undo();assert window.project.dumps()==before
        dialog.keep_reference.setChecked(True);assert dialog.project is None
        preview(dialog);window.apply_raster_trace(dialog.project)
        assert window.project.reference==dialog.project.reference
        assert window.project.reference!=Project.loads(before).reference
        window.undo();assert window.project.dumps()==before
    finally:dialog.close();window.saved=window.project.dumps();window.close()


def test_invalid_incoming_reference_rejects_objects_atomically(tmp_path):
    window=MainWindow();source=deepcopy(window.project)
    source.reference=import_reference(artwork(tmp_path),100,100);source.reference['png']='invalid'
    before=window.project.dumps()
    try:
        with pytest.raises(ValueError):window.apply_raster_trace(source)
        assert window.project.dumps()==before
    finally:window.saved=window.project.dumps();window.close()
