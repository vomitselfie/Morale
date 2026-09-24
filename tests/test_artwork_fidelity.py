from copy import deepcopy
import pytest
from morale.model import DesignObject
from morale.artwork_fidelity import color_geometry,visible_colors
from morale.auto_digitize import area


def objects():return [DesignObject(kind='rectangle',x=-5,width=10,height=10,color='#ff0000'),DesignObject(kind='rectangle',x=5,width=10,height=10,color='#0000ff')]


def test_swapped_colors_fail_despite_identical_silhouette():
    before=objects();after=deepcopy(before)
    after[0].color,after[1].color=after[1].color,after[0].color
    assert visible_colors(before)[1]==visible_colors(after)[1]
    assert color_geometry(before,after)['error_ratio']==pytest.approx(2)


def test_visible_overlap_uses_upper_color_and_union_area():
    before=objects();before[0].x=before[1].x=0
    assert area(visible_colors(before)[1])==pytest.approx(100)
    assert color_geometry(before,[before[1]])['error_ratio']==0
    assert color_geometry(before,list(reversed(before)))['error_ratio']==pytest.approx(2)


def test_wrong_palette_missing_region_and_hidden_objects():
    before=objects();after=deepcopy(before)
    after[1].color='#00ff00'
    assert color_geometry(before,after)['unmatched_color_area_mm2']==pytest.approx(100)
    after=deepcopy(before);after[1].visible=False
    assert color_geometry(before,after)['error_ratio']==pytest.approx(.5)
    assert color_geometry(before,before)['error_ratio']==0
