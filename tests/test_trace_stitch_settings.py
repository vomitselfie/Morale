import json
import pytest
from PySide6.QtWidgets import QApplication
from morale.model import Project,DesignObject
from morale.engine import generate
from morale.trace_stitch_settings import apply_stitch_settings


@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])


def test_spacing_changes_sewing_without_changing_artwork():
    source=Project(objects=[DesignObject(kind='rectangle',width=20,height=20,underlay=False)])
    snapshot=source.dumps()
    result,report=apply_stitch_settings(source,{'fill_spacing':1,'stitch_length':4})
    assert source.dumps()==snapshot and result.objects[0].rings()==source.objects[0].rings()
    assert result.objects[0].id==source.objects[0].id and report['changed_objects']==1
    assert sum(len(b.stitches) for b in generate(result))<sum(len(b.stitches) for b in generate(source))
    assert Project.loads(result.dumps()).objects==result.objects


def test_type_specific_settings_and_underlay():
    from morale.auto_digitize import choose_stitches
    satin,_=choose_stitches(Project(objects=[DesignObject(kind='rectangle',width=3,height=20)]))
    assert satin.objects[0].stitch_type=='satin'
    running=DesignObject(stitch_type='running',underlay=False)
    source=Project(objects=[*satin.objects,running])
    result,_=apply_stitch_settings(source,{'fill_spacing':1,'satin_spacing':.6,'underlay':'auto','pull_compensation':.2})
    assert result.objects[0].spacing==.6 and result.objects[0].underlay
    assert result.objects[0].pull_compensation==.2
    assert result.objects[1]==running
    disabled,_=apply_stitch_settings(result,{'underlay':'off'})
    assert not any(o.underlay for o in disabled.objects)
    assert generate(disabled)


@pytest.mark.parametrize('settings',[None,[],{'unknown':1},{'fill_spacing':True},{'satin_spacing':.1},
    {'stitch_length':float('nan')},{'pull_compensation':float('inf')},{'underlay':True},{'underlay':'edge'}])
def test_invalid_settings_are_rejected(settings):
    with pytest.raises(ValueError):apply_stitch_settings(Project(),settings)


@pytest.mark.parametrize('fill_underlay',['off','edge_sparse'])
def test_worker_native_preview_and_undo(tmp_path,fill_underlay):
    from morale.raster_trace import worker_main
    from morale.trace_dialog import TraceDialog
    from morale.app import MainWindow
    from morale.trace_quality import quality_text
    path=tmp_path/'fill.svg';path.write_text('<svg width="30" height="30"><rect x="5" y="5" width="20" height="20" fill="red"/></svg>')
    output=tmp_path/'out';output.mkdir()
    options=dict(width=30,stitch_settings={'fill_spacing':.9,'underlay':'off','fill_underlay':fill_underlay,'underlay_inset':.4,'underlay_spacing':1.5,'pull_compensation':.2},optimize_fill_angles=True)
    assert worker_main([str(path),str(output),json.dumps(options)])==0
    info=json.loads((output/'preview.json').read_text());result=Project.loads(info['project']);obj=result.objects[0]
    assert obj.spacing==.9 and obj.underlay==(fill_underlay!='off') and obj.pull_compensation==.2
    assert obj.underlay_inset==.4 and obj.underlay_spacing==1.5
    if obj.underlay:assert obj.underlay_style==fill_underlay
    assert 'Custom stitch settings: 1 objects changed' in quality_text(info['trace_stats']['quality'])
    assert info['trace_stats']['quality']['density']['penetrations']==sum(s.command=='stitch' for b in generate(result) for s in b.stitches)
    dialog=TraceDialog(str(path));window=MainWindow()
    try:
        assert not dialog.custom_stitches.isChecked()
        dialog.overrides={'0':'fill'};dialog.custom_stitches.setChecked(True)
        dialog.stitch_settings['fill_spacing'].setValue(.9)
        assert dialog.overrides=={'0':'fill'} and dialog.project is None
        dialog.runner.load=lambda path:None
        dialog.generate();assert dialog.runner.options['stitch_settings']['fill_spacing']==.9
        before=window.project.dumps();window.apply_raster_trace(result);window.undo()
        assert window.project.dumps()==before
        dialog.custom_stitches.setChecked(False);dialog.generate()
        assert 'stitch_settings' not in dialog.runner.options
    finally:dialog.close();window.saved=window.project.dumps();window.close()


def test_mixed_underlay_supports_preserve_artwork_and_use_engine_geometry():
    from morale.auto_digitize import choose_stitches
    from morale.engine import generate_underlay
    satin,_=choose_stitches(Project(objects=[DesignObject(kind='rectangle',width=3,height=20)]))
    fill=DesignObject(kind='rectangle',width=20,height=20)
    running=DesignObject(stitch_type='running',underlay=False)
    source=Project(objects=[fill,*satin.objects,running]);snapshot=source.dumps()
    result,_=apply_stitch_settings(source,{'underlay':'off','fill_underlay':'edge_sparse',
        'satin_underlay':'center_zigzag','underlay_inset':.4,'underlay_spacing':1.5})
    assert source.dumps()==snapshot and result.objects[-1]==running
    for original,converted,style in zip(source.objects,result.objects,['edge_sparse','center_zigzag']):
        assert converted.rings()==original.rings() and converted.id==original.id
        assert converted.underlay and converted.underlay_style==style
        assert converted.underlay_inset==.4 and converted.underlay_spacing==1.5
        assert generate_underlay(converted)!=generate_underlay(original)
    assert generate(result)
    assert Project.loads(result.dumps()).objects==result.objects


@pytest.mark.parametrize('settings',[{'fill_underlay':'zigzag'},{'satin_underlay':'edge'},
    {'underlay_inset':3.1},{'underlay_spacing':0},{'underlay_inset':True}])
def test_invalid_type_specific_underlay_rejected(settings):
    with pytest.raises(ValueError):apply_stitch_settings(Project(),settings)
