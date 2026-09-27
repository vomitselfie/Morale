import json
import pytest
from PySide6.QtWidgets import QApplication
from morale import coupons
from morale.embroidery_fonts import available_fonts
from morale.engine import generate
from morale.formats import import_machine


@pytest.fixture(scope='module', autouse=True)
def app():
    return QApplication.instance() or QApplication([])


def names():
    # The lettering coupon needs the bundled embroidery fonts.
    return [n for n in coupons.COUPONS if n != 'lettering' or available_fonts()]


@pytest.mark.parametrize('name', names())
def test_coupon_fits_the_field_and_keeps_clear_of_the_scale_square(name):
    project, tests, title, guidance = coupons.build_project(name)
    assert title and guidance and tests
    x0, y0 = coupons.SCALE_CORNER
    for block in generate(project):
        obj = next(o for o in project.objects if o.id == block.object_id)
        for s in block.stitches:
            if s.command != 'stitch':
                continue
            assert -50 <= s.x <= 50 and -50 <= s.y <= 50, (name, obj.name)
            if not obj.name.startswith('Scale'):
                inside = x0 - .5 <= s.x <= x0 + 10.5 and y0 - .5 <= s.y <= y0 + 10.5
                assert not inside, (name, obj.name)
    assert len({o.color for o in project.objects}) == 1


def test_coupon_folder_has_machine_files_templates_and_every_test_object(tmp_path):
    report = coupons.build_coupon('satin-width', tmp_path / 'satin-width')
    root = tmp_path / 'satin-width'
    for name in ('satin-width.pes', 'satin-width-v1.pes', 'satin-width.exp', 'satin-width.dst', 'satin-width.morale',
                 'placement.pdf', 'thread-chart.csv', 'metadata.json', 'evaluation.json', 'README.txt'):
        assert (root / name).stat().st_size > 0, name
    evaluation = json.loads((root / 'evaluation.json').read_text())
    widths = sorted({o['target']['width_mm'] for o in evaluation['objects']})
    assert widths == sorted(set(coupons.SATIN_WIDTHS)) and all(o['status'] is None for o in evaluation['objects'])
    metadata = json.loads((root / 'metadata.json').read_text())
    assert metadata['design'] == 'satin-width.morale' and {'machine', 'fabric', 'stabilizer', 'upper_thread'} <= set(metadata)
    decoded = [s for b in generate(import_machine(root / 'satin-width.pes').project) for s in b.stitches if s.command == 'stitch']
    assert len(decoded) >= report['stitches']
    with pytest.raises(FileExistsError):
        coupons.build_coupon('satin-width', root)


def test_stitch_length_coupon_uses_exact_spans():
    project, tests, _, _ = coupons.build_project('stitch-length')
    for obj, target in tests:
        stitches = [s for s in generate(__import__('morale.model', fromlist=['Project']).Project(objects=[obj]))[0].stitches if s.command == 'stitch']
        spans = [((b.x - a.x) ** 2 + (b.y - a.y) ** 2) ** .5 for a, b in zip(stitches, stitches[1:])]
        assert spans and all(abs(span - target['stitch_length_mm']) < .01 for span in spans)
