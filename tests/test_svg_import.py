import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication

from morale.svg_import import import_svg
from morale.canvas import Canvas
from morale.model import Project, DesignObject
from morale.engine import generate
from morale.formats import export_machine, import_machine


@pytest.fixture(scope="module", autouse=True)
def app():
    return QApplication.instance() or QApplication([])


def artwork(tmp_path, body, attributes='width="40mm" height="40mm" viewBox="0 0 40 40"'):
    path = tmp_path / "artwork.svg"
    path.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" {attributes}>{body}</svg>')
    return path


@pytest.mark.parametrize("width,expected", [("25.4mm",25.4), ("2.54cm",25.4), ("1in",25.4), ("96px",25.4), ("72pt",25.4)])
def test_physical_units_and_viewbox(tmp_path, width, expected):
    result = import_svg(artwork(tmp_path, '<rect width="100" height="100"/>', f'width="{width}" height="{width}" viewBox="0 0 100 100"'))
    obj = result.objects[0]
    assert obj.width == pytest.approx(expected, abs=.0001)
    assert obj.height == pytest.approx(expected, abs=.0001)
    assert obj.x == pytest.approx(0) and obj.y == pytest.approx(0)


@pytest.mark.parametrize("rule,hole", [("evenodd", True), ("nonzero",False)])
def test_svg_fill_rule_preserves_holes_correctly(tmp_path, rule, hole):
    result = import_svg(artwork(tmp_path, f'<path fill-rule="{rule}" d="M0 0 H30 V30 H0 Z M10 10 H20 V20 H10 Z"/>'))
    obj = result.objects[0]
    assert Canvas.outline_path(obj).contains(QPointF(0,0)) != hole
    if hole:
        assert all(not(abs(s.x)<4.9 and abs(s.y)<4.9) for s in generate(Project(objects=[obj]))[0].stitches if s.command == "stitch")


def test_opposite_winding_makes_nonzero_hole(tmp_path):
    result = import_svg(artwork(tmp_path, '<path d="M0 0 H30 V30 H0 Z M10 10 V20 H20 V10 Z"/>'))
    assert not Canvas.outline_path(result.objects[0]).contains(QPointF(0,0))


def test_nested_transform_color_order_and_spacing(tmp_path):
    result = import_svg(artwork(tmp_path, '<g transform="translate(5 10)" fill="red"><rect width="10" height="5"/><g transform="translate(20 0) rotate(90)"><rect width="10" height="5" fill="blue"/></g></g>'))
    a,b = result.objects
    assert (a.color,b.color) == ("#ff0000", "#0000ff")
    assert (a.width,a.height) == pytest.approx((10,5), abs=.0001)
    assert (b.width,b.height) == pytest.approx((5,10), abs=.0001)
    assert b.x-a.x == pytest.approx(12.5, abs=.0001)


def test_defs_use_local_references_and_hidden_shapes(tmp_path):
    result = import_svg(artwork(tmp_path, '<defs><rect id="tile" width="5" height="5"/></defs><use href="#tile"/><use href="#tile" x="10"/><rect visibility="hidden" width="40" height="40"/><rect display="none" width="40" height="40"/>'))
    assert len(result.objects) == 2
    assert result.objects[1].x-result.objects[0].x == pytest.approx(10, abs=.0001)


@pytest.mark.parametrize("d", ["M0 0 C1 2 3 4 5 6", "M0 0 Q5 10 10 0", "M0 0 A10 10 0 0 1 20 0"])
def test_curved_strokes_remain_editable_and_persist(tmp_path, d):
    result = import_svg(artwork(tmp_path, f'<path fill="none" stroke="blue" stroke-width="2" d="{d}"/>'))
    obj = result.objects[0]
    assert obj.kind == "path" and obj.handles and obj.stitch_type == "running"
    assert "centerlines" in result.notices[0]
    assert Project.loads(Project(objects=result.objects).dumps()).objects == result.objects
    assert generate(Project(objects=result.objects))


def test_fill_and_stroke_produce_separate_ordered_objects(tmp_path):
    result = import_svg(artwork(tmp_path, '<rect width="20" height="10" fill="red" stroke="blue"/>'))
    assert [o.stitch_type for o in result.objects] == ["fill","running"]
    assert [o.color for o in result.objects] == ["#ff0000","#0000ff"]


@pytest.mark.parametrize("d", ["M0 0 C0 -10 20 -10 20 0 C20 10 0 10 0 0Z", "M0 0 C30 -30 30 30 0 0Z"])
def test_closed_cubic_loops_with_few_anchors_are_not_discarded(tmp_path, d):
    result = import_svg(artwork(tmp_path, f'<path d="{d}" fill="red" stroke="blue"/>'))
    assert [o.stitch_type for o in result.objects] == ["fill", "running"]
    assert result.objects[0].width > 10
    assert result.objects[1].handles


def test_bad_path_is_rejected_even_when_other_shapes_are_valid(tmp_path):
    with pytest.raises(ValueError):
        import_svg(artwork(tmp_path, '<rect width="10" height="10"/><path d="M0 0 C"/>'))


@pytest.mark.parametrize("body,match", [
    ('<text>Hello</text>', "text"),
    ('<rect width="10" height="10" clip-path="url(#c)"/>', "clip-path"),
    ('<path fill="url(#gradient)" d="M0 0 H10 V10Z"/>', "paint"),
    ('<use href="https://example.com/art.svg#x"/>', "local"),
    ('<defs><g id="loop"><use href="#loop"/></g></defs>', "circular"),
    ('<style>rect {fill:red}</style>', "style"),
    ('<path stroke-dasharray="1 2" d="M0 0L10 10"/>', "stroke-dasharray"),
])
def test_unsupported_or_external_content_rejected(tmp_path, body, match):
    with pytest.raises(ValueError, match=match):
        import_svg(artwork(tmp_path, body))


def test_doctype_and_missing_page_dimensions(tmp_path):
    path = artwork(tmp_path, '<rect width="96" height="96"/>', 'viewBox="0 0 96 96"')
    result = import_svg(path)
    assert result.objects[0].width == pytest.approx(25.4)
    assert result.notices
    path.write_text('<!DOCTYPE svg [<!ENTITY x "x">]><svg/>')
    with pytest.raises(ValueError, match="entity"):
        import_svg(path)


def test_native_import_merge_undo_and_failed_import_preserve_project(tmp_path):
    from morale.app import MainWindow
    window = MainWindow()
    try:
        window.replace_project(Project(objects=[DesignObject()]))
        before = window.project.dumps()
        path = artwork(tmp_path, '<rect width="10" height="10"/>')
        window.apply_svg_artwork(path)
        assert len(window.project.objects) == 2 and len(window.selected_ids) == 1
        window.undo()
        assert window.project.dumps() == before
        path.write_text('<svg><text>unconverted</text></svg>')
        with pytest.raises(ValueError):
            window.apply_svg_artwork(path)
        assert window.project.dumps() == before
    finally:
        window.saved = window.project.dumps()
        window.close()


@pytest.mark.parametrize("extension", ["dst","exp","jef","pec","pes","tbf","u01","vp3","xxx"])
def test_svg_hole_exports_to_all_formats(tmp_path, extension):
    result = import_svg(artwork(tmp_path, '<path fill-rule="evenodd" d="M0 0 H30 V30 H0 Z M10 10 H20 V20 H10 Z"/>'))
    path = tmp_path / f"hole.{extension}"
    export_machine(Project(objects=result.objects), path)
    stitches = [s for b in generate(import_machine(path).project) for s in b.stitches if s.command == "stitch"]
    assert stitches and all(not(abs(s.x)<4.8 and abs(s.y)<4.8) for s in stitches)
