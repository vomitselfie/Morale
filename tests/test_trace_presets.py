import json
import pytest
from PySide6.QtWidgets import QApplication
from morale.trace_dialog import TraceDialog
from morale.trace_presets import load_preset,save_preset


@pytest.fixture
def dialog():
    app=QApplication.instance() or QApplication([]);dialog=TraceDialog('artwork.png')
    yield dialog
    dialog.close()


def test_portable_preset_round_trip_and_native_worker_options(dialog,tmp_path):
    dialog.custom_stitches.setChecked(True);dialog.stitch_settings['fill_spacing'].setValue(.7)
    dialog.route.setChecked(True);dialog.reverse_travel.setChecked(True)
    dialog.finishing.setChecked(True);dialog.internal_trims.setChecked(True)
    settings=dialog.preset_settings();path=tmp_path/'cotton.morale-trace.json';save_preset(path,settings)
    target=TraceDialog('different.png')
    try:
        target.width.setValue(55);target.keep_reference.setChecked(False)
        target.thread_catalog.addItem('My chart','/private/chart.csv');target.thread_catalog.setCurrentIndex(3)
        target.overrides={'0':'running'};target.seams={'0':30}
        target.apply_preset(load_preset(path))
        assert target.preset_settings()==settings
        assert target.width.value()==55 and not target.keep_reference.isChecked()
        assert target.thread_catalog.currentData()=='/private/chart.csv'
        assert not target.overrides and not target.seams and target.project is None
        assert target.reverse_travel.isEnabled() and target.internal_trims.isEnabled()
        assert target.stitch_settings['fill_spacing'].isEnabled()
        target.runner.load=lambda _:None;target.generate()
        assert target.runner.options['stitch_settings']['fill_spacing']==.7
        assert target.runner.options['reverse_for_travel'] and target.runner.options['internal_trims']
        assert '/private' not in path.read_text() and 'width' not in settings and 'keep_reference' not in settings
    finally:target.close()


@pytest.mark.parametrize('key,value',[('method','photo'),('resolution',100),('colors',True),('colors',2.5),('smoothing',float('nan')),
    ('stitch_length',10),('underlay',[]),('route_fill',1),('trim_threshold',float('inf'))])
def test_invalid_preset_does_not_mutate_native_settings(dialog,key,value):
    before=dialog.preset_settings();bad={**before,key:value}
    with pytest.raises(ValueError):dialog.apply_preset(bad)
    assert dialog.preset_settings()==before


def test_invalid_resolution_for_pixel_mode_rejected(dialog):
    settings=dialog.preset_settings();settings.update(method='pixels',resolution=512)
    with pytest.raises(ValueError):dialog.apply_preset(settings)


def test_svg_load_preserves_vector_mode(dialog):
    settings=dialog.preset_settings();settings.update(method='pixels',resolution=256)
    target=TraceDialog('art.svg')
    try:
        target.apply_preset(settings)
        assert not target.method.isEnabled() and target.method.currentData()=='smooth'
        assert 'SVG vectors' in target.method.currentText()
    finally:target.close()


def test_failed_atomic_save_preserves_existing_file(dialog,tmp_path,monkeypatch):
    import morale.trace_presets as module
    path=tmp_path/'preset.json';path.write_text('original')
    def fail(*_):raise OSError('publish failed')
    monkeypatch.setattr(module.os,'replace',fail)
    with pytest.raises(OSError):save_preset(path,dialog.preset_settings())
    assert path.read_text()=='original' and list(tmp_path.iterdir())==[path]


@pytest.mark.parametrize('data',['{','[]','x'*32769,json.dumps({'format':'morale-trace-preset','version':True,'settings':{}})])
def test_corrupt_or_oversized_file_rejected(tmp_path,data):
    path=tmp_path/'bad.json';path.write_text(data)
    with pytest.raises(ValueError):load_preset(path)


def test_disabled_dependencies_remain_disabled_after_load(dialog):
    settings=dialog.preset_settings();dialog.custom_stitches.setChecked(True);dialog.finishing.setChecked(True);dialog.route.setChecked(True)
    dialog.apply_preset(settings)
    assert not dialog.reverse_travel.isEnabled() and not dialog.internal_trims.isEnabled()
    assert not dialog.stitch_settings['fill_spacing'].isEnabled()


def test_underlay_presets_native_options_and_legacy_defaults(dialog,tmp_path):
    dialog.custom_stitches.setChecked(True)
    dialog.underlay_choices['fill_underlay'].setCurrentIndex(dialog.underlay_choices['fill_underlay'].findData('edge_sparse'))
    dialog.underlay_choices['satin_underlay'].setCurrentIndex(dialog.underlay_choices['satin_underlay'].findData('center_zigzag'))
    dialog.stitch_settings['underlay_inset'].setValue(.4)
    dialog.stitch_settings['underlay_spacing'].setValue(1.5)
    path=tmp_path/'supports.json';save_preset(path,dialog.preset_settings())
    dialog.apply_preset(load_preset(path));dialog.runner.load=lambda _:None;dialog.generate()
    settings=dialog.runner.options['stitch_settings']
    assert settings['fill_underlay']=='edge_sparse' and settings['satin_underlay']=='center_zigzag'
    assert settings['underlay_inset']==.4 and settings['underlay_spacing']==1.5
    legacy=dialog.preset_settings()
    for key in ('fill_underlay','satin_underlay','underlay_inset','underlay_spacing'):legacy.pop(key)
    dialog.apply_preset(legacy)
    assert dialog.underlay_choices['fill_underlay'].currentData()=='keep'
    assert dialog.underlay_choices['satin_underlay'].currentData()=='keep'
    assert dialog.stitch_settings['underlay_inset'].value()==0
    assert dialog.stitch_settings['underlay_spacing'].value()==2
