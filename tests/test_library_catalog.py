import time
import unicodedata
import subprocess
import shutil
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage,QColor
from PySide6.QtCore import QTimer
from morale.library_catalog import CatalogDialog,save_catalog
from morale.model import Project,DesignObject

@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])


def entry(index):
    image=QImage(200,200,QImage.Format.Format_RGB32);image.fill(QColor('white'))
    return {'path':f'/designs/design-{index}.morale','info':{'width':20,'height':10,'stitches':123,'colors':2},'image':image}


def test_paginated_catalog_and_failed_file(tmp_path):
    entries=[entry(i) for i in range(7)];entries[3]={'path':'/designs/broken.pes','error':'Invalid design'}
    path=tmp_path/'catalog.pdf';save_catalog(path,entries)
    assert path.read_bytes().startswith(b'%PDF-')
    if shutil.which('pdfinfo'):
        info=subprocess.check_output(['pdfinfo',str(path)],text=True)
        assert 'Pages:           3' in info
    if shutil.which('pdftotext'):
        text=unicodedata.normalize('NFKC',subprocess.check_output(['pdftotext','-layout',str(path),'-'],text=True))
        assert 'design-6.morale' in text and 'broken.pes' in text and 'Preview unavailable' in text
        assert '123 stitches' in text and 'not actual size' in text


def test_pdf_failure_keeps_existing_destination(tmp_path,monkeypatch):
    from PySide6.QtGui import QPdfWriter
    path=tmp_path/'catalog.pdf';path.write_bytes(b'original')
    monkeypatch.setattr(QPdfWriter,'newPage',lambda self:False)
    with pytest.raises(OSError):save_catalog(path,[entry(i) for i in range(7)])
    assert path.read_bytes()==b'original'


def test_real_preview_queue_remains_responsive_and_lists_failures(tmp_path,app):
    paths=[]
    for i in range(2):
        path=tmp_path/f'design-{i}.morale';Project(objects=[DesignObject()]).save(path);paths.append(path)
    bad=tmp_path/'broken.morale';bad.write_text('invalid');paths.append(bad)
    dialog=CatalogDialog(paths);dialog.show();ticks=[]
    timer=QTimer();timer.setInterval(10);timer.timeout.connect(lambda:ticks.append(1));timer.start()
    try:
        deadline=time.monotonic()+20
        while not dialog.save.isEnabled() and time.monotonic()<deadline:
            app.processEvents();time.sleep(.01)
        assert dialog.save.isEnabled() and len(dialog.entries)==3 and len(ticks)>2
        assert sum('error' in e for e in dialog.entries)==1
        path=tmp_path/'catalog.pdf';save_catalog(path,dialog.entries)
        assert path.exists()
    finally:timer.stop();dialog.reject()


def test_cancel_ignores_late_results_and_stops_worker(tmp_path,app):
    path=tmp_path/'design.morale';Project(objects=[DesignObject()]).save(path)
    dialog=CatalogDialog([path]);dialog.advance();dialog.reject()
    dialog.failed(str(path.resolve()),'late')
    app.processEvents()
    assert dialog.entries==[] and dialog.runner.path is None and not dialog.save.isEnabled()


@pytest.mark.parametrize('paths',[[],['a']*101+[str(i) for i in range(101)]])
def test_catalog_size_bounds(paths):
    with pytest.raises(ValueError):CatalogDialog(paths)


def test_library_opens_catalog_for_chosen_designs(tmp_path,monkeypatch):
    from PySide6.QtWidgets import QFileDialog
    from morale.library import LibraryDialog
    import morale.library_catalog as catalog
    calls=[];paths=[str(tmp_path/'one.morale'),str(tmp_path/'two.pes')]
    monkeypatch.setattr(QFileDialog,'getOpenFileNames',lambda *args:(paths,''))
    class Prepared:
        def __init__(self,selected,parent):calls.append(selected)
        def exec(self):calls.append('opened')
    monkeypatch.setattr(catalog,'CatalogDialog',Prepared)
    dialog=LibraryDialog(folder=str(tmp_path))
    try:dialog.create_catalog();assert calls==[paths,'opened']
    finally:dialog.reject()



def test_catalog_file_index_preserves_long_paths_and_errors(tmp_path):
    long_path='/designs/'+'long-directory-'*30+'/unique-end.morale'
    entries=[entry(1),{'path':long_path,'error':'Failure detail '+('more detail '*1500)+'UNIQUE END'}]
    path=tmp_path/'long.pdf';save_catalog(path,entries)
    if shutil.which('pdftotext'):
        text=unicodedata.normalize('NFKC',subprocess.check_output(['pdftotext','-layout',str(path),'-'],text=True))
        assert 'unique-end.morale' in text and 'Catalog file index' in text
        assert 'UNIQUE END' in text and 'Failure detail' in text
        assert ''.join(long_path.split()) in ''.join(text.split())


@pytest.mark.parametrize('alias',['same','symlink','hardlink'])
def test_catalog_never_replaces_a_source_design(tmp_path,alias):
    import os
    source=tmp_path/'source.morale';source.write_bytes(b'original design')
    destination=source if alias=='same' else tmp_path/'catalog.pdf'
    if alias=='symlink':
        try:destination.symlink_to(source)
        except OSError:pytest.skip('Symlinks unavailable')
    elif alias=='hardlink':os.link(source,destination)
    item=entry(1);item['path']=str(source)
    with pytest.raises(ValueError,match='source design'):save_catalog(destination,[item])
    assert source.read_bytes()==b'original design' and destination.read_bytes()==b'original design'


def test_destination_is_rechecked_after_pdf_rendering(tmp_path,monkeypatch):
    from PySide6.QtGui import QPainter
    import os
    source=tmp_path/'source.morale';source.write_bytes(b'keep')
    destination=tmp_path/'catalog.pdf';item=entry(1);item['path']=str(source)
    original=QPainter.end
    def end(painter):
        result=original(painter)
        if not destination.exists():os.link(source,destination)
        return result
    monkeypatch.setattr(QPainter,'end',end)
    with pytest.raises(ValueError,match='source design'):save_catalog(destination,[item])
    assert source.read_bytes()==b'keep' and destination.read_bytes()==b'keep'
    assert sorted(p.name for p in tmp_path.iterdir())==['catalog.pdf','source.morale']


def test_window_close_cancels_preview_and_ignores_late_success(tmp_path,app):
    path=tmp_path/'design.morale';Project(objects=[DesignObject()]).save(path)
    dialog=CatalogDialog([path]);dialog.show();dialog.advance()
    stat=path.stat();info={**entry(1)['info'],'size':stat.st_size,'mtime_ns':stat.st_mtime_ns}
    assert dialog.close()
    dialog.ready(str(path.resolve()),info,entry(1)['image']);app.processEvents()
    assert dialog.cancelled and dialog.entries==[] and dialog.runner.path is None
    assert not dialog.save.isEnabled()


def test_file_changed_during_preview_is_listed_as_failure(tmp_path,app,monkeypatch):
    path=tmp_path/'design.morale';path.write_bytes(b'first')
    dialog=CatalogDialog([path]);monkeypatch.setattr(dialog.runner,'load',lambda path:None)
    try:
        dialog.advance();stat=path.stat()
        info={**entry(1)['info'],'size':stat.st_size,'mtime_ns':stat.st_mtime_ns}
        path.write_bytes(b'changed contents')
        dialog.ready(str(path.resolve()),info,entry(1)['image']);app.processEvents()
        assert dialog.save.isEnabled() and len(dialog.entries)==1
        assert 'File changed during preview' in dialog.entries[0]['error']
        assert 'image' not in dialog.entries[0]
    finally:dialog.reject()


def test_search_catalog_snapshots_all_results_in_order(tmp_path,monkeypatch):
    from morale.library import LibraryDialog
    dialog=LibraryDialog(folder=str(tmp_path));calls=[]
    monkeypatch.setattr(dialog,'open_catalog',lambda paths:calls.append(paths))
    try:
        dialog.file_views.setCurrentIndex(1)
        dialog.results.addItems(['flowers/rose.pes','letters/name.morale'])
        dialog.catalog_results()
        assert calls==[[str(tmp_path/'flowers/rose.pes'),str(tmp_path/'letters/name.morale')]]
        dialog.results.clear()
        assert len(calls[0])==2
    finally:dialog.reject()


@pytest.mark.parametrize('count',[0,101])
def test_search_catalog_never_silently_truncates(tmp_path,monkeypatch,count):
    from morale.library import LibraryDialog
    dialog=LibraryDialog(folder=str(tmp_path));calls=[]
    monkeypatch.setattr(dialog,'open_catalog',lambda paths:calls.append(paths))
    try:
        dialog.file_views.setCurrentIndex(1);dialog.results.addItems([f'{i}.pes' for i in range(count)])
        dialog.catalog_results()
        assert not calls
        assert ('Narrow the search' if count else 'Search subfolders') in dialog.search_status.text()
    finally:dialog.reject()


def test_folder_view_does_not_catalog_stale_search_results(tmp_path,monkeypatch):
    from morale.library import LibraryDialog
    dialog=LibraryDialog(folder=str(tmp_path));calls=[]
    monkeypatch.setattr(dialog,'open_catalog',lambda paths:calls.append(paths))
    try:
        dialog.results.addItem('old.pes');dialog.file_views.setCurrentIndex(0);dialog.catalog_results()
        assert not calls
    finally:dialog.reject()


def test_catalog_selection_from_large_result_set_preserves_display_order(tmp_path,monkeypatch):
    from morale.library import LibraryDialog
    dialog=LibraryDialog(folder=str(tmp_path));calls=[]
    monkeypatch.setattr(dialog,'open_catalog',lambda paths:calls.append(paths))
    try:
        dialog.file_views.setCurrentIndex(1);dialog.results.addItems([f'{i}.pes' for i in range(120)])
        dialog.results.item(90).setSelected(True);dialog.results.item(2).setSelected(True)
        assert dialog.catalog_results_button.text()=='Catalog selection (2)…'
        dialog.catalog_results_button.click()
        assert calls==[[str(tmp_path/'2.pes'),str(tmp_path/'90.pes')]]
        dialog.results.clearSelection()
        assert dialog.catalog_results_button.text()=='Catalog results…'
        dialog.catalog_results();assert len(calls)==1
    finally:dialog.reject()


def test_more_than_100_selected_results_are_not_truncated(tmp_path,monkeypatch):
    from morale.library import LibraryDialog
    dialog=LibraryDialog(folder=str(tmp_path));calls=[]
    monkeypatch.setattr(dialog,'open_catalog',lambda paths:calls.append(paths))
    try:
        dialog.file_views.setCurrentIndex(1);dialog.results.addItems([f'{i}.pes' for i in range(101)])
        dialog.results.selectAll();dialog.catalog_results()
        assert not calls and '101 designs' in dialog.search_status.text()
    finally:dialog.reject()
