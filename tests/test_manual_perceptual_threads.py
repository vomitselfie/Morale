import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication,QDialog
from morale.catalog_dialog import CatalogDialog
from morale.catalogs import builtin_catalog,nearest_thread
from morale.model import Project,DesignObject

@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])


def test_native_metric_changes_ranking_and_header():
    dialog=CatalogDialog('#cc8833',1)
    try:
        assert dialog.metric_choice.currentData()=='oklab'
        assert dialog.model.rows[0][1].color=='#ba9800'
        assert dialog.model.headerData(5,Qt.Orientation.Horizontal)=='Oklab ×100'
        dialog.metric_choice.setCurrentIndex(dialog.metric_choice.findData('rgb'))
        assert dialog.model.rows[0][1].color=='#b27624'
        assert dialog.model.headerData(5,Qt.Orientation.Horizontal)=='RGB distance'
    finally:dialog.reject()


@pytest.mark.parametrize('metric,expected',[('oklab','#ba9800'),('rgb','#b27624')])
def test_native_application_uses_selected_metric_and_undo(monkeypatch,metric,expected):
    from morale.app import MainWindow
    window=MainWindow();window.replace_project(Project(objects=[DesignObject(x=-10,color='#cc8833'),DesignObject(x=10,color='#cc8833')]))
    window.select_many([o.id for o in window.project.objects]);before=window.project.dumps()
    def choose(dialog):
        assert dialog.source_colors==[('#cc8833',2)]
        dialog.metric_choice.setCurrentIndex(dialog.metric_choice.findData(metric));dialog.match_colors()
        return QDialog.DialogCode.Accepted
    monkeypatch.setattr(CatalogDialog,'exec',choose)
    try:
        window.thread_catalog_dialog()
        assert all(o.color==expected and o.thread for o in window.project.objects)
        assert window.thread_match_metric==metric
        window.undo();assert window.project.dumps()==before
    finally:window.saved=window.project.dumps();window.close()


def test_programmatic_rgb_default_and_invalid_metric():
    entries=builtin_catalog('PEC fixed palette')
    assert nearest_thread('#cc8833',entries).color=='#b27624'
    assert nearest_thread('#cc8833',entries,'oklab').color=='#ba9800'
    with pytest.raises(ValueError):nearest_thread('#cc8833',entries,'invalid')


def finish_preview(dialog,app):
    import time
    deadline=time.monotonic()+2
    while dialog.match_timer.isActive() and time.monotonic()<deadline:app.processEvents()
    assert not dialog.match_timer.isActive()


def test_bulk_preview_counts_and_filter_match_actual_candidates(app):
    from morale.catalogs import ThreadEntry
    entries=[ThreadEntry('#ff0000',{'description':'Red'}),ThreadEntry('#0000ff',{'description':'Blue'})]
    dialog=CatalogDialog('#fe0000',3,cached=('Two threads',entries),colors=['#fe0000','#fe0000','#0000fe'])
    try:
        dialog.tabs.setCurrentIndex(1);finish_preview(dialog,app)
        rows=dialog.match_model.rows
        assert [(color,count,entry.color) for color,count,entry,distance in rows]==[('#fe0000',2,'#ff0000'),('#0000fe',1,'#0000ff')]
        assert not dialog.assign_button.isEnabled()
        dialog.search.setText('Blue');finish_preview(dialog,app)
        assert [row[2].color for row in dialog.match_model.rows]==['#0000ff','#0000ff']
        dialog.match_colors();assert dialog.candidates==[entries[1]]
    finally:dialog.reject()


def test_preview_metric_refresh_empty_filter_and_cancellation(app):
    dialog=CatalogDialog('#cc8833',1,colors=['#cc8833'])
    try:
        dialog.tabs.setCurrentIndex(1);finish_preview(dialog,app)
        assert dialog.match_model.rows[0][2].color=='#ba9800'
        dialog.metric_choice.setCurrentIndex(dialog.metric_choice.findData('rgb'));finish_preview(dialog,app)
        assert dialog.match_model.rows[0][2].color=='#b27624'
        dialog.search.setText('no such thread zzz')
        assert not dialog.match_timer.isActive() and not dialog.match_model.rows
        assert 'No threads' in dialog.match_status.text()
        dialog.search.clear();dialog.reject();app.processEvents()
        assert not dialog.match_timer.isActive() and not dialog.match_model.rows
    finally:dialog.reject()


def test_partial_preview_is_discarded_on_filter_and_tab_changes(app):
    from morale.catalogs import ThreadEntry
    entries=[ThreadEntry('#ff0000',{'description':'Red'}),ThreadEntry('#0000ff',{'description':'Blue'})]
    dialog=CatalogDialog('#fe0000',2,cached=('Two',entries),colors=['#fe0000','#0000fe'])
    try:
        dialog.tabs.setCurrentIndex(1);dialog.advance_matches()
        assert len(dialog.match_model.rows)==1 and dialog.match_model.rows[0][2].color=='#ff0000'
        dialog.search.setText('Blue')
        assert dialog.match_model.rows==[]
        dialog.advance_matches()
        assert dialog.match_model.rows[0][2].color=='#0000ff'
        dialog.tabs.setCurrentIndex(0)
        assert not dialog.match_timer.isActive() and dialog.match_model.rows==[]
        dialog.advance_matches();assert dialog.match_model.rows==[]
        dialog.tabs.setCurrentIndex(1);finish_preview(dialog,app)
        assert [row[2].color for row in dialog.match_model.rows]==['#0000ff','#0000ff']
        assert '2 of 2 source colors matched' in dialog.match_status.text()
    finally:dialog.reject()
