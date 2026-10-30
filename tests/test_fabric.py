import pytest
from PySide6.QtWidgets import QApplication
from morale.fabric import apply_fabric
from morale.fabric_dialog import FabricDialog
from morale.model import DesignObject,Project
from morale.engine import generate

@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])


def test_profiles_generate_and_preserve_source():
    dialog=FabricDialog()
    try:
        fill=DesignObject(kind='rectangle')
        satin=DesignObject(kind='satin',stitch_type='satin',points=[[-.2,-.5],[.2,-.5],[-.2,.5],[.2,.5]])
        running=DesignObject(stitch_type='running')
        source=Project(objects=[fill,satin,running]);before=source.dumps()
        for index in range(dialog.profile.count()):
            dialog.profile.setCurrentIndex(index)
            result,count=apply_fabric(source,{o.id for o in source.objects},dialog.settings())
            assert count==2 and source.dumps()==before
            assert result.objects[2]==running
            assert result.objects[1].underlay_style in {'auto','center_zigzag'}
            assert generate(result)==generate(Project.loads(result.dumps()))
    finally:dialog.close()


def test_native_selection_application_undo_redo():
    from morale.app import MainWindow
    window=MainWindow();dialog=FabricDialog()
    try:
        a,b=DesignObject(),DesignObject(x=30)
        window.replace_project(Project(objects=[a,b]));window.select(a.id)
        before=window.project.dumps()
        dialog.profile.setCurrentText('Stretch knit')
        window.apply_fabric_settings(dialog.settings())
        after=window.project.dumps()
        assert after!=before and window.project.objects[1]==b
        assert window.project.objects[0].pull_compensation==.25
        window.undo();assert window.project.dumps()==before
        window.redo();assert window.project.dumps()==after
        invalid=dialog.settings();invalid['spacing']=-1
        with pytest.raises(ValueError):window.apply_fabric_settings(invalid)
        assert window.project.dumps()==after
    finally:
        dialog.close();window.saved=window.project.dumps();window.close()


def test_no_applicable_selection_leaves_source_unchanged():
    source=Project(objects=[DesignObject(stitch_type='running')]);before=source.dumps()
    dialog=FabricDialog()
    try:
        with pytest.raises(ValueError,match='editable fill or satin'):
            apply_fabric(source,{source.objects[0].id},dialog.settings())
        assert source.dumps()==before
    finally:dialog.close()


@pytest.mark.parametrize('profile',['Stable woven','Stretch knit','Textured / pile'])
@pytest.mark.parametrize('extension',['pes','pec','exp','dst','jef','vp3','u01','tbf','xxx'])
def test_fabric_profiles_preserve_generated_paths_in_machine_exports(tmp_path,profile,extension):
    from morale.formats import export_machine
    from morale.export_verify import verify_export
    dialog=FabricDialog()
    try:
        dialog.profile.setCurrentText(profile)
        fill=DesignObject(kind='rectangle',x=-18,width=20,height=20,angle=0,color='#ff0000')
        satin=DesignObject(kind='satin',stitch_type='satin',x=18,width=10,height=20,
                           color='#0000ff',points=[[-.2,-.5],[.2,-.5],[-.3,0],[.3,0],[-.2,.5],[.2,.5]])
        source=Project(objects=[fill,satin]);before=source.dumps()
        result,count=apply_fabric(source,{fill.id,satin.id},dialog.settings())
        assert count==2 and source.dumps()==before
        blocks=generate(result)
        assert blocks!=generate(source)
        target=tmp_path/f'fabric.{extension}'
        export_machine(result,target,blocks)
        report=verify_export(blocks,target)
        assert report['complete_path_comparison']
        assert report['bounds_delta_mm']<=.3
        assert all(issue.startswith('Trim commands increased:') for issue in report['problems']),report
    finally:dialog.close()


def test_custom_fabric_preset_native_roundtrip_and_invalid_load(tmp_path,monkeypatch):
    from PySide6.QtWidgets import QFileDialog,QMessageBox
    path=tmp_path/'mother-knit.morale-fabric.json'
    dialog=FabricDialog();messages=[]
    monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *a:(str(path),''))
    monkeypatch.setattr(QFileDialog,'getOpenFileName',lambda *a:(str(path),''))
    monkeypatch.setattr(QMessageBox,'warning',lambda *a:messages.append(a[-1]))
    try:
        dialog.fields['pull_compensation'].setValue(.35)
        dialog.fields['spacing'].setValue(.55)
        expected=dialog.settings();dialog.save_file()
        dialog.load_profile('Textured / pile');dialog.load_file()
        assert dialog.settings()==expected and dialog.profile.currentIndex()==-1
        path.write_text('{"format":"wrong"}')
        dialog.load_file()
        assert dialog.settings()==expected and messages
    finally:dialog.close()


@pytest.mark.parametrize('key,value',[('spacing',True),('spacing',float('nan')),('spacing',.1),('underlay_style',[]),('underlay_spacing',11)])
def test_invalid_fabric_preset_does_not_overwrite(tmp_path,key,value):
    from morale.fabric_presets import save_preset
    path=tmp_path/'preset.json';path.write_text('original')
    dialog=FabricDialog()
    try:
        settings=dialog.settings();settings[key]=value
        with pytest.raises(ValueError):save_preset(path,settings)
        assert path.read_text()=='original'
    finally:dialog.close()


def test_fabric_preset_replacement_failure_keeps_original(tmp_path,monkeypatch):
    import morale.fabric_presets as presets
    path=tmp_path/'preset.json';path.write_text('original')
    def fail(*args):raise OSError('read only')
    monkeypatch.setattr(presets.os,'replace',fail)
    dialog=FabricDialog()
    try:
        with pytest.raises(OSError):presets.save_preset(path,dialog.settings())
        assert path.read_text()=='original' and list(tmp_path.iterdir())==[path]
    finally:dialog.close()


def test_reopen_fabric_dialog_retains_selection_settings(monkeypatch):
    from morale.app import MainWindow
    from PySide6.QtWidgets import QDialog
    window=MainWindow();seen=[]
    try:
        obj=DesignObject(underlay_style='edge_sparse',spacing=.55,pull_compensation=.35,underlay_inset=.8)
        window.replace_project(Project(objects=[obj]));window.select(obj.id)
        before=window.project.dumps()
        def review(dialog):
            seen.append(dialog.settings())
            assert dialog.profile.currentIndex()==-1
            return QDialog.DialogCode.Accepted
        monkeypatch.setattr(FabricDialog,'exec',review)
        window.fabric_dialog()
        assert seen[0]['spacing']==.55 and seen[0]['pull_compensation']==.35
        assert window.project.dumps()==before
    finally:window.saved=window.project.dumps();window.close()


def test_mixed_fabric_settings_are_not_reported_as_common():
    from morale.fabric import selection_settings
    a=DesignObject(underlay_style='edge_sparse')
    b=DesignObject(underlay_style='edge_sparse',spacing=.6)
    assert selection_settings([a,b]) is None
    b.spacing=a.spacing
    assert selection_settings([a,b])['spacing']==a.spacing
    b.underlay=False
    assert selection_settings([a,b]) is None


def test_review_preserves_unedited_subdisplay_precision():
    settings=dict(spacing=.4567,pull_compensation=.1234,underlay_inset=.5678,underlay_spacing=2.1234,underlay_style='edge')
    dialog=FabricDialog(initial_settings=settings)
    try:
        assert dialog.settings()==settings
        dialog.fields['spacing'].setValue(.6)
        assert dialog.settings()==dict(settings,spacing=.6)
    finally:dialog.close()


def test_edit_then_return_to_displayed_value_keeps_user_choice():
    settings=dict(spacing=.4567,pull_compensation=.1234,underlay_inset=.5678,underlay_spacing=2.1234,underlay_style='edge')
    dialog=FabricDialog(initial_settings=settings)
    try:
        dialog.fields['spacing'].setValue(.6)
        dialog.fields['spacing'].setValue(.46)
        assert dialog.settings()['spacing']==.46
        assert dialog.settings()['pull_compensation']==.1234
        assert 'Custom values' in dialog.context.text()
    finally:dialog.close()


def test_editing_builtin_clears_profile_and_reselecting_restores_it():
    dialog=FabricDialog()
    try:
        dialog.fields['spacing'].setValue(.7)
        assert dialog.profile.currentIndex()==-1
        dialog.profile.setCurrentText('Stable woven')
        assert dialog.fields['spacing'].value()==.45
        assert dialog.profile.currentText()=='Stable woven'
        assert 'Starting-point' in dialog.context.text()
    finally:dialog.close()


@pytest.mark.parametrize('payload',[
    b'{"format":"morale-fabric-preset","version":1,"version":2,"settings":{}}',
    b'{"format":"morale-fabric-preset","version":true,"settings":{}}',
    b'{"format":"morale-fabric-preset","version":1,"settings":{"spacing":0.4,"spacing":0.5}}',
    b'['*2000+b']'*2000,
    b' '*8193,
    b'\xff\xfe\xff',
])
def test_malformed_fabric_files_are_normal_validation_errors(tmp_path,payload):
    from morale.fabric_presets import load_preset
    path=tmp_path/'bad.json';path.write_bytes(payload)
    with pytest.raises(ValueError):load_preset(path)


def test_huge_fabric_number_is_rejected_without_overflow(tmp_path):
    from morale.fabric_presets import load_preset
    path=tmp_path/'huge.json'
    path.write_text('{"format":"morale-fabric-preset","version":1,"settings":{"spacing":'+('9'*1000)+',"pull_compensation":0,"underlay_inset":0,"underlay_spacing":2,"underlay_style":"edge"}}')
    with pytest.raises(ValueError,match='spacing'):load_preset(path)


def test_large_text_fabric_controls_scroll_without_compression():
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QScrollArea,QDialogButtonBox
    from morale.window_ui import style_sheet
    dialog=FabricDialog()
    try:
        dialog.setFont(QFont('Sans Serif',16));dialog.setStyleSheet(style_sheet(16))
        dialog.resize(560,500);dialog.show();QApplication.processEvents()
        scroll=dialog.findChild(QScrollArea)
        assert scroll.verticalScrollBar().maximum()>0
        for field in [dialog.profile,dialog.style,*dialog.fields.values()]:
            assert field.height()>=field.minimumSizeHint().height()
        buttons=dialog.findChild(QDialogButtonBox)
        assert buttons.geometry().bottom()<dialog.height()
        assert buttons.geometry().top()>scroll.geometry().bottom()
    finally:dialog.close()


def test_underlay_off_preset_roundtrip_and_application(tmp_path):
    from morale.fabric_presets import save_preset,load_preset
    from morale.fabric import selection_settings
    dialog=FabricDialog()
    try:
        dialog.underlay.setChecked(False)
        assert not dialog.style.isEnabled() and not dialog.fields['underlay_inset'].isEnabled()
        path=tmp_path/'off.json';save_preset(path,dialog.settings());settings=load_preset(path)
        obj=DesignObject(underlay_style='edge')
        result,_=apply_fabric(Project(objects=[obj]),{obj.id},settings)
        assert not result.objects[0].underlay
        assert selection_settings(result.objects)['underlay'] is False
        dialog.load_profile('Stable woven');assert dialog.underlay.isChecked()
        dialog.set_settings(settings);assert not dialog.underlay.isChecked()
    finally:dialog.close()


@pytest.mark.parametrize('value',[0,1,'false',None,[],{}])
def test_invalid_underlay_switch_cannot_replace_preset(tmp_path,value):
    from morale.fabric_presets import save_preset
    path=tmp_path/'fabric.json';path.write_text('existing preset')
    settings=dict(spacing=.45,pull_compensation=.2,underlay_inset=.5,underlay_spacing=2,underlay_style='edge',underlay=value)
    with pytest.raises(ValueError,match='underlay switch'):save_preset(path,settings)
    assert path.read_text()=='existing preset'


def test_legacy_fabric_preset_keeps_enabled_underlay(tmp_path):
    import json
    from morale.fabric_presets import load_preset
    settings=dict(spacing=.45,pull_compensation=.2,underlay_inset=.5,underlay_spacing=2,underlay_style='edge')
    path=tmp_path/'legacy.json'
    path.write_text(json.dumps(dict(format='morale-fabric-preset',version=1,settings=settings)))
    obj=DesignObject(underlay=False)
    result,_=apply_fabric(Project(objects=[obj]),{obj.id},load_preset(path))
    assert result.objects[0].underlay
    assert not obj.underlay
