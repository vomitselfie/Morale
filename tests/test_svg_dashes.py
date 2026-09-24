import pytest
from PySide6.QtCore import QPointF
from PySide6.QtGui import QPainterPathStroker
from PySide6.QtWidgets import QApplication
from morale.vector_artwork import vector_artwork
from morale.auto_digitize import outline_path
from morale.engine import generate
from morale.model import Project

@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])


def convert(tmp_path,pattern='4 2',offset=0,cap='butt',extra='',d='M0 20 H30'):
    path=tmp_path/'dashes.svg'
    path.write_text(f'<svg width="40" height="40"><path d="{d}" fill="none" stroke="red" stroke-width="2" stroke-dasharray="{pattern}" stroke-dashoffset="{offset}" stroke-linecap="{cap}" {extra}/></svg>')
    return vector_artwork(path,width=40,expand_strokes=True)[0]


def region(project):return outline_path([ring for obj in project.objects for ring in obj.rings()])


@pytest.mark.parametrize('offset',[0,1,-1,13,-13])
def test_dash_offset_and_gaps(tmp_path,offset):
    project=convert(tmp_path,offset=offset);shape=region(project)
    for n in range(60):
        x=(n+.25)/2
        assert shape.contains(QPointF(x-20,0))==((x+offset)%6<4)
    edge=QPainterPathStroker();edge.setWidth(.0001)
    tolerance=shape.united(edge.createStroke(shape))
    for block in generate(project):
        previous=None
        for s in block.stitches:
            if s.command=='stitch' and previous is not None:
                for step in range(11):
                    t=step/10
                    assert tolerance.contains(QPointF(previous[0]+t*(s.x-previous[0]),previous[1]+t*(s.y-previous[1])))
            if s.command in {'stitch','jump'}:previous=(s.x,s.y)


def test_odd_dash_list_repeats_entire_list(tmp_path):
    a=region(convert(tmp_path,'4 2 1'));b=region(convert(tmp_path,'4 2 1 4 2 1'))
    assert a==b


@pytest.mark.parametrize('cap',['round','square'])
def test_zero_dash_visible_dots(tmp_path,cap):
    shape=region(convert(tmp_path,'0 4',cap=cap))
    for x in range(0,29,4):assert shape.contains(QPointF(x-20,.4))
    for x in range(2,29,4):assert not shape.contains(QPointF(x-20,0))
    assert shape.contains(QPointF(-19.2,.8))==(cap=='square')


def test_all_zero_pattern_is_solid(tmp_path):
    shape=region(convert(tmp_path,'0 0'))
    assert all(shape.contains(QPointF(x-20,0)) for x in range(1,30))


def test_absolute_units_and_nonuniform_transform(tmp_path):
    a=region(convert(tmp_path,'4px 2px',extra='transform="scale(1 2)"'))
    b=region(convert(tmp_path,'1.05833333333mm .529166666667mm',extra='transform="scale(1 2)"'))
    for x in range(30):
        point=QPointF(x+.25-20,20)
        assert a.contains(point)==b.contains(point)
    assert a.contains(QPointF(-19,21.5)) and not a.contains(QPointF(-19,22.1))


def test_each_subpath_restarts_dash_offset(tmp_path):
    shape=region(convert(tmp_path,d='M0 10 H9 M0 20 H9'))
    for y in (-10,0):
        assert shape.contains(QPointF(-19,y)) and not shape.contains(QPointF(-15,y))


@pytest.mark.parametrize('pattern',['-1 2','nan 2','1% 2','1em 2','1,,2','1,','1e-20 1e-20'])
def test_unsupported_or_excessive_dash_rejected(tmp_path,pattern):
    with pytest.raises(ValueError):convert(tmp_path,pattern)


@pytest.mark.parametrize('authored',[1,10,100])
@pytest.mark.parametrize('offset',[0,1,-1])
def test_calibrated_path_length_matches_analytic_intervals(tmp_path,authored,offset):
    shape=region(convert(tmp_path,pattern=f'{4*authored/30} {2*authored/30}',offset=offset*authored/30,extra=f'pathLength="{authored}"'))
    for n in range(60):
        x=(n+.25)/2
        assert shape.contains(QPointF(x-20,0))==((x+offset)%6<4)


@pytest.mark.parametrize('authored',['0','-1','nan','inf','1mm','1e-320','1e999'])
def test_invalid_or_unsupported_calibration_rejected(tmp_path,authored):
    with pytest.raises(ValueError,match='pathLength'):convert(tmp_path,extra=f'pathLength="{authored}"')


def test_without_expansion_retains_explicit_rejection(tmp_path):
    convert(tmp_path)
    with pytest.raises(ValueError,match='stroke-dasharray'):vector_artwork(tmp_path/'dashes.svg',expand_strokes=False)


def test_inherited_style_local_use_and_source_unchanged(tmp_path):
    path=tmp_path/'inherited.svg'
    text='<svg width="40" height="40"><defs><path id="dash" d="M0 20 H30"/></defs><g style="fill:none;stroke:red;stroke-width:2;stroke-dasharray:4 2;stroke-dashoffset:1"><use href="#dash"/></g></svg>'
    path.write_text(text)
    project,_,_=vector_artwork(path,width=40,expand_strokes=True)
    assert path.read_text()==text
    assert region(project)==region(convert(tmp_path,offset=1))
    assert Project.loads(project.dumps()).objects[0].contours==project.objects[0].contours


@pytest.mark.parametrize('cap',['butt','round','square'])
def test_curved_dashes_agree_with_svg_rendering(tmp_path,cap):
    from PySide6.QtGui import QImage,QPainter
    from PySide6.QtSvg import QSvgRenderer
    project=convert(tmp_path,pattern='5 3',offset=-2,cap=cap,d='M3 20 C3 2 35 2 35 20')
    shape=region(project)
    source=QImage(400,400,QImage.Format.Format_ARGB32);source.fill(0)
    painter=QPainter(source);painter.setRenderHint(QPainter.RenderHint.Antialiasing);QSvgRenderer(str(tmp_path/'dashes.svg')).render(painter);painter.end()
    disagreements=painted=0
    for y in range(400):
        for x in range(400):
            actual=shape.contains(QPointF((x+.5)/10-20,(y+.5)/10-20))
            expected=source.pixelColor(x,y).alpha()>127
            painted+=actual or expected;disagreements+=actual!=expected
    assert disagreements/max(1,painted)<.035


@pytest.mark.parametrize('extension',['dst','exp','jef','pec','pes','tbf','u01','vp3','xxx'])
def test_worker_and_export_bounds(tmp_path,extension):
    import json
    from morale.raster_trace import worker_main
    from morale.formats import export_machine,import_machine
    convert(tmp_path,pattern='.4 .2',extra='pathLength="3"')
    output=tmp_path/'worker';output.mkdir()
    assert worker_main([str(tmp_path/'dashes.svg'),str(output),json.dumps({'width':40,'expand_strokes':True,'stitch_mode':'auto'})])==0
    project=Project.loads(json.loads((output/'preview.json').read_text())['project'])
    path=tmp_path/f'dashes.{extension}';export_machine(project,path)
    before=[s for b in generate(project) for s in b.stitches if s.command=='stitch']
    after=[s for b in generate(import_machine(path).project) for s in b.stitches if s.command=='stitch']
    for axis in ('x','y'):
        for fn in (min,max):assert fn(getattr(s,axis) for s in after)==pytest.approx(fn(getattr(s,axis) for s in before),abs=.15)


def test_calibration_uses_total_length_but_restarts_each_subpath(tmp_path):
    # Two 9-unit subpaths, calibrated to 3: a 2/3 dash becomes 4 units.
    shape=region(convert(tmp_path,pattern='0.6666666666666667 0.3333333333333333',extra='pathLength="3"',d='M0 10 H9 M0 20 H9'))
    for y in (-10,0):
        for x in (1,3,7):assert shape.contains(QPointF(x-20,y))
        assert not shape.contains(QPointF(-15,y))


def test_calibrated_curve_and_nonuniform_transform(tmp_path):
    # This symmetric cubic has exact arc length 40 before scaling.
    d='M5 20 C5 0 25 0 25 20'
    a=region(convert(tmp_path,pattern='.5 .3',offset=-.2,d=d,extra='pathLength="4" transform="scale(1 1.5)"'))
    b=region(convert(tmp_path,pattern='5 3',offset=-2,d=d,extra='transform="scale(1 1.5)"'))
    for yi in range(-30,25):
        for xi in range(-35,20):
            point=QPointF(xi/2+.137,yi/2+.173)
            assert a.contains(point)==b.contains(point)


def test_calibrated_dots_retain_cap_size(tmp_path):
    a=region(convert(tmp_path,pattern='0 .4',cap='round',extra='pathLength="3"'))
    b=region(convert(tmp_path,pattern='0 4',cap='round'))
    assert a==b


def test_group_calibration_is_not_inherited(tmp_path):
    path=tmp_path/'group.svg'
    path.write_text('<svg width="40" height="40"><g pathLength="1"><path d="M0 20 H30" fill="none" stroke="red" stroke-width="2" stroke-dasharray="4 2"/></g></svg>')
    project,_,_=vector_artwork(path,width=40,expand_strokes=True)
    assert region(project)==region(convert(tmp_path))


def test_calibrated_local_reference(tmp_path):
    path=tmp_path/'reference.svg'
    path.write_text('<svg width="40" height="40"><defs><path id="dash" d="M0 20 H30" pathLength="3"/></defs><use href="#dash" fill="none" stroke="red" stroke-width="2" stroke-dasharray=".4 .2"/></svg>')
    project,_,_=vector_artwork(path,width=40,expand_strokes=True)
    assert region(project)==region(convert(tmp_path))
