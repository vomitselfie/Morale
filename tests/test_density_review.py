import base64
import json
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage
from morale.engine import Block,Stitch,generate
from morale.density_review import measure_density,render_density

@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])

def test_counts_only_needle_penetrations_including_repeated_points():
    blocks=[Block('a','#ff0000',[Stitch(.2,.2),Stitch(.2,.2),Stitch(.2,.2,'trim'),Stitch(10,10,'jump'),Stitch(10,10,'stop')])]
    report,cells=measure_density(blocks)
    assert report['penetrations']==2 and report['peak_per_mm2']==2 and cells=={(0,0):2}

def test_fixed_grid_handles_negative_coordinates_and_boundaries():
    points=[(-.01,-.01),(0,0),(.99,.99),(1,1),(-1,-1)]
    report,cells=measure_density([Block('a','#ff0000',[Stitch(*p) for p in points])])
    assert cells=={(-1,-1):2,(0,0):2,(1,1):1}
    assert report['occupied_cells']==3 and report['origin_mm']==[0,0]

def test_overlap_counts_object_identity_not_color_or_block_count():
    blocks=[Block('a','#ff0000',[Stitch(.1,.1)]),Block('a','#ff0000',[Stitch(.2,.2)]),Block('b','#ff0000',[Stitch(.3,.3)])]
    report,_=measure_density(blocks)
    assert report['multi_object_cells']==1 and report['hottest_cells'][0]['objects']==2
    assert report['peak_per_mm2']==3

def test_generated_ties_underlay_and_hidden_objects_match_command_count():
    from morale.model import Project,DesignObject
    project=Project(objects=[DesignObject(tie_in=True,tie_off=True,underlay=True),DesignObject(visible=False)])
    blocks=generate(project);report,_=measure_density(blocks)
    assert report['penetrations']==sum(s.command=='stitch' for b in blocks for s in b.stitches)
    assert report['multi_object_cells']==0

def test_empty_design_and_report_image():
    report,cells=measure_density([])
    assert report['peak_per_mm2']==0 and not report['hottest_cells']
    image=render_density(report,cells)
    assert not image.isNull() and (image.width(),image.height())==(640,520)

def test_hotspot_report_is_bounded_and_deterministic():
    blocks=[Block('a','#ff0000',[Stitch(i,0) for i in range(100)])]
    report,_=measure_density(blocks)
    assert len(report['hottest_cells'])==20
    assert [c['x_mm'] for c in report['hottest_cells']]==list(range(20))

def test_heatmap_colors_encode_relative_count():
    blocks=[Block('a','#ff0000',[Stitch(0,0)]*10+[Stitch(1,0)])]
    report,cells=measure_density(blocks);image=render_density(report,cells)
    assert image.pixelColor(170,250).green()<image.pixelColor(470,250).green()

def test_worker_density_and_native_invalidation(tmp_path):
    from morale.raster_trace import worker_main
    from morale.trace_dialog import TraceDialog
    from morale.model import Project
    from morale.trace_quality import quality_text
    path=tmp_path/'source.svg';path.write_text('<svg width="40" height="40"><rect x="5" y="5" width="30" height="30" fill="red"/></svg>')
    output=tmp_path/'output';output.mkdir()
    assert worker_main([str(path),str(output),json.dumps(dict(width=40,stitch_mode='fill'))])==0
    info=json.loads((output/'preview.json').read_text());project=Project.loads(info['project'])
    report=info['trace_stats']['quality']['density']
    assert report['penetrations']==sum(s.command=='stitch' for b in generate(project) for s in b.stitches)
    thread=info['trace_stats']['quality']['thread_density']
    assert thread['complete'] and thread['mapped_sewn_mm']==pytest.approx(thread['total_sewn_mm'])
    assert not QImage.fromData(base64.b64decode(info['thread_density_png'])).isNull()
    assert 'Needle penetrations:' in quality_text(info['trace_stats']['quality'])
    assert not QImage.fromData(base64.b64decode(info['density_png'])).isNull()
    dialog=TraceDialog(str(path))
    try:
        dialog.ready(str(output/'preview.png'),info,QImage(str(output/'preview.png')))
        assert dialog.density_button.isEnabled() and not dialog.density_image.isNull()
        assert not dialog.thread_density_image.isNull()
        dialog.invalidate_preview()
        assert not dialog.density_button.isEnabled() and dialog.density_image.isNull()
        assert dialog.thread_density_image.isNull()
    finally:dialog.close()

def test_standalone_worker_initializes_font_database(tmp_path):
    import subprocess,sys,os
    source=tmp_path/'image.svg';source.write_text('<svg width="40" height="40"><rect width="10" height="10"/></svg>')
    output=tmp_path/'worker';output.mkdir()
    result=subprocess.run([sys.executable,'-m','morale.raster_trace','--worker',str(source),str(output),'{}'],
                          env={**os.environ,'QT_QPA_PLATFORM':'offscreen'},capture_output=True,text=True,timeout=15)
    assert result.returncode==0,result.stderr
    info=json.loads((output/'preview.json').read_text())
    assert not QImage.fromData(base64.b64decode(info['density_png'])).isNull()
