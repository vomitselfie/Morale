import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pyembroidery as emb
import pytest
from PySide6.QtWidgets import QApplication

from morale.catalogs import BUILTIN_CATALOGS, builtin_catalog
from morale.formats import export_machine
from morale.model import demo_project
from morale.thread_palette_files import read_palette


@pytest.fixture(scope="module", autouse=True)
def app():
    return QApplication.instance() or QApplication([])


def color_blocks(path):
    pattern = emb.read(str(path))
    return 1 + sum(1 for s in pattern.stitches if s[2] & emb.COMMAND_MASK == emb.COLOR_CHANGE)


@pytest.mark.parametrize("pause", [False, True])
def test_exp_companion_inf_matches_the_exp_color_blocks(tmp_path, pause):
    project = demo_project()
    project.objects[3].stop_after = pause
    project.objects[3].thread = {"description": "Petal pink", "chart": "Madeira"}
    result = export_machine(project, tmp_path / "flower.exp", companion=True)
    inf = tmp_path / "flower.inf"
    assert result["companion"] == str(inf)
    palette = read_palette(inf)
    assert len(palette) == color_blocks(tmp_path / "flower.exp")
    assert any(entry.metadata.get("description") == "Petal pink" for entry in palette)


def test_companion_only_for_exp_and_only_when_asked(tmp_path):
    project = demo_project()
    assert "companion" not in export_machine(project, tmp_path / "a.exp")
    assert "companion" not in export_machine(project, tmp_path / "a.pes", companion=True)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["a.exp", "a.pes"]


def test_coupon_pack_includes_the_companion_with_a_hash(tmp_path):
    from morale.coupons import build_coupon
    report = build_coupon("tiny-stitches", tmp_path / "pack")
    assert report["companion_files"] == ["tiny-stitches.inf"]
    assert "tiny-stitches.inf" in report["exports_sha256"] and "tiny-stitches.inf" not in report["files"]
    assert (tmp_path / "pack" / "tiny-stitches.inf").exists()


def test_brother_chart_has_catalog_numbers_and_pec_names():
    assert BUILTIN_CATALOGS[0] == "Brother Embroidery threads"
    chart = builtin_catalog("Brother Embroidery threads")
    assert len(chart) == 61 and len({e.metadata["catalog_number"] for e in chart}) == 61
    white = chart[0]
    assert (white.color, white.metadata["catalog_number"], white.metadata["description"]) == ("#f0f0f0", "001", "White")
    assert all(e.metadata["brand"] == "Brother" and e.metadata["catalog_number"].isdigit() for e in chart)
    # Most numbers name a PEC palette color; the rest are labelled by number.
    named = [e for e in chart if not e.metadata["description"].startswith("Brother ")]
    assert len(named) >= 58


def test_artwork_threads_can_match_the_brother_chart():
    from morale.trace_threads import match_trace_threads
    result, matches = match_trace_threads(demo_project(), "Brother Embroidery threads")
    assert all(obj.thread.get("chart") == "Brother Embroidery" for obj in result.objects)
