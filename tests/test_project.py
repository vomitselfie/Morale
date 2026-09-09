import json

import pytest

from morale.model import Project, demo_project


def test_round_trip_and_atomic_save(tmp_path):
    original = demo_project()
    path = tmp_path / "flowers.morale"
    original.save(path)
    loaded = Project.loads(path.read_text())
    assert loaded.dumps() == original.dumps()
    loaded.name = "Changed"
    loaded.save(path)
    assert Project.loads(path.read_text()).name == "Changed"
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize("key,value", [("spacing", 0), ("width", float("nan")), ("color", "red"), ("id", []), ("visible", "false"), ("kind", "script"), ("points", [[10, 20]])])
def test_invalid_objects_are_rejected(key, value):
    data = json.loads(demo_project().dumps())
    data["objects"][0][key] = value
    with pytest.raises(ValueError):
        Project.loads(json.dumps(data))


def test_unknown_version_and_duplicate_ids():
    data = json.loads(demo_project().dumps())
    data["version"] = 99
    with pytest.raises(ValueError):
        Project.loads(json.dumps(data))
    data["version"] = 2
    data["objects"][1]["id"] = data["objects"][0]["id"]
    with pytest.raises(ValueError):
        Project.loads(json.dumps(data))


def test_version_one_projects_migrate_to_version_two():
    data = json.loads(demo_project().dumps())
    data["version"] = 1
    for obj in data["objects"]:
        obj.pop("stitch_data")
        obj.pop("color_break")
    loaded = Project.loads(json.dumps(data))
    assert json.loads(loaded.dumps())["version"] == 2
    assert len(loaded.objects) == 10
