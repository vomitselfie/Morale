import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from morale.model import DesignObject, Project, demo_project
from morale.settings_copy import copy_settings, paste_settings


@pytest.fixture(scope="module", autouse=True)
def app():
    return QApplication.instance() or QApplication([])


def test_paste_keeps_shape_thread_name_and_fill_points():
    source = DesignObject(name="Source", kind="rectangle", spacing=.6, angle=12, pull_compensation=.3, underlay_style="edge_sparse",
                          tie_in=True, trim_after=True, color="#112233", fill_start=[-.5, -.5])
    target = DesignObject(name="Target", kind="ellipse", x=20, width=11, color="#445566", fill_end=[.5, 0])
    project = Project(objects=[source, target])
    result, changed, kept = paste_settings(project, {target.id}, copy_settings(source))
    pasted = result.objects[1]
    assert (changed, kept) == (1, 0)
    assert (pasted.spacing, pasted.angle, pasted.pull_compensation, pasted.underlay_style) == (.6, 12, .3, "edge_sparse")
    assert pasted.tie_in and pasted.trim_after
    assert (pasted.name, pasted.color, pasted.kind, pasted.x, pasted.width) == ("Target", "#445566", "ellipse", 20, 11)
    assert pasted.fill_end == [.5, 0] and pasted.fill_start == []
    assert project.objects[1] == target


def test_stitch_type_comes_along_only_where_the_shape_allows_it():
    satin = DesignObject(kind="satin", stitch_type="satin", spacing=.3, points=[[-.5, -.5], [.5, -.5], [-.5, .5], [.5, .5]])
    fill = DesignObject(kind="ellipse", spacing=.5)
    running = DesignObject(kind="ellipse", stitch_type="running", stitch_length=3.5)
    project = Project(objects=[satin, fill, running])
    result, changed, kept = paste_settings(project, {fill.id}, copy_settings(satin))
    assert result.objects[1].stitch_type == "fill" and result.objects[1].spacing == .3 and (changed, kept) == (1, 1)
    result, _, kept = paste_settings(project, {fill.id}, copy_settings(running))
    assert result.objects[1].stitch_type == "running" and result.objects[1].stitch_length == 3.5 and kept == 0


def test_native_copy_paste_and_select_same_type_with_undo():
    from morale.app import MainWindow
    window = MainWindow()
    try:
        window.replace_project(demo_project())
        objects = window.project.objects
        window.select(objects[1].id)  # Left leaf, fill
        window.update_property("spacing", .7)
        window.copy_stitch_settings()
        window.select_same_stitch_type()
        assert window.selected_ids == {o.id for o in objects if o.stitch_type == "fill"}
        before = window.project.dumps()
        window.paste_stitch_settings()
        assert all(o.spacing == .7 for o in window.project.objects if o.stitch_type == "fill")
        assert window.project.objects[0].spacing != .7  # The running stem was not selected.
        window.undo()
        assert window.project.dumps() == before
    finally:
        window.saved = window.project.dumps(); window.close()


def test_paste_without_copy_or_selection_changes_nothing():
    from morale.app import MainWindow
    window = MainWindow()
    try:
        before = window.project.dumps()
        window.paste_stitch_settings()
        window.select(window.project.objects[1].id); window.copy_stitch_settings()
        window.select("")
        window.paste_stitch_settings()
        assert window.project.dumps() == before
    finally:
        window.saved = window.project.dumps(); window.close()
