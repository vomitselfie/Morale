import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication

from morale.canvas import Canvas
from morale.engine import generate
from morale.geometry import combine_outlines
from morale.model import DesignObject, Project
from morale.formats import export_machine, import_machine


@pytest.fixture(scope="module", autouse=True)
def app():
    return QApplication.instance() or QApplication([])


def rectangle(**kwargs):
    return DesignObject(kind="rectangle", width=20, height=20, underlay=False, angle=0, **kwargs)


def test_subtraction_creates_hole_and_does_not_sew_across_it():
    outer = rectangle(connect_fill=True)
    inner = DesignObject(kind="rectangle", width=8, height=8)
    result = combine_outlines([outer, inner], "subtract")
    path = Canvas.outline_path(result)
    assert path.contains(QPointF(8, 0))
    assert not path.contains(QPointF(0, 0))
    assert len(result.contours) == 2
    previous = None
    for stitch in generate(Project(objects=[result]))[0].stitches:
        if stitch.command == "stitch" and previous is not None:
            for t in [.1, .3, .5, .7, .9]:
                x = previous.x + t * (stitch.x - previous.x)
                y = previous.y + t * (stitch.y - previous.y)
                assert not (abs(x) < 3.99 and abs(y) < 3.99)
        previous = stitch


@pytest.mark.parametrize("operation,width,inside,outside", [
    ("union", 30, (14, 0), (21, 0)),
    ("intersection", 10, (5, 0), (-5, 0)),
    ("subtract", 10, (-5, 0), (5, 0)),
])
def test_overlap_operations_have_expected_geometry(operation, width, inside, outside):
    result = combine_outlines([rectangle(), rectangle(x=10)], operation)
    assert result.width == pytest.approx(width)
    path = Canvas.outline_path(result)
    assert path.contains(QPointF(*inside))
    assert not path.contains(QPointF(*outside))


def test_union_retains_separate_components_and_nested_island():
    ring = combine_outlines([rectangle(), DesignObject(kind="rectangle", width=12, height=12)], "subtract")
    island = DesignObject(kind="rectangle", width=4, height=4)
    result = combine_outlines([ring, island, rectangle(x=35)], "union")
    path = Canvas.outline_path(result)
    for point, expected in [((0, 0), True), ((4, 0), False), ((9, 0), True), ((35, 0), True), ((20, 0), False)]:
        assert path.contains(QPointF(*point)) == expected
    assert Project.loads(Project(objects=[result]).dumps()).objects[0].contours == result.contours


def test_transforms_and_settings_retained_without_double_transform():
    source = rectangle(rotation=37, flip_x=True, x=7, y=-4, color="#ff0000", thread={"brand": "Example"}, spacing=.7)
    other = rectangle(x=35)
    snapshot = Project(objects=[source, other]).dumps()
    result = combine_outlines([source, other], "union")
    before = Canvas.outline_path(source)
    after = Canvas.outline_path(result)
    for x in range(-15, 20, 2):
        for y in range(-20, 20, 2):
            assert after.contains(QPointF(x, y)) == before.contains(QPointF(x, y))
    assert result.rotation == 0 and not result.flip_x
    assert result.thread == source.thread and result.spacing == .7
    assert result.color == source.color and result.id not in {source.id, other.id}
    assert Project(objects=[source, other]).dumps() == snapshot


@pytest.mark.parametrize("kind", ["path", "satin", "stitches"])
def test_non_closed_sources_rejected(kind):
    with pytest.raises(ValueError, match="closed vector"):
        combine_outlines([rectangle(), DesignObject(kind=kind)], "union")


@pytest.mark.parametrize("operation", ["subtract", "intersection"])
def test_empty_results_rejected(operation):
    other = rectangle(x=0 if operation == "subtract" else 40)
    with pytest.raises(ValueError, match="no usable area"):
        combine_outlines([rectangle(), other], operation)


def test_native_operation_preserves_sequence_and_undo_and_rejects_atomically():
    from morale.app import MainWindow
    window = MainWindow()
    try:
        outer, unrelated, inner = rectangle(), rectangle(x=40), DesignObject(kind="ellipse", width=8, height=8)
        window.replace_project(Project(objects=[outer, unrelated, inner]))
        original = window.project.dumps()
        window.select_many([inner.id, outer.id])
        window.apply_outline_operation("subtract")
        assert len(window.project.objects) == 2
        assert window.project.objects[1].id == unrelated.id
        assert not Canvas.outline_path(window.project.objects[0]).contains(QPointF(0, 0))
        assert window.selected_id == window.project.objects[0].id
        window.undo()
        assert window.project.dumps() == original
        window.select_many([outer.id, unrelated.id])
        history = list(window.history)
        with pytest.raises(ValueError, match="no usable area"):
            window.apply_outline_operation("intersection")
        assert window.project.dumps() == original and window.history == history
    finally:
        window.saved = window.project.dumps()
        window.close()


@pytest.mark.parametrize("extension", ["dst", "exp", "jef", "pec", "pes", "tbf", "u01", "vp3", "xxx"])
def test_hole_survives_machine_export(tmp_path, extension):
    result = combine_outlines([rectangle(), DesignObject(kind="rectangle", width=8, height=8)], "subtract")
    destination = tmp_path / f"hole.{extension}"
    export_machine(Project(objects=[result]), destination)
    blocks = generate(import_machine(destination).project)
    sewn = [s for b in blocks for s in b.stitches if s.command == "stitch"]
    assert sewn
    assert all(not (abs(s.x) < 3.8 and abs(s.y) < 3.8) for s in sewn)
