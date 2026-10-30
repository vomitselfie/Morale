import pytest
from PySide6.QtWidgets import QApplication
from morale.svg_import import import_svg_text
from morale.vector_artwork import vector_artwork

@pytest.fixture(scope='module',autouse=True)
def app():return QApplication.instance() or QApplication([])


def test_symbol_instances_scale_and_preserve_paint_inheritance(tmp_path):
    source=tmp_path/'symbols.svg'
    source.write_text('<svg width="100" height="100"><defs><symbol id="s" viewBox="0 0 10 10"><rect width="10" height="10"/></symbol></defs><use href="#s" x="20" y="30" width="40" height="20" fill="red"/><use href="#s" x="60" y="60" width="10" height="10" fill="blue"/></svg>')
    project,image,info=vector_artwork(source,width=100)
    assert len(project.objects)==2
    first,second=project.objects
    assert (first.x,first.y,first.width,first.height)==pytest.approx((-10,-10,20,20))
    assert (second.x,second.y,second.width,second.height)==pytest.approx((15,15,10,10))
    assert [o.color for o in project.objects]==['#ff0000','#0000ff']


def test_unused_symbol_never_paints_and_instance_crops_overflow():
    text='<svg width="100" height="100"><symbol id="s" viewBox="0 0 10 10"><rect x="-10" y="-10" width="30" height="30"/></symbol><use href="#s" width="20" height="20"/></svg>'
    objects=import_svg_text(text).objects
    assert len(objects)==1
    assert (objects[0].width,objects[0].height)==pytest.approx((20*25.4/96,20*25.4/96))


def test_nested_symbol_and_transform():
    text='<svg width="100" height="100"><defs><symbol id="a" viewBox="0 0 10 10"><rect width="10" height="10"/></symbol><symbol id="b" viewBox="0 0 20 20"><use href="#a" width="10" height="10"/></symbol></defs><use href="#b" width="40" height="40" transform="translate(10,20)"/></svg>'
    obj=import_svg_text(text,center_artwork=False).objects[0]
    assert (obj.x,obj.y,obj.width,obj.height)==pytest.approx((-30*25.4/96,-20*25.4/96,20*25.4/96,20*25.4/96))


def test_circular_symbol_rejected():
    text='<svg><defs><symbol id="s"><use href="#s"/></symbol></defs><use href="#s"/></svg>'
    with pytest.raises(ValueError,match='circular'):import_svg_text(text)


@pytest.mark.parametrize('extension',['pes','pec','jef','dst','exp','vp3','u01','tbf','xxx'])
def test_symbol_worker_cutouts_and_machine_exports(tmp_path,extension):
    import json
    from morale.raster_trace import worker_main
    from morale.model import Project
    from morale.engine import generate
    from morale.formats import export_machine
    from morale.export_verify import verify_export
    source=tmp_path/'symbol-design.svg'
    source.write_text('<svg width="100" height="50"><defs><symbol id="ring" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M0 0H20V20H0Z M5 5H15V15H5Z"/></symbol></defs><use href="#ring" x="10" y="10" width="30" height="30" fill="red"/><use href="#ring" x="60" y="10" width="20" height="20" fill="blue"/></svg>')
    original=source.read_bytes();destination=tmp_path/'worker';destination.mkdir()
    assert worker_main([str(source),str(destination),json.dumps({'width':100,'stitch_mode':'fill'})])==0
    assert source.read_bytes()==original
    info=json.loads((destination/'preview.json').read_text());project=Project.loads(info['project'])
    assert len(project.objects)==2
    assert [o.color for o in project.objects]==['#ff0000','#0000ff']
    assert all(len(o.contours)==2 for o in project.objects)
    assert [o.width for o in project.objects]==pytest.approx([30,20])
    blocks=generate(project)
    assert generate(Project.loads(project.dumps()))==blocks
    path=tmp_path/f'symbols.{extension}'
    export_machine(project,path,blocks)
    result=verify_export(blocks,path)
    assert result['complete_path_comparison']
    assert result['bounds_delta_mm']<=.3
    assert all(problem.startswith('Trim commands increased:') for problem in result['problems']),result


def test_repeated_symbols_keep_internal_ids_unique_and_references_local():
    import xml.etree.ElementTree as ET
    from morale.svg_symbols import expand_symbols
    text='<svg width="100" height="100"><defs><symbol id="s" viewBox="0 0 10 10"><defs><clipPath id="cut"><rect width="50%" height="100%"/></clipPath></defs><rect id="face" width="10" height="10" clip-path="url(#cut)"/></symbol></defs><use href="#s" width="20" height="20"/><use href="#s" x="40" width="40" height="40"/></svg>'
    root=ET.fromstring(text);expand_symbols(root)
    ids=[n.get('id') for n in root.iter() if n.get('id')]
    assert len(ids)==len(set(ids))
    objects=import_svg_text(text,center_artwork=False).objects
    assert len(objects)==2
    assert [o.width for o in objects]==pytest.approx([10*25.4/96,20*25.4/96])


def test_symbol_localization_preserves_href_and_quoted_style_references():
    import xml.etree.ElementTree as ET
    from morale.svg_symbols import expand_symbols
    text="""<svg width="100" height="100"><defs><rect id="morale-symbol-1" width="1" height="1"/><symbol id="s" viewBox="0 0 10 10"><defs><rect id="shape" width="10" height="10"/><clipPath id="cut"><rect width="5" height="10"/></clipPath></defs><use href="#shape" style="clip-path:url('#cut')"/></symbol></defs><use href="#s" width="20" height="20"/><use href="#s" x="40" width="20" height="20"/></svg>"""
    root=ET.fromstring(text);expand_symbols(root)
    ids=[node.get('id') for node in root.iter() if node.get('id')]
    assert len(ids)==len(set(ids))
    objects=import_svg_text(text).objects
    assert len(objects)==2
    assert all(obj.width==pytest.approx(10*25.4/96) for obj in objects)


@pytest.mark.parametrize('dimension',['width','height'])
@pytest.mark.parametrize('zero',['0','0mm','0%'])
def test_zero_sized_symbol_does_not_hide_other_artwork(dimension,zero):
    sizes={'width':'20','height':'20'};sizes[dimension]=zero
    text=f'<svg width="100" height="100"><defs><symbol id="s" viewBox="0 0 10 10"><rect width="10" height="10"/></symbol></defs><use href="#s" width="{sizes["width"]}" height="{sizes["height"]}"/><rect x="50" width="5" height="5" fill="blue"/></svg>'
    objects=import_svg_text(text).objects
    assert len(objects)==1 and objects[0].color=='#0000ff'


@pytest.mark.parametrize('dimension',['width','height'])
def test_negative_symbol_instance_dimension_is_rejected(dimension):
    sizes={'width':'20','height':'20'};sizes[dimension]='-10'
    text=f'<svg width="100" height="100"><defs><symbol id="s" viewBox="0 0 10 10"><rect width="10" height="10"/></symbol></defs><use href="#s" width="{sizes["width"]}" height="{sizes["height"]}"/></svg>'
    with pytest.raises(ValueError,match='viewport dimensions'):import_svg_text(text)
