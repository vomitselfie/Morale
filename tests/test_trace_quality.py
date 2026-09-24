import math
from morale.model import DesignObject,Project
from morale.trace_quality import conversion_quality,quality_text


def test_measured_lengths_ignore_nonmovement_commands_and_keep_zero_separate():
    obj=DesignObject(kind='stitches',stitch_type='manual',width=20,height=20,stitch_data=[
        [0,0,'jump'],[.01,0,'stitch'],[.01,0,'stitch'],[.5,.5,'trim'],
        [.06,0,'stitch'],[.5,.5,'jump'],[.1,-.5,'stop'],[.5,.49,'stitch']])
    project=Project(objects=[obj]);before=project.dumps()
    report=conversion_quality(project);region=report['regions'][0]
    assert project.dumps()==before
    assert region['stitches']==4 and region['short_stitches']==2 and region['zero_length_stitches']==1
    assert region['long_jumps']==1
    assert math.isclose(region['sewn_length_mm'],1.4)
    assert math.isclose(region['jump_length_mm'],math.hypot(8.8,10))
    assert 'review aids' in quality_text(report)


def test_fine_detail_changes_with_physical_size():
    obj=DesignObject(kind='rectangle',width=.8,height=5)
    small=conversion_quality(Project(objects=[obj]))
    assert any('fine detail' in n for n in small['regions'][0]['notes'])
    obj.width=2
    large=conversion_quality(Project(objects=[obj]))
    assert not any('fine detail' in n for n in large['regions'][0]['notes'])


def test_sewing_order_and_travel_across_regions():
    objects=[DesignObject(name=name,kind='path',stitch_type='running',x=x,width=2,height=2,
              points=[[-.5,0],[.5,0]],underlay=False) for name,x in (('First',10),('Second',30))]
    report=conversion_quality(Project(objects=objects))
    assert [r['name'] for r in report['regions']]==['First','Second']
    assert report['jump_length_mm']==27
    text=quality_text(report)
    assert text.index('Sew 1: First')<text.index('Sew 2: Second')
    assert 'starting at the artwork origin' in text


def test_empty_project_report():
    report=conversion_quality(Project())
    assert report['regions']==[] and report['review_regions']==0


def test_routing_rejection_is_explained_without_claiming_a_reduction():
    report=conversion_quality(Project())
    report['routing']={'before_mm':12,'after_mm':12,'moved_regions':0,'reversed_regions':[],
                       'status':'rejected','reason':'Reversed stitches conflict with the candidate layer order.'}
    text=quality_text(report)
    assert '12.00 → 12.00' in text and 'Original route retained:' in text and 'layer order' in text
    assert 'exclude transfers within a region' in text
    report['routing']['status']='unchanged'
    assert 'no shorter valid candidate' in quality_text(report)
    del report['routing']['status']
    assert 'Inter-region travel' in quality_text(report)


def test_worker_retains_routing_decision_in_quality_report(tmp_path,monkeypatch):
    import json
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QImage,QColor
    from morale.raster_trace import worker_main
    import morale.trace_routing as routing
    app=QApplication.instance() or QApplication([])
    image=QImage(20,20,QImage.Format.Format_RGB32);image.fill(QColor('red'))
    source=tmp_path/'source.png';assert image.save(str(source))
    out=tmp_path/'trace';out.mkdir()
    report={'before_mm':10,'after_mm':10,'order':[0],'moved_regions':0,'reversed_regions':[],
            'status':'rejected','reason':'Candidate layering test failed.'}
    monkeypatch.setattr(routing,'reduce_travel',lambda project,reverse:(project,report))
    assert worker_main([str(source),str(out),json.dumps({'width':20,'method':'pixels','colors':2,'minimum_region':1,'reduce_travel':True,'stitch_mode':'fill'})])==0
    info=json.loads((out/'preview.json').read_text())
    assert info['trace_stats']['quality']['routing']==report
    assert 'Candidate layering test failed.' in quality_text(info['trace_stats']['quality'])


def test_effective_underlay_settings_and_legacy_reports():
    from copy import deepcopy
    from morale.auto_digitize import choose_stitches
    from morale.trace_stitch_settings import apply_stitch_settings
    source=Project(objects=[DesignObject(kind='rectangle',width=20,height=20),
                            DesignObject(kind='rectangle',width=3,height=20)])
    chosen,_=choose_stitches(source)
    project,settings=apply_stitch_settings(chosen,{'fill_underlay':'edge_sparse','satin_underlay':'auto',
        'underlay_inset':.4,'underlay_spacing':1.5})
    report=conversion_quality(project);report['stitch_settings']=settings
    text=quality_text(report)
    assert 'Fill underlay: Edge run and sparse fill\n' in text
    assert 'Satin underlay: Automatic\n' in text
    assert 'Underlay: Edge run and sparse fill; inset 0.4 mm, support spacing 1.5 mm' in text
    assert 'Underlay: Center run; run stitch length 2.5 mm.' in text
    assert 'Automatic mm' not in text and 'edge_sparse mm' not in text
    # A center run does not use the configured inset or zigzag spacing.
    assert report['regions'][1]['underlay']['style']=='center'
    legacy=deepcopy(report)
    for region in legacy['regions']:region.pop('underlay')
    assert 'Conversion measurements' in quality_text(legacy)
    assert report['regions'][0]['underlay']['enabled']
    project.objects[0].underlay=False
    assert 'Underlay: Disabled.' in quality_text(conversion_quality(project))
