"""Geometric regressions for SVG borders, independent of stitch heuristics."""
import json
import pytest
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication
from morale.vector_artwork import vector_artwork
from morale.auto_digitize import outline_path,choose_stitches
from morale.model import Project

@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])

def source(tmp_path,shape):
    path=tmp_path/'border.svg'
    path.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40">{shape}</svg>')
    return path

@pytest.mark.parametrize('cap,length',[('butt',20),('round',22),('square',22)])
def test_caps_physical_width_and_unchanged_source(tmp_path,cap,length):
    path=source(tmp_path,f'<path d="M10 20 H30" fill="none" stroke="red" stroke-width="2" stroke-linecap="{cap}"/>')
    before=path.read_bytes()
    project,_,_=vector_artwork(path,width=80,expand_strokes=True)
    assert path.read_bytes()==before
    obj=project.objects[0]
    assert (obj.width,obj.height)==pytest.approx((length*2,4),abs=.01)
    result,_=choose_stitches(project)
    assert result.objects[0].stitch_type=='satin'
    region=outline_path(obj.rings())
    assert region.contains(QPointF(0,0))
    if cap=='round':assert not region.contains(QPointF(21.8,1.8))
    if cap=='square':assert region.contains(QPointF(21.8,1.8))

def test_nonuniform_transform_applies_after_expansion(tmp_path):
    path=source(tmp_path,'<path transform="translate(2 3) scale(2 3)" d="M2 4 H12" fill="none" stroke="red" stroke-width="2"/>')
    project,_,_=vector_artwork(path,width=40,expand_strokes=True)
    obj=project.objects[0]
    assert (obj.x,obj.y,obj.width,obj.height)==pytest.approx((-4,-5,20,6),abs=.001)

@pytest.mark.parametrize('join,limit,inside',[('miter',4,True),('miter',1,False),('bevel',4,False),('round',4,False)])
def test_svg_miter_limit_and_join_shape(tmp_path,join,limit,inside):
    path=source(tmp_path,f'<path d="M10 30 V10 H30" fill="none" stroke="red" stroke-width="4" stroke-linejoin="{join}" stroke-miterlimit="{limit}"/>')
    project,_,_=vector_artwork(path,width=40,expand_strokes=True)
    assert outline_path(project.objects[0].rings()).contains(QPointF(-11.8,-11.8))==inside

def test_closed_border_retains_hole_and_becomes_satin(tmp_path):
    path=source(tmp_path,'<circle cx="20" cy="20" r="12" fill="none" stroke="blue" stroke-width="2"/>')
    project,_,_=vector_artwork(path,width=40,expand_strokes=True)
    region=outline_path(project.objects[0].rings())
    assert not region.contains(QPointF(0,0)) and region.contains(QPointF(12,0))
    result,_=choose_stitches(project)
    assert result.objects[0].stitch_type=='satin'

def test_fill_precedes_border_and_wide_border_uses_fill(tmp_path):
    path=source(tmp_path,'<rect x="10" y="10" width="20" height="20" fill="red" stroke="blue" stroke-width="8"/>')
    project,_,stats=vector_artwork(path,width=40,expand_strokes=True)
    assert [o.color.lower() for o in project.objects]==['#ff0000','#0000ff']
    assert any('overlap' in note for note in stats['notes'])
    result,_=choose_stitches(project)
    assert result.objects[1].stitch_type=='fill'

@pytest.mark.parametrize('extension',['dst','exp','jef','pec','pes','tbf','u01','vp3','xxx'])
def test_expanded_border_worker_and_machine_exports(tmp_path,extension):
    from morale.raster_trace import worker_main
    from morale.formats import export_machine,import_machine
    from morale.engine import generate
    path=source(tmp_path,'<path d="M10 20 H30" fill="none" stroke="red" stroke-width="2"/>')
    output=tmp_path/'worker';output.mkdir()
    assert worker_main([str(path),str(output),json.dumps(dict(width=40,expand_strokes=True,stitch_mode='auto'))])==0
    project=Project.loads(json.loads((output/'preview.json').read_text())['project'])
    assert project.objects[0].stitch_type=='satin'
    machine=tmp_path/f'border.{extension}';export_machine(project,machine)
    sewn=[s for b in generate(import_machine(machine).project) for s in b.stitches if s.command=='stitch']
    assert sewn and max(s.y for s in sewn)-min(s.y for s in sewn)==pytest.approx(2,abs=.15)

def test_native_option_invalidates_geometry_choices(tmp_path):
    from morale.trace_dialog import TraceDialog
    dialog=TraceDialog(str(source(tmp_path,'<path d="M10 20 H30" stroke="red"/>')))
    try:
        assert not dialog.expand_strokes.isHidden() and not dialog.expand_strokes.isChecked()
        dialog.overrides={'0':'fill'};dialog.seams={'0':20}
        dialog.expand_strokes.setChecked(True)
        assert dialog.overrides=={} and dialog.seams=={}
    finally:dialog.close()

@pytest.mark.parametrize('setting',[1,'yes',None])
def test_invalid_expansion_setting(tmp_path,setting):
    with pytest.raises(ValueError,match='expansion'):vector_artwork(source(tmp_path,''),expand_strokes=setting)
