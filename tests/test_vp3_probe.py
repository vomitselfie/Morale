import pytest
from morale.vp3_probe import build_probe
from morale.model import Project


def test_probe_preserves_distinct_sources_and_exposes_lost_landings(tmp_path):
    root=tmp_path/'probe';report=build_probe(root)
    assert not report['external_files'] and not report['physical_sewouts']
    a=Project.loads((root/'landing-4/source.morale').read_text())
    b=Project.loads((root/'landing-8/source.morale').read_text())
    assert a.objects[0].stitch_data!=b.objects[0].stitch_data
    assert report['formats']['.vp3']['identical_bytes_for_different_jump_landings']
    for extension in ('.pes','.exp'):
        assert not report['formats'][extension]['identical_bytes_for_different_jump_landings']
        for case in report['cases']:
            geometry=case['exports'][extension]['comparison']['sewn_geometry']
            assert all(geometry[d]['complete'] and geometry[d]['outside_samples']==0 for d in ('decoded_outside_source','source_outside_decoded'))
    with pytest.raises(FileExistsError):build_probe(root)
