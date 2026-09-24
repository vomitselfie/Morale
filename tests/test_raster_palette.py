import json
import pytest
from PySide6.QtGui import QImage,QColor
from PySide6.QtWidgets import QApplication
from morale.raster_palette import quantize,lab,squared
from morale.raster_trace import trace_image,worker_main
from morale.model import Project
from morale.engine import generate


@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])


def test_gray_ramp_reduces_perceptual_error_at_equal_color_budget():
    histogram={(v,v,v):1 for v in range(256)}
    rgb,rgb_map,_=quantize(histogram,3,'rgb')
    palette,mapping,report=quantize(histogram,3,'oklab')
    def error(result):return sum(squared(lab(c),lab(result[c])) for c in histogram)
    assert len(palette)==len(rgb)==3
    assert error(mapping)<error(rgb_map)*.75
    assert report['fit_error_after']<=report['fit_error_before']
    assert quantize(dict(reversed(list(histogram.items()))),3,'oklab')==(palette,mapping,report)


def test_small_flat_palette_preserves_even_similar_colors_exactly():
    histogram={(16,16,16):50,(17,17,17):2,(255,0,0):20}
    palette,mapping,_=quantize(histogram,3,'oklab')
    assert set(palette)==set(histogram) and all(c==v for c,v in mapping.items())


def test_population_weight_changes_single_swatch():
    dark=(30,30,30);light=(220,220,220)
    dark_palette=quantize({dark:99,light:1},1,'oklab')[0][0]
    light_palette=quantize({dark:1,light:99},1,'oklab')[0][0]
    assert squared(lab(dark_palette),lab(dark))<.001
    assert squared(lab(light_palette),lab(light))<.001
    assert dark_palette!=light_palette


def test_large_histogram_has_bounded_fit_and_complete_assignment():
    histogram={(r,g,b):1 for r in range(0,256,15) for g in range(0,256,15) for b in range(0,256,15)}
    palette,mapping,report=quantize(histogram,2,'oklab')
    assert report['fit_colors']<=4096 and report['iterations']<=8
    assert len(mapping)==len(histogram) and set(mapping.values())<=set(palette)
    assert report['fit_error_after']<=report['fit_error_before']+1e-12


def artwork(tmp_path):
    image=QImage(64,32,QImage.Format.Format_ARGB32);image.fill(QColor('transparent'))
    for y in range(4,28):
        for x in range(4,60):image.setPixelColor(x,y,QColor(30 if x<32 else 180,50,100))
    path=tmp_path/'colors.png';assert image.save(str(path));return path


@pytest.mark.parametrize('method',['pixels','smooth'])
def test_perceptual_trace_preserves_palette_transparency_and_frame(tmp_path,method):
    path=artwork(tmp_path);before=path.read_bytes()
    project,image,stats=trace_image(path,width=32,resolution=64,colors=2,minimum_region=1,method=method,palette_metric='oklab',smoothing=0)
    assert path.read_bytes()==before and image.pixelColor(0,0).alpha()==0
    assert {o.color.lower() for o in project.objects}=={'#1e3264','#b43264'}
    assert stats['palette_reduction']['metric']=='oklab' and stats['artwork_size_mm']==[32,16]
    assert Project.loads(project.dumps()).objects==project.objects
    assert all(-14.1<=s.x<=14.1 and -6.1<=s.y<=6.1 for b in generate(project) for s in b.stitches)


@pytest.mark.parametrize('metric',[None,True,'unsupported'])
def test_invalid_metric_rejected_before_reading_file(tmp_path,metric):
    with pytest.raises(ValueError,match='palette reduction'):trace_image(tmp_path/'missing.png',palette_metric=metric)


def test_worker_and_native_control_invalidate_region_choices(tmp_path):
    from morale.trace_dialog import TraceDialog
    from morale.trace_quality import quality_text
    path=artwork(tmp_path);output=tmp_path/'out';output.mkdir()
    assert worker_main([str(path),str(output),json.dumps(dict(width=32,resolution=64,colors=2,minimum_region=1,method='smooth',palette_metric='oklab'))])==0
    info=json.loads((output/'preview.json').read_text())
    assert 'Raster palette: Oklab' in quality_text(info['trace_stats']['quality'])
    dialog=TraceDialog(str(path))
    try:
        assert dialog.palette_metric.currentData()=='oklab'
        dialog.overrides={'0':'fill'};dialog.seams={'0':30}
        dialog.palette_metric.setCurrentIndex(1)
        assert not dialog.overrides and not dialog.seams
        dialog.runner.start=lambda path:None
        dialog.generate()
        assert dialog.runner.options['palette_metric']=='rgb'
    finally:dialog.close()
