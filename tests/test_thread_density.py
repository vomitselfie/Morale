import math
import pytest
from morale.engine import Block,Stitch
from morale.density_review import measure_thread_density,measure_density

def blocks(points):return [Block('a','#ff0000',[Stitch(*p) for p in points])]

def test_horizontal_line_partition_conserves_length():
    report,cells=measure_thread_density(blocks([(-.5,.5,'jump'),(2.5,.5,'stitch')]))
    assert dict(cells)==pytest.approx({(-1,0):.5,(0,0):1,(1,0):1,(2,0):.5})
    assert report['complete'] and report['total_sewn_mm']==report['mapped_sewn_mm']==3

def test_diagonal_corner_crossings_are_not_double_counted():
    report,cells=measure_thread_density(blocks([(0,0,'jump'),(2,2,'stitch')]))
    assert set(cells)=={(0,0),(1,1)}
    assert list(cells.values())==pytest.approx([math.sqrt(2)]*2)
    assert report['mapped_sewn_mm']==pytest.approx(math.sqrt(8))

def test_grid_edge_line_has_single_owner_and_is_direction_independent():
    a=blocks([(1,-2,'jump'),(1,2,'stitch')]);b=blocks([(1,2,'jump'),(1,-2,'stitch')])
    assert measure_thread_density(a)[1]==measure_thread_density(b)[1]=={(1,-2):1,(1,-1):1,(1,0):1,(1,1):1}

def test_travel_and_controls_do_not_add_sewn_length():
    report,cells=measure_thread_density(blocks([(0,0,'jump'),(1,0,'stitch'),(8,0,'jump'),(99,99,'trim'),(9,0,'stitch'),(9,0,'stitch')]))
    assert report['total_sewn_mm']==2 and set(cells)=={(0,0),(8,0)}

def test_satin_span_has_thread_in_cells_without_needle_points():
    source=blocks([(0,.5,'jump'),(5,.5,'stitch')])
    _,needle=measure_density(source);_,thread=measure_thread_density(source)
    assert (2,0) not in needle and thread[2,0]==pytest.approx(1)

def test_multiple_objects_sum_length_and_report_shared_cells():
    source=blocks([(0,.5,'jump'),(1,.5,'stitch')])+[Block('b','#0000ff',[Stitch(0,.5,'jump'),Stitch(1,.5)])]
    report,cells=measure_thread_density(source)
    assert cells[0,0]==2 and report['multi_object_cells']==1

def test_budget_partial_map_keeps_total_length_honest():
    report,cells=measure_thread_density(blocks([(0,0,'jump'),(1,0,'stitch'),(4,0,'stitch')]),budget=1)
    assert not report['complete'] and report['mapped_sewn_mm']==1 and report['total_sewn_mm']==4
    assert cells=={(0,0):1}

def test_empty_map():
    report,cells=measure_thread_density([])
    assert report['complete'] and report['total_sewn_mm']==0 and not cells

@pytest.mark.parametrize('endpoint',[(3.3,4.7),(-4.4,2.1),(-3.3,-7.8),(8.2,-1.1)])
def test_arbitrary_segments_conserve_total(endpoint):
    report,cells=measure_thread_density(blocks([(.13,.27,'jump'),(*endpoint,'stitch')]))
    assert sum(cells.values())==pytest.approx(math.dist((.13,.27),endpoint))
    assert report['mapped_sewn_mm']==pytest.approx(report['total_sewn_mm'])
