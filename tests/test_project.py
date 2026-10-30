import json

import pytest

from dataclasses import fields

from morale.model import DesignObject, PROJECT_VERSION, SETTING_GROUPS, Project, demo_project, satin_sample
from project_files import flat_document

GROUP_OF = {key: group for group, keys in SETTING_GROUPS.items() for key in keys}


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


INVALID = [("spacing", 0), ("width", float("nan")), ("color", "red"), ("id", []), ("visible", "false"), ("kind", "script"), ("points", [[10, 20]])]


@pytest.mark.parametrize("key,value", INVALID)
def test_invalid_objects_are_rejected(key, value):
    data = json.loads(demo_project().dumps())
    data["objects"][0][GROUP_OF[key]][key] = value
    with pytest.raises(ValueError):
        Project.loads(json.dumps(data))


@pytest.mark.parametrize("key,value", INVALID)
def test_invalid_objects_in_older_files_are_rejected(key, value):
    data = flat_document(demo_project())
    data["objects"][0][key] = value
    with pytest.raises(ValueError):
        Project.loads(json.dumps(data))


def test_unknown_version_and_duplicate_ids():
    data = json.loads(demo_project().dumps())
    data["version"] = 99
    with pytest.raises(ValueError, match="newer Morale"):
        Project.loads(json.dumps(data))
    data["version"] = 3
    data["objects"][1]["identity"]["id"] = data["objects"][0]["identity"]["id"]
    with pytest.raises(ValueError):
        Project.loads(json.dumps(data))


def test_version_one_projects_migrate_to_current_version():
    data = flat_document(demo_project(), version=1)
    for obj in data["objects"]:
        obj.pop("stitch_data")
        obj.pop("color_break")
    loaded = Project.loads(json.dumps(data))
    assert json.loads(loaded.dumps())["version"] == PROJECT_VERSION == 3
    assert len(loaded.objects) == 10


def test_every_object_property_belongs_to_exactly_one_group():
    grouped = [key for keys in SETTING_GROUPS.values() for key in keys]
    assert sorted(grouped) == sorted(f.name for f in fields(DesignObject))
    assert len(grouped) == len(set(grouped))


def test_saved_objects_are_grouped_by_purpose():
    data = json.loads(satin_sample().dumps())
    obj = data["objects"][0]
    assert list(obj) == list(SETTING_GROUPS)
    assert obj["satin"] == {"satin_max": 6, "satin_style": "plain"} and obj["finishing"]["tie_in"] is True
    assert obj["stitch"]["stitch_type"] == "satin" and obj["shape"]["kind"] == "satin"


@pytest.mark.parametrize("project", [demo_project(), satin_sample()])
def test_version_two_files_load_identically(project):
    old = Project.loads(json.dumps(flat_document(project)))
    assert old == project and old.dumps() == project.dumps()


def test_missing_groups_and_properties_take_defaults():
    data = json.loads(Project(objects=[DesignObject(spacing=.6)]).dumps())
    obj = data["objects"][0]
    del obj["motif"], obj["ripple"], obj["fill"]["route_fill"]
    loaded = Project.loads(json.dumps(data)).objects[0]
    assert loaded.spacing == .6 and loaded.motif_pattern == "diamond" and loaded.route_fill is False


@pytest.mark.parametrize("change", ["unknown group", "unknown property", "wrong group", "group not object", "object not grouped"])
def test_malformed_grouped_objects_are_rejected(change):
    data = json.loads(demo_project().dumps())
    obj = data["objects"][0]
    if change == "unknown group":
        obj["colour"] = {}
    elif change == "unknown property":
        obj["fill"]["sparkle"] = True
    elif change == "wrong group":
        obj["fill"]["satin_max"] = obj["satin"].pop("satin_max")
    elif change == "group not object":
        obj["fill"] = []
    else:
        data["objects"][0] = {key: value for values in obj.values() for key, value in values.items()}
    with pytest.raises(ValueError, match="Unsupported object properties"):
        Project.loads(json.dumps(data))


def test_bundled_older_example_projects_still_open():
    from pathlib import Path
    examples = sorted(Path(__file__).parent.parent.joinpath("examples").rglob("*.morale"))
    assert examples
    for path in examples:
        assert json.loads(path.read_text())["version"] < PROJECT_VERSION
        project = Project.loads(path.read_text())
        assert Project.loads(project.dumps()) == project
