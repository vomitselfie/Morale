from collections import Counter
from copy import deepcopy
import json
import math
import pytest
from PySide6.QtWidgets import QApplication
from morale.engine import generate,Stitch
from morale.model import Project,DesignObject
from morale.fill_routing import route_fill_runs

@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])

def split_fill():
    return DesignObject(kind='compound',width=30,height=20,underlay=False,angle=0,
        contours=[[[-.5,-.5],[-.2,-.5],[-.2,.5],[-.5,.5]],[[.2,-.5],[.5,-.5],[.5,.5],[.2,.5]]])

def metrics(rows):
    previous=(0,0);travel=0;segments=Counter()
    for s in rows:
        point=(s.x,s.y)
        if s.command=='jump':travel+=math.dist(previous,point)
        elif s.command=='stitch':segments[tuple(sorted((tuple(round(v,8) for v in previous),tuple(round(v,8) for v in point))))]+=1
        if s.command in {'stitch','jump'}:previous=point
    return travel,segments

@pytest.mark.parametrize('connected',[False,True])
def test_reduces_disconnected_travel_preserving_sewn_geometry_and_endpoints(connected):
    obj=split_fill();obj.connect_fill=connected
    source=Project(objects=[obj]);before=source.dumps();original=generate(source)[0].stitches
    obj.route_fill=True;routed=generate(source)[0].stitches
    assert metrics(routed)[0]<metrics(original)[0]-50
    assert metrics(routed)[1]==metrics(original)[1]
    assert len(routed)==len(original) and routed[0]==original[0] and routed[-1]==original[-1]
    assert Project.loads(source.dumps()).objects[0].route_fill


def test_run_limit_and_control_commands_leave_sequence_unchanged():
    rows=[s for i in range(5) for s in [Stitch(i,0,'jump'),Stitch(i,1)]]
    assert route_fill_runs(rows,limit=4)==rows
    controlled=rows+[Stitch(4,1,'stop')]
    assert route_fill_runs(controlled)==controlled

def test_source_rows_are_not_mutated():
    rows=generate(Project(objects=[split_fill()]))[0].stitches;before=deepcopy(rows)
    route_fill_runs(rows);assert rows==before

def test_default_off_and_boolean_validation():
    source=Project(objects=[split_fill()]);data=json.loads(source.dumps());data['objects'][0].pop('route_fill')
    assert not Project.loads(json.dumps(data)).objects[0].route_fill
    data['objects'][0]['route_fill']=1
    with pytest.raises(ValueError):Project.loads(json.dumps(data))

def test_underlay_and_finishing_remain_present():
    obj=split_fill();obj.underlay=True;obj.tie_in=True;obj.tie_off=True;obj.trim_after=True;obj.route_fill=True
    rows=generate(Project(objects=[obj]))[0].stitches
    assert rows[-1].command=='trim'
    assert any(s.command=='stitch' for s in rows)

@pytest.mark.parametrize('extension',['dst','exp','jef','pec','pes','tbf','u01','vp3','xxx'])
def test_routed_fill_exports_with_expected_bounds(tmp_path,extension):
    from morale.formats import export_machine,import_machine
    obj=split_fill();obj.route_fill=True;project=Project(objects=[obj])
    path=tmp_path/f'routed.{extension}';export_machine(project,path)
    sewn=[s for b in generate(import_machine(path).project) for s in b.stitches if s.command=='stitch']
    assert sewn and all(-15.15<=s.x<=15.15 and -10.15<=s.y<=10.15 for s in sewn)

def test_native_property_and_undo():
    from morale.app import MainWindow
    window=MainWindow()
    try:
        obj=split_fill();window.replace_project(Project(objects=[obj]));window.select(obj.id)
        before=window.project.dumps();window.finishing['route_fill'].setChecked(True)
        assert window.project.objects[0].route_fill
        window.undo();assert window.project.dumps()==before
    finally:window.saved=window.project.dumps();window.close()

def test_three_run_case_can_reverse_middle_run():
    rows=[Stitch(0,0,'jump'),Stitch(1,0),Stitch(10,0,'jump'),Stitch(2,0),Stitch(11,0,'jump'),Stitch(12,0)]
    result=route_fill_runs(rows)
    assert metrics(result)[0]<metrics(rows)[0]
    assert metrics(result)[1]==metrics(rows)[1]

def test_worker_option_persists_and_reports_routing(tmp_path):
    from morale.raster_trace import worker_main
    from morale.trace_dialog import TraceDialog
    path=tmp_path/'islands.svg';path.write_text('<svg width="40" height="30"><path d="M5 5 H14 V25 H5 Z M26 5 H35 V25 H26 Z" fill="red"/></svg>')
    output=tmp_path/'output';output.mkdir()
    assert worker_main([str(path),str(output),json.dumps(dict(width=40,stitch_mode='fill',route_fill=True))])==0
    info=json.loads((output/'preview.json').read_text());project=Project.loads(info['project'])
    assert project.objects[0].route_fill
    routed=metrics(generate(project)[0].stitches)[0]
    project.objects[0].route_fill=False
    assert routed<metrics(generate(project)[0].stitches)[0]
    assert any('routing enabled' in note for note in info['trace_stats']['quality']['regions'][0]['notes'])
    dialog=TraceDialog(str(path))
    try:
        assert not dialog.route_fill.isChecked()
        dialog.overrides={'0':'fill'};dialog.route_fill.setChecked(True)
        assert dialog.overrides=={'0':'fill'}
    finally:dialog.close()
