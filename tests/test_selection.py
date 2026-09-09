import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from morale.app import MainWindow
from morale.model import DesignObject, Project
from morale.arrange import arrange_selection, bounds
from morale.clipboard import encode_objects, decode_objects


@pytest.fixture
def window():
    app = QApplication.instance() or QApplication([])
    widget = MainWindow()
    widget.replace_project(Project(objects=[DesignObject(name="A", x=-25, width=10, height=10),
                                           DesignObject(name="B", x=0, width=10, height=10),
                                           DesignObject(name="C", x=30, width=10, height=10)]))
    widget.show()
    widget.canvas.setFocus()
    app.processEvents()
    widget.canvas.scale = 5
    yield widget
    QApplication.clipboard().clear()
    widget.saved = widget.project.dumps()
    widget.close()


def test_native_modifier_selection_and_group_drag(window):
    canvas = window.canvas
    center = canvas.rect().center()
    QTest.mouseClick(canvas, Qt.MouseButton.LeftButton, pos=center + QPoint(-125, 0))
    QTest.mouseClick(canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier, center)
    assert len(window.selected_ids) == 2
    before = window.project.dumps()
    QTest.mousePress(canvas, Qt.MouseButton.LeftButton, pos=center)
    QTest.mouseMove(canvas, center + QPoint(20, 15))
    QTest.mouseRelease(canvas, Qt.MouseButton.LeftButton, pos=center + QPoint(20, 15))
    assert [obj.x for obj in window.project.objects] == pytest.approx([-21, 4, 30])
    assert [obj.y for obj in window.project.objects] == pytest.approx([3, 3, 0])
    window.undo()
    assert window.project.dumps() == before


def test_sequence_list_extended_selection(window):
    first, second = window.layers.item(0), window.layers.item(1)
    first.setSelected(True)
    second.setSelected(True)
    assert window.selected_ids == {obj.id for obj in window.project.objects[:2]}
    assert not window.properties.isEnabled()


def test_selection_duplicate_copy_delete_and_undo(window):
    window.select_many([obj.id for obj in window.project.objects[:2]])
    before = window.project.dumps()
    window.duplicate()
    assert len(window.project.objects) == 5
    assert len(window.selected_ids) == 2
    assert [obj.x for obj in window.selected_objects()] == [-22, 3]
    window.undo()
    assert window.project.dumps() == before
    window.select_many([obj.id for obj in window.project.objects[:2]])
    window.canvas.setFocus()
    assert window.copy_selection()
    window.paste_selection()
    assert len(window.selected_ids) == 2
    window.delete()
    assert len(window.project.objects) == 3


def test_group_persistence_and_member_selection(window):
    ids = [obj.id for obj in window.project.objects[:2]]
    window.select_many(ids)
    window.group_selection()
    saved = window.project.dumps()
    assert window.project.objects[0].group_id == window.project.objects[1].group_id
    assert window.project.objects[0].group_id
    window.replace_project(Project.loads(saved))
    window.select(ids[0])
    assert window.selected_ids == set(ids)
    window.select_many([ids[0]], expand_groups=False)
    assert window.selected_object().id == ids[0]
    window.select(ids[0])
    window.ungroup_selection()
    assert not any(obj.group_id for obj in window.selected_objects())
    window.undo()
    assert window.project.dumps() == saved


def test_clipboard_and_duplicate_make_independent_groups(window):
    window.select_many([obj.id for obj in window.project.objects[:2]])
    window.group_selection()
    group = window.selected_objects()[0].group_id
    copies = decode_objects(encode_objects(window.selected_objects()))
    assert copies[0].group_id == copies[1].group_id != group
    window.duplicate()
    assert window.selected_objects()[0].group_id != group
    assert len({obj.group_id for obj in window.selected_objects()}) == 1


def test_selection_alignment_and_distribution_preserve_sequence():
    objects = [DesignObject(x=-20), DesignObject(x=-10), DesignObject(x=30)]
    distributed = arrange_selection(objects, "distribute", "horizontal", 100, 100)
    assert [obj.id for obj in distributed] == [obj.id for obj in objects]
    assert [obj.x for obj in distributed] == [-20, 5, 30]
    aligned = arrange_selection(objects, "align_objects", "left", 100, 100)
    assert all(bounds(obj)[0] == -30 for obj in aligned)
    centered = arrange_selection(objects, "align", "center", 100, 100)
    assert [obj.x for obj in centered] == [-25, -15, 25]


def test_selection_mirror_reflects_relative_positions():
    objects = [DesignObject(x=-20), DesignObject(x=30)]
    mirrored = arrange_selection(objects, "mirror", "horizontal", 100, 100)
    assert [obj.x for obj in mirrored] == [30, -20]
    assert all(obj.flip_x for obj in mirrored)


def test_multi_reorder_preserves_relative_order(window):
    ids = [obj.id for obj in window.project.objects]
    window.select_many(ids[1:])
    window.reorder(-1)
    assert [obj.id for obj in window.project.objects] == [ids[1], ids[2], ids[0]]
    window.undo()
    assert [obj.id for obj in window.project.objects] == ids


def test_group_movement_clamps_as_a_unit(window):
    window.project.objects[0].x = 999
    window.project.objects[1].x = 990
    window.select_many([obj.id for obj in window.project.objects[:2]])
    window.move_object(window.selected_id, 10, 0)
    assert [obj.x for obj in window.project.objects[:2]] == [1000, 991]


def test_palette_recolors_selection_in_one_undo(window):
    window.select_many([obj.id for obj in window.project.objects[:2]])
    before = window.project.dumps()
    window.update_property("color", "#123456")
    assert [obj.color for obj in window.project.objects[:2]] == ["#123456", "#123456"]
    window.undo()
    assert window.project.dumps() == before


def test_native_selection_transform_and_atomic_validation(window):
    window.select_many([obj.id for obj in window.project.objects[:2]])
    before = window.project.dumps()
    window.apply_transform(2, 90, "hoop")
    for obj, expected in zip(window.project.objects[:2], [(0, -50), (0, 0)]):
        assert (obj.x, obj.y) == pytest.approx(expected)
    assert window.project.objects[2].x == 30
    window.undo()
    assert window.project.dumps() == before
    window.project.objects[0].width = 400
    unchanged = window.project.dumps()
    with pytest.raises(ValueError):
        window.apply_transform(2, 0)
    assert window.project.dumps() == unchanged


def test_native_nonuniform_transform_preserves_unselected_and_undo(window):
    window.select_many([obj.id for obj in window.project.objects[:2]])
    before=window.project.dumps()
    untouched=window.project.objects[2]
    window.apply_transform(1.5,20,'selection',.75)
    assert window.project.objects[2]==untouched
    assert all(o.kind=='polygon' for o in window.project.objects[:2])
    window.undo()
    assert window.project.dumps()==before
    window.project.objects[0].width=400
    before=window.project.dumps()
    with pytest.raises(ValueError): window.apply_transform(2,0,'selection',.5)
    assert window.project.dumps()==before


def test_transform_dialog_linked_dimensions_and_independent_axes(window):
    from morale.transform_dialog import TransformDialog
    dialog=TransformDialog(2,window,(40,20))
    try:
        dialog.target_width.setValue(80)
        assert dialog.scale.value()==200 and dialog.scale_y.value()==200
        assert dialog.target_height.value()==40
        dialog.lock.setChecked(False)
        dialog.target_height.setValue(10)
        assert dialog.scale_y.value()==50 and dialog.scale.value()==200
        dialog.scale.setValue(150)
        assert dialog.target_width.value()==60 and dialog.target_height.value()==10
        dialog.lock.setChecked(True)
        assert dialog.scale_y.value()==150 and dialog.target_height.value()==30
    finally:
        dialog.close()


def test_nonuniform_lettering_outlines_survive_and_text_conversion_undo(window):
    from morale.lettering import make_lettering
    from morale.arrange import bounds
    obj=make_lettering('O','DejaVu Sans',height=15)
    window.replace_project(Project(objects=[obj]))
    window.select(obj.id)
    before=window.project.dumps()
    box=bounds(obj)
    window.apply_transform(2,0,scale_y=.5)
    result=window.project.objects[0]
    assert result.kind=='compound' and not result.lettering
    assert len(result.contours)==len(obj.contours)
    changed=bounds(result)
    assert changed[2]-changed[0]==pytest.approx(2*(box[2]-box[0]))
    assert changed[3]-changed[1]==pytest.approx(.5*(box[3]-box[1]))
    window.undo()
    assert window.project.dumps()==before
