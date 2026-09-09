import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import math
import pytest
from PySide6.QtWidgets import QApplication
from morale.model import Project,DesignObject
from morale.stitch_edit import manual_object
from morale.engine import generate,preflight
from morale.multihoop import split_design


@pytest.fixture(scope='module',autouse=True)
def app(): return QApplication.instance() or QApplication([])


def project_from_rows(rows):
    return Project(objects=[manual_object(DesignObject(name='Source'),rows)])


def segments(project,offset=(0,0),skip_marks=False):
    result=[]
    for block in generate(project):
        obj=next(o for o in project.objects if o.id==block.object_id)
        if skip_marks and obj.name=='Removable alignment crosses': continue
        previous=None
        for s in block.stitches:
            point=(s.x+offset[0],s.y+offset[1])
            if s.command=='stitch' and previous is not None: result.append((previous,point))
            if s.command in {'stitch','jump'}: previous=point
    return result


@pytest.mark.parametrize('end',[ (180,90),(180,-90),(180,0),(0,180),(-180,90)])
def test_split_segment_has_exactly_once_continuous_coverage(end):
    project=project_from_rows([[0,0,'jump'],[*end,'stitch']])
    before=project.dumps()
    plan=split_design(project,80,80,8,False)
    result=[line for tile in plan.tiles for line in segments(tile.project,tile.center)]
    length=math.hypot(*end)
    intervals=[]
    for a,b in result:
        assert abs(a[0]*end[1]-a[1]*end[0])<1e-8
        assert abs(b[0]*end[1]-b[1]*end[0])<1e-8
        intervals.append(tuple(sorted(((a[0]*end[0]+a[1]*end[1])/length**2,(b[0]*end[0]+b[1]*end[1])/length**2))))
    intervals.sort()
    assert intervals[0][0]==pytest.approx(0) and intervals[-1][1]==pytest.approx(1)
    for a,b in zip(intervals,intervals[1:]): assert a[1]==pytest.approx(b[0])
    assert sum(math.dist(a,b) for a,b in result)==pytest.approx(length)
    assert project.dumps()==before
    assert all(not preflight(t.project,generate(t.project)) for t in plan.tiles)


def test_line_on_shared_boundary_is_not_sewn_twice():
    project=project_from_rows([[-64,-64,'jump'],[64,64,'stitch'],[0,-64,'jump'],[0,64,'stitch']])
    plan=split_design(project,80,80,8,False)
    assert plan.columns==2 and plan.rows==2
    vertical=[(a,b) for t in plan.tiles for a,b in segments(t.project,t.center) if abs(a[0])<1e-8 and abs(b[0])<1e-8]
    assert sum(math.dist(a,b) for a,b in vertical)==pytest.approx(128)


def test_shared_alignment_marks_match_world_coordinates_and_stay_in_hoops():
    project=project_from_rows([[-70,-70,'jump'],[70,70,'stitch']])
    plan=split_design(project,100,100,8,True)
    marks={}
    for tile in plan.tiles:
        for mark in tile.marks:
            marks.setdefault(mark['id'],[]).append(mark['position'])
            x,y=mark['position'][0]-tile.center[0],mark['position'][1]-tile.center[1]
            assert abs(x)+1<=plan.width/2 and abs(y)+1<=plan.height/2
        if tile.marks:
            first=tile.project.objects[0]
            assert first.name=='Removable alignment crosses'
            assert generate(Project(objects=[first]))[0].stitches[-1].command=='stop'
    # This diagonal only activates diagonal cores, so use a border for adjacency.
    border=Project(objects=[DesignObject(kind='rectangle',stitch_type='running',width=150,height=150)])
    plan=split_design(border,100,100,8,True)
    marks={}
    for tile in plan.tiles:
        for mark in tile.marks: marks.setdefault(mark['id'],[]).append(mark['position'])
    assert marks and all(len(positions)==2 and positions[0]==positions[1] for positions in marks.values())


def test_pause_and_thread_metadata_survive_each_relevant_tile():
    project=project_from_rows([[-80,0,'jump'],[80,0,'stitch'],[80,0,'stop'],[-80,10,'jump'],[80,10,'stitch'],[80,10,'trim']])
    project.objects[0].thread={'brand':'Test','catalog_number':'001'}
    plan=split_design(project,100,100,8,False)
    for tile in plan.tiles:
        assert tile.project.objects[0].thread==project.objects[0].thread
        commands=[s.command for b in generate(tile.project) for s in b.stitches]
        assert commands.count('stop')==1 and 'trim' in commands
        assert Project.loads(tile.project.dumps())==tile.project


def test_holes_have_no_new_sewn_bridges():
    obj=DesignObject(kind='compound',width=180,height=100,angle=0,underlay=False,contours=[[[-.5,-.5],[.5,-.5],[.5,.5],[-.5,.5]],[[-.2,-.2],[.2,-.2],[.2,.2],[-.2,.2]]])
    project=Project(objects=[obj]); plan=split_design(project,100,100,8,False)
    original=sum(math.dist(a,b) for a,b in segments(project))
    split=sum(math.dist(a,b) for tile in plan.tiles for a,b in segments(tile.project,tile.center))
    assert split==pytest.approx(original,abs=1e-8)


@pytest.mark.parametrize('settings',[{'width':10},{'margin':3},{'margin':50},{'width':20,'margin':8},{'registration':'yes'},{'height':float('nan')}])
def test_invalid_hoop_settings(settings):
    with pytest.raises(ValueError): split_design(project_from_rows([[0,0,'jump'],[10,0,'stitch']]),**settings)


def test_empty_and_unanchored_design_rejected():
    with pytest.raises(ValueError): split_design(Project(objects=[]))
    with pytest.raises(ValueError,match='jump'):
        split_design(Project(objects=[DesignObject(kind='stitches',stitch_type='manual',stitch_data=[[0,0,'stitch']])]))


def test_native_planning_worker_bundle_pdf_archive_and_invalidation(tmp_path):
    import json,time,zipfile
    from pathlib import Path
    from PySide6.QtTest import QTest
    from morale.hoop_dialog import HoopDialog
    from morale.hoop_bundle import save_archive
    project=Project(objects=[DesignObject(kind='rectangle',stitch_type='running',width=150,height=150)])
    before=project.dumps(); dialog=HoopDialog(project)
    try:
        dialog.generate()
        deadline=time.monotonic()+15
        while dialog.manifest is None and dialog.process.state()!=dialog.process.ProcessState.NotRunning and time.monotonic()<deadline:
            QTest.qWait(20)
        assert dialog.manifest is not None,dialog.status.text()
        assert len(dialog.manifest['tiles'])==4
        root=Path(dialog.directory.name)/'bundle'
        assert (root/'placement.pdf').read_bytes().startswith(b'%PDF')
        target=tmp_path/'plan.zip'; save_archive(root,target)
        with zipfile.ZipFile(target) as archive:
            assert {'source.morale','plan.json','placement.pdf','placement.png','alignment.csv','README.txt'}<=set(archive.namelist())
            manifest=json.loads(archive.read('plan.json'))
            for tile in manifest['tiles']:
                restored=Project.loads(archive.read(tile['project']).decode())
                assert not preflight(restored,generate(restored))
        old=target.read_bytes()
        with pytest.raises(FileExistsError): save_archive(root,target)
        assert target.read_bytes()==old
        temporary=Path(dialog.directory.name)
        dialog.width.setValue(120)
        assert dialog.manifest is None and not temporary.exists() and not dialog.save_button.isEnabled()
        assert project.dumps()==before
    finally: dialog.close()


def test_cancel_and_worker_failure_are_recoverable():
    import time
    from PySide6.QtTest import QTest
    from PySide6.QtCore import QProcess
    from morale.hoop_dialog import HoopDialog
    dialog=HoopDialog(Project(objects=[DesignObject(width=150,height=150)]))
    try:
        dialog.generate(); process=dialog.process
        dialog.invalidate()
        assert process.state()==QProcess.ProcessState.NotRunning and dialog.directory is None
        dialog.width.setValue(20); dialog.height.setValue(20); dialog.margin.setValue(8)
        dialog.generate()
        deadline=time.monotonic()+10
        while process.state()!=QProcess.ProcessState.NotRunning and time.monotonic()<deadline: QTest.qWait(20)
        assert dialog.manifest is None and '10 mm content core' in dialog.status.text()
    finally: dialog.close()


@pytest.mark.parametrize('extension',['dst','exp','jef','pec','pes','tbf','u01','vp3','xxx'])
def test_split_tiles_export_in_all_machine_formats(tmp_path,extension):
    from morale.formats import export_machine,import_machine
    project=Project(objects=[DesignObject(kind='rectangle',stitch_type='running',width=150,height=100)])
    plan=split_design(project,100,100,8,True)
    for index,tile in enumerate(plan.tiles):
        path=tmp_path/f'tile-{index}.{extension}'; export_machine(tile.project,path)
        decoded=import_machine(path).project
        points=[s for b in generate(decoded) for s in b.stitches if s.command=='stitch']
        assert points and all(abs(s.x)<=50.15 and abs(s.y)<=50.15 for s in points)
        blocks=generate(decoded)
        pauses=len(blocks)-1+sum(s.command=='stop' for b in blocks for s in b.stitches)
        assert pauses==2  # alignment stop plus transition to the design thread


def test_global_stage_stops_survive_when_stage_geometry_is_in_another_tile():
    first=manual_object(DesignObject(name='Left stage'),[[-80,0,'jump'],[-70,0,'stitch'],[-70,0,'stop']])
    second=manual_object(DesignObject(name='Right stage'),[[70,0,'jump'],[80,0,'stitch'],[80,0,'stop']])
    plan=split_design(Project(objects=[first,second]),100,100,8,False)
    assert len(plan.tiles)==2
    for tile in plan.tiles:
        commands=[s.command for b in generate(tile.project) for s in b.stitches]
        assert commands.count('stop')==2
    right=plan.tiles[-1].project
    commands=[s.command for b in generate(right) for s in b.stitches]
    assert commands.index('stop')<commands.index('stitch')


def test_too_many_placements_rejected():
    with pytest.raises(ValueError,match='100 placements'):
        split_design(Project(objects=[DesignObject(kind='rectangle',stitch_type='running',width=500,height=500)]),20,20,4)
