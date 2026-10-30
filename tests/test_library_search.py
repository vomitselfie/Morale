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

@pytest.mark.parametrize('query',['x'*201,None])
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


@pytest.mark.parametrize('query',['','   '])
def test_blank_query_lists_all_supported_designs_with_limits(tmp_path,query):
    files(tmp_path)
    result=find_designs(tmp_path,query)
    assert len(result['matches'])==3 and result['complete']
    assert all(not path.endswith('.txt') for path in result['matches'])
    limited=find_designs(tmp_path,query,limit=2)
    assert len(limited['matches'])==2 and not limited['complete']


def test_native_blank_search_lists_nested_designs(tmp_path):
    files(tmp_path);dialog=LibraryDialog(folder=str(tmp_path))
    try:
        assert not dialog.search.text()
        dialog.search_subfolders()
        wait(lambda:dialog.results.count()==3)
        assert 'in this folder and its subfolders' in dialog.search_status.text()
        assert dialog.file_views.currentIndex()==1
    finally:dialog.close()


def test_query_change_cancels_search_and_discards_late_results(tmp_path):
    files(tmp_path);dialog=LibraryDialog(folder=str(tmp_path))
    try:
        dialog.search.setText('rose');dialog.search_subfolders()
        dialog.search.setText('blue')
        assert dialog.search_runner.process.state()==QProcess.ProcessState.NotRunning
        assert dialog.search_runner.path is None
        dialog.show_search(find_designs(tmp_path,'rose'))
        assert dialog.results.count()==0 and not dialog.open_button.isEnabled()
        assert 'Query changed' in dialog.search_status.text()
        dialog.search_subfolders();wait(lambda:dialog.results.count()==1)
        assert 'Blue Rose' in dialog.results.item(0).text()
    finally:dialog.close()


def test_query_change_clears_completed_results_and_selected_preview(tmp_path):
    files(tmp_path);dialog=LibraryDialog(folder=str(tmp_path))
    try:
        dialog.search.setText('rose');dialog.search_subfolders()
        wait(lambda:dialog.results.count()==2)
        dialog.results.setCurrentRow(0);wait(lambda:dialog.preview_path is not None)
        dialog.search.clear()
        assert dialog.results.count()==0 and dialog.preview_path is None
        assert not dialog.open_button.isEnabled()
        dialog.search_subfolders();wait(lambda:dialog.results.count()==3)
    finally:dialog.close()


@pytest.mark.parametrize('query,count',[('rose',2),('',3)])
def test_enter_in_search_field_runs_recursive_search_without_default_action(tmp_path,query,count):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QPushButton
    files(tmp_path);dialog=LibraryDialog(folder=str(tmp_path));dialog.show()
    clicked=[]
    for button in dialog.findChildren(QPushButton):
        button.clicked.connect(lambda checked=False,b=button:clicked.append(b.text()))
    try:
        dialog.search.setText(query);dialog.search.setFocus()
        QTest.keyClick(dialog.search,Qt.Key.Key_Return)
        wait(lambda:dialog.results.count()==count)
        assert dialog.isVisible() and not clicked
        assert dialog.selected_path is None
        assert 'Enter searches' in dialog.search.accessibleDescription()
    finally:dialog.close()


@pytest.mark.parametrize('platform_activation',[True,False])
def test_enter_on_previewed_search_result_opens_design(tmp_path,platform_activation):
    from PySide6.QtCore import Qt
    files(tmp_path);dialog=LibraryDialog(folder=str(tmp_path));dialog.show()
    opened=[];dialog.accepted.connect(lambda:opened.append(dialog.selected_path))
    try:
        # macOS list views do not activate items with Return.
        if not platform_activation:dialog.results.itemActivated.disconnect()
        dialog.search.setText('blue');dialog.search_subfolders()
        wait(lambda:dialog.results.count()==1)
        dialog.results.setCurrentRow(0);wait(lambda:dialog.preview_path is not None)
        expected=dialog.preview_path
        dialog.results.setFocus();QTest.keyClick(dialog.results,Qt.Key.Key_Return)
        assert dialog.selected_path==expected and not dialog.isVisible()
        assert opened==[expected]
    finally:dialog.close()


def test_explicit_note_search_reads_only_native_notes(tmp_path):
    import json
    (tmp_path/'a.morale').write_text(json.dumps({'notes':'Linen & cotton\nStabilizer: woven'}))
    (tmp_path/'b.morale').write_text(json.dumps({'name':'linen','notes':'silk'}))
    (tmp_path/'linen.pes').write_bytes(b'linen')
    (tmp_path/'old.morale').write_text('{}')
    (tmp_path/'bad.morale').write_text('{bad')
    result=find_designs(tmp_path,'notes: LINEN')
    assert result['matches']==['a.morale'] and result['notes_search']
    assert result['unreadable_entries']==1 and result['complete']
    assert find_designs(tmp_path,'linen')['matches']==['linen.pes']


def test_note_search_budget_and_empty_query(tmp_path):
    (tmp_path/'large.morale').write_text('{"notes":"linen"}')
    result=find_designs(tmp_path,'notes: linen',metadata_byte_limit=5)
    assert not result['complete'] and result['matches']==[]
    assert result['metadata_bytes_read']==6
    with pytest.raises(ValueError,match='Enter text after notes:'):
        find_designs(tmp_path,'notes: ')


def test_native_note_search_returns_saved_project(tmp_path):
    path=tmp_path/'sample.morale'
    Project(objects=[DesignObject()],notes='Fabric: linen').save(path)
    before=path.read_bytes();dialog=LibraryDialog(folder=str(tmp_path))
    try:
        dialog.search.setText('notes: linen');dialog.search_subfolders()
        wait(lambda:dialog.results.count()==1)
        assert dialog.results.item(0).text()=='sample.morale'
        assert path.read_bytes()==before
    finally:dialog.close()


def test_oversized_project_does_not_prevent_other_note_matches(tmp_path):
    with (tmp_path/'huge.morale').open('wb') as stream:stream.truncate(20_000_001)
    (tmp_path/'small.morale').write_text('{"notes":"linen"}')
    result=find_designs(tmp_path,'notes: linen')
    assert result['matches']==['small.morale'] and result['complete']
    assert result['unreadable_entries']==1
    assert result['metadata_bytes_read']==(tmp_path/'small.morale').stat().st_size


@pytest.mark.parametrize('key,value',[('limit',0),('entry_limit',True),('metadata_byte_limit',-1)])
def test_invalid_search_limits_rejected(tmp_path,key,value):
    with pytest.raises(ValueError,match='positive integers'):find_designs(tmp_path,'',**{key:value})


def test_note_read_limit_has_actionable_native_status(tmp_path):
    (tmp_path/'sample.morale').write_text('{"notes":"linen"}')
    result=find_designs(tmp_path,'notes: linen',metadata_byte_limit=5)
    assert result['stop_reason']=='metadata_byte_limit'
    dialog=LibraryDialog(folder=str(tmp_path))
    try:
        dialog.search.setText(result['query']);dialog.show_search(result)
        assert 'Saved-note read limit reached; choose a smaller folder.' in dialog.search_status.text()
    finally:dialog.close()
