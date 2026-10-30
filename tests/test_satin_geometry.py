import math
import pytest
from morale.engine import satin


def circular_rails(turns):
    points=[]
    for i in range(turns+1):
        angle=i*math.pi/4
        points.extend([(r*math.cos(angle),r*math.sin(angle)) for r in (8,12)])
    return points


def test_looping_column_rejects_global_overlap_despite_valid_local_cells():
    with pytest.raises(ValueError,match='rail cells .* overlap'):
        satin(circular_rails(10),.4,6)


def test_closed_seam_and_adjacent_edges_remain_valid():
    assert satin(circular_rails(8),.4,6)
    assert satin([(0,0),(4,0),(0,5),(4,5),(0,10),(4,10)],.4,6)


def test_lettering_opt_out_preserves_intentional_overlaps():
    assert satin(circular_rails(10),.4,6,strict=False)


def test_tapered_cells_remain_valid():
    assert satin([(0,0),(0,0),(-2,5),(2,5),(-2,10),(2,10)],.4,6)


@pytest.mark.parametrize('rotation,mirror',[(0,1),(.31,-1),(1.17,1)])
def test_compensation_rejects_fold_in_otherwise_valid_curved_column(rotation,mirror):
    points=[(mirror*r*math.cos(i*math.pi/16+rotation),r*math.sin(i*math.pi/16+rotation))
            for i in range(25) for r in (.2,2)]
    original=list(points)
    assert satin(points,.4,6) and satin(points,.4,6,.1)
    with pytest.raises(ValueError,match='Pull compensation produces invalid satin rails'):
        satin(points,.4,6,.5)
    assert points==original
    assert satin(points,.4,6,.5,strict=False)


def test_compensated_closed_seam_and_taper_remain_valid():
    assert satin(circular_rails(8),.4,6,.5)
    assert satin([(0,0),(0,0),(-2,5),(2,5),(-2,10),(2,10)],.4,6,.5)


@pytest.mark.parametrize('rotation,mirror',[(.31,1),(.31,-1),(1.17,1)])
def test_overlap_check_follows_rotation_translation_and_mirroring(rotation,mirror):
    c,s=math.cos(rotation),math.sin(rotation)
    def transform(points):
        return [(100+mirror*x*c-y*s,-50+mirror*x*s+y*c) for x,y in points]
    with pytest.raises(ValueError,match='rail cells .* overlap'):
        satin(transform(circular_rails(10)),.4,6)
    assert satin(transform(circular_rails(8)),.4,6)


def test_native_rail_edit_rejection_preserves_design_history_and_redo():
    from PySide6.QtWidgets import QApplication
    from morale.app import MainWindow
    from morale.model import Project,DesignObject
    app=QApplication.instance() or QApplication([])
    obj=DesignObject(kind='satin',stitch_type='satin',width=24,height=24,underlay=False,
        points=[[x/24,y/24] for x,y in circular_rails(6)])
    window=MainWindow()
    try:
        window.replace_project(Project(objects=[obj]));window.select(obj.id)
        window.replace_points(circular_rails(8));accepted=window.project.dumps()
        window.undo()
        before=window.project.dumps();history=list(window.history);future=list(window.future)
        with pytest.raises(ValueError,match='Split the column or adjust its rails'):
            window.replace_points(circular_rails(10))
        assert window.project.dumps()==before
        assert window.history==history and window.future==future
        window.redo();assert window.project.dumps()==accepted
    finally:
        window.saved=window.project.dumps();window.close()


@pytest.mark.parametrize('extension',['dst','exp','jef','pec','pes','tbf','u01','vp3','xxx'])
@pytest.mark.parametrize('compensation',[0,.5])
def test_valid_closed_satin_seam_exports_with_complete_path(tmp_path,extension,compensation):
    from morale.model import Project,DesignObject
    from morale.engine import generate
    from morale.formats import export_machine
    from morale.export_verify import verify_export
    obj=DesignObject(kind='satin',stitch_type='satin',width=24,height=24,underlay=False,pull_compensation=compensation,
        points=[[x/24,y/24] for x,y in circular_rails(8)])
    project=Project(objects=[obj]);blocks=generate(project)
    path=tmp_path/f'closed.{extension}';export_machine(project,path,blocks)
    result=verify_export(blocks,path)
    assert result['complete_path_comparison']
    assert result['bounds_delta_mm']<=.3
    if extension=='vp3':
        assert result['problems']==['Trim commands increased: 0 in the design, 1 in the reopened file. Review added controls before sewing.']
    else:
        assert not result['problems']


@pytest.mark.parametrize('vertical',[False,True])
def test_long_narrow_column_at_project_rail_limit(vertical):
    from morale.satin_geometry import overlapping_cells
    pairs=[((i*.1,-.2),(i*.1,.2)) for i in range(1000)]
    if vertical:pairs=[tuple((y,x) for x,y in pair) for pair in pairs]
    assert overlapping_cells(pairs) is None
    stitches=satin([p for pair in pairs for p in pair],.4,6)
    assert stitches and all(math.isfinite(s.x) and math.isfinite(s.y) for s in stitches)
