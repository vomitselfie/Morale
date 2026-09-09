import math

import pyembroidery as emb
import pytest

from morale.engine import generate
from morale.formats import export_machine, import_machine, from_pattern, to_pattern, EXPORT_FORMATS
from morale.model import Project, DesignObject, demo_project


@pytest.mark.parametrize("extension", [ext[1:] for ext in sorted(EXPORT_FORMATS)])
def test_export_readback_preserves_geometry_and_color_changes(tmp_path, extension):
    project = demo_project()
    path = tmp_path / f"test.{extension}"
    export_machine(project, path)
    result = emb.read(str(path))
    assert result is not None
    sewn = [s for s in result.stitches if s[2] & emb.COMMAND_MASK == emb.STITCH]
    assert len(sewn) > 1000
    imported = import_machine(path).project
    assert len(imported.objects) == 4
    original = [s for b in generate(project) for s in b.stitches if s.command == "stitch"]
    # Machine coordinates use 0.1 mm. Writers may add tie/zero stitches.
    for axis in [0, 1]:
        values = [s.x if axis == 0 else s.y for s in original]
        assert math.isclose(min(s[axis] for s in sewn) / 10, min(values), abs_tol=.15)
        assert math.isclose(max(s[axis] for s in sewn) / 10, max(values), abs_tol=.15)
    assert result.stitches[-1][2] & emb.COMMAND_MASK == emb.END


def test_failed_preflight_does_not_overwrite_existing_file(tmp_path):
    path = tmp_path / "keep.dst"
    path.write_bytes(b"previous file")
    with pytest.raises(ValueError, match="beyond"):
        export_machine(Project(objects=[DesignObject(x=100)]), path)
    assert path.read_bytes() == b"previous file"


def test_unsupported_extension(tmp_path):
    with pytest.raises(ValueError, match="Choose"):
        export_machine(demo_project(), tmp_path / "bad.exe")


def test_import_preserves_controls_and_repeated_color_boundaries():
    pattern = emb.EmbPattern()
    for _ in range(4):
        pattern.add_thread("#123456")
    for command, x, y in [(emb.STITCH, 10, 20), (emb.TRIM, 10, 20), (emb.JUMP, 30, 40),
                           (emb.STOP, 30, 40), (emb.COLOR_CHANGE, 30, 40),
                           (emb.STITCH, 50, 60), (emb.COLOR_CHANGE, 50, 60),
                           (emb.COLOR_CHANGE, 50, 60), (emb.END, 50, 60)]:
        pattern.add_stitch_absolute(command, x, y)
    project = from_pattern(pattern).project
    result = to_pattern(Project.loads(project.dumps()))
    semantic = lambda p: [(s[2] & 255, round(s[0], 6), round(s[1], 6)) for s in p.stitches if s[2] & 255 != emb.JUMP]
    assert semantic(result) == semantic(pattern)
    assert len(project.objects) == 4


def test_import_rejects_specialist_commands():
    pattern = emb.EmbPattern()
    pattern.add_stitch_absolute(emb.STITCH, 0, 0)
    pattern.add_command(emb.SEQUIN_MODE)
    with pytest.raises(ValueError, match="Unsupported machine command"):
        from_pattern(pattern)


def test_hand_encoded_dst_fixture(tmp_path):
    # Hand-encoded Tajima ternary records, independent of our format writer.
    path = tmp_path / "hand.dst"
    header = b"LA:hand            \rST:      5\rCO:  1\r"
    path.write_bytes(header.ljust(512, b" ") + bytes([1, 0, 3, 128, 0, 3, 0, 0, 195, 2, 0, 131, 0, 0, 243]))
    result = import_machine(path)
    points = [(s.x, s.y) for b in generate(result.project) for s in b.stitches if s.command == "stitch"]
    assert points == pytest.approx([(.1, 0), (.1, -.1)])
    assert len(result.project.objects) == 2
    assert any("Placeholder" in n for n in result.notes)


def test_imported_stitches_transform_without_redigitizing():
    pattern = emb.EmbPattern()
    pattern.add_stitch_absolute(emb.JUMP, -20, -10)
    pattern.add_stitch_absolute(emb.STITCH, 20, 10)
    project = from_pattern(pattern).project
    obj = project.objects[0]
    obj.width *= 2
    obj.rotation = 90
    obj.x = 10
    stitches = generate(project)[0].stitches
    assert len(stitches) == 2
    assert (stitches[-1].x, stitches[-1].y) == pytest.approx((9, 4))


@pytest.mark.parametrize("extension", ["dst", "tbf"])
def test_fixed_headers_survive_long_unicode_project_names(tmp_path, extension):
    project = demo_project()
    project.name = "🌼 A very long embroidery design name" * 3
    path = tmp_path / f"long.{extension}"
    export_machine(project, path)
    imported = import_machine(path).project
    assert len(imported.objects) == 4
    if extension == "tbf":
        assert path.read_bytes()[0x10A:0x10E] == bytes([1, 2, 3, 4])


@pytest.mark.parametrize("source", sorted(EXPORT_FORMATS))
@pytest.mark.parametrize("target", sorted(EXPORT_FORMATS))
def test_all_machine_conversion_pairs(tmp_path, source, target):
    original = demo_project()
    first = tmp_path / ("source" + source)
    second = tmp_path / ("target" + target)
    export_machine(original, first)
    intermediate = import_machine(first).project
    export_machine(intermediate, second)
    result = import_machine(second).project
    assert len(result.objects) == 4
    before = [(s.x, s.y) for b in generate(intermediate) for s in b.stitches if s.command == "stitch"]
    after = [(s.x, s.y) for b in generate(result) for s in b.stitches if s.command == "stitch"]
    for axis in [0, 1]:
        assert min(p[axis] for p in after) == pytest.approx(min(p[axis] for p in before), abs=.15)
        assert max(p[axis] for p in after) == pytest.approx(max(p[axis] for p in before), abs=.15)


def test_pes_version_choices_and_rgb(tmp_path):
    project = demo_project()
    for version in [1, 6]:
        path = tmp_path / f"v{version}.pes"
        export_machine(project, path, pes_version=version)
        assert path.read_bytes()[:8] == (b"#PES0001" if version == 1 else b"#PES0060")
        imported = import_machine(path).project
        if version == 6:
            assert [o.color for o in imported.objects] == ["#447568", "#7d9c69", "#d68b79", "#e9b75e"]


@pytest.mark.parametrize("extension", sorted(EXPORT_FORMATS))
def test_operator_pauses_survive_as_stops_or_thread_changes(tmp_path, extension):
    pattern = emb.EmbPattern()
    pattern.add_thread("#123456")
    pattern.add_thread("#123456")
    for cmd, x, y in [(emb.JUMP, 0, 0), (emb.STITCH, 10, 10), (emb.TRIM, 10, 10),
                      (emb.JUMP, 40, 40), (emb.STOP, 40, 40), (emb.STITCH, 50, 50),
                      (emb.COLOR_CHANGE, 50, 50), (emb.STITCH, 60, 60), (emb.END, 60, 60)]:
        pattern.add_stitch_absolute(cmd, x, y)
    path = tmp_path / ("pauses" + extension)
    export_machine(from_pattern(pattern).project, path)
    imported = import_machine(path).project
    blocks = generate(imported)
    pauses = len(blocks) - 1 + sum(s.command == "stop" for b in blocks for s in b.stitches)
    assert pauses == 2
    assert any(s.command == "trim" for b in blocks for s in b.stitches)
