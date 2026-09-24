import pyembroidery as emb
from morale.formats import export_machine,import_machine,decode_jef_trims
from morale.model import Project,DesignObject
from morale.engine import generate


def test_jef_writes_explicit_stationary_trim_markers(tmp_path):
    project=Project(objects=[DesignObject(kind='path',stitch_type='running',width=10,height=2,
        points=[[-.5,0],[.5,0]],trim_after=True)])
    path=tmp_path/'trim.jef';export_machine(project,path)
    raw=emb.read(str(path),settings={'trim_distance':None,'trims':False,'clipping':False})
    triples=[raw.stitches[i:i+3] for i in range(len(raw.stitches)-2)]
    assert any(all(r[2]&emb.COMMAND_MASK==emb.JUMP for r in group) and len({tuple(r[:2]) for r in group})==1 for group in triples)
    result=import_machine(path)
    assert sum(s.command=='trim' for b in generate(result.project) for s in b.stitches)==1
    assert any('stationary jumps' in note for note in result.notes)


def test_long_travel_does_not_invent_jef_trims(tmp_path):
    project=Project(objects=[DesignObject(kind='stitches',stitch_type='manual',width=100,height=2,
        stitch_data=[[-.4,0,'jump'],[-.39,0,'stitch'],[.4,0,'jump'],[.41,0,'stitch']])])
    path=tmp_path/'travel.jef';export_machine(project,path)
    commands=[s.command for b in generate(import_machine(path).project) for s in b.stitches]
    assert 'trim' not in commands and commands.count('stitch')==2


def test_marker_detection_preserves_nonzero_and_short_zero_jump_runs():
    pattern=emb.EmbPattern()
    pattern.stitches=[[0,0,emb.STITCH],[0,0,emb.JUMP],[0,0,emb.JUMP],
        [10,0,emb.JUMP],[20,0,emb.JUMP],[30,0,emb.JUMP],[30,0,emb.JUMP],
        [30,0,emb.JUMP],[30,0,emb.JUMP],[40,0,emb.STITCH]]
    decode_jef_trims(pattern)
    assert pattern.stitches==[[0,0,emb.STITCH],[0,0,emb.JUMP],[0,0,emb.JUMP],
        [10,0,emb.JUMP],[20,0,emb.JUMP],[30,0,emb.JUMP],[30,0,emb.TRIM],[40,0,emb.STITCH]]
