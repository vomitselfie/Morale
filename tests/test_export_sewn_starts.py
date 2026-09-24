import math
import pytest
from morale.model import DesignObject,Project
from morale.stitch_edit import manual_object
from morale.formats import export_machine,import_machine
from morale.engine import generate


@pytest.mark.parametrize('diagonal',[False,True])
@pytest.mark.parametrize('extension',['exp','jef','pec','pes'])
@pytest.mark.parametrize('boundary',['initial','trim','stop','color_change'])
def test_export_keeps_first_sewn_span_after_explicit_travel(tmp_path,extension,boundary,diagonal):
    rows=[[-10,0,'jump'],[-5,0,'stitch']]
    if boundary in {'trim','stop'}:rows.extend([[-5,0,boundary],[5,0,'jump'],[10,0,'stitch']])
    objects=[manual_object(DesignObject(color='#ff0000'),rows)]
    if boundary=='color_change':objects.append(manual_object(DesignObject(color='#0000ff'),[[5,0,'jump'],[10,0,'stitch']]))
    if diagonal:
        for obj in objects:
            obj.rotation=45
    source=Project(objects=objects);before=source.dumps();path=tmp_path/f'start.{extension}'
    export_machine(source,path);assert source.dumps()==before
    decoded=import_machine(path).project;previous=(0,0);sewn=[]
    for block in generate(decoded):
        for stitch in block.stitches:
            point=(stitch.x,stitch.y)
            if stitch.command=='stitch' and math.dist(previous,point)>1e-6:sewn.append((previous,point))
            if stitch.command in {'stitch','jump'}:previous=point
    expected=[((-10,0),(-5,0))]+([] if boundary=='initial' else [((5,0),(10,0))])
    # Object rotation is around each object's own center. Compare generated
    # source spans directly for rotated multi-object designs.
    if diagonal:
        expected=[];previous=(0,0)
        for block in generate(source):
            for stitch in block.stitches:
                point=(stitch.x,stitch.y)
                if stitch.command=='stitch' and math.dist(previous,point)>1e-6:expected.append((previous,point))
                if stitch.command in {'stitch','jump'}:previous=point
    assert len(sewn)==len(expected)
    for actual,wanted in zip(sewn,expected):
        assert actual[0]==pytest.approx(wanted[0],abs=.1) and actual[1]==pytest.approx(wanted[1],abs=.1)
