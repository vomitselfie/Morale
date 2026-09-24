import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import math

import pytest
from PySide6.QtWidgets import QApplication

from morale.cleanup import short_stitch_cleanup
from morale.engine import Stitch, generate
from morale.model import DesignObject, Project
from morale.stitch_edit import manual_object
from morale.formats import export_machine, import_machine


@pytest.fixture(scope="module",autouse=True)
def app():
    return QApplication.instance() or QApplication([])


def test_redundant_interior_points_removed_but_run_endpoints_kept():
    source=[Stitch(0,0,'jump'),Stitch(1,0),Stitch(1.05,0),Stitch(1.1,0),Stitch(2,0)]
    result=short_stitch_cleanup(source,.2,3)
    assert result==[source[0],source[1],source[-1]]
    assert len(source)==5
    assert short_stitch_cleanup(source,0,3)==source


@pytest.mark.parametrize('middle,end', [((1.05,0),(1.05,.1)), ((1.05,0),(1,0))])
def test_sharp_corners_and_reversals_retained(middle,end):
    source=[Stitch(0,0,'jump'),Stitch(1,0),Stitch(*middle),Stitch(*end)]
    assert short_stitch_cleanup(source,.2,3)==source


def test_maximum_length_is_not_exceeded_by_cleanup():
    source=[Stitch(0,0,'jump'),Stitch(.1,0),Stitch(.15,0),Stitch(1,0)]
    assert short_stitch_cleanup(source,.2,.86)==source


def test_controls_and_first_last_stitches_of_each_run_are_retained():
    source=[Stitch(0,0,'jump'),Stitch(.01,0),Stitch(.02,0),Stitch(.02,0,'trim'),
            Stitch(10,0,'jump'),Stitch(10.01,0),Stitch(10.02,0),Stitch(10.02,0,'stop')]
    assert short_stitch_cleanup(source,.5,3)==source


def test_successive_removals_do_not_accumulate_geometric_error():
    source=[Stitch(0,0,'jump')]+[Stitch(i/500,.1*math.sin(i/100)) for i in range(1001)]
    result=short_stitch_cleanup(source,.1,.3)
    assert len(result)<len(source)/2
    def distance(p,a,b):
        dx,dy=b.x-a.x,b.y-a.y
        square=dx*dx+dy*dy
        t=max(0,min(1,((p.x-a.x)*dx+(p.y-a.y)*dy)/square)) if square else 0
        return math.hypot(p.x-a.x-t*dx,p.y-a.y-t*dy)
    segments=list(zip(result[1:],result[2:]))
    assert max(min(distance(p,a,b) for a,b in segments) for p in source[1:])<=.010000001
    assert all(math.dist((a.x,a.y),(b.x,b.y))<=.300000001 for a,b in segments)


def leaf():
    return DesignObject(kind='leaf',width=10,height=15,underlay_inset=.5)


def test_generated_cleanup_reduces_redundancy_without_changing_source_or_controls():
    obj=leaf()
    outline=obj.rings()
    before=generate(Project(objects=[obj]))[0].stitches
    obj.minimum_stitch=.3
    after=generate(Project(objects=[obj]))[0].stitches
    assert len(after)<len(before)
    assert obj.rings()==outline
    assert [s for s in after if s.command!='stitch']==[s for s in before if s.command!='stitch']


def test_finishing_ties_remain_short_and_manual_stitches_are_untouched():
    obj=DesignObject(kind='path',stitch_type='running',points=[[-.5,0],[.5,0]],minimum_stitch=1,tie_in=True,tie_off=True)
    stitches=generate(Project(objects=[obj]))[0].stitches
    assert sum(0<math.dist((a.x,a.y),(b.x,b.y))<1 for a,b in zip(stitches,stitches[1:]) if b.command=='stitch')>=8
    manual=manual_object(DesignObject(),[(0,0,'jump'),(.01,0,'stitch'),(.02,0,'stitch'),(1,0,'stitch')])
    before=generate(Project(objects=[manual]))
    manual.minimum_stitch=1
    assert generate(Project(objects=[manual]))==before


@pytest.mark.parametrize('value',[-1,1.1,float('nan'),True,'bad'])
def test_invalid_threshold_rejected(value):
    with pytest.raises(ValueError):
        short_stitch_cleanup([],value,3)


def test_native_setting_units_persistence_and_undo():
    from morale.app import MainWindow
    window=MainWindow()
    try:
        obj=leaf()
        window.replace_project(Project(objects=[obj]))
        window.select(obj.id)
        before=window.project.dumps()
        window.fields['minimum_stitch'].setValue(.3)
        saved=window.project.dumps()
        window.set_unit('in')
        assert window.project.dumps()==saved
        assert window.fields['minimum_stitch'].value()==pytest.approx(.3/25.4,abs=.0001)
        assert Project.loads(saved).objects[0].minimum_stitch==.3
        window.undo()
        assert window.project.dumps()==before
    finally:
        window.saved=window.project.dumps()
        window.close()


@pytest.mark.parametrize('extension',['dst','exp','jef','pec','pes','tbf','u01','vp3','xxx'])
def test_cleaned_generated_design_exports_in_all_formats(tmp_path,extension):
    obj=leaf()
    obj.minimum_stitch=.3
    path=tmp_path/f'cleaned.{extension}'
    export_machine(Project(objects=[obj]),path)
    stitches=[s for b in generate(import_machine(path).project) for s in b.stitches if s.command=='stitch']
    assert stitches
    source=generate(Project(objects=[obj]))[0].stitches
    # All writers must retain the sewn needle bounds. PEC/PES no longer get
    # an exception for synthetic needle points at travel-only extrema.
    reference=[s for s in source if s.command=='stitch']
    assert (min(s.y for s in stitches),max(s.y for s in stitches))==pytest.approx(
        (min(s.y for s in reference),max(s.y for s in reference)),abs=.15)
