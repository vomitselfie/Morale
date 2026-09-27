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
    with pytest.raises(ValueError, match='digitized for letters'):
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
        assert 'Sews best from' in dialog.size_hint.text()
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
