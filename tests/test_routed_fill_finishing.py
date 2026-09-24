"""Combined routing, cleanup, gradient, underlay and finishing invariants."""
import math
import pytest
from morale.model import Project,DesignObject
from morale.engine import generate,segment_inside

@pytest.mark.parametrize('rotation,angle,gradient',[(0,0,False),(17,30,True),(63,45,False),(17,90,True)])
@pytest.mark.parametrize('cleanup',[0,.5])
def test_finished_routed_fill_stays_in_material_and_controls_follow_motion(rotation,angle,gradient,cleanup):
    obj=DesignObject(kind='compound',width=30,height=20,rotation=rotation,angle=angle,spacing=.6,
        connect_fill=True,underlay=True,underlay_style='edge_sparse',underlay_spacing=3,
        minimum_stitch=cleanup,tie_in=True,tie_off=True,jump_trim=2,trim_after=True,stop_after=True,
        density_gradient=gradient,flip_x=gradient,flip_y=rotation==63,
        contours=[[[-.5,-.5],[.5,-.5],[.5,.5],[-.5,.5]],[[-.2,-.2],[.2,-.2],[.2,.2],[-.2,.2]]])
    project=Project(objects=[obj]);baseline=generate(project)[0].stitches
    obj.route_fill=True;actual=generate(project)[0].stitches
    rings=obj.rings()
    def check(rows):
        previous=(0,0);travel=0
        for i,s in enumerate(rows):
            point=(s.x,s.y)
            if s.command=='stitch':assert segment_inside(previous,point,rings[0],rings[1:]),(i,previous,point)
            elif s.command=='jump':travel+=math.dist(previous,point)
            else:assert point==pytest.approx(previous,abs=1e-8)
            if s.command in {'stitch','jump'}:previous=point
            if s.command=='trim':
                following=next((p for p in rows[i+1:] if p.command in {'stitch','jump'}),None)
                assert following is None or following.command=='jump'
        assert rows[-1].command=='stop' and any(s.command=='trim' for s in rows)
        return travel
    assert check(actual)<=check(baseline)+1e-6
    assert (actual[0].x,actual[0].y)==pytest.approx((baseline[0].x,baseline[0].y))
    assert (actual[-1].x,actual[-1].y)==pytest.approx((baseline[-1].x,baseline[-1].y))
    assert generate(Project.loads(project.dumps()))==generate(project)
