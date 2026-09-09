import csv
import io

import pyembroidery as emb
import pytest

from morale.engine import Block, Stitch, generate
from morale.formats import from_pattern, to_pattern, export_machine, import_machine
from morale.model import DesignObject, Project
from morale.threads import usage, write_chart


def test_usage_separates_sewing_travel_and_controls():
    blocks = [Block("one", "#123456", [Stitch(3, 4, "jump"), Stitch(6, 8), Stitch(6, 8, "trim"), Stitch(6, 8, "stop")]),
              Block("two", "#654321", [Stitch(9, 12)])]
    result = usage(blocks)
    assert result[0]["sewn_m"] == pytest.approx(.005)
    assert result[0]["travel_m"] == pytest.approx(.005)
    assert result[0]["trims"] == result[0]["stops"] == 1
    assert result[1]["sewn_m"] == pytest.approx(.005)
    assert result[1]["travel_m"] == 0


def test_thread_metadata_import_project_and_pattern_roundtrip():
    pattern = emb.EmbPattern()
    thread = emb.EmbThread()
    thread.set("#123456")
    thread.brand = "Example brand"
    thread.catalog_number = "0012"
    thread.description = "Moss"
    thread.weight = "40"
    pattern.add_thread(thread)
    pattern.add_stitch_absolute(emb.JUMP, 0, 0)
    pattern.add_stitch_absolute(emb.STITCH, 10, 10)
    project = Project.loads(from_pattern(pattern).project.dumps())
    restored = to_pattern(project).threadlist[0]
    for key in ["brand", "catalog_number", "description", "weight"]:
        assert getattr(restored, key) == getattr(thread, key)


def test_same_rgb_different_catalogs_require_thread_change(tmp_path):
    objects = [DesignObject(color="#123456", thread={"catalog_number": "one"}),
               DesignObject(color="#123456", thread={"catalog_number": "two"})]
    pattern = to_pattern(Project(objects=objects))
    assert len(pattern.threadlist) == 2
    assert sum(s[2] & 255 == emb.COLOR_CHANGE for s in pattern.stitches) == 1
    path = tmp_path / "same-color.pes"
    export_machine(Project(objects=objects), path)
    restored = import_machine(path).project
    assert [obj.thread["catalog_number"] for obj in restored.objects] == ["one", "two"]


def test_pes_saves_catalog_information(tmp_path):
    obj = DesignObject(thread={"brand": "Example", "catalog_number": "0012", "description": "Moss"})
    path = tmp_path / "thread.pes"
    export_machine(Project(objects=[obj]), path)
    restored = import_machine(path).project.objects[0]
    for key, value in obj.thread.items():
        assert restored.thread[key] == value


def test_csv_contains_metadata_lengths_and_escapes_formulas():
    obj = DesignObject(name="=object", thread={"brand": " +formula", "catalog_number": "0012"})
    project = Project(objects=[obj])
    stream = io.StringIO()
    write_chart(project, generate(project), stream)
    rows = list(csv.DictReader(io.StringIO(stream.getvalue())))
    assert rows[0]["Object"] == "'=object"
    assert rows[0]["brand"] == "' +formula"
    assert rows[0]["catalog_number"] == "0012"
    assert float(rows[0]["Sewn path (m)"]) > 0


@pytest.mark.parametrize("metadata", [{"script": "bad"}, {"brand": 42}, {"description": "x" * 1025}, []])
def test_bad_thread_metadata_rejected(metadata):
    with pytest.raises(ValueError):
        Project.loads(Project(objects=[DesignObject(thread=metadata)]).dumps())
