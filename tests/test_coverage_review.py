import json
import re
import shutil
import subprocess
import pytest
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication
from morale.model import Project,DesignObject
from morale.engine import generate
from morale.coverage_review import measure_layers,render_layers,detail_measurements,fabric_guidance,layers_text,FABRICS
from morale.density_review import measure_thread_density


@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])


def squares(*positions,size=10):
    return Project(objects=[DesignObject(name=f'Square {i+1}',kind='rectangle',x=x,y=y,width=size,height=size,underlay=False)
                            for i,(x,y) in enumerate(positions)])


def test_separate_objects_are_one_layer_with_no_pairs():
    project=squares((0,0),(20,0))
    report,raster=measure_layers(project,generate(project))
    assert report['peak_layers']==1 and report['overlap_pairs']==[] and report['pixel_mm']==pytest.approx(.1)
    # Outline plus at most the 0.4 mm thread band around its edge.
    assert 2*100<=report['area_by_layers_mm2']['1']<=2*10.4*10.4
    assert raster is not None and render_layers(report,raster).width()==640


def test_overlap_area_and_three_way_stacking_are_measured():
    # Squares 1 and 2 overlap by 5 x 10 mm; the third covers the middle of both.
    project=squares((0,0),(5,0),(2.5,0))
    report,_=measure_layers(project,generate(project))
    assert report['peak_layers']==3
    pairs={(p['first'],p['second']):p['area_mm2'] for p in report['overlap_pairs']}
    # Exact geometric overlap, plus at most the thread band on each side.
    assert 50<=pairs[('Square 1','Square 2')]<=5.4*10.4
    assert 75<=pairs[('Square 1','Square 3')]<=7.9*10.4
    assert 50<=report['area_by_layers_mm2']['3']<=5.4*10.4
    assert report['stacked_locations'] and all(s['layers']==3 for s in report['stacked_locations'])
    assert 'Square 1 / Square 3' in '\n'.join(layers_text(report))


def test_touching_objects_show_only_the_thread_band_overlap():
    project=squares((0,0),(10,0))
    report,_=measure_layers(project,generate(project))
    # Abutting edges share only the 0.4 mm band along the seam.
    assert report['overlap_pairs'][0]['area_mm2']<=.45*10.4


def test_empty_design_is_reported_without_a_map():
    report,raster=measure_layers(Project(),[])
    assert report['peak_layers']==0 and raster is None
    assert not render_layers(report,None).isNull()


def test_fabric_guidance_flags_layers_density_and_small_details():
    project=squares((0,0),(2,0),(4,0))
    narrow=DesignObject(name='Hairline',kind='satin',x=30,y=0,width=.9,height=12,points=[[-.5,-.5],[.5,-.5],[-.5,.5],[.5,.5]])
    tiny=DesignObject(name='Speck',kind='rectangle',x=40,y=0,width=1.5,height=1.5)
    project.objects+=[narrow,tiny];blocks=generate(project)
    quality={'layers':measure_layers(project,blocks)[0],'thread_density':measure_thread_density(blocks)[0],'details':detail_measurements(project)}
    findings,text=fabric_guidance(quality,'light')
    assert findings>=3 and 'more than 2 stacked layers' in text and 'Hairline: satin 0.90 mm' in text and 'Speck: fill of 2.25' in text
    _,heavy=fabric_guidance(quality,'heavy')
    assert 'Hairline' in heavy and 'stacked layers' not in heavy
    with pytest.raises(ValueError):fabric_guidance(quality,'leather')
    assert all(0<f['max_layers'] and 0<f['max_density'] and f['max_density']*2==int(f['max_density']*2) for f in FABRICS.values())


def test_single_layer_satin_and_fill_pass_medium_woven_guidance():
    satin=DesignObject(kind='satin',width=4,height=30,points=[[-.5,-.5],[.5,-.5],[-.5,.5],[.5,.5]])
    fill=DesignObject(kind='rectangle',x=20,width=20,height=20)
    project=Project(objects=[satin,fill]);blocks=generate(project)
    quality={'layers':measure_layers(project,blocks)[0],'thread_density':measure_thread_density(blocks)[0],'details':detail_measurements(project)}
    findings,text=fabric_guidance(quality,'woven')
    assert findings==0 and 'No thresholds exceeded' in text


def test_worker_review_pdf_and_dialog_include_coverage(tmp_path,monkeypatch):
    from morale.raster_trace import worker_main
    from morale.conversion_report import save_conversion_review
    from morale.trace_quality import quality_text
    import morale.trace_dialog as module
    source=tmp_path/'art.svg'
    source.write_text('<svg width="40" height="40"><rect x="5" y="5" width="20" height="20" fill="red"/><rect x="15" y="15" width="20" height="20" fill="blue"/></svg>')
    output=tmp_path/'worker';output.mkdir()
    assert worker_main([str(source),str(output),'{}'])==0
    info=json.loads((output/'preview.json').read_text());image=QImage(str(output/'preview.png'))
    quality=info['trace_stats']['quality']
    assert quality['layers']['peak_layers']==2 and quality['layers']['overlap_pairs'] and quality['details']
    assert not QImage.fromData(__import__('base64').b64decode(info['layers_png'])).isNull()
    assert 'Coverage layers: peak 2' in quality_text(quality) and 'Fabric guidance' not in quality_text(quality)
    assert 'Fabric guidance: Pile' in quality_text({**quality,'fabric':'pile'})
    path=tmp_path/'review.pdf';save_conversion_review(path,'art.svg',info,image,fabric='knit')
    assert len(re.findall(rb'/Type /Page\b',path.read_bytes()))>=5
    if shutil.which('pdftotext'):
        text=subprocess.check_output(['pdftotext',str(path),'-'],text=True)
        assert 'Coverage-layers review' in text and 'Knit or stretch' in text
    # Reviews saved from older previews without a coverage map keep two map pages.
    info.pop('layers_png');save_conversion_review(tmp_path/'old.pdf','art.svg',info,image)
    dialog=module.TraceDialog(str(source))
    try:
        dialog.ready('preview.png',{**json.loads((output/'preview.json').read_text())},image)
        assert not dialog.layers_image.isNull() and dialog.density_button.isEnabled()
        shown=[]
        monkeypatch.setattr(module.QDialog,'exec',lambda self:shown.append(self))
        dialog.fabric.setCurrentIndex(dialog.fabric.findData('pile'));dialog.show_density()
        from PySide6.QtWidgets import QComboBox,QPlainTextEdit
        views=shown[0].findChildren(QComboBox)
        assert [views[0].itemText(i) for i in range(views[0].count())]==['Needle penetrations','Sewn thread length','Coverage layers']
        assert 'Pile (towel, fleece)' in shown[0].findChildren(QPlainTextEdit)[0].toPlainText()
        views[1].setCurrentIndex(views[1].findData('heavy'))
        assert dialog.fabric.currentData()=='heavy' and dialog.project is not None
    finally:dialog.close()
