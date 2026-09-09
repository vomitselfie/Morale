import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import io
import csv

import pytest
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication

from morale.applique import applique_stages
from morale.model import DesignObject, Project
from morale.engine import generate
from morale.canvas import Canvas
from morale.formats import export_machine, import_machine
from morale.threads import write_chart


@pytest.fixture(scope="module", autouse=True)
def app():
    return QApplication.instance() or QApplication([])


def test_applique_sequence_contains_two_operator_stops():
    stages = applique_stages(DesignObject(kind="rectangle", width=20, height=30), 2)
    assert [o.stitch_type for o in stages] == ["running", "running", "fill"]
    assert [o.stop_after for o in stages] == [True, True, False]
    blocks = generate(Project(objects=stages))
    assert sum(s.command == "stop" for b in blocks for s in b.stitches) == 2
    assert all(b.stitches[-1].command == "stop" for b in blocks[:2])
    assert blocks[-1].stitches[-1].command == "trim"
    assert all(o.stage_note for o in stages)


def test_cover_is_a_band_not_a_solid_shape():
    stages = applique_stages(DesignObject(kind="rectangle", width=20, height=30), 2)
    cover = stages[-1]
    assert cover.width == pytest.approx(22, abs=.01)
    assert cover.height == pytest.approx(32, abs=.01)
    path = Canvas.outline_path(cover)
    assert not path.contains(QPointF(0, 0))
    assert path.contains(QPointF(10, 0))
    assert all(not (abs(s.x) < 8 and abs(s.y) < 13) for s in generate(Project(objects=[cover]))[0].stitches if s.command == "stitch")


def test_hidden_shape_stays_hidden_and_thread_metadata_survives():
    source = DesignObject(visible=False, color_break=True, thread={"catalog_number": "0012"})
    stages = applique_stages(source)
    assert not any(obj.visible for obj in stages)
    assert stages[0].color_break
    assert all(obj.thread == source.thread for obj in stages)
    assert generate(Project(objects=stages)) == []


@pytest.mark.parametrize("kind", ["path", "stitches", "satin"])
def test_unsuitable_source_rejected(kind):
    with pytest.raises(ValueError, match="closed"):
        applique_stages(DesignObject(kind=kind))


@pytest.mark.parametrize("extension", ["dst", "exp", "jef", "pec", "pes", "tbf", "u01", "vp3", "xxx"])
def test_applique_pauses_survive_all_machine_exports(tmp_path, extension):
    project = Project(objects=applique_stages(DesignObject(width=20, height=30)))
    path = tmp_path / f"applique.{extension}"
    export_machine(project, path)
    blocks = generate(import_machine(path).project)
    pauses = len(blocks) - 1 + sum(s.command == "stop" for b in blocks for s in b.stitches)
    assert pauses == 2
    assert any(s.command == "stitch" for b in blocks for s in b.stitches)


def test_project_and_csv_keep_stage_instructions():
    original = Project(objects=applique_stages(DesignObject()))
    project = Project.loads(original.dumps())
    stream = io.StringIO()
    write_chart(project, generate(project), stream)
    rows = list(csv.DictReader(io.StringIO(stream.getvalue())))
    assert "place" in rows[0]["Instruction"]
    assert "trim" in rows[1]["Instruction"]
    assert "cover" in rows[2]["Instruction"]


def test_dst_header_counts_applique_pause_events(tmp_path):
    project = Project(objects=applique_stages(DesignObject()))
    path = tmp_path / "pauses.dst"
    export_machine(project, path)
    header = path.read_bytes()[:512].decode("ascii")
    field = next(part for part in header.split("\r") if part.startswith("CO:"))
    assert int(field[3:]) == 2
