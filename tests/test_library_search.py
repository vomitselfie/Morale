import time
import pytest
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from PySide6.QtCore import QProcess
from morale.library_search import find_designs
from morale.library import LibraryDialog,SearchRunner
from morale.model import Project,DesignObject

@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])

def wait(predicate):
    end=time.monotonic()+10
    while not predicate() and time.monotonic()<end:QTest.qWait(10)
    assert predicate()

def files(root):
    (root/'Flowers').mkdir();(root/'Flowers'/'Nested').mkdir()
    project=Project(objects=[DesignObject(kind='rectangle',width=5,height=5)])
    project.save(root/'Flowers'/'Rose.morale');project.save(root/'Flowers'/'Nested'/'Blue Rose.morale')
    (root/'Flowers'/'rose.txt').write_text('not embroidery')
    (root/'Flowers'/'unreadable-content.PES').write_bytes(b'not a real design')

def test_nested_case_insensitive_path_search_never_decodes_files(tmp_path):
    files(tmp_path)
    result=find_designs(tmp_path,'flowers')
    assert len(result['matches'])==3 and result['complete']
    assert len(find_designs(tmp_path,'ROSE')['matches'])==2
    assert len(find_designs(tmp_path,'unreadable-content')['matches'])==1

def test_hidden_entries_and_symlinks_are_not_traversed(tmp_path):
    (tmp_path/'.hidden').mkdir();(tmp_path/'.hidden'/'rose.morale').write_text('hidden')
    (tmp_path/'visible.morale').write_text('visible')
    try:(tmp_path/'link').symlink_to(tmp_path,target_is_directory=True)
    except OSError:pass
    result=find_designs(tmp_path,'morale')
    assert result['matches']==['visible.morale']

def test_result_and_entry_limits_are_explicit(tmp_path):
    for i in range(5):(tmp_path/f'rose{i}.pes').write_text('invalid but searchable')
    result=find_designs(tmp_path,'rose',limit=2)
    assert not result['complete'] and len(result['matches'])==2
    result=find_designs(tmp_path,'rose',entry_limit=1)
    assert not result['complete'] and result['entries_examined']==1

@pytest.mark.parametrize('query',['',' '*3,'x'*201,None])
def test_invalid_queries_rejected(tmp_path,query):
    with pytest.raises(ValueError):find_designs(tmp_path,query)

def test_native_search_preview_open_and_folder_view(tmp_path):
    files(tmp_path);dialog=LibraryDialog(folder=str(tmp_path));dialog.show()
    try:
        dialog.search.setText('rose');dialog.search_subfolders()
        wait(lambda:dialog.results.count()==2)
        assert dialog.file_views.currentIndex()==1 and '2 designs found' in dialog.search_status.text()
        dialog.results.setCurrentRow(1)
        wait(lambda:dialog.preview_path is not None)
        expected=Path(tmp_path)/dialog.results.currentItem().text()
        assert Path(dialog.preview_path)==expected and dialog.open_button.isEnabled()
        dialog.refresh_preview();wait(lambda:dialog.preview_path is not None)
        dialog.open_selected();assert Path(dialog.selected_path)==expected
    finally:dialog.close()

def test_search_cancel_and_folder_change_stop_worker(tmp_path):
    files(tmp_path);dialog=LibraryDialog(folder=str(tmp_path))
    try:
        dialog.search.setText('rose');dialog.search_subfolders();dialog.cancel_search()
        assert dialog.search_runner.path is None and dialog.search_runner.process.state()==QProcess.ProcessState.NotRunning
        dialog.search_subfolders();dialog.set_folder(tmp_path/'Flowers')
        assert dialog.search_runner.path is None and dialog.results.count()==0 and dialog.file_views.currentIndex()==0
        dialog.search.setText('rose');dialog.search_subfolders();dialog.folder_view()
        assert dialog.search_runner.path is None and dialog.file_views.currentIndex()==0
    finally:dialog.close()

def test_search_runner_subprocess_result_and_cleanup(tmp_path):
    files(tmp_path);runner=SearchRunner();runner.query='rose';results=[];runner.found.connect(results.append)
    try:
        runner.load(tmp_path);directory=Path(runner.directory.name)
        wait(lambda:bool(results))
        assert len(results[0]['matches'])==2 and not directory.exists()
    finally:runner.cancel()
