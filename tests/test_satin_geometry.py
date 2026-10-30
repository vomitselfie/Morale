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
def test_compensation_past_curve_center_fans_in_otherwise_valid_column(rotation,mirror):
    points=[(mirror*r*math.cos(i*math.pi/16+rotation),r*math.sin(i*math.pi/16+rotation))
            for i in range(25) for r in (.2,2)]
    original=list(points)
    assert satin(points,.4,6) and satin(points,.4,6,.1)
    # Compensation reaches past the center of the curve; the inner side pivots there.
    stitches=satin(points,.4,6,.5)
    assert min(math.hypot(s.x,s.y) for s in stitches if s.command=='stitch')<1e-6
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


def arc_rails(center_radius,width,steps=8,step=math.pi/16):
    return [(r*math.cos(i*step),r*math.sin(i*step)) for i in range(steps+1)
            for r in (center_radius-width/2,center_radius+width/2)]


def landings(stitches):
    return [(s.x,s.y) for s in stitches if s.command=='stitch']


@pytest.mark.parametrize('center_radius',[1.5,1,.4])
def test_corner_tighter_than_column_sews_as_fan(center_radius):
    from morale.satin_geometry import validate_cells,pivot_corners
    points=arc_rails(center_radius,4);original=list(points)
    pairs=list(zip(points[::2],points[1::2]))
    with pytest.raises(ValueError,match='cross or fold'):validate_cells(pairs)
    pivoted=pivot_corners(pairs)
    assert all(math.dist(left,(0,0))<1e-9 for left,right in pivoted)
    assert [right for left,right in pivoted]==[right for left,right in pairs]
    stitches=satin(points,.4,6)
    assert points==original
    # Nothing is sewn past the pivot on the inner side.
    assert all(math.hypot(x,y)<=center_radius+2+1e-6 for x,y in landings(stitches))
    assert min(math.hypot(x,y) for x,y in landings(stitches))<1e-9


def test_fan_alternates_full_and_short_stitches_at_pivot():
    from morale.satin_geometry import SHORT_STITCH_INSET
    stitches=satin(arc_rails(1.5,4),.4,6)
    inner=[math.hypot(x,y) for x,y in landings(stitches) if math.hypot(x,y)<1.5]
    assert inner.count(0)>=2
    short=[r for r in inner if r>1e-9]
    # Interpolated stations lie on chords, just inside the 3.5 mm outer arc.
    assert short and all(r==pytest.approx(3.5*SHORT_STITCH_INSET,rel=.01) for r in short)
    assert abs(len(short)-inner.count(0))<=1


def test_straight_and_gentle_columns_keep_full_stitches():
    for points in ([(0,0),(4,0),(0,30),(4,30)],arc_rails(20,4,steps=16)):
        pairs=list(zip(points[::2],points[1::2]))
        def rail_distance(p):
            def segment_distance(a,b):
                dx,dy=b[0]-a[0],b[1]-a[1]
                k=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(dx*dx+dy*dy)))
                return math.dist(p,(a[0]+dx*k,a[1]+dy*k))
            return min(segment_distance(pa[rail],pb[rail]) for rail in (0,1) for pa,pb in zip(pairs,pairs[1:]))
        assert max(rail_distance(p) for p in landings(satin(points,.4,6)))<1e-6


def test_compensation_at_tight_corner_pivots_instead_of_rejecting():
    from morale.satin_geometry import validate_cells
    points=arc_rails(2.5,4)
    pairs=list(zip(points[::2],points[1::2]))
    validate_cells(pairs)
    expanded=[((l[0]-(r[0]-l[0])/4,l[1]-(r[1]-l[1])/4),(r[0]+(r[0]-l[0])/4,r[1]+(r[1]-l[1])/4)) for l,r in pairs]
    with pytest.raises(ValueError,match='cross or fold'):validate_cells(expanded)
    stitches=satin(points,.4,6,1)
    assert max(math.hypot(x,y) for x,y in landings(stitches))==pytest.approx(5.5)


def test_swapped_rails_are_rejected_not_fanned():
    with pytest.raises(ValueError,match='cross or fold'):
        satin([(-5,-5),(5,5),(-5,5),(5,-5)],.4,6)


def v_column(angle,width,leg=10):
    """Rungs square to each leg of a V, as tracing and the coupons produce."""
    from morale.coupons import satin as coupon_satin
    half=math.radians(angle)/2
    obj=coupon_satin([(-leg*math.sin(half),-leg*math.cos(half)),(0,0),(leg*math.sin(half),-leg*math.cos(half))],width,'V')
    return obj.transform(obj.points)


@pytest.mark.parametrize('angle',[120,90,60,45,30])
@pytest.mark.parametrize('width',[2,4])
def test_sharp_corner_fans_around_inner_corner_point(angle,width):
    from morale.satin_geometry import pivot_corners,overlapping_cells
    points=v_column(angle,width)
    pairs=list(zip(points[::2],points[1::2]))
    inner=(0,-width/2/math.sin(math.radians(angle)/2))
    pivoted=pivot_corners(pairs)
    assert overlapping_cells(pivoted) is None
    # No inner rail point is left past the corner where the inner edges meet.
    assert all(left[1]<=inner[1]+1e-6 for left,right in pivoted)
    assert sum(math.dist(left,inner)<1e-6 for left,right in pivoted)>=3
    for compensation in (0,.4):
        assert satin(points,.4,6,compensation)


def test_long_rail_loop_is_an_overlap_not_a_corner():
    from morale.satin_geometry import clip_rail_loops
    loop=[(r*math.cos(i*math.pi/4),r*math.sin(i*math.pi/4)) for i in range(11) for r in (12,)]
    assert clip_rail_loops(loop,8)==loop
