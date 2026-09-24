import pytest
from morale.model import DesignObject,Project
from morale.engine import Block,Stitch
from morale.trace_quality import conversion_quality,quality_text


def report_for(rows):
    obj=DesignObject();project=Project(objects=[obj]);block=Block(obj.id,obj.color,[Stitch(x,y,command) for x,y,command in rows])
    return conversion_quality(project,[block])


def test_long_stitches_ignore_jumps_and_stationary_controls():
    report=report_for([(10,0,'jump'),(16,0,'stitch'),(999,999,'trim'),(23,0,'stitch'),(-999,-999,'stop'),(23,100,'jump'),(23,108,'stitch')])
    region=report['regions'][0]
    assert report['long_stitches']==2 and report['maximum_stitch_mm']==8
    assert region['long_stitch_locations'][0]=={'command_index':3,'from_mm':[16,0],'to_mm':[23,0],'length_mm':7}
    assert region['long_stitch_locations_complete']
    text=quality_text(report)
    assert 'command 4' in text and 'review threshold' in text and 'not fabric or machine limits' in text


def test_location_limit_keeps_full_count_and_maximum():
    report=report_for([(0,0,'jump')]+[(i*10,0,'stitch') for i in range(1,26)])
    region=report['regions'][0]
    assert region['long_stitches']==25 and region['maximum_stitch_mm']==10
    assert len(region['long_stitch_locations'])==20 and not region['long_stitch_locations_complete']
    assert 'totals include all spans' in quality_text(report)


def test_empty_and_zero_length_designs_have_zero_maximum():
    assert conversion_quality(Project())['maximum_stitch_mm']==0
    report=report_for([(0,0,'jump'),(0,0,'stitch')])
    assert report['maximum_stitch_mm']==0 and report['zero_length_stitches']==1


def test_global_previous_position_survives_block_boundary():
    a,b=DesignObject(),DesignObject();project=Project(objects=[a,b])
    blocks=[Block(a.id,a.color,[Stitch(5,0,'jump'),Stitch(7,0)]),Block(b.id,b.color,[Stitch(15,0)])]
    report=conversion_quality(project,blocks)
    assert report['maximum_stitch_mm']==8 and report['long_stitches']==1
    assert report['regions'][1]['long_stitch_locations'][0]['from_mm']==[7,0]


def test_older_review_without_new_metrics_still_renders():
    report=report_for([(0,0,'jump'),(1,0,'stitch')])
    for key in ('long_stitches','maximum_stitch_mm'):report.pop(key)
    for key in ('long_stitches','maximum_stitch_mm','long_stitch_locations','long_stitch_locations_complete'):report['regions'][0].pop(key)
    assert 'Conversion measurements' in quality_text(report)
