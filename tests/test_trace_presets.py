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


# Short ids: long test data in the id becomes a temporary path too long for Windows.
@pytest.mark.parametrize('data',['{','[]','x'*32769,json.dumps({'format':'morale-trace-preset','version':True,'settings':{}})],
                         ids=['truncated','array','oversized','boolean-version'])
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


def test_branch_join_overlap_preset_worker_option_and_legacy_default(dialog,tmp_path):
    assert dialog.branch_overlap.value()==.3 and not dialog.branch_overlap.isEnabled()
    dialog.branching.setChecked(True);assert dialog.branch_overlap.isEnabled()
    dialog.branch_overlap.setValue(.6)
    path=tmp_path/'joins.json';save_preset(path,dialog.preset_settings())
    target=TraceDialog('other.png')
    try:
        target.apply_preset(load_preset(path))
        assert target.branch_overlap.value()==.6 and target.branch_overlap.isEnabled()
        target.runner.load=lambda _:None;target.generate()
        assert target.runner.options['split_branches'] and target.runner.options['branch_overlap']==.6
        # Presets saved before join overlap keep their original exact joins.
        legacy=target.preset_settings();legacy.pop('branch_overlap')
        target.apply_preset(legacy);assert target.branch_overlap.value()==0
    finally:target.close()


def test_svg_color_mode_preset_restores_controls_and_legacy_vector_default(dialog,tmp_path):
    source=TraceDialog('source.svg');target=TraceDialog('target.svg')
    try:
        source.render_svg.setChecked(True)
        source.method.setCurrentIndex(source.method.findData('pixels'))
        source.resolution.setCurrentIndex(source.resolution.findData(256))
        path=tmp_path/'gradient.json';save_preset(path,source.preset_settings())
        target.apply_preset(load_preset(path))
        assert target.render_svg.isChecked() and target.method.isEnabled()
        assert target.method.currentData()=='pixels' and not target.colors.isHidden()
        target.runner.load=lambda _:None;target.generate()
        assert target.runner.options['render_svg'] is True
        legacy=target.preset_settings();legacy.pop('render_svg')
        target.apply_preset(legacy)
        assert not target.render_svg.isChecked() and not target.method.isEnabled()
        assert target.colors.isHidden()
        dialog.apply_preset(load_preset(path))
        dialog.runner.load=lambda _:None;dialog.generate()
        assert dialog.runner.options['render_svg'] is False
        assert dialog.method.isEnabled() and dialog.method.currentData()=='pixels'
    finally:source.close();target.close()


def test_fabric_preset_maps_to_conversion_worker_without_changing_artwork(dialog):
    dialog.width.setValue(73);dialog.colors.setValue(5)
    dialog.stitch_settings['stitch_length'].setValue(3.1)
    dialog.overrides={'0':'running'};dialog.seams={'0':30}
    settings=dict(spacing=.55,pull_compensation=.3,underlay_inset=.7,underlay_spacing=2.3,underlay_style='edge_sparse')
    dialog.apply_fabric_preset(settings)
    assert dialog.width.value()==73 and dialog.colors.value()==5
    assert dialog.custom_stitches.isChecked()
    assert dialog.overrides=={'0':'running'} and dialog.seams=={'0':30}
    dialog.runner.load=lambda _:None;dialog.generate()
    stitches=dialog.runner.options['stitch_settings']
    assert stitches['fill_spacing']==stitches['satin_spacing']==.55
    assert stitches['fill_underlay']=='edge_sparse' and stitches['satin_underlay']=='center_zigzag'
    assert stitches['stitch_length']==3.1 and stitches['pull_compensation']==.3
    assert stitches['underlay_inset']==.7 and stitches['underlay_spacing']==2.3


def test_invalid_fabric_settings_leave_conversion_unchanged(dialog):
    before=dialog.preset_settings()
    with pytest.raises(ValueError):dialog.apply_fabric_preset({'spacing':.5})
    assert dialog.preset_settings()==before


def test_fabric_change_retains_region_density_and_angle_corrections(dialog):
    dialog.region_spacing={'0':.8};dialog.region_angles={'0':25}
    dialog.project=object();dialog.review_snapshot=object()
    dialog.apply_fabric_preset(dict(spacing=.5,pull_compensation=.2,underlay_inset=.5,underlay_spacing=2,underlay_style='edge'))
    assert dialog.region_spacing=={'0':.8} and dialog.region_angles=={'0':25}
    assert dialog.project is None and dialog.review_snapshot is None
    assert all(control.isEnabled() for control in dialog.stitch_settings.values())


def test_fabric_preset_can_disable_both_generated_underlays(dialog):
    dialog.apply_fabric_preset(dict(spacing=.5,pull_compensation=.2,underlay_inset=.5,underlay_spacing=2,underlay_style='edge',underlay=False))
    dialog.runner.load=lambda _:None;dialog.generate()
    settings=dialog.runner.options['stitch_settings']
    assert settings['underlay']==settings['fill_underlay']==settings['satin_underlay']=='off'
