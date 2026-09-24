import pytest
from morale.engine import Block,Stitch
from morale.stitch_edit import manual_object
from morale.path_fidelity import compare_sewn_paths,sewn_segments

def block(points):return [Block('a','#ff0000',[Stitch(*p) for p in points])]

def test_subdivision_and_extra_controls_do_not_change_sewn_geometry():
    a=block([(0,0,'jump'),(10,0,'stitch')])
    b=block([(0,0,'jump'),(5,0,'stitch'),(5,0,'trim'),(10,0,'stitch')])
    result=compare_sewn_paths(a,b)
    assert all(result[k]['complete'] and not result[k]['outside_samples'] for k in ('decoded_outside_source','source_outside_decoded'))

def test_lost_jump_detected_despite_equal_sewn_point_bounds():
    a=block([(0,0,'jump'),(1,0,'stitch'),(9,0,'jump'),(10,0,'stitch')])
    b=block([(0,0,'jump'),(1,0,'stitch'),(10,0,'stitch')])
    result=compare_sewn_paths(a,b)
    assert result['decoded_outside_source']['estimated_outside_length_mm']==pytest.approx(7.7,abs=.25)
    assert not result['source_outside_decoded']['outside_samples']
    assert result['decoded_outside_source']['locations']

def test_missing_sewn_line_is_checked_in_reverse_direction():
    a=block([(0,0,'jump'),(10,0,'stitch')]);b=block([(0,0,'jump'),(10,0,'jump')])
    result=compare_sewn_paths(a,b)
    assert result['source_outside_decoded']['estimated_outside_length_mm']==pytest.approx(10)
    assert not result['decoded_outside_source']['outside_samples']

@pytest.mark.parametrize('offset,detected',[(.1,False),(.2,True),(-.2,True)])
def test_quantization_tolerance(offset,detected):
    a=block([(-4,0,'jump'),(4,0,'stitch')]);b=block([(-4,offset,'jump'),(4,offset,'stitch')])
    assert bool(compare_sewn_paths(a,b)['decoded_outside_source']['outside_samples'])==detected

def test_long_diagonal_and_cell_boundaries_match():
    a=block([(-30.1,-30.1,'jump'),(30.1,30.1,'stitch')])
    assert not compare_sewn_paths(a,a)['decoded_outside_source']['outside_samples']

def test_budget_exhaustion_is_explicit_not_success():
    a=block([(0,0,'jump'),(10,0,'stitch')])
    result=compare_sewn_paths(a,a,budget=1)
    assert not result['decoded_outside_source']['complete']

def test_controls_do_not_reposition_and_zero_length_is_ignored():
    a=block([(1,0,'jump'),(99,99,'trim'),(2,0,'stitch'),(2,0,'stitch')])
    assert list(sewn_segments(a))==[((1,0),(2,0))]

def test_installed_vp3_jump_omission_is_visible(tmp_path):
    from morale.model import Project,DesignObject
    from morale.formats import export_machine
    from morale.comparison import load_comparison
    project=Project(objects=[manual_object(DesignObject(),[[0,0,'jump'],[1,0,'stitch'],[9,0,'jump'],[10,0,'stitch']])])
    path=tmp_path/'gap.vp3';export_machine(project,path)
    _,_,report,_=load_comparison(project,path)
    assert report['source']['sewn_bounds_mm']==report['decoded']['sewn_bounds_mm']
    assert report['sewn_geometry']['decoded_outside_source']['estimated_outside_length_mm']>7

def test_native_difference_markers_and_disclosure(tmp_path):
    from PySide6.QtWidgets import QApplication
    from morale.model import Project,DesignObject
    from morale.formats import export_machine
    from morale.comparison import ComparisonDialog
    app=QApplication.instance() or QApplication([])
    project=Project(objects=[manual_object(DesignObject(),[[0,0,'jump'],[1,0,'stitch'],[9,0,'jump'],[10,0,'stitch']])])
    path=tmp_path/'gap.vp3';export_machine(project,path)
    dialog=ComparisonDialog(project,path)
    try:
        assert dialog.view.deviations and '0.15 mm tolerance' in dialog.geometry_note.text()
        dialog.deviation_toggle.setChecked(True)
        assert dialog.view.show_deviations
        assert not dialog.view.travel
    finally:dialog.close()
