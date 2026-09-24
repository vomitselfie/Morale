import time
import pytest
from PySide6.QtCore import QProcess
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from morale.library import LibraryDialog
from morale.model import Project,DesignObject

@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])

def wait(predicate):
    end=time.monotonic()+12
    while not predicate() and time.monotonic()<end:QTest.qWait(10)
    assert predicate()

def populate(root,count):
    for i in range(count):Project(objects=[DesignObject(kind='rectangle',width=5,height=5)]).save(root/f'design-{i:03}.morale')

def show(dialog,names):
    dialog.show();dialog.file_views.setCurrentIndex(1);dialog.results.addItems(names)
    dialog.thumbnail_button.setChecked(True);QApplication.processEvents()

def test_only_visible_tiles_are_decoded_and_scrolling_loads_more(tmp_path):
    populate(tmp_path,30);dialog=LibraryDialog(folder=str(tmp_path))
    try:
        show(dialog,[f'design-{i:03}.morale' for i in range(30)])
        visible=set(dialog.thumbnails.visible_rows());assert len(visible)<30
        wait(lambda:all(i in dialog.thumbnails.cache for i in visible))
        assert set(dialog.thumbnails.cache)<=visible
        assert all(not dialog.results.item(i).icon().isNull() for i in visible)
        assert dialog.preview_path is None
        dialog.results.scrollToItem(dialog.results.item(29));QApplication.processEvents()
        wait(lambda:29 in dialog.thumbnails.cache)
        assert 'stitches' in dialog.results.item(29).toolTip()
        dialog.results.setCurrentRow(29);wait(lambda:dialog.preview_path is not None)
        assert dialog.open_button.isEnabled()
    finally:dialog.close()

def test_bad_file_does_not_block_later_thumbnails(tmp_path):
    (tmp_path/'a.morale').write_text('invalid');populate(tmp_path,1)
    dialog=LibraryDialog(folder=str(tmp_path))
    try:
        show(dialog,['a.morale','design-000.morale'])
        wait(lambda:len(dialog.thumbnails.cache)==2)
        assert 'unavailable' in dialog.results.item(0).toolTip()
        assert 'stitches' in dialog.results.item(1).toolTip()
    finally:dialog.close()

def test_toggle_folder_change_and_close_cancel_loader(tmp_path):
    populate(tmp_path,1);dialog=LibraryDialog(folder=str(tmp_path))
    try:
        show(dialog,['design-000.morale']);dialog.thumbnail_button.setChecked(False)
        assert dialog.thumbnails.runner.path is None and not dialog.thumbnails.timer.isActive()
        dialog.thumbnail_button.setChecked(True);dialog.folder_view()
        assert dialog.thumbnails.runner.path is None
        dialog.set_folder(tmp_path);assert not dialog.thumbnails.cache
        dialog.close()
        assert dialog.thumbnails.runner.process.state()==QProcess.ProcessState.NotRunning
    finally:dialog.close()

def test_changed_file_refreshes_thumbnail(tmp_path):
    populate(tmp_path,1);dialog=LibraryDialog(folder=str(tmp_path))
    try:
        show(dialog,['design-000.morale']);wait(lambda:0 in dialog.thumbnails.cache)
        old=dialog.thumbnails.cache[0]
        Project(objects=[DesignObject(kind='ellipse',width=18,height=12)]).save(tmp_path/'design-000.morale')
        dialog.thumbnails.schedule();wait(lambda:dialog.thumbnails.cache.get(0)!=old)
        assert 'stitches' in dialog.results.item(0).toolTip()
    finally:dialog.close()

def test_cache_eviction_removes_old_icons(tmp_path):
    dialog=LibraryDialog(folder=str(tmp_path))
    try:
        dialog.results.addItems([str(i) for i in range(201)])
        for i in range(201):dialog.thumbnails.remember(i,(str(i),(1,1)))
        assert len(dialog.thumbnails.cache)==200 and 0 not in dialog.thumbnails.cache
    finally:dialog.close()
