import pytest
import pyembroidery as emb
from pyembroidery import Vp3Writer
from morale.formats import import_machine
from morale.engine import generate
from morale.vp3_positions import block_positions


@pytest.mark.parametrize('start',[(0,40),(30,0),(0,0),(-30,0),(0,-40),(30,40)])
def test_color_block_start_on_axis_is_restored(tmp_path,start):
    pattern=emb.EmbPattern();pattern.add_thread('red');pattern.add_thread('blue')
    pattern.add_stitch_absolute(emb.STITCH,30,40)
    pattern.add_stitch_absolute(emb.JUMP,*start)
    pattern.add_stitch_absolute(emb.COLOR_CHANGE,*start)
    target=(start[0]+10,start[1]+10)
    pattern.add_stitch_absolute(emb.STITCH,*target);pattern.add_stitch_absolute(emb.END,*target)
    path=tmp_path/'axis.vp3'
    with path.open('wb') as stream:Vp3Writer.write(pattern,stream)
    positions=block_positions(path.read_bytes());assert positions[1]==start
    blocks=generate(import_machine(path).project)
    sewn=[s for s in blocks[-1].stitches if s.command=='stitch']
    assert (sewn[-1].x,sewn[-1].y)==pytest.approx((target[0]/10,target[1]/10))
    jumps=[s for s in blocks[-1].stitches if s.command=='jump']
    assert any((s.x,s.y)==pytest.approx((start[0]/10,start[1]/10)) for s in jumps)
    if 0 in start:
        legacy=emb.read(str(path));last=next(s for s in reversed(legacy.stitches) if s[2]&emb.COMMAND_MASK==emb.STITCH)
        assert tuple(last[:2])!=target  # Regression demonstrably affects the upstream reader.


@pytest.mark.parametrize('data',[b'',b'%vsm%\0',b'not a vp3 file'])
def test_truncated_metadata_rejected(data):
    with pytest.raises(ValueError):block_positions(data)
