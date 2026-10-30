import gzip
import importlib.util
import json
import math
from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication
from morale import embroidery_fonts
from morale.embroidery_fonts import make_font_lettering, height_range
from morale.engine import generate
from morale.model import Project

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('import_inkstitch_fonts', ROOT / 'scripts' / 'import_inkstitch_fonts.py')
converter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(converter)


@pytest.fixture(scope='module', autouse=True)
def app():
    return QApplication.instance() or QApplication([])


def svg_font(layers, height='100', view='0 0 100 100', guide='0,0'):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
 xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd" xmlns:inkstitch="http://inkstitch.org/namespace"
 width="{height}" height="{height}" {f'viewBox="{view}"' if view else ''}>
<sodipodi:namedview><sodipodi:guide position="{guide}" orientation="0,1" inkscape:label="baseline"/></sodipodi:namedview>
{layers}</svg>'''


def satin_layer(char, dx=0, extra=''):
    # A 10 px wide vertical column from y=20 to y=100 (the baseline), with one rung.
    return f'''<g inkscape:groupmode="layer" inkscape:label="GlyphLayer-{char}" style="display:none">
 <g transform="translate({dx},0)"><path d="M 10,20 L 10,100 M 20,20 L 20,100 M 5,60 L 25,60" style="fill:none;stroke:#000"
 inkstitch:satin_column="True"/>
 <path d="M 30,40 L 50,40 L 50,100 L 30,100 Z" style="fill:#000"/>
 <path d="M 60,100 L 70,50" style="fill:none;stroke:#000" inkstitch:running_stitch_length_mm="2"/>{extra}</g></g>'''


def write_source(tmp_path, name, svg, license_name='SIL Open Font License v1.1', **meta):
    folder = tmp_path / 'src' / name
    folder.mkdir(parents=True)
    (folder / 'ltr.svg').write_text(svg)
    (folder / 'LICENSE').write_text(license_name)
    data = {'name': name.title(), 'font_license': license_name, 'size': 20, 'min_scale': .5, 'max_scale': 2,
            'horiz_adv_x': {c: 80 for c in 'ABCDEFGHIJKLM'}, 'horiz_adv_x_space': 30, 'kerning_pairs': {'A B': 10}}
    data.update(meta)
    (folder / 'font.json').write_text(json.dumps(data))
    return folder


def converted(tmp_path, name):
    with gzip.open(tmp_path / 'out' / name / 'font.json.gz', 'rt') as stream:
        return json.load(stream)


def test_converter_reads_satins_fills_runs_and_nested_transforms(tmp_path):
    layers = ''.join(satin_layer(c, dx=5 if c == 'B' else 0) for c in 'ABCDEFGHIJKL')
    folder = write_source(tmp_path, 'demo', svg_font(layers))
    font, message = converter.convert(folder, tmp_path / 'out')
    assert font and '12 glyphs' in message
    stored = converted(tmp_path, 'demo')
    glyph = stored['glyphs']['A']
    kinds = [next(iter(p)) for p in glyph['pieces']]
    assert kinds == ['rails', 'fill', 'run']
    rails = glyph['pieces'][0]['rails']
    px = 25.4 / 96
    # Stations pair the two rails; the column spans 10 px and ends on the baseline (y = 0).
    assert all(math.isclose(math.dist(a, b), 10 * px, abs_tol=1e-3) for a, b in zip(rails[::2], rails[1::2]))
    assert max(y for _, y in rails) == pytest.approx(0, abs=1e-6) and min(y for _, y in rails) == pytest.approx(-80 * px, abs=1e-3)
    # The inner group transform shifts B by 5 px.
    shift = stored['glyphs']['B']['pieces'][0]['rails'][0][0] - rails[0][0]
    assert shift == pytest.approx(5 * px, abs=1e-3)
    assert glyph['advance'] == pytest.approx(80 * px, abs=1e-3) and stored['kerning']['A B'] == pytest.approx(10 * px, abs=1e-3)
    assert stored['cap_height_mm'] == pytest.approx(80 * px, abs=1e-3)
    assert (tmp_path / 'out' / 'demo' / 'LICENSE').exists()


def test_converter_handles_mm_documents_without_viewbox_and_skips_blocked_licenses(tmp_path):
    layers = ''.join(satin_layer(c) for c in 'ABCDEFGHIJKL')
    # A 100 mm document with a 0 0 100 100 viewBox: one unit is one millimetre.
    folder = write_source(tmp_path, 'metric', svg_font(layers, height='100mm'))
    converter.convert(folder, tmp_path / 'out')
    rails = converted(tmp_path, 'metric')['glyphs']['A']['pieces'][0]['rails']
    assert math.dist(rails[0], rails[1]) == pytest.approx(10, abs=1e-3)
    plain = write_source(tmp_path, 'plain', svg_font(layers, view=None))
    converter.convert(plain, tmp_path / 'out')
    assert math.dist(*converted(tmp_path, 'plain')['glyphs']['A']['pieces'][0]['rails'][:2]) == pytest.approx(10 * 25.4 / 96, abs=1e-3)
    blocked = write_source(tmp_path, 'nc', svg_font(layers), license_name='CC BY-NC-SA 4.0')
    font, message = converter.convert(blocked, tmp_path / 'out')
    assert font is None and 'license' in message


def test_rungless_satins_pair_rail_nodes_in_order():
    first = [(0, 0), (0, 10), (0, 30)]
    second = [(5, 0), (5, 20), (5, 30)]
    pairs = converter.satin_pairs([first, second], 1)
    # The middle nodes (10 and 20) pair up, so a station joins them.
    assert any(math.isclose(a[1], 10) and math.isclose(b[1], 20) for a, b in zip(pairs[::2], pairs[1::2]))


@pytest.fixture
def font_dir(tmp_path, monkeypatch):
    layers = ''.join(satin_layer(c) for c in 'ABCDEFGHIJKLM')
    converter.convert(write_source(tmp_path, 'demo', svg_font(layers), letter_case='upper'), tmp_path / 'fonts')
    monkeypatch.setattr(embroidery_fonts, 'FONT_DIR', tmp_path / 'fonts')
    embroidery_fonts.available_fonts.cache_clear()
    embroidery_fonts.load_font.cache_clear()
    yield tmp_path / 'fonts'
    embroidery_fonts.available_fonts.cache_clear()
    embroidery_fonts.load_font.cache_clear()


def test_font_lettering_lays_out_kerns_and_sews_the_designed_pieces(font_dir):
    assert [f[0] for f in embroidery_fonts.available_fonts()] == ['demo']
    low, high = height_range(embroidery_fonts.load_font('demo'))
    reference = embroidery_fonts.reference_height(embroidery_fonts.load_font('demo'))
    obj = make_font_lettering('ab c', 'demo', reference)
    assert obj.stitch_type == 'satin' and obj.lettering['embroidery_font'] == 'demo' and obj.underlay
    kinds = [next(iter(p)) for p in obj.lettering['columns']]
    assert kinds == ['rails', 'fill', 'run'] * 3
    restored = Project.loads(Project(objects=[obj]).dumps()).objects[0]
    assert restored.lettering == obj.lettering
    assert any(s.command == 'stitch' for b in generate(Project(objects=[restored])) for s in b.stitches)
    # Kerning (A B only) pulls B towards A by 10 px; B to C keeps the full 80 px advance.
    kerned = make_font_lettering('ABC', 'demo', reference)
    starts = [kerned.transform([p['rails'][0]])[0][0] for p in kerned.lettering['columns'] if 'rails' in p]
    px = 25.4 / 96 * reference / embroidery_fonts.load_font('demo')['cap_height_mm']
    assert starts[2] - starts[1] == pytest.approx(80 * px, abs=1e-3)
    assert starts[1] - starts[0] == pytest.approx(70 * px, abs=1e-3)
    assert low == pytest.approx(reference * .5) and high == pytest.approx(reference * 2)


def test_font_lettering_refuses_unsupported_sizes_and_characters(font_dir):
    reference = embroidery_fonts.reference_height(embroidery_fonts.load_font('demo'))
    with pytest.raises(ValueError, match='designed height range'):
        make_font_lettering('AB', 'demo', reference * 3)
    with pytest.raises(ValueError, match='no stitches for: Z'):
        make_font_lettering('AZ', 'demo', reference)
    with pytest.raises(ValueError):
        make_font_lettering('AB', '../demo', reference)
    bad = make_font_lettering('AB', 'demo', reference)
    bad.lettering['embroidery_font'] = 'bad id!'
    with pytest.raises(ValueError):
        Project.loads(Project(objects=[bad]).dumps())


def test_dialog_offers_embroidery_fonts_and_switches_rows(font_dir):
    from morale.lettering import LetteringDialog
    dialog = LetteringDialog()
    try:
        assert dialog.source.currentData() == 'embroidery' and dialog.embroidery_font.currentData() == 'demo'
        assert dialog.form.isRowVisible(dialog.embroidery_font) and not dialog.form.isRowVisible(dialog.stitches)
        assert 'Designed height range:' in dialog.size_hint.text()
        dialog.text.setText('AB'); dialog.accept()
        assert dialog.candidate.lettering['embroidery_font'] == 'demo'
        dialog.source.setCurrentIndex(1)
        assert dialog.form.isRowVisible(dialog.stitches) and not dialog.form.isRowVisible(dialog.embroidery_font)
    finally:
        dialog.close()


def test_embroidery_lettering_keeps_its_satin_stitches(font_dir):
    from morale.app import MainWindow
    window = MainWindow()
    try:
        reference = embroidery_fonts.reference_height(embroidery_fonts.load_font('demo'))
        window.apply_lettering(make_font_lettering('AB', 'demo', reference))
        before = window.project.dumps()
        window.update_property('stitch_type', 'fill')
        assert window.project.dumps() == before
    finally:
        window.saved = window.project.dumps(); window.close()


@pytest.mark.parametrize('curve',[-120,0,120])
def test_curved_embroidery_font_preserves_piece_geometry_and_roundtrips(font_dir,curve):
    height=embroidery_fonts.reference_height(embroidery_fonts.load_font('demo'))
    straight=make_font_lettering('ABC','demo',height)
    curved=make_font_lettering('ABC','demo',height,layout='curved',curve=curve)
    assert curved.lettering['layout']=='curved' and curved.lettering['curve']==curve
    assert len(curved.lettering['columns'])==len(straight.lettering['columns'])
    def paths(obj,piece):
        kind,value=next(iter(piece.items()))
        return [[(x*obj.width,y*obj.height) for x,y in ring] for ring in (value if kind=='fill' else [value])]
    for old,new in zip(straight.lettering['columns'],curved.lettering['columns']):
        assert old.keys()==new.keys()
        for a,b in zip(paths(straight,old),paths(curved,new)):
            assert len(a)==len(b)
            assert [math.dist(p,q) for p,q in zip(a,a[1:])]==pytest.approx([math.dist(p,q) for p,q in zip(b,b[1:])])
    if curve:assert curved.height!=pytest.approx(straight.height)
    else:assert curved.lettering['columns']==straight.lettering['columns']
    project=Project(objects=[curved])
    reopened=Project.loads(project.dumps())
    assert generate(project)==generate(reopened)


def test_embroidery_font_dialog_offers_curved_layout(font_dir):
    from morale.lettering import LetteringDialog
    dialog=LetteringDialog()
    try:
        dialog.layout_choice.setCurrentIndex(dialog.layout_choice.findData('curved'))
        dialog.text.setText('ABC');dialog.curve.setValue(90)
        dialog.accept()
        assert dialog.candidate.lettering['embroidery_font']=='demo'
        assert dialog.candidate.lettering['layout']=='curved'
        assert dialog.candidate.lettering['curve']==90
    finally:dialog.close()


@pytest.mark.parametrize('extension',['pes','pec','jef','dst','exp','vp3','u01','tbf','xxx'])
@pytest.mark.parametrize('layout',['curved','path','monogram'])
def test_curved_font_exports_preserve_sewn_geometry(font_dir,tmp_path,extension,layout):
    from morale.formats import export_machine
    from morale.export_verify import verify_export
    height=embroidery_fonts.reference_height(embroidery_fonts.load_font('demo'))
    obj=make_font_lettering('ABC','demo',height,layout=layout,curve=90,baseline=[[-80,0],[0,-20],[80,0]] if layout=='path' else None)
    project=Project(objects=[obj]);blocks=generate(project)
    destination=tmp_path/f'curved.{extension}'
    export_machine(project,destination,blocks)
    result=verify_export(blocks,destination)
    assert result['complete_path_comparison']
    assert result['bounds_delta_mm']<=.3
    # Format-specific trim behavior remains visible; no geometry discrepancy
    # or missing needle penetrations may be hidden by that control warning.
    assert all(problem.startswith('Trim commands increased:') for problem in result['problems']),result


@pytest.mark.parametrize('font_id',['small_font','emilio_20','neon'])
def test_bundled_curved_font_edit_retains_layout_and_geometry(font_id):
    from morale.lettering import LetteringDialog
    height=math.ceil(height_range(embroidery_fonts.load_font(font_id))[0])
    obj=make_font_lettering('ABC',font_id,height,layout='curved',curve=-90)
    before=Project(objects=[obj]).dumps()
    dialog=LetteringDialog(obj=obj)
    try:
        assert dialog.source.currentData()=='embroidery'
        assert dialog.layout_choice.currentData()=='curved'
        assert dialog.curve.value()==-90 and dialog.height.value()==height
        assert dialog.form.isRowVisible(dialog.layout_choice) and dialog.form.isRowVisible(dialog.curve)
        dialog.accept()
        assert dialog.candidate.lettering==obj.lettering
        assert dialog.candidate.contours==obj.contours
        assert generate(Project(objects=[dialog.candidate]))==generate(Project(objects=[obj]))
        assert Project(objects=[obj]).dumps()==before
    finally:dialog.close()


def test_curved_font_edit_preserves_placement_thread_and_editor_history(font_dir):
    from morale.app import MainWindow
    from morale.lettering import LetteringDialog
    height=round(embroidery_fonts.reference_height(embroidery_fonts.load_font('demo')),2)
    obj=make_font_lettering('ABC','demo',height,layout='curved',curve=60)
    obj.x=12;obj.y=-8;obj.rotation=25;obj.color='#123456'
    obj.thread={'description':'Test cotton','catalog_number':'42'}
    window=MainWindow();dialog=None
    try:
        window.apply_lettering(obj)
        before=window.project.dumps()
        dialog=LetteringDialog(obj=obj)
        dialog.text.setText('CAB');dialog.curve.setValue(-90);dialog.accept()
        edited=dialog.candidate
        assert edited.id==obj.id
        assert (edited.x,edited.y,edited.rotation,edited.color,edited.thread)==(obj.x,obj.y,obj.rotation,obj.color,obj.thread)
        window.apply_lettering(edited,replace=True)
        after=window.project.dumps()
        assert after!=before and len(window.project.objects)==len(Project.loads(before).objects)
        assert window.project.objects[-1].lettering['text']=='CAB'
        assert window.project.objects[-1].lettering['curve']==-90
        window.undo();assert window.project.dumps()==before
        window.redo();assert window.project.dumps()==after
        assert Project.loads(after).objects[-1].lettering==edited.lettering
    finally:
        if dialog:dialog.close()
        window.saved=window.project.dumps();window.close()


def test_missing_embroidery_font_requires_explicit_replacement(font_dir,monkeypatch):
    from morale.lettering import LetteringDialog
    from PySide6.QtWidgets import QLabel,QMessageBox
    height=round(embroidery_fonts.reference_height(embroidery_fonts.load_font('demo')),2)
    obj=make_font_lettering('ABC','demo',height,layout='curved',curve=90)
    obj.lettering['embroidery_font']='uninstalled_font'
    before=Project(objects=[obj]).dumps();stitches=generate(Project(objects=[obj]))
    warnings=[];monkeypatch.setattr(QMessageBox,'warning',lambda *args:warnings.append(args[-1]))
    dialog=LetteringDialog(obj=obj)
    try:
        assert dialog.embroidery_font.currentIndex()==-1
        assert any('saved embroidery font' in label.text() and 'unavailable' in label.text() for label in dialog.findChildren(QLabel))
        dialog.accept()
        assert dialog.candidate is None and warnings
        assert Project(objects=[obj]).dumps()==before
        assert generate(Project.loads(before))==stitches
        dialog.embroidery_font.setCurrentIndex(0);dialog.accept()
        assert dialog.candidate.lettering['embroidery_font']=='demo'
        assert dialog.candidate.lettering['layout']=='curved'
        assert Project(objects=[obj]).dumps()==before
    finally:dialog.close()


def test_empty_font_library_does_not_silently_convert_saved_embroidery(font_dir,monkeypatch):
    from morale.lettering import LetteringDialog
    from PySide6.QtWidgets import QMessageBox
    height=round(embroidery_fonts.reference_height(embroidery_fonts.load_font('demo')),2)
    obj=make_font_lettering('ABC','demo',height,layout='curved',curve=45)
    before=Project(objects=[obj]).dumps()
    original_available=embroidery_fonts.available_fonts
    monkeypatch.setattr(embroidery_fonts,'available_fonts',lambda:())
    warnings=[];monkeypatch.setattr(QMessageBox,'warning',lambda *args:warnings.append(args[-1]))
    dialog=LetteringDialog(obj=obj)
    try:
        assert dialog.source.currentData()=='embroidery'
        assert dialog.embroidery_font.count()==0
        dialog.accept()
        assert dialog.candidate is None and warnings
        assert Project(objects=[obj]).dumps()==before
        dialog.source.setCurrentIndex(dialog.source.findData('system'))
        assert dialog.source.currentData()=='system'
        assert dialog.form.isRowVisible(dialog.font)
        dialog.reject()
        assert Project(objects=[obj]).dumps()==before
    finally:
        dialog.close()
        monkeypatch.setattr(embroidery_fonts,'available_fonts',original_available)


@pytest.mark.parametrize('initial,expected',[(1,10.22),(100,10.49)])
def test_font_switch_clamps_to_supported_fractional_height(font_dir,monkeypatch,initial,expected):
    from morale.lettering import LetteringDialog
    monkeypatch.setattr(embroidery_fonts,'height_range',lambda font,layout='straight':(10.211,10.499))
    embroidery_fonts.available_fonts.cache_clear()
    dialog=LetteringDialog()
    try:
        dialog.height.setValue(initial);dialog.update_source()
        assert dialog.height.value()==expected
        dialog.text.setText('ABC');dialog.accept()
        assert dialog.candidate.lettering['height']==expected
    finally:dialog.close()


def test_oversized_bundled_glyph_identifies_font_and_character(monkeypatch):
    from copy import deepcopy
    font=deepcopy(embroidery_fonts.load_font('califragilistic'))
    font['glyphs']['y']['pieces']=[{'run':[[0,0],[1,1]]}]*2001
    monkeypatch.setattr(embroidery_fonts,'load_font',lambda _:font)
    height=math.ceil(height_range(font)[0]*100)/100
    with pytest.raises(ValueError,match="character 'y' exceeds the 2,000-piece"):
        make_font_lettering('yA',font['id'],height,layout='curved')


@pytest.mark.parametrize('container',['defs','clipPath','mask','symbol','metadata'])
def test_converter_ignores_glyph_labels_inside_svg_definitions(tmp_path,container):
    hidden=f'<{container}>'+satin_layer('A',dx=900)+f'</{container}>'
    layers=''.join(satin_layer(c) for c in 'ABCDEFGHIJKL')
    source=write_source(tmp_path,'definitions',svg_font(hidden+layers))
    result,_=converter.convert(source,tmp_path/'out')
    clean=write_source(tmp_path,'clean',svg_font(layers))
    expected,_=converter.convert(clean,tmp_path/'clean-out')
    assert result['glyphs']==expected['glyphs']


@pytest.mark.parametrize('layout',['straight','curved'])
def test_repaired_califragilistic_y_generates_and_roundtrips(layout):
    font=embroidery_fonts.load_font('califragilistic')
    assert len(font['glyphs']['y']['pieces'])==4
    height=math.ceil(height_range(font)[0]*100)/100
    obj=make_font_lettering('yAÁ',font['id'],height,layout=layout,curve=60)
    project=Project(objects=[obj]);blocks=generate(project)
    assert any(s.command=='stitch' for b in blocks for s in b.stitches)
    assert generate(Project.loads(project.dumps()))==blocks


def test_definition_geometry_inside_glyph_does_not_become_stitches(tmp_path):
    import xml.etree.ElementTree as ET
    layers=''.join(satin_layer(c) for c in 'ABCDEFGHIJKL')
    source=write_source(tmp_path,'nested',svg_font(layers))
    root=ET.parse(source/'ltr.svg')
    glyph=next(g for g in root.getroot().iter() if g.get(converter.LABEL)=='GlyphLayer-A')
    definitions=ET.SubElement(glyph,'{http://www.w3.org/2000/svg}defs')
    group=ET.SubElement(definitions,'{http://www.w3.org/2000/svg}g')
    ET.SubElement(group,'{http://www.w3.org/2000/svg}path',{'d':'M900 900 L950 950','style':'fill:none;stroke:black'})
    root.write(source/'ltr.svg')
    result,_=converter.convert(source,tmp_path/'out')
    clean=write_source(tmp_path,'clean',svg_font(layers))
    expected,_=converter.convert(clean,tmp_path/'clean-out')
    assert result['glyphs']==expected['glyphs']


def test_unchanged_lettering_edit_preserves_subcontrol_precision(font_dir):
    from morale.lettering import LetteringDialog
    height=embroidery_fonts.reference_height(embroidery_fonts.load_font('demo'))
    obj=make_font_lettering('ABC','demo',height,spacing=103.4567,layout='curved',curve=67.89123)
    obj.width*=1.12345
    before=Project(objects=[obj]).dumps()
    dialog=LetteringDialog(obj=obj)
    try:
        assert dialog.spacing.value()!=obj.lettering['spacing']
        dialog.accept()
        assert dialog.candidate is not obj
        assert Project(objects=[dialog.candidate]).dumps()==before
        assert Project(objects=[obj]).dumps()==before
    finally:dialog.close()


def test_text_edit_preserves_unchanged_numeric_precision(font_dir):
    from morale.lettering import LetteringDialog
    height=embroidery_fonts.reference_height(embroidery_fonts.load_font('demo'))
    obj=make_font_lettering('ABC','demo',height,spacing=103.4567,layout='curved',curve=67.89123)
    dialog=LetteringDialog(obj=obj)
    try:
        dialog.text.setText('CAB');dialog.accept()
        result=dialog.candidate
        assert result.lettering['text']=='CAB'
        for key in ('height','spacing','curve'):assert result.lettering[key]==obj.lettering[key]
        expected=make_font_lettering('CAB','demo',height,spacing=103.4567,previous=obj,layout='curved',curve=67.89123)
        assert Project(objects=[result]).dumps()==Project(objects=[expected]).dumps()
    finally:dialog.close()


def test_embroidery_font_path_edit_keeps_world_baseline(font_dir):
    height=embroidery_fonts.reference_height(embroidery_fonts.load_font('demo'))
    baseline=[[10,20],[80,-10],[150,20]]
    obj=make_font_lettering('ABC','demo',height,layout='path',baseline=baseline)
    for a,b in zip(obj.transform(obj.lettering['baseline']),baseline):assert a==pytest.approx(b)
    obj.rotation=23;obj.flip_x=True;obj.x+=12
    original=obj.transform(obj.lettering['baseline'])
    edited=make_font_lettering('CAB','demo',height,previous=obj,layout='path')
    for a,b in zip(original,edited.transform(edited.lettering['baseline'])):assert a==pytest.approx(b)
    assert edited.lettering['embroidery_font']=='demo'
    project=Project(objects=[edited]);assert generate(project)==generate(Project.loads(project.dumps()))


def test_embroidery_font_path_rejects_short_baseline(font_dir):
    height=embroidery_fonts.reference_height(embroidery_fonts.load_font('demo'))
    with pytest.raises(ValueError,match='longer than the baseline'):
        make_font_lettering('ABC','demo',height,layout='path',baseline=[[0,0],[1,0]])


def test_native_path_lettering_can_choose_embroidery_font(font_dir):
    from morale.lettering import LetteringDialog
    dialog=LetteringDialog(baseline=[[0,0],[150,0]])
    try:
        dialog.source.setCurrentIndex(dialog.source.findData('embroidery'))
        assert dialog.layout_choice.currentData()=='path'
        dialog.text.setText('ABC');dialog.accept()
        assert dialog.candidate.lettering['embroidery_font']=='demo'
        assert dialog.candidate.lettering['layout']=='path'
    finally:dialog.close()


def test_explicit_replacement_baseline_is_not_an_unchanged_edit(font_dir):
    from morale.lettering import LetteringDialog
    height=round(embroidery_fonts.reference_height(embroidery_fonts.load_font('demo')),2)
    obj=make_font_lettering('ABC','demo',height,layout='path',baseline=[[-80,0],[80,0]])
    obj.rotation=20;obj.flip_y=True
    before=Project(objects=[obj]).dumps()
    baseline=[[-80,30],[0,0],[80,30]]
    dialog=LetteringDialog(obj=obj,baseline=baseline)
    try:
        dialog.accept()
        result=dialog.candidate
        assert result is not None and result.lettering['layout']=='path'
        assert result.lettering['baseline']!=obj.lettering['baseline']
        for a,b in zip(result.transform(result.lettering['baseline']),baseline):assert a==pytest.approx(b)
        assert Project(objects=[obj]).dumps()==before
    finally:dialog.close()


@pytest.mark.parametrize('layout',['straight','curved'])
def test_leaving_embroidery_path_layout_removes_saved_baseline(font_dir,layout):
    from morale.lettering import LetteringDialog
    height=round(embroidery_fonts.reference_height(embroidery_fonts.load_font('demo')),2)
    obj=make_font_lettering('ABC','demo',height,layout='path',baseline=[[-80,0],[80,0]])
    dialog=LetteringDialog(obj=obj)
    try:
        dialog.layout_choice.setCurrentIndex(dialog.layout_choice.findData(layout));dialog.accept()
        result=dialog.candidate
        assert result.lettering['layout']==layout and 'baseline' not in result.lettering
        Project.loads(Project(objects=[result]).dumps())
        reopened=LetteringDialog(obj=result)
        try:assert reopened.layout_choice.findData('path')==-1
        finally:reopened.close()
    finally:dialog.close()


@pytest.mark.parametrize('layout',['straight','curved','path'])
def test_case_substitution_uses_resolved_glyph_kerning(font_dir,layout):
    height=embroidery_fonts.reference_height(embroidery_fonts.load_font('demo'))
    options={'layout':layout,'curve':90}
    if layout=='path':options['baseline']=[[-80,0],[0,-20],[80,0]]
    upper=make_font_lettering('ABC','demo',height,**options)
    lower=make_font_lettering('abc','demo',height,**options)
    assert lower.lettering['text']=='abc'
    assert lower.lettering['columns']==upper.lettering['columns']
    assert lower.contours==upper.contours
    assert (lower.x,lower.y,lower.width,lower.height)==(upper.x,upper.y,upper.width,upper.height)
    assert [b.stitches for b in generate(Project(objects=[lower]))]==[b.stitches for b in generate(Project(objects=[upper]))]


@pytest.mark.parametrize('font_id',['initials_XL','ondulamarif_XL'])
def test_xl_font_is_selectable_and_preserves_designed_size(font_id):
    from morale.lettering import LetteringDialog
    font=embroidery_fonts.load_font(font_id)
    height=math.ceil(height_range(font)[0]*100)/100
    assert height>100 and font_id in {f[0] for f in embroidery_fonts.available_fonts()}
    obj=make_font_lettering('A',font_id,height)
    project=Project(objects=[obj])
    assert generate(project)==generate(Project.loads(project.dumps()))
    dialog=LetteringDialog(obj=obj)
    try:
        assert dialog.height.value()==height and dialog.height.maximum()==500
        dialog.accept();assert dialog.candidate==obj
        dialog.source.setCurrentIndex(dialog.source.findData('system'))
        assert dialog.height.maximum()==100
    finally:dialog.close()


@pytest.mark.parametrize('extension',['pes','pec','jef','dst','exp','vp3','u01','tbf','xxx'])
def test_xl_lettering_exports_with_large_field_and_rejects_small_hoop(tmp_path,extension):
    from morale.formats import export_machine
    from morale.export_verify import verify_export
    font=embroidery_fonts.load_font('initials_XL')
    height=math.ceil(height_range(font)[0]*100)/100
    obj=make_font_lettering('A','initials_XL',height)
    project=Project(objects=[obj]);blocks=generate(project)
    destination=tmp_path/f'xl.{extension}'
    with pytest.raises(ValueError,match='extends beyond'):
        export_machine(project,destination,blocks)
    assert not destination.exists()
    project.hoop_width=300;project.hoop_height=300
    export_machine(project,destination,blocks)
    result=verify_export(blocks,destination)
    assert result['complete_path_comparison']
    assert result['bounds_delta_mm']<=.3
    assert all(problem.startswith('Trim commands increased:') for problem in result['problems']),result


def test_xl_to_computer_font_conversion_uses_visible_size_and_preserves_source():
    from morale.lettering import LetteringDialog
    font=embroidery_fonts.load_font('initials_XL')
    height=math.ceil(height_range(font)[0]*100)/100
    obj=make_font_lettering('A','initials_XL',height)
    before=Project(objects=[obj]).dumps()
    dialog=LetteringDialog(obj=obj)
    try:
        dialog.source.setCurrentIndex(dialog.source.findData('system'))
        dialog.stitches.setCurrentIndex(dialog.stitches.findData('fill'))
        assert dialog.height.value()==100
        dialog.accept()
        result=dialog.candidate
        assert result is not None and result.lettering['height']==100
        assert 'embroidery_font' not in result.lettering and 'columns' not in result.lettering
        assert result.stitch_type=='fill' and result.id==obj.id
        assert Project(objects=[obj]).dumps()==before
        project=Project(objects=[result])
        assert generate(project)==generate(Project.loads(project.dumps()))
    finally:dialog.close()


def test_native_font_character_coverage_updates_before_apply(font_dir):
    from morale.lettering import LetteringDialog
    dialog=LetteringDialog()
    try:
        dialog.text.setText('ABC')
        assert dialog.glyph_hint.text()=='All characters available in this font.'
        dialog.text.setText('abc')
        assert 'a → A' in dialog.glyph_hint.text()
        dialog.text.setText('AZZ')
        assert dialog.glyph_hint.text().startswith('Missing characters: Z.')
        assert dialog.candidate is None
        dialog.text.clear();assert dialog.glyph_hint.text().startswith('Enter text')
        dialog.source.setCurrentIndex(dialog.source.findData('system'))
        assert not dialog.form.isRowVisible(dialog.glyph_hint)
    finally:dialog.close()


def test_designed_monogram_proportions_spacing_and_portability(font_dir):
    font=embroidery_fonts.load_font('demo')
    height=embroidery_fonts.reference_height(font)
    obj=make_font_lettering('AAA','demo',height,layout='monogram')
    groups=[]
    count=len(font['glyphs']['A']['pieces'])
    for start in range(0,len(obj.lettering['columns']),count):
        points=[p for piece in obj.lettering['columns'][start:start+count] for kind,value in piece.items()
                for ring in (value if kind=='fill' else [value]) for p in obj.transform(ring)]
        groups.append((min(x for x,y in points),max(x for x,y in points),min(y for x,y in points),max(y for x,y in points)))
    assert (groups[1][3]-groups[1][2])/(groups[0][3]-groups[0][2])==pytest.approx(1.4)
    assert (groups[2][3]-groups[2][2])==pytest.approx(groups[0][3]-groups[0][2])
    assert all((a[2]+a[3])/2==pytest.approx(0) for a in groups)
    assert groups[0][1]<groups[1][0]<groups[1][1]<groups[2][0]
    assert make_font_lettering('AAA','demo',height,spacing=200,layout='monogram').width>obj.width
    project=Project(objects=[obj])
    assert generate(Project.loads(project.dumps()))==generate(project)
    from morale.lettering import LetteringDialog
    dialog=LetteringDialog(obj=obj)
    try:
        assert dialog.layout_choice.currentData()=='monogram'
        assert 'middle letter' in dialog.size_hint.text()
        dialog.accept();assert dialog.candidate==obj
    finally:dialog.close()


@pytest.mark.parametrize('text',['A','AB','ABCD','A B','A1B'])
def test_designed_monogram_requires_three_letters(font_dir,text):
    with pytest.raises(ValueError,match='three letters'):
        make_font_lettering(text,'demo',20,layout='monogram')


def test_designed_monogram_checks_outer_letter_minimum(font_dir):
    font=embroidery_fonts.load_font('demo');low,high=height_range(font)
    with pytest.raises(ValueError,match='designed height range'):
        make_font_lettering('ABC','demo',low,layout='monogram')
    make_font_lettering('ABC','demo',low*1.4,layout='monogram')
    assert height_range(font,'monogram')==pytest.approx((low*1.4,high))


def test_native_designed_monogram_creation_clamps_outer_size(font_dir):
    from morale.lettering import LetteringDialog
    dialog=LetteringDialog()
    try:
        dialog.source.setCurrentIndex(dialog.source.findData('embroidery'))
        dialog.embroidery_font.setCurrentIndex(dialog.embroidery_font.findData('demo'))
        dialog.text.setText('ABC')
        dialog.height.setValue(height_range(embroidery_fonts.load_font('demo'))[0])
        dialog.layout_choice.setCurrentIndex(dialog.layout_choice.findData('monogram'))
        assert dialog.height.value()>=height_range(embroidery_fonts.load_font('demo'),'monogram')[0]
        dialog.accept()
        assert dialog.candidate.lettering['layout']=='monogram'
    finally:dialog.close()


def test_fixed_size_font_refuses_monogram(font_dir,monkeypatch):
    from copy import deepcopy
    font=deepcopy(embroidery_fonts.load_font('demo'))
    font['min_scale']=font['max_scale']=1
    with monkeypatch.context() as patch:
        patch.setattr(embroidery_fonts,'load_font',lambda ident:font)
        with pytest.raises(ValueError,match='cannot accommodate'):
            make_font_lettering('ABC','demo',embroidery_fonts.reference_height(font),layout='monogram')


@pytest.mark.parametrize('font_id',['emilio_20_tricolore','paquerette'])
def test_bundled_narrow_range_fonts_explain_unavailable_monograms(font_id):
    font=embroidery_fonts.load_font(font_id)
    low,high=height_range(font,'monogram')
    assert low>high
    with pytest.raises(ValueError,match='cannot accommodate'):
        make_font_lettering('ABC',font_id,high,layout='monogram')
    from morale.lettering import LetteringDialog
    dialog=LetteringDialog()
    try:
        dialog.source.setCurrentIndex(dialog.source.findData('embroidery'))
        dialog.embroidery_font.setCurrentIndex(dialog.embroidery_font.findData(font_id))
        dialog.layout_choice.setCurrentIndex(dialog.layout_choice.findData('monogram'))
        assert 'cannot accommodate' in dialog.size_hint.text()
        dialog.layout_choice.setCurrentIndex(dialog.layout_choice.findData('straight'))
        assert 'cannot accommodate' not in dialog.size_hint.text()
        assert height_range(font)[0]<=dialog.height.value()<=height_range(font)[1]
    finally:dialog.close()


def test_converter_preserves_printable_non_latin_glyphs(tmp_path):
    characters='ΑΒΓΔΕΖΗΘΙΚΛΜЖЯ中∞'
    folder=write_source(tmp_path,'unicode',svg_font(''.join(satin_layer(c) for c in characters)),
                        kerning_pairs={'Α Β':2})
    font,message=converter.convert(folder,tmp_path/'out')
    assert set(font['glyphs'])==set(characters)
    assert font['kerning']['Α Β']==pytest.approx(2*25.4/96,abs=.001)
    assert all(len(g['pieces'])==3 for g in font['glyphs'].values())


@pytest.mark.parametrize('layout',['straight','curved','path','monogram'])
def test_bundled_greek_letters_generate_and_reopen(layout):
    font=embroidery_fonts.load_font('ellenika')
    assert set('ΑΒΓαβγάέήίόύώ').issubset(font['glyphs'])
    assert 'Α Β' in font['kerning']
    assert font['cap_height_mm']==pytest.approx(converter.glyph_top(font['glyphs']['Η']))
    height=math.ceil(height_range(font,layout)[0]*100)/100
    obj=make_font_lettering('ΑΒΓ','ellenika',height,layout=layout,
                            baseline=[[-100,0],[0,-10],[100,0]] if layout=='path' else None)
    project=Project(objects=[obj]);blocks=generate(project)
    assert any(s.command=='stitch' for b in blocks for s in b.stitches)
    assert generate(Project.loads(project.dumps()))==blocks
    from morale.lettering import LetteringDialog
    dialog=LetteringDialog(obj=obj)
    try:
        assert 'Missing characters' not in dialog.glyph_hint.text()
        dialog.accept();assert dialog.candidate==obj
    finally:dialog.close()


@pytest.mark.parametrize('extension',['pes','pec','jef','dst','exp','vp3','u01','tbf','xxx'])
def test_greek_monogram_machine_exports(tmp_path,extension):
    from morale.formats import export_machine
    from morale.export_verify import verify_export
    font=embroidery_fonts.load_font('ellenika')
    height=math.ceil(height_range(font,'monogram')[0]*100)/100
    obj=make_font_lettering('ΆΒΩ','ellenika',height,layout='monogram')
    project=Project(name='Ελληνικά',objects=[obj]);blocks=generate(project)
    path=tmp_path/f'Ελληνικά.{extension}'
    export_machine(project,path,blocks)
    result=verify_export(blocks,path)
    assert result['complete_path_comparison']
    assert result['bounds_delta_mm']<=.3
    assert all(problem.startswith('Trim commands increased:') for problem in result['problems']),result


@pytest.mark.parametrize('layout',['straight','monogram'])
def test_decomposed_greek_accents_resolve_to_same_stitches(layout):
    import unicodedata
    from morale.lettering import LetteringDialog
    text='ΆΒΏ';decomposed=unicodedata.normalize('NFD',text)
    font=embroidery_fonts.load_font('ellenika')
    height=math.ceil(height_range(font,layout)[0]*100)/100
    first=make_font_lettering(text,'ellenika',height,layout=layout)
    second=make_font_lettering(decomposed,'ellenika',height,layout=layout)
    assert first.lettering==second.lettering
    second.id=first.id
    assert generate(Project(objects=[first]))==generate(Project(objects=[second]))
    dialog=LetteringDialog(obj=first)
    try:
        dialog.text.setText(decomposed)
        assert 'Missing characters' not in dialog.glyph_hint.text()
        dialog.accept()
        assert dialog.candidate.lettering==first.lettering
    finally:dialog.close()
