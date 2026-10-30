import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from morale.engine import generate
from morale.model import Project
from morale.svg_import import import_svg_text
from morale.svg_settings import decode, parse, point_along


@pytest.fixture(scope="module", autouse=True)
def app():
    return QApplication.instance() or QApplication([])


def document(body):
    return ('<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" '
            f'width="100mm" height="100mm" viewBox="0 0 100 100">{body}</svg>')


def objects(body):
    result = import_svg_text(document(body))
    return {obj.name: obj for obj in result.objects}, result.notices


def test_illustrator_escapes_and_token_parsing():
    assert decode("logo_fill_a_x3D_45_s_x3D_0.35") == "logo_fill_a=45_s=0.35"
    base, stroke, words, notices = parse("Layer 1 logo fill a=45 s=0.35 stroke.satin stroke.w=2 t=E8A33C trim")
    assert base == {"type": "fill", "angle": 45, "spacing": .35, "color": "#e8a33c", "trim": True}
    assert stroke == {"type": "satin", "width": 2}
    assert words == ["Layer", "1", "logo"] and notices == []
    _, _, _, notices = parse("s=9 o=2 a=north")
    assert len(notices) == 3 and "0.2 to 5" in notices[0] and "does not use" in notices[1]


def test_group_settings_apply_inside_and_inner_names_override():
    found, _ = objects('<g id="Badge_fill_a_x3D_30_s_x3D_0.5">'
                       '<rect id="Background" x="10" y="10" width="40" height="30" fill="#ff0000"/>'
                       '<rect id="Second_a_x3D_90" x="55" y="10" width="20" height="30" fill="#00ff00"/></g>')
    assert (found["Background"].angle, found["Background"].spacing) == (30, .5)
    assert (found["Second"].angle, found["Second"].spacing) == (90, .5)


def test_inkscape_labels_make_satin_outlines_and_skip_shapes():
    found, notices = objects('<g inkscape:label="Lines stroke.satin w=2">'
                             '<path id="Wave" d="M10 60 L40 70 L70 60" stroke="#0000ff" stroke-width="1" fill="none"/>'
                             '<circle id="Ring" cx="80" cy="75" r="10" stroke="#000" stroke-width="3" fill="none"/></g>'
                             '<rect id="Hidden skip" x="5" y="80" width="5" height="5" fill="#000"/>'
                             '<rect id="Kept" x="5" y="90" width="5" height="5" fill="#000"/>')
    assert found["Wave · outline"].stitch_type == "satin" and found["Ring · outline"].stitch_type == "satin"
    assert found["Ring · outline"].width == pytest.approx(22)  # 20 mm ring plus a 2 mm column
    assert "Hidden" not in found and "Kept" in found
    assert not any("running centerlines" in notice for notice in notices)


def test_filled_bars_named_satin_become_columns_or_explain():
    found, notices = objects('<rect id="Bar satin pc=0.2" x="10" y="85" width="40" height="4" fill="#333"/>'
                             '<rect id="Block satin" x="10" y="10" width="40" height="40" fill="#333"/>')
    assert found["Bar"].stitch_type == "satin" and found["Bar"].pull_compensation == .2
    assert found["Block"].stitch_type == "fill"
    assert any(notice.startswith("Block: kept as fill") for notice in notices)


def test_running_triple_underlay_finishing_and_fill_points():
    found, notices = objects('<rect id="Edge run r=3 stop" x="10" y="10" width="20" height="20" fill="#333"/>'
                             '<rect id="Under fill ul=edge+sparse st=0 en=0.5" x="40" y="10" width="20" height="20" fill="#333"/>'
                             '<rect id="Wrong ul=zigzag" x="70" y="10" width="20" height="20" fill="#333"/>')
    assert found["Edge"].stitch_type == "triple" and found["Edge"].stop_after
    under = found["Under"]
    assert under.underlay and under.underlay_style == "edge_sparse"
    assert under.fill_start == point_along(under.contours[0], 0) and under.fill_end == point_along(under.contours[0], .5)
    assert not found["Wrong"].underlay and any("suits satin columns" in notice for notice in notices)
    generate(Project(objects=list(found.values())))


def test_clipped_shapes_keep_their_names_settings():
    found, _ = objects('<clipPath id="c"><rect x="0" y="0" width="30" height="30"/></clipPath>'
                       '<g id="Clipped_a_x3D_10"><rect id="Inner s=0.6" x="10" y="10" width="40" height="40" fill="#f00" clip-path="url(#c)"/></g>')
    assert (found["Inner"].angle, found["Inner"].spacing) == (10, .6)


def test_names_without_settings_import_as_before():
    found, notices = objects('<rect id="Plain shape" x="10" y="10" width="20" height="20" fill="#333"/>')
    plain = found["Plain shape"]
    assert (plain.stitch_type, plain.angle, plain.spacing, plain.underlay) == ("fill", 45, .45, False)
    assert not any("SVG name" in notice for notice in notices)
