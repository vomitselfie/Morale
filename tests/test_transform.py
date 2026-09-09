import math

import pytest

from morale.arrange import transform_selection
from morale.model import DesignObject, Project
from morale.engine import generate


@pytest.mark.parametrize("flip", [False, True])
@pytest.mark.parametrize("rotation", [30, -90, 180])
def test_transform_rotates_and_scales_actual_geometry(flip, rotation):
    objects = [DesignObject(kind="path", stitch_type="running", x=-12, y=3, rotation=27, flip_x=flip,
                            points=[[-.5, -.5], [.25, 0], [.5, .5]]),
               DesignObject(x=20, y=12)]
    transformed = transform_selection(objects, 1.5, rotation, "hoop")
    c, s = math.cos(math.radians(rotation)), math.sin(math.radians(rotation))
    for original, result in zip(objects, transformed):
        for (x, y), actual in zip(original.outline(), result.outline()):
            assert actual == pytest.approx((1.5 * (x * c - y * s), 1.5 * (x * s + y * c)))
        assert result.id == original.id
        assert result.stitch_type == original.stitch_type


def test_selection_center_preserves_relative_arrangement():
    objects = [DesignObject(x=-10), DesignObject(x=30)]
    transformed = transform_selection(objects, 2, 90)
    for obj, expected in zip(transformed, [(10, -40), (10, 40)]):
        assert (obj.x, obj.y) == pytest.approx(expected)
    assert [o.width for o in transformed] == [40, 40]


def test_manual_commands_survive_scaling_and_rotation():
    obj = DesignObject(kind="stitches", stitch_type="manual", group_id="group",
                       stitch_data=[[-.5, 0, "jump"], [.5, 0, "stitch"], [.5, 0, "stop"]])
    result = transform_selection([obj], 2, 90)[0]
    stitches = generate(Project(objects=[result]))[0].stitches
    assert [s.command for s in stitches] == ["jump", "stitch", "stop"]
    assert (stitches[1].x, stitches[1].y) == pytest.approx((0, 20))
    assert result.group_id == "group"


def test_identity_transform_is_a_true_noop():
    objects = [DesignObject(rotation=360, angle=360)]
    assert transform_selection(objects, 1, 360) == objects


@pytest.mark.parametrize("scale,rotation", [(0, 0), (11, 0), (1, 361), (float("nan"), 0)])
def test_invalid_transform_parameters(scale, rotation):
    with pytest.raises(ValueError):
        transform_selection([DesignObject()], scale, rotation)


def affine(point):
    x,y=point[0]*1.7,point[1]*.6
    a=math.radians(23)
    return x*math.cos(a)-y*math.sin(a),x*math.sin(a)+y*math.cos(a)


@pytest.mark.parametrize('kind',['ellipse','rectangle','leaf','path','polygon','satin','compound'])
@pytest.mark.parametrize('flip',[False,True])
def test_nonuniform_world_geometry_and_settings(kind,flip):
    obj=DesignObject(kind=kind,x=11,y=-7,rotation=37,flip_x=flip,group_id='group',
                     stitch_type='satin' if kind=='satin' else 'running' if kind=='path' else 'fill',
                     points=[[-.5,-.5],[.5,-.5],[-.5,.5],[.5,.5]] if kind=='satin' else [[-.5,-.5],[.5,-.5],[0,.5]],
                     contours=[[[-.5,-.5],[.5,-.5],[.5,.5],[-.5,.5]],[[-.1,-.1],[.1,-.1],[.1,.1],[-.1,.1]]] if kind=='compound' else [],
                     spacing=.7,pull_compensation=.2,thread={'brand':'Test'},tie_off=True)
    result=transform_selection([obj],1.7,23,'hoop',.6)[0]
    for source_ring,result_ring in zip(obj.rings(),result.rings()):
        assert len(source_ring)==len(result_ring)
        for point,actual in zip(source_ring,result_ring):
            assert actual==pytest.approx(affine(point))
    for key in ('id','group_id','spacing','stitch_type','pull_compensation','thread','tie_off'):
        assert getattr(result,key)==getattr(obj,key)
    assert result.motif_reflected==flip
    assert Project.loads(Project(objects=[result]).dumps()).objects[0]==result


def test_nonuniform_bezier_retains_cubic_controls():
    from morale.bezier import edit_controls
    obj=edit_controls(DesignObject(kind='path',stitch_type='running'),[(-10,0),(-8,0),(-8,9),(4,10),(10,0),(12,0)])
    obj.rotation=31
    obj.flip_y=True
    result=transform_selection([obj],1.7,23,'hoop',.6)[0]
    assert result.handles
    for point,actual in zip(obj.control_points(),result.control_points()):
        assert actual==pytest.approx(affine(point))
    assert generate(Project(objects=[result]))


def test_nonuniform_manual_commands_and_coordinates_preserved():
    obj=DesignObject(kind='stitches',stitch_type='manual',rotation=37,flip_x=True,
                     stitch_data=[[-.5,-.5,'jump'],[0,.5,'stitch'],[0,.5,'trim'],[0,.5,'stop'],[.5,0,'jump'],[.5,.5,'stitch']])
    result=transform_selection([obj],1.7,23,'hoop',.6)[0]
    before=generate(Project(objects=[obj]))[0].stitches
    after=generate(Project(objects=[result]))[0].stitches
    assert [s.command for s in after]==[s.command for s in before]
    for a,b in zip(before,after):
        assert (b.x,b.y)==pytest.approx(affine((a.x,a.y)))


def test_nonuniform_selection_size_center_and_fill_direction():
    from morale.arrange import bounds
    objects=[DesignObject(x=-10,angle=45),DesignObject(x=30,angle=45)]
    result=transform_selection(objects,2,0,scale_y=.5)
    boxes=[bounds(o) for o in result]
    assert min(b[0] for b in boxes)==pytest.approx(-50)
    assert max(b[2] for b in boxes)==pytest.approx(70)
    assert max(b[3] for b in boxes)-min(b[1] for b in boxes)==pytest.approx(15)
    assert result[0].angle==pytest.approx(math.degrees(math.atan2(.5,2)))


@pytest.mark.parametrize('value',[0,11,float('nan'),float('inf')])
def test_invalid_vertical_scale(value):
    with pytest.raises(ValueError): transform_selection([DesignObject()],scale_y=value)


@pytest.mark.parametrize('extension',['dst','exp','jef','pec','pes','tbf','u01','vp3','xxx'])
def test_nonuniform_export_sewn_bounds(tmp_path,extension):
    from morale.formats import export_machine,import_machine
    objects=[DesignObject(rotation=31,x=-15,width=12,height=18),
             DesignObject(kind='path',stitch_type='triple',x=14,width=10,height=10,points=[[-.5,-.5],[.5,0],[0,.5]])]
    project=Project(objects=transform_selection(objects,1.4,15,'selection',.7))
    path=tmp_path/f'stretched.{extension}'
    export_machine(project,path)
    def sewn_bounds(design):
        points=[(s.x,s.y) for b in generate(design) for s in b.stitches if s.command=='stitch']
        return tuple(fn(p[i] for p in points) for fn,i in ((min,0),(min,1),(max,0),(max,1)))
    assert sewn_bounds(import_machine(path).project)==pytest.approx(sewn_bounds(project),abs=.15)
