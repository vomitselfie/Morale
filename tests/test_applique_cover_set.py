from copy import deepcopy
import math
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPainterPath
from morale.applique import applique_stages,cover_set_valid
from morale.model import Project,DesignObject
from morale.engine import generate
from morale.auto_digitize import outline_path,area,difference_area

@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])

def star():
    return DesignObject(kind='polygon',width=25,height=25,points=[[math.cos(i*math.pi/5)*(.5 if i%2==0 else .18),math.sin(i*math.pi/5)*(.5 if i%2==0 else .18)] for i in range(10)])

@pytest.mark.parametrize('width',[.5,2,6])
def test_sharp_cover_union_preserves_band_without_double_coverage(width):
    source=star();original=applique_stages(source,width,'fill')[-1];stages=applique_stages(source,width,'auto')
    union=QPainterPath();total=0
    for obj in stages[2:]:
        path=outline_path(obj.rings());total+=area(path);union=union.united(path)
    expected=outline_path(original.rings())
    assert difference_area(expected,union)<=max(.02,area(expected)*.01)
    assert total-area(union)<=.0001
    assert sum(s.command=='stop' for b in generate(Project(objects=stages)) for s in b.stitches)==2

def test_duplicated_components_are_not_accepted_as_valid_cover():
    cover=applique_stages(DesignObject(),2,'fill')[-1]
    assert cover_set_valid(cover,[cover])
    assert not cover_set_valid(cover,[cover,deepcopy(cover)],approximate=True)
    assert not cover_set_valid(cover,[])

def test_bad_component_split_keeps_original_band_with_reason(monkeypatch):
    import morale.applique as module
    monkeypatch.setattr(module,'cover_components',lambda cover:[cover,deepcopy(cover)])
    source=DesignObject(kind='rectangle',width=20,height=30)
    expected=applique_stages(source,2,'fill')[-1]
    stages=applique_stages(source,2,'auto')
    assert len(stages)==3 and stages[-1].stitch_type=='fill'
    assert 'separated' in stages[-1].stage_note
    assert stages[-1].rings()==expected.rings()

def test_bad_planned_geometry_keeps_original_band(monkeypatch):
    import morale.auto_digitize as module
    def invalid(project,**unused):
        candidate=deepcopy(project.objects[0]);candidate.width*=2
        return Project(objects=[candidate]),[{'reason':'test planner'}]
    monkeypatch.setattr(module,'choose_stitches',invalid)
    source=DesignObject(kind='rectangle',width=20,height=30)
    expected=applique_stages(source,2,'fill')[-1]
    stages=applique_stages(source,2,'auto')
    assert stages[-1].stitch_type=='fill' and 'overlap or change' in stages[-1].stage_note
    assert stages[-1].rings()==expected.rings()

def test_missing_cutout_border_is_detected():
    from morale.applique import cover_components
    source=DesignObject(kind='compound',width=20,height=20,contours=[[[-.5,-.5],[.5,-.5],[.5,.5],[-.5,.5]],[[-.2,-.2],[.2,-.2],[.2,.2],[-.2,.2]]])
    cover=applique_stages(source,2,'fill')[-1];pieces=cover_components(cover)
    assert len(pieces)==2 and cover_set_valid(cover,pieces)
    assert not cover_set_valid(cover,pieces[:1])
