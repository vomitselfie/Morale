import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from copy import deepcopy

import pytest
from PySide6.QtWidgets import QApplication

from morale.motifs import capture_motif,load_motif,save_motif,motif_paths,validate_packet
from morale.model import DesignObject,Project
from morale.bezier import enable_handles,edit_controls
from morale.formats import export_machine,import_machine
from morale.engine import generate


@pytest.fixture(scope='module',autouse=True)
def app():
    return QApplication.instance() or QApplication([])


def source():
    return DesignObject(name='Corner',kind='path',stitch_type='running',points=[[-.5,-.5],[-.5,.5],[.5,.5]])


def guide():
    packet=capture_motif(source())
    return DesignObject(kind='path',stitch_type='motif',points=[[-.5,0],[.5,0]],
                        motif_pattern='custom',custom_motif_paths=packet['paths'],custom_motif_name=packet['name'])


def test_capture_is_independent_and_retains_open_and_closed_paths():
    obj=source()
    before=deepcopy(obj)
    packet=capture_motif(obj)
    assert obj==before and packet['paths'][0]==[[-.5,-.5],[-.5,.5],[.5,.5]]
    closed=capture_motif(DesignObject(kind='rectangle'))
    assert closed['paths'][0][0]==closed['paths'][0][-1]
    packet['paths'][0][0][0]=0
    assert obj==before


def test_motif_file_and_embedded_project_roundtrip(tmp_path):
    packet=capture_motif(source())
    path=tmp_path/'corner.mmotif'
    save_motif(packet,path)
    assert load_motif(path)==packet
    obj=guide()
    restored=Project.loads(Project(objects=[obj]).dumps()).objects[0]
    assert restored.custom_motif_paths==obj.custom_motif_paths
    assert list(motif_paths(restored))==list(motif_paths(obj))


@pytest.mark.parametrize('bad',[
    {'format':'other','version':1,'name':'Bad','paths':[]},
    {'format':'morale-motif','version':True,'name':'Bad','paths':[]},
    {'format':'morale-motif','version':1,'name':'Bad','paths':[[[0,0],[2,0]]]},
    {'format':'morale-motif','version':1,'name':'Bad','paths':[[[0,0],[0,0]]]},
    {'format':'morale-motif','version':1,'name':'Bad','paths':[[[0,0],[float('nan'),0]]]},
])
def test_bad_custom_motifs_rejected(bad):
    with pytest.raises(ValueError):
        validate_packet(bad)


def test_failed_motif_save_preserves_existing_file(tmp_path,monkeypatch):
    import morale.motifs as module
    path=tmp_path/'corner.mmotif'
    path.write_bytes(b'original')
    def fail(*args):
        raise OSError('cannot replace')
    monkeypatch.setattr(module.os,'replace',fail)
    with pytest.raises(OSError):
        save_motif(capture_motif(source()),path)
    assert path.read_bytes()==b'original' and list(tmp_path.iterdir())==[path]


@pytest.mark.parametrize('axis',['x','y'])
def test_asymmetric_motif_reflects_with_the_guide(axis):
    obj=guide()
    before=list(motif_paths(obj))
    setattr(obj,f'flip_{axis}',True)
    after=list(motif_paths(obj))
    for a,b in zip(before,after):
        for (x,y),point in zip(a,b):
            assert point==pytest.approx((-x,y) if axis=='x' else (x,-y))


def test_bezier_rebasing_keeps_mirrored_motif_orientation():
    obj=enable_handles(guide())
    obj.flip_x=True
    controls=obj.control_points()
    # Translate the complete guide to force rebasing without altering its shape.
    candidate=edit_controls(obj,[(x+1,y) for x,y in controls])
    assert not candidate.flip_x and candidate.motif_reflected
    for before,after in zip(motif_paths(obj),motif_paths(candidate)):
        for (x,y),point in zip(before,after):
            assert point==pytest.approx((x+1,y))


def test_native_capture_apply_and_point_edit_undo():
    from morale.app import MainWindow
    window=MainWindow()
    try:
        original_source=source()
        target=DesignObject(kind='path',stitch_type='running',points=[[-.5,0],[.5,0]],flip_y=True)
        window.replace_project(Project(objects=[original_source,target]))
        before=window.project.dumps()
        window.select(original_source.id)
        window.capture_custom_motif()
        assert window.project.dumps()==before and not window.history
        window.select(target.id)
        window.apply_custom_motif()
        obj=window.selected_object()
        assert obj.motif_pattern=='custom'
        patterns=list(motif_paths(obj))
        window.replace_points([(x+1,y) for x,y in obj.transform(obj.points)])
        for a,b in zip(patterns,motif_paths(window.selected_object())):
            for (x,y),point in zip(a,b):
                assert point==pytest.approx((x+1,y))
        window.undo()
        window.undo()
        assert window.project.dumps()==before
    finally:
        window.saved=window.project.dumps()
        window.close()


def test_saving_selected_motif_is_distinct_from_captured_motif(tmp_path,monkeypatch):
    import morale.app as module
    window=module.MainWindow()
    try:
        obj=guide()
        window.replace_project(Project(objects=[obj]))
        window.select(obj.id)
        window.captured_motif=capture_motif(DesignObject(name='Other',kind='rectangle'))
        path=tmp_path/'selected.mmotif'
        monkeypatch.setattr(module.QFileDialog,'getSaveFileName',lambda *args:(str(path),''))
        window.save_custom_motif(True)
        assert load_motif(path)['name']=='Corner'
        path=tmp_path/'captured.mmotif'
        window.save_custom_motif()
        assert load_motif(path)['name']=='Other'
        assert not window.history
    finally:
        window.saved=window.project.dumps()
        window.close()


@pytest.mark.parametrize('extension',['dst','exp','jef','pec','pes','tbf','u01','vp3','xxx'])
def test_custom_motif_exports_in_all_formats(tmp_path,extension):
    path=tmp_path/f'custom.{extension}'
    project=Project(objects=[guide()])
    source=[s for b in generate(project) for s in b.stitches if s.command=='stitch']
    export_machine(project,path)
    stitches=[s for b in generate(import_machine(path).project) for s in b.stitches if s.command=='stitch']
    assert stitches
    assert (min(s.x for s in stitches),max(s.x for s in stitches),min(s.y for s in stitches),max(s.y for s in stitches))==pytest.approx(
        (min(s.x for s in source),max(s.x for s in source),min(s.y for s in source),max(s.y for s in source)),abs=.15)
