import json
from copy import deepcopy
import pytest
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication
from morale.model import Project,DesignObject
from morale.trace_overlap import remove_covered_fill
from morale.auto_digitize import outline_path,area,difference_area

@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])

def rectangle(x=0,y=0,width=20,height=20,color='#ff0000',**kwargs):
    return DesignObject(kind='rectangle',x=x,y=y,width=width,height=height,color=color,underlay=False,**kwargs)

def test_exact_knockout_keeps_visible_union_and_creates_hole():
    source=Project(objects=[rectangle(),rectangle(width=10,height=10,color='#0000ff')]);before=source.dumps()
    result,report=remove_covered_fill(source,0)
    assert source.dumps()==before
    lower,upper=result.objects
    region=outline_path(lower.rings())
    assert area(region)==pytest.approx(300)
    assert not region.contains(QPointF(0,0)) and region.contains(QPointF(8,0))
    assert upper==source.objects[1] and lower.id==source.objects[0].id
    assert difference_area(region.united(outline_path(upper.rings())),outline_path(source.objects[0].rings()))<.001
    assert report['removed_area_mm2']==pytest.approx(100)
    assert Project.loads(result.dumps()).objects==result.objects

@pytest.mark.parametrize('allowance',[0,.2,1,2])
def test_allowance_is_physical_distance_under_top_region(allowance):
    source=Project(objects=[rectangle(),rectangle(x=10,width=20,color='#0000ff')])
    result,report=remove_covered_fill(source,allowance)
    assert area(outline_path(result.objects[0].rings()))==pytest.approx(400-(10-allowance)*(20-2*allowance),abs=.001)
    assert report['allowance_mm']==allowance
    assert outline_path(result.objects[0].rings()).contains(QPointF(-.1,0))
    assert not outline_path(result.objects[0].rings()).contains(QPointF(allowance+.1,0))

def test_covered_region_removed_and_sewing_order_retained():
    source=Project(objects=[rectangle(width=5,height=5),rectangle(color='#0000ff'),rectangle(x=40)])
    result,report=remove_covered_fill(source,0)
    assert [o.id for o in result.objects]==[o.id for o in source.objects[1:]]
    assert report['removed_regions']==1

def test_three_layers_use_original_coverage():
    source=Project(objects=[rectangle(),rectangle(width=15,height=15,color='#0000ff'),rectangle(width=10,height=10,color='#00ff00')])
    result,_=remove_covered_fill(source,0)
    assert [area(outline_path(o.rings())) for o in result.objects]==pytest.approx([175,125,100])

def test_upper_hole_does_not_remove_lower_visible_fill():
    top=rectangle(color='#0000ff');top.kind='compound'
    top.contours=[[[-.5,-.5],[.5,-.5],[.5,.5],[-.5,.5]],[[-.25,-.25],[.25,-.25],[.25,.25],[-.25,.25]]]
    result,_=remove_covered_fill(Project(objects=[rectangle(),top]),0)
    region=outline_path(result.objects[0].rings())
    assert area(region)==pytest.approx(100)
    assert region.contains(QPointF(0,0)) and not region.contains(QPointF(8,0))

@pytest.mark.parametrize('field,value',[('stop_after',True),('color_break',True),('stage_note','Placement'),('group_id','group'),('visible',False),('stitch_type','running')])
def test_semantic_boundaries_and_nonfill_objects_preserved(field,value):
    middle=rectangle();setattr(middle,field,value)
    project=Project(objects=[rectangle(),middle,rectangle(color='#0000ff')])
    result,report=remove_covered_fill(project,0)
    assert result==project and not report['changes']

@pytest.mark.parametrize('value',[-1,3,True,None,float('nan')])
def test_invalid_allowance(value):
    with pytest.raises(ValueError,match='allowance'):remove_covered_fill(Project(),value)

@pytest.mark.parametrize('extension',['dst','exp','jef','pec','pes','tbf','u01','vp3','xxx'])
def test_nine_exports_do_not_sew_lower_color_through_hole(tmp_path,extension):
    from morale.formats import export_machine,import_machine
    from morale.engine import generate
    source=Project(objects=[rectangle(),rectangle(width=10,height=10,color='#0000ff')])
    result,_=remove_covered_fill(source,0)
    path=tmp_path/f'cut.{extension}';export_machine(result,path)
    blocks=generate(import_machine(path).project)
    stitches=[s for s in blocks[0].stitches if s.command=='stitch']
    assert stitches and not any(-4.8<s.x<4.8 and -4.8<s.y<4.8 for s in stitches)

def test_worker_svg_border_overlap_and_atomic_undo(tmp_path):
    from morale.raster_trace import worker_main
    from morale.app import MainWindow
    path=tmp_path/'layered.svg';path.write_text('<svg width="40" height="40"><rect x="5" y="5" width="30" height="30" fill="red"/><rect x="10" y="10" width="20" height="20" fill="blue"/></svg>')
    output=tmp_path/'output';output.mkdir()
    assert worker_main([str(path),str(output),json.dumps(dict(width=40,remove_overlap=True,overlap_allowance=0,stitch_mode='fill',keep_reference=True))])==0
    info=json.loads((output/'preview.json').read_text());project=Project.loads(info['project'])
    assert info['trace_stats']['quality']['overlap']['removed_area_mm2']==pytest.approx(400,abs=.01)
    assert not outline_path(project.objects[0].rings()).contains(QPointF(0,0))
    window=MainWindow()
    try:
        before=window.project.dumps();window.apply_raster_trace(project)
        assert window.project.reference
        window.undo();assert window.project.dumps()==before
    finally:window.saved=window.project.dumps();window.close()

def test_dialog_geometry_settings_clear_overrides(tmp_path):
    from morale.trace_dialog import TraceDialog
    dialog=TraceDialog(str(tmp_path/'source.svg'))
    try:
        dialog.overrides={'0':'satin'};dialog.seams={'0':25}
        dialog.remove_overlap.setChecked(True)
        assert dialog.overlap_allowance.isEnabled() and not dialog.overrides and not dialog.seams
        dialog.overrides={'0':'fill'};dialog.overlap_allowance.setValue(.5)
        assert not dialog.overrides
    finally:dialog.close()

def test_rotated_occluder_preserves_visible_geometry():
    top=rectangle(width=10,height=10,rotation=35,color='#0000ff')
    source=Project(objects=[rectangle(),top])
    result,_=remove_covered_fill(source,0)
    lower=outline_path(result.objects[0].rings());upper=outline_path(top.rings())
    assert area(lower)==pytest.approx(300,abs=.001)
    assert difference_area(lower.united(upper),outline_path(source.objects[0].rings()))<.001

def test_disconnected_remainder_retained_as_editable_contours():
    result,_=remove_covered_fill(Project(objects=[rectangle(),rectangle(width=4,height=30,color='#0000ff')]),0)
    lower=result.objects[0];region=outline_path(lower.rings())
    assert len(lower.contours)==2 and area(region)==pytest.approx(320)
    assert region.contains(QPointF(-5,0)) and region.contains(QPointF(5,0))
    assert not region.contains(QPointF(0,0))

def test_expanded_circle_border_removes_underlying_fill(tmp_path):
    from morale.vector_artwork import vector_artwork
    path=tmp_path/'circle.svg';path.write_text('<svg width="40" height="40"><circle cx="20" cy="20" r="12" fill="red" stroke="blue" stroke-width="2"/></svg>')
    source,_,_=vector_artwork(path,width=40,expand_strokes=True)
    result,report=remove_covered_fill(source,.2)
    lower=outline_path(result.objects[0].rings())
    assert lower.contains(QPointF(0,0)) and not lower.contains(QPointF(11.8,0))
    assert report['removed_area_mm2']>50


def test_traced_coincident_hole_does_not_hide_a_separate_real_overlap(tmp_path):
    from morale.image_benchmark import make_source
    from morale.raster_trace import worker_main
    from morale.svg_import import import_svg_text
    objects=[rectangle(width=24,height=24,color='#2266bb'),rectangle(width=12,height=12,color='#cc3355')]
    source=tmp_path/'nested.png';make_source(objects,source)
    out=tmp_path/'trace';out.mkdir()
    assert worker_main([str(source),str(out),json.dumps({'width':40,'method':'smooth','resolution':512,'colors':6,'minimum_region':1,'smoothing':.15,'stitch_mode':'fill'})])==0
    info=json.loads((out/'preview.json').read_text())
    traced=import_svg_text(info['trace_svg'],center_artwork=False).objects
    assert len(traced[0].contours)==2
    project=Project(objects=traced+[rectangle(x=9,width=2,height=4,color='#00ff00')]);before=project.dumps()
    result,report=remove_covered_fill(project,0)
    assert project.dumps()==before
    lower=outline_path(result.objects[0].rings())
    assert report['removed_area_mm2']==pytest.approx(8,abs=.001)
    assert area(lower)==pytest.approx(area(outline_path(project.objects[0].rings()))-8,abs=.001)
    assert not lower.contains(QPointF(0,0)) and not lower.contains(QPointF(9,0))
    assert lower.contains(QPointF(-9,0))
    assert result.objects[1:]==project.objects[1:]
