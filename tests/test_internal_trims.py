import pytest
from morale.engine import Stitch,finish_stitches,generate
from morale.model import Project,DesignObject


def commands():
    return [Stitch(0,0,'jump'),Stitch(1,0),Stitch(2,0),Stitch(5,0,'jump'),Stitch(10,0,'jump'),Stitch(11,0)]


def test_internal_transfer_gets_one_trim_and_local_locks():
    source=commands();result=finish_stitches(source,jump_trim=5)
    assert source==commands()
    assert [s for s in result if s.command=='trim']==[Stitch(2,0,'trim')]
    assert sum(s.command=='stitch' for s in result)==11
    assert [s for s in result if s.command=='jump']==[s for s in source if s.command=='jump']
    trim=next(i for i,s in enumerate(result) if s.command=='trim')
    assert result[trim-1]==Stitch(2,0) and result[trim+1]==Stitch(5,0,'jump')
    assert all(s.x<=2 or s.x>=10 for s in result if s.command=='stitch')


def test_disabled_short_and_terminal_travel_are_unchanged():
    source=commands()
    assert finish_stitches(source)==source
    assert finish_stitches(source,jump_trim=8)==source
    source=[Stitch(0,0,'jump'),Stitch(10,0,'jump'),Stitch(11,0),Stitch(30,0,'jump')]
    assert finish_stitches(source,jump_trim=5)==source


def design():
    return Project(objects=[DesignObject(kind='compound',stitch_type='running',width=40,height=4,
        contours=[[[-.4,-.5],[-.2,-.5],[-.2,.5],[-.4,.5]],[[.2,-.5],[.4,-.5],[.4,.5],[.2,.5]]],jump_trim=5)])


def test_setting_persists_and_engine_keeps_hole_travel_unsewn():
    project=Project.loads(design().dumps());blocks=generate(project)
    assert project.objects[0].jump_trim==5
    assert sum(s.command=='trim' for b in blocks for s in b.stitches)==1
    assert all(abs(s.x)>=8 for b in blocks for s in b.stitches if s.command=='stitch')


@pytest.mark.parametrize('value',[True,-1,51,float('nan')])
def test_invalid_settings(value):
    project=design();project.objects[0].jump_trim=value
    with pytest.raises(ValueError):Project.loads(project.dumps())


@pytest.mark.parametrize('extension',['dst','exp','jef','pec','pes','tbf','u01','vp3','xxx'])
def test_exported_internal_locks_preserve_empty_gap(tmp_path,extension):
    from morale.formats import export_machine,import_machine
    path=tmp_path/f'internal.{extension}';export_machine(design(),path)
    sewn=[s for b in generate(import_machine(path).project) for s in b.stitches if s.command=='stitch']
    assert sewn and all(abs(s.x)>=7.9 and abs(s.x)<=16.1 and abs(s.y)<=2.1 for s in sewn)
