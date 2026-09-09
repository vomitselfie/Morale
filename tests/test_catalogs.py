import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import csv

import pytest
from PySide6.QtWidgets import QApplication, QDialog

from morale.catalogs import ThreadEntry,builtin_catalog,read_catalog,nearest_thread
from morale.catalog_dialog import CatalogDialog
from morale.model import DesignObject,Project
from morale.threads import write_chart
from morale.engine import generate


@pytest.fixture(scope='module',autouse=True)
def app():
    return QApplication.instance() or QApplication([])


def entries():
    return [ThreadEntry('#ff0000',{'brand':'Example','catalog_number':'001','description':'Red'}),
            ThreadEntry('#0000ff',{'brand':'Example','catalog_number':'002','description':'Blue'})]


@pytest.mark.parametrize('name,count',[('PEC fixed palette',64),('JEF fixed palette',78)])
def test_builtin_fixed_palettes_have_metadata_and_exact_matches(name,count):
    catalog=builtin_catalog(name)
    assert len(catalog)==count
    assert all(entry.metadata.get('catalog_number') and entry.metadata.get('description') for entry in catalog)
    assert nearest_thread(catalog[0].color,catalog).color==catalog[0].color


def test_nearest_color_and_stable_ties():
    catalog=entries()
    assert nearest_thread('#f00102',catalog)==catalog[0]
    assert nearest_thread('#0102f0',catalog)==catalog[1]
    assert nearest_thread('#000000',catalog)==catalog[0]
    with pytest.raises(ValueError):
        nearest_thread('#123456',[])


def test_csv_keeps_leading_zero_codes_unicode_and_quoted_names(tmp_path):
    path=tmp_path/'threads.csv'
    path.write_text('\ufeffcolor,brand,catalog_number,description\n#FF0000,Example,0001,"Rouge, été"\n#ff0000,Example,0001,"Rouge, été"\n',encoding='utf-8')
    catalog=read_catalog(path)
    assert len(catalog)==1
    assert catalog[0].color=='#ff0000'
    assert catalog[0].metadata['catalog_number']=='0001'
    assert catalog[0].metadata['description']=='Rouge, été'


def test_app_thread_chart_can_be_reused_as_catalog(tmp_path):
    obj=DesignObject(color='#ff0000',thread={'brand':'Example','catalog_number':'0007'})
    project=Project(objects=[obj])
    path=tmp_path/'chart.csv'
    with path.open('w',newline='',encoding='utf-8') as stream:
        write_chart(project,generate(project),stream)
    catalog=read_catalog(path)
    assert len(catalog)==1 and catalog[0].metadata['catalog_number']=='0007'


@pytest.mark.parametrize('text',[
    'brand,description\nExample,red\n',
    'color,color\n#ff0000,#0000ff\n',
    'color,Thread RGB\n#ff0000,#0000ff\n',
    'color\nnot-a-color\n',
    'color\n#ff0000,extra\n',
    'color,brand\n#ff0000,'+'x'*1025+'\n',
])
def test_malformed_catalogs_are_rejected(tmp_path,text):
    path=tmp_path/'bad.csv'
    path.write_text(text)
    with pytest.raises(ValueError):
        read_catalog(path)


def test_catalog_table_is_virtual_and_searchable(tmp_path):
    path=tmp_path/'large.csv'
    with path.open('w',newline='') as stream:
        writer=csv.writer(stream)
        writer.writerow(['color','catalog_number','description'])
        for i in range(10000):
            writer.writerow([f'#{i:06x}',f'{i:05d}',f'Thread {i}'])
    dialog=CatalogDialog('#000001',1,cached=('Personal',read_catalog(path)))
    try:
        assert dialog.model.rowCount()==10000
        dialog.search.setText('09999')
        assert dialog.model.rowCount()==1
        dialog.assign()
        assert dialog.entry.metadata['catalog_number']=='09999'
    finally:
        dialog.close()


def test_cached_custom_catalog_survives_switching_and_search_limits_matching():
    dialog=CatalogDialog('#ff0000',2,cached=('Personal',entries()))
    try:
        dialog.catalog_choice.setCurrentIndex(0)
        dialog.catalog_choice.setCurrentIndex(2)
        assert dialog.model.rowCount()==2
        dialog.search.setText('blue')
        dialog.match_colors()
        assert dialog.mode=='nearest' and dialog.candidates==[entries()[1]]
    finally:
        dialog.close()


def test_native_catalog_application_matching_undo_and_metadata_independence():
    from morale.app import MainWindow
    window=MainWindow()
    try:
        a,b=DesignObject(color='#f00102'),DesignObject(color='#0102f0')
        window.replace_project(Project(objects=[a,b]))
        window.select_many([a.id,b.id])
        original=window.project.dumps()
        catalog=entries()
        window.apply_catalog_threads(catalog,nearest=True)
        assert [o.color for o in window.project.objects]==['#ff0000','#0000ff']
        assert [o.thread['catalog_number'] for o in window.project.objects]==['001','002']
        assert Project.loads(window.project.dumps()).objects[0].thread['brand']=='Example'
        catalog[0].metadata['brand']='Changed outside project'
        assert window.project.objects[0].thread['brand']=='Example'
        window.undo()
        assert window.project.dumps()==original
        window.select_many([a.id,b.id])
        with pytest.raises(ValueError):
            window.apply_catalog_threads([ThreadEntry('invalid',{})])
        assert window.project.dumps()==original
        window.apply_catalog_threads([entries()[0]])
        assert all(o.color=='#ff0000' and o.thread['catalog_number']=='001' for o in window.project.objects)
    finally:
        window.saved=window.project.dumps()
        window.close()


def test_cancel_keeps_project_unchanged(tmp_path,monkeypatch):
    from morale.app import MainWindow
    window=MainWindow()
    try:
        obj=window.project.objects[0]
        window.select(obj.id)
        before=window.project.dumps()
        monkeypatch.setattr(CatalogDialog,'exec',lambda self:QDialog.DialogCode.Rejected)
        window.thread_catalog_dialog()
        assert window.project.dumps()==before and not window.history
    finally:
        window.saved=window.project.dumps()
        window.close()
