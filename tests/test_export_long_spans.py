import math
from copy import deepcopy
import pyembroidery as emb
import pytest
from morale.model import DesignObject,Project
from morale.stitch_edit import manual_object
from morale.formats import export_machine,import_machine,FORMAT_REGISTRY
from morale.engine import generate
from morale.export_spans import subdivide_sewn_spans


@pytest.mark.parametrize('extension',['dst','exp','jef','pec','pes','tbf','u01','vp3','xxx'])
@pytest.mark.parametrize('diagonal',[False,True])
def test_oversized_run_retains_sewn_length_and_endpoints(tmp_path,extension,diagonal):
    a=(-150,-150 if diagonal else 0);b=(150,150 if diagonal else 0)
    obj=manual_object(DesignObject(),[[*a,'jump'],[*b,'stitch']]);source=Project(hoop_width=500,hoop_height=500,objects=[obj]);before=source.dumps()
    path=tmp_path/f'long.{extension}';export_machine(source,path);assert source.dumps()==before
    previous=(0,0);segments=[]
    for block in generate(import_machine(path).project):
        for stitch in block.stitches:
            point=(stitch.x,stitch.y)
            if stitch.command=='stitch' and math.dist(previous,point)>1e-6:segments.append((previous,point))
            if stitch.command in {'stitch','jump'}:previous=point
    assert segments and segments[0][0]==pytest.approx(a,abs=.15) and segments[-1][1]==pytest.approx(b,abs=.15)
    assert sum(math.dist(x,y) for x,y in segments)==pytest.approx(math.dist(a,b),abs=.25)
    limit=FORMAT_REGISTRY['.'+extension]['writer'].MAX_STITCH_DISTANCE/10
    assert max(math.dist(x,y) for x,y in segments)<=limit+.01


def test_preparation_keeps_travel_controls_flags_and_original_pattern():
    pattern=emb.EmbPattern();pattern.add_thread('red')
    pattern.stitches=[[0,0,emb.JUMP],[300,0,emb.STITCH],[300,0,emb.TRIM],[900,900,emb.JUMP],[900,900,emb.STOP],[900,1200,emb.STITCH],[900,1200,emb.END]]
    before=deepcopy(pattern.stitches);result,added=subdivide_sewn_spans(pattern,120)
    assert added==4 and pattern.stitches==before
    assert [r for r in result.stitches if r[2]!=emb.STITCH]==[r for r in before if r[2]!=emb.STITCH]
    assert result.threadlist==pattern.threadlist
    assert result.stitches[-2]==before[-2]


def test_capacity_failure_preserves_destination_and_source(tmp_path,monkeypatch):
    import morale.export_spans as module
    source=Project(hoop_width=500,objects=[manual_object(DesignObject(),[[-150,0,'jump'],[150,0,'stitch']])]);before=source.dumps()
    path=tmp_path/'long.dst';path.write_bytes(b'original')
    original=module.subdivide_sewn_spans
    monkeypatch.setattr(module,'subdivide_sewn_spans',lambda pattern,maximum:original(pattern,maximum,limit=10))
    with pytest.raises(ValueError,match='export limit'):export_machine(source,path)
    assert source.dumps()==before and path.read_bytes()==b'original' and list(tmp_path.iterdir())==[path]


@pytest.mark.parametrize('offset',[-3.27,2.27,-8.99])
def test_vp3_fractional_block_center_preserves_rounded_positions(tmp_path,offset):
    source=Project(objects=[manual_object(DesignObject(),[[offset,4.81,'jump'],[offset+4.51,7.53,'stitch'],[offset+10.09,3.92,'stitch']])])
    path=tmp_path/'fractional.vp3';export_machine(source,path)
    actual=[(s.x,s.y) for b in generate(import_machine(path).project) for s in b.stitches if s.command=='stitch']
    expected=[(s.x,s.y) for b in generate(source) for s in b.stitches if s.command=='stitch']
    assert len(actual)==len(expected)
    for a,b in zip(actual,expected):assert a==pytest.approx(b,abs=.051)
