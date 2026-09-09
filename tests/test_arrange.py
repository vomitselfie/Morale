import pytest

from morale.arrange import mirror, bounds, align_to_hoop
from morale.model import DesignObject, Project
from morale.engine import generate
from morale.stitch_edit import manual_object


@pytest.mark.parametrize("axis", ["horizontal", "vertical"])
@pytest.mark.parametrize("rotation", [0, 37, -125])
def test_mirroring_is_in_world_coordinates_and_reversible(axis, rotation):
    obj = DesignObject(kind="path", stitch_type="running", x=12, y=8, rotation=rotation,
                       points=[[-.5, -.5], [.3, -.1], [.5, .5]])
    original = obj.outline()
    flipped = mirror(obj, axis)
    expected = [(2 * obj.x - x, y) if axis == "horizontal" else (x, 2 * obj.y - y) for x, y in original]
    for actual, target in zip(flipped.outline(), expected):
        assert actual == pytest.approx(target)
    assert mirror(flipped, axis) == obj
    assert flipped.angle == -obj.angle
    restored = Project.loads(Project(objects=[flipped]).dumps()).objects[0]
    assert restored == flipped


def test_imported_stitches_keep_commands_when_mirrored():
    obj = DesignObject(kind="stitches", stitch_type="manual", rotation=31,
                       stitch_data=[[-.5, -.5, "jump"], [.2, 0, "stitch"], [.2, 0, "trim"], [.5, .5, "stitch"]])
    original = generate(Project(objects=[obj]))[0].stitches
    flipped = generate(Project(objects=[mirror(obj, "horizontal")]))[0].stitches
    for a, b in zip(original, flipped):
        assert a.command == b.command
        assert (b.x, b.y) == pytest.approx((-a.x, a.y))


@pytest.mark.parametrize("alignment,index,target", [("left", 0, -50), ("right", 2, 50), ("top", 1, -65), ("bottom", 3, 65)])
def test_alignment_uses_rotated_geometry(alignment, index, target):
    obj = DesignObject(x=17, y=23, rotation=37)
    result = align_to_hoop(obj, 100, 130, alignment)
    assert bounds(result)[index] == pytest.approx(target)
    assert result.width == obj.width and result.height == obj.height
    assert result.rotation == obj.rotation


def test_centering_and_empty_stitch_object():
    obj = DesignObject(x=17, y=23, rotation=37)
    left, top, right, bottom = bounds(align_to_hoop(obj, 100, 130, "center"))
    assert left + right == pytest.approx(0)
    assert top + bottom == pytest.approx(0)
    with pytest.raises(ValueError):
        bounds(DesignObject(kind="stitches", stitch_type="manual"))


def test_manual_rebasing_does_not_apply_mirror_twice():
    obj = mirror(DesignObject(), "vertical")
    rows = [[0, 0, "jump"], [10, 5, "stitch"]]
    edited = manual_object(obj, rows)
    assert not edited.flip_x and not edited.flip_y
    stitches = generate(Project(objects=[edited]))[0].stitches
    assert (stitches[-1].x, stitches[-1].y) == pytest.approx((10, 5))
