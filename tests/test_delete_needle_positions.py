import pytest
from morale.stitch_edit import delete_needle_positions


def test_retained_motion_and_controls_are_not_dropped():
    rows=[[0,0,'jump'],[1,1,'stitch'],[1,1,'trim'],[1,1,'stop'],[2,2,'stitch']]
    result,added=delete_needle_positions(rows,[1])
    assert not added and result==[[0,0,'jump'],[0,0,'trim'],[0,0,'stop'],[2,2,'stitch']]
    assert rows[2][:2]==[1,1]

def test_initial_controls_follow_synthesized_entry():
    result,added=delete_needle_positions([[0,0,'jump'],[0,0,'stop'],[3,4,'stitch']],[0])
    assert added and result==[[3,4,'jump'],[3,4,'stop'],[3,4,'stitch']]

@pytest.mark.parametrize('indices',[[2],[-1],[9],[True],['1']])
def test_invalid_or_nonmotion_selection_rejected(indices):
    with pytest.raises(ValueError):delete_needle_positions([[0,0,'jump'],[1,1,'stitch'],[1,1,'trim']],indices)

def test_reject_removing_every_position():
    with pytest.raises(ValueError,match='Keep at least one'):
        delete_needle_positions([[0,0,'jump'],[1,1,'stitch'],[1,1,'stop']],[0,1])
