import pytest
import pyembroidery as emb
from pyembroidery import PesWriter,Vp3Writer
from morale.formats import export_machine,import_machine,to_pattern
from morale.model import Project,DesignObject
from morale.engine import generate


@pytest.mark.parametrize('extension',['.pes','.vp3'])
def test_unicode_thread_fields_roundtrip_without_moving_stitches(tmp_path,extension):
    metadata={'brand':'糸 café','catalog_number':'色12','description':'Été 🌸'}
    source=Project(name='刺繍 Étoile 🌸',objects=[DesignObject(thread=metadata)])
    before=source.dumps();path=tmp_path/('unicode'+extension)
    export_machine(source,path);decoded=import_machine(path).project
    assert decoded.objects[0].thread==metadata
    assert source.dumps()==before
    baseline=Project.loads(before);baseline.name='ASCII';baseline.objects[0].thread={}
    reference=tmp_path/('ascii'+extension);export_machine(baseline,reference)
    assert [b.stitches for b in generate(decoded)]==[b.stitches for b in generate(import_machine(reference).project)]
    if extension=='.pes':assert emb.read(str(path)).get_metadata('name')==source.name


def test_pes_byte_limit_does_not_split_utf8_or_corrupt_following_fields(tmp_path):
    source=Project(name='🌸'*120,objects=[DesignObject(thread={'description':'🌸'*300,'brand':'Following field'})])
    path=tmp_path/'long.pes';export_machine(source,path)
    raw=emb.read(str(path));obj=import_machine(path).project.objects[0]
    assert raw.get_metadata('name')=='🌸'*63
    assert obj.thread['description']=='🌸'*63 and obj.thread['brand']=='Following field'


@pytest.mark.parametrize('extension,version',[('.pec',6),('.pes',1)])
def test_fixed_pec_label_handles_non_ascii_project_names(tmp_path,extension,version):
    source=Project(name='刺繍 🌸 café',objects=[DesignObject()]);path=tmp_path/('label'+extension)
    export_machine(source,path,pes_version=version)
    assert any(s.command=='stitch' for b in generate(import_machine(path).project) for s in b.stitches)
    data=path.read_bytes();start=data.index(b'LA:')
    assert data[start+19:start+20]==b'\r'


@pytest.mark.parametrize('extension',['.pes','.pec','.vp3'])
def test_ascii_exports_are_byte_identical_and_upstream_helpers_unchanged(tmp_path,extension):
    # Axis-aligned sewing from the origin isolates text changes from geometry corrections.
    source=Project(name='ASCII example',objects=[DesignObject(kind='path',stitch_type='running',x=10,width=20,points=[[-.5,0],[.5,0]],thread={'brand':'Brand','catalog_number':'42','description':'Blue'})])
    original_pes=PesWriter.write_pes_string_8;original_vp3=Vp3Writer.vp3_write_string_8
    actual=tmp_path/('actual'+extension);reference=tmp_path/('reference'+extension)
    export_machine(source,actual)
    emb.write(to_pattern(source),str(reference),{'full_jump':False,'version':6} if extension=='.pes' else {'full_jump':False})
    assert actual.read_bytes()==reference.read_bytes()
    assert PesWriter.write_pes_string_8 is original_pes and Vp3Writer.vp3_write_string_8 is original_vp3
