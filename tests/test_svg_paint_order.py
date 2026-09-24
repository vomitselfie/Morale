import json
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPointF
from morale.svg_import import import_svg,paint_order
from morale.vector_artwork import vector_artwork
from morale.auto_digitize import outline_path
from morale.trace_overlap import remove_covered_fill
from morale.model import Project

@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])


def source(tmp_path,order='stroke',extra=''):
    path=tmp_path/'order.svg'
    path.write_text(f'<svg width="40" height="40"><g style="paint-order:{order}"><rect id="badge" x="10" y="10" width="20" height="20" fill="red" stroke="blue" stroke-width="4" {extra}/></g></svg>')
    return path


@pytest.mark.parametrize('order,first',[('normal','fill'),('fill','fill'),('markers','fill'),('stroke','stroke'),('markers stroke','stroke'),('stroke fill markers','stroke')])
@pytest.mark.parametrize('mode',['direct','expanded','centerline'])
def test_order_preserves_geometry_and_visible_layers(tmp_path,order,first,mode):
    path=source(tmp_path,order);before=path.read_bytes()
    if mode=='direct':objects=import_svg(path).objects
    else:
        project,image,_=vector_artwork(path,width=40,resolution=512,expand_strokes=mode=='expanded');objects=project.objects
        # Inside the rectangle, within the inward half of its border.
        assert image.pixelColor(round(11*512/40),256).name()==('#ff0000' if first=='stroke' else '#0000ff')
    assert [o.color for o in objects]==(['#0000ff','#ff0000'] if first=='stroke' else ['#ff0000','#0000ff'])
    assert path.read_bytes()==before and Project.loads(Project(objects=objects).dumps()).objects==objects


def test_local_style_overrides_inherited_order(tmp_path):
    project,_,_=vector_artwork(source(tmp_path,'stroke','style="paint-order:fill"'),width=40,expand_strokes=True)
    assert [o.color for o in project.objects]==['#ff0000','#0000ff']


def test_overlap_removal_keeps_the_correct_upper_color(tmp_path):
    project,_,_=vector_artwork(source(tmp_path),width=40,expand_strokes=True)
    result,stats=remove_covered_fill(project,0)
    assert stats['removed_area_mm2']>0
    assert not outline_path(result.objects[0].rings()).contains(QPointF(-9,0))
    assert outline_path(result.objects[1].rings()).contains(QPointF(-9,0))
    assert outline_path(result.objects[0].rings()).contains(QPointF(-11,0))


@pytest.mark.parametrize('bad',['','stroke stroke','normal fill','stroke,fill','bogus'])
def test_invalid_order_rejected(bad):
    with pytest.raises(ValueError,match='paint-order'):paint_order(bad)


@pytest.mark.parametrize('extension',['dst','exp','jef','pec','pes','tbf','u01','vp3','xxx'])
def test_worker_and_machine_thread_order(tmp_path,extension):
    from morale.raster_trace import worker_main
    from morale.formats import export_machine,import_machine
    from morale.engine import generate
    path=source(tmp_path);out=tmp_path/'worker';out.mkdir()
    assert worker_main([str(path),str(out),json.dumps({'width':40,'expand_strokes':True,'stitch_mode':'fill'})])==0
    project=Project.loads(json.loads((out/'preview.json').read_text())['project'])
    assert [o.color for o in project.objects]==['#0000ff','#ff0000']
    machine=tmp_path/f'order.{extension}';export_machine(project,machine)
    # Formats without a stored palette cannot prove RGB identity. Geometry
    # identifies the first (outer border) and second (inner fill) stitch blocks.
    blocks=generate(import_machine(machine).project)
    widths=[]
    for block in blocks:
        xs=[s.x for s in block.stitches if s.command=='stitch']
        if xs:widths.append(max(xs)-min(xs))
    assert len(widths)==2
    assert widths==pytest.approx([24,20],abs=.15)


def test_reordering_stays_within_each_shape(tmp_path):
    path=tmp_path/'neighbors.svg'
    path.write_text('<svg width="80" height="40"><rect width="5" height="5" fill="green"/><path d="M10 10 H20 V20 H10 Z M30 10 H40 V20 H30 Z" fill="red" stroke="blue" paint-order="stroke"/><rect x="50" width="5" height="5" fill="yellow"/></svg>')
    objects=import_svg(path).objects
    assert [o.color for o in objects]==['#008000','#0000ff','#0000ff','#ff0000','#ffff00']
    assert [o.stitch_type for o in objects]==['fill','running','running','fill','fill']
