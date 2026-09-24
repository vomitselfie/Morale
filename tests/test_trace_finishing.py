import pytest
from morale.model import Project,DesignObject
from morale.engine import generate
from morale.trace_finishing import finish_regions


def project():
    return Project(objects=[DesignObject(kind='path',stitch_type='running',x=x,width=2,height=2,
        points=[[-.5,0],[.5,0]],underlay=False) for x in (0,3,20)])


def test_finishing_separates_long_transfers_but_keeps_nearby_regions_connected():
    source=project();before=source.dumps();result,info=finish_regions(source)
    assert source.dumps()==before
    assert [(o.tie_in,o.tie_off,o.trim_after) for o in result.objects]==[(True,False,False),(False,True,True),(True,True,True)]
    assert len(info['boundaries'])==1 and info['boundaries'][0]['distance_mm']==15
    assert [sum(s.command=='trim' for s in b.stitches) for b in generate(result)]==[0,1,1]
    assert Project.loads(result.dumps()).objects==result.objects
    assert [o.points for o in result.objects]==[o.points for o in source.objects]


@pytest.mark.parametrize('reason',['color','metadata','break','stop'])
def test_controls_separate_even_short_transfers(reason):
    source=project()
    if reason=='color':source.objects[1].color='#ff0000'
    elif reason=='metadata':source.objects[1].thread={'brand':'Different'}
    elif reason=='break':source.objects[1].color_break=True
    else:source.objects[0].stop_after=True
    result,info=finish_regions(source)
    assert result.objects[0].tie_off and result.objects[0].trim_after and result.objects[1].tie_in
    assert info['boundaries'][0]['reason']==('stop' if reason=='stop' else 'thread change')


def test_threshold_and_existing_user_flags():
    source=project();source.objects[0].tie_off=True
    result,info=finish_regions(source,50)
    assert result.objects[0].tie_off and not result.objects[0].trim_after
    assert not info['boundaries']
    result,_=finish_regions(source,.5)
    assert all(o.tie_in and o.tie_off and o.trim_after for o in result.objects)


@pytest.mark.parametrize('value',[True,0,51,float('nan'),'5'])
def test_bad_threshold(value):
    with pytest.raises(ValueError):finish_regions(project(),value)


@pytest.mark.parametrize('extension',['dst','exp','jef','pec','pes','tbf','u01','vp3','xxx'])
def test_exported_ties_stay_in_the_regions(tmp_path,extension):
    from morale.formats import export_machine,import_machine
    result,_=finish_regions(project());path=tmp_path/f'finished.{extension}';export_machine(result,path)
    sewn=[s for b in generate(import_machine(path).project) for s in b.stitches if s.command=='stitch']
    assert sewn and all(abs(s.y)<.1 and any(abs(s.x-x)<=1.1 for x in (0,3,20)) for s in sewn)
