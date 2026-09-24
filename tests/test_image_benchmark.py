import pytest
from PySide6.QtWidgets import QApplication
from morale.image_benchmark import build_report


@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])


def test_complete_generated_corpus_reports_geometry_and_export_fidelity(tmp_path):
    root=tmp_path/'review';report=build_report(root)
    assert report['artwork_checks_passed'] and len(report['cases'])==11
    # Known VP3 sewn travel remains a failing release gate, not an exemption.
    assert not report['checks_passed']
    failures=[(row['name'],ext) for row in report['cases'] for ext,result in row['exports'].items() if not result['sewn_path_check']]
    assert len(failures)==7 and {ext for _,ext in failures}=={'.vp3'}
    assert not report['external_files_tested'] and not report['physical_sewouts_tested']
    assert len(report['implementation_sha256'])==64
    assert sum(len(row['exports']) for row in report['cases'])==99
    palette=next(row for row in report['cases'] if row['name']=='reduced-palette-fill')
    assert palette['palette_check'] and palette['stitch_settings_check'] and len(palette['result_palette'])==3
    assert palette['settings']['palette_metric']=='oklab'
    white=next(row for row in report['cases'] if row['name']=='enclosed-white')
    assert white['color_geometry_check'] and white['planned_color_geometry_check']
    assert white['quality']['background_removal']['mode']=='border_white'
    assert '#ffffff' in white['color_geometry']['per_color_area_mm2']
    combined=next(row for row in report['cases'] if row['name']=='holed-fill-routing')
    assert combined['native_sewn_containment']
    assert combined['planned_color_geometry_check']
    for name in ('adjacent-colors','overlapping-colors'):
        assert next(row for row in report['cases'] if row['name']==name)['planned_color_geometry_check']
    assert combined['settings']['route_fill'] and combined['settings']['optimize_fill_angles'] and combined['settings']['internal_trims']
    assert combined['quality']['fill_angles']['after_mm']<=combined['quality']['fill_angles']['before_mm']
    for row in report['cases']:
        assert row['type_check'] and row['vector_check']
        if row['name']!='reduced-palette-fill':assert row['color_geometry_check']
        assert len(row['source_sha256'])==64
        for result in row['exports'].values():
            assert result['bounds_check']
            assert 'same_command_sequence' in result['comparison']
            assert 'travel_path_m' in result['comparison']['decoded']
        assert (root/row['name']/'vectors.svg').exists()
        assert (root/row['name']/'trace.morale').exists()
        from morale.model import Project
        assert Project.loads((root/row['name']/'trace.morale').read_text()).reference
        assert (root/row['name']/'stitches.png').exists()
    assert (root/'review.pdf').read_bytes().startswith(b'%PDF-')
    with pytest.raises(FileExistsError):build_report(root)


def test_pipeline_failure_is_reported_not_silently_skipped(tmp_path,monkeypatch):
    import morale.image_benchmark as benchmark
    def fail(*args):raise ValueError('fixture conversion failed')
    monkeypatch.setattr(benchmark,'worker_main',fail)
    report=build_report(tmp_path/'failed')
    assert not report['checks_passed'] and len(report['cases'])==11
    assert all(row['error']=='fixture conversion failed' and not row['checks_passed'] for row in report['cases'])



def test_planning_color_swap_fails_even_when_vectors_are_correct(tmp_path,monkeypatch):
    import json
    from pathlib import Path
    import morale.image_benchmark as benchmark
    from morale.model import Project
    fixtures=[case for case in benchmark.fixtures() if case[0]=='adjacent-colors']
    monkeypatch.setattr(benchmark,'fixtures',lambda:fixtures)
    original=benchmark.worker_main
    def swap(args):
        result=original(args)
        path=Path(args[1])/'preview.json'
        info=json.loads(path.read_text());project=Project.loads(info['project'])
        project.objects[0].color,project.objects[1].color=project.objects[1].color,project.objects[0].color
        info['project']=project.dumps();path.write_text(json.dumps(info))
        return result
    monkeypatch.setattr(benchmark,'worker_main',swap)
    report=build_report(tmp_path/'swapped');row=report['cases'][0]
    assert row['vector_check'] and row['color_geometry_check']
    assert not row['planned_color_geometry_check'] and not report['checks_passed']
    assert row['planned_color_geometry']['error_ratio']>1.9



@pytest.mark.parametrize('direction',['decoded_outside_source','source_outside_decoded'])
def test_sewn_path_gate_rejects_incomplete_or_missing_evidence(direction):
    from copy import deepcopy
    from morale.image_benchmark import sewn_path_check
    valid={'sewn_geometry':{d:{'complete':True,'samples':20,'outside_samples':0} for d in ('decoded_outside_source','source_outside_decoded')}}
    assert sewn_path_check(valid)
    for key,value in [('complete',False),('samples',0),('outside_samples',1)]:
        broken=deepcopy(valid);broken['sewn_geometry'][direction][key]=value
        assert not sewn_path_check(broken)
    del valid['sewn_geometry'][direction]
    assert not sewn_path_check(valid)
