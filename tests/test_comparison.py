import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')

import pytest
from PySide6.QtWidgets import QApplication, QDialog

from morale.comparison import compare_commands, command_metrics, command_paths, load_comparison, ComparisonDialog, ComparisonView
from morale.engine import Block, Stitch, generate
from morale.model import Project, DesignObject
from morale.formats import export_machine


@pytest.fixture(scope='module',autouse=True)
def app():
    return QApplication.instance() or QApplication([])


def blocks(offset=0):
    return [Block('a','#ff0000',[Stitch(offset,0,'jump'),Stitch(offset+1,0),Stitch(offset+1,0,'trim'),
                  Stitch(offset+2,0,'jump'),Stitch(offset+3,0),Stitch(offset+3,0,'stop')])]


def test_matching_sequence_reports_coordinate_difference_without_alignment():
    report=compare_commands(blocks(),blocks(5))
    assert report['same_command_sequence']
    assert report['maximum_indexed_displacement_mm']==5
    assert report['source']['sewn_bounds_mm']==(1,0,3,0)
    assert report['decoded']['sewn_bounds_mm']==(6,0,8,0)


def test_changed_commands_disable_pointwise_displacement():
    other=blocks()
    other[0].stitches.insert(2,Stitch(1,0,'jump'))
    report=compare_commands(blocks(),other)
    assert not report['same_command_sequence']
    assert report['maximum_indexed_displacement_mm'] is None
    other=blocks()
    other[0].stitches[2]=Stitch(1,0,'stop')
    assert compare_commands(blocks(),other)['maximum_indexed_displacement_mm'] is None


def test_counts_lengths_and_rgb_runs_retain_different_meanings():
    metrics=command_metrics(blocks())
    assert metrics['counts']=={'jump':2,'stitch':2,'trim':1,'stop':1}
    assert metrics['sewn_path_m']==pytest.approx(.002)
    assert metrics['travel_path_m']==pytest.approx(.001)
    assert metrics['thread_rgb']==['#ff0000']
    repeated=blocks()+[Block('b','#ff0000',[Stitch(4,0)],color_break=True)]
    assert command_metrics(repeated)['thread_rgb']==['#ff0000','#ff0000']


def test_sewn_and_travel_paths_are_drawn_separately():
    sewn,travel=command_paths(blocks())
    assert sewn.elementCount()==4
    assert [(sewn.elementAt(i).x,sewn.elementAt(i).y) for i in range(4)]==[(0,0),(1,0),(2,0),(3,0)]
    assert travel.boundingRect().right()==2


def test_rendered_overlay_toggles_are_independent():
    view=ComparisonView(blocks(),blocks(5))
    view.resize(600,400)
    view.show()
    view.fit()
    QApplication.processEvents()
    def green():
        image=view.grab().toImage()
        return sum(1 for y in range(195,206) for x in range(20,580)
                   if (c:=image.pixelColor(x,y)).green()>c.red()+20 and c.green()>c.blue()+10)
    assert green()>0
    view.visible[0]=False
    view.update()
    assert green()==0
    view.close()


@pytest.mark.parametrize('extension',['dst','exp','jef','pec','pes','tbf','u01','vp3','xxx'])
def test_load_comparison_for_all_export_formats_without_modifying_files(tmp_path,extension):
    project=Project(objects=[DesignObject(kind='rectangle',width=10,height=10,underlay=False)])
    path=tmp_path/f'compare.{extension}'
    export_machine(project,path)
    original=project.dumps()
    data=path.read_bytes()
    source,decoded,report,notes=load_comparison(project,path)
    assert source==generate(project)
    assert report['source']['counts']['stitch']>0 and report['decoded']['counts']['stitch']>0
    assert decoded and notes
    assert project.dumps()==original and path.read_bytes()==data


def test_native_comparison_and_cancel_leave_project_unchanged(tmp_path,monkeypatch):
    import morale.app as module
    window=module.MainWindow()
    try:
        original=window.project.dumps()
        path=tmp_path/'sample.pes'
        export_machine(window.project,path)
        monkeypatch.setattr(module.QFileDialog,'getOpenFileName',lambda *args: (str(path),''))
        seen=[]
        def close(dialog):
            seen.append(dialog.report)
            dialog.source_toggle.setChecked(False)
            dialog.travel_toggle.setChecked(True)
            assert not dialog.view.visible[0] and dialog.view.travel
            return QDialog.DialogCode.Rejected
        monkeypatch.setattr(ComparisonDialog,'exec',close)
        window.compare_machine_file()
        assert seen and window.project.dumps()==original and not window.history
        monkeypatch.setattr(module.QFileDialog,'getOpenFileName',lambda *args: ('',''))
        window.compare_machine_file()
        assert len(seen)==1
    finally:
        window.saved=window.project.dumps()
        window.close()
