import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLineEdit
from PySide6.QtTest import QTest

from morale.engine import generate
from morale.model import DesignObject, Project
from morale.stitch_edit import StitchTableModel, StitchDialog, manual_object


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_coordinates_commands_and_control_positions():
    model = StitchTableModel([[0, 0, "jump"], [2, 3, "stitch"], [2, 3, "trim"], [2, 3, "stop"], [4, 5, "stitch"]])
    assert model.setData(model.index(1, 0), "7.5")
    assert model.rows[2] == [7.5, 3, "trim"]
    assert model.rows[3] == [7.5, 3, "stop"]
    assert not model.setData(model.index(2, 0), "99")
    assert not model.setData(model.index(1, 0), "nan")
    assert not model.setData(model.index(1, 2), "unknown")
    assert model.setData(model.index(1, 2), "jump")


def test_insert_delete_and_normalization():
    model = StitchTableModel([[0, 0, "jump"], [10, 10, "stitch"], [20, 20, "stitch"]])
    model.insert_command(2, "stitch")
    assert model.rows[2] == [15, 15, "stitch"]
    model.insert_command(3, "trim")
    assert model.rows[3] == [15, 15, "trim"]
    model.delete_rows([2, 2])
    assert model.rows[2] == [10, 10, "trim"]


def test_manual_edit_preserves_absolute_geometry_color_and_identity():
    obj = DesignObject(x=10, rotation=37, color="#123456", color_break=True)
    rows = [[-5, -2, "jump"], [10, 8, "stitch"], [99, 99, "stop"], [15, 4, "jump"], [20, 6, "stitch"]]
    edited = manual_object(obj, rows)
    assert edited.id == obj.id
    assert edited.color == obj.color
    assert edited.color_break
    assert edited.rotation == 0
    result = generate(Project.loads(Project(objects=[edited]).dumps()))[0].stitches
    assert [(s.x, s.y) for s in result] == pytest.approx([(-5, -2), (10, 8), (10, 8), (15, 4), (20, 6)])
    assert [s.command for s in result] == ["jump", "stitch", "stop", "jump", "stitch"]


@pytest.mark.parametrize("rows", [[], [[0, 0, "stitch"]], [[0, 0, "jump"], [float("inf"), 0, "stitch"]], [[0, 0, "jump"], [600, 0, "stitch"]], [None]])
def test_invalid_edits_rejected(rows):
    with pytest.raises(ValueError):
        manual_object(DesignObject(), rows)


def test_large_table_is_virtual(app):
    model = StitchTableModel([[0, 0, "jump"]] + [[i / 1000, 0, "stitch"] for i in range(100_000)])
    assert model.rowCount() == 100_001
    assert model.data(model.index(100_000, 0)) == "99.999"
    assert model.setData(model.index(100_000, 1), "3")


def test_native_delegate_commits_before_apply(app):
    dialog = StitchDialog(DesignObject(), [[0, 0, "jump"], [2, 3, "stitch"]])
    dialog.show()
    app.processEvents()
    index = dialog.model.index(1, 0)
    dialog.table.setCurrentIndex(index)
    dialog.table.edit(index)
    app.processEvents()
    editor = dialog.table.findChild(QLineEdit)
    assert editor is not None
    editor.setFocus()
    editor.selectAll()
    QTest.keyClicks(editor, "9.5")
    dialog.accept()
    assert dialog.candidate is not None
    assert dialog.model.rows[1][0] == 9.5


def test_cancel_leaves_original_untouched(app):
    obj = DesignObject()
    before = Project(objects=[obj]).dumps()
    dialog = StitchDialog(obj, [[0, 0, "jump"], [2, 3, "stitch"]])
    dialog.model.setData(dialog.model.index(1, 0), 12)
    dialog.reject()
    assert dialog.candidate is None
    assert Project(objects=[obj]).dumps() == before


def test_undo_redo_restores_command_conversion_and_dependent_controls():
    rows=[[0,0,'jump'],[8,9,'stitch'],[8,9,'trim'],[8,9,'stop'],[20,20,'stitch']]
    model=StitchTableModel(rows)
    model.setData(model.index(1,2),'trim')
    assert model.rows[1:4]==[[0,0,'trim'],[0,0,'trim'],[0,0,'stop']]
    model.undo(); assert model.rows==rows
    model.redo(); assert model.rows[3]==[0,0,'stop']
    model.undo()
    model.setData(model.index(1,0),12)
    assert not model.future
    assert model.rows[2]==[12,9,'trim']
    model.undo(); assert model.rows==rows


def test_disjoint_delete_is_one_action_and_empty_table_can_be_restored():
    rows=[[0,0,'jump'],[8,9,'stitch'],[8,9,'trim'],[8,9,'stop'],[20,20,'stitch'],[20,20,'trim']]
    model=StitchTableModel(rows)
    model.delete_rows([1,4,1,-1,99])
    assert model.rows==[[0,0,'jump'],[0,0,'trim'],[0,0,'stop'],[0,0,'trim']]
    assert len(model.history)==1
    model.undo(); assert model.rows==rows
    model.redo()
    model.delete_rows(range(model.rowCount()))
    assert not model.rows
    model.undo(); model.undo(); assert model.rows==rows
    model.redo(); model.redo(); assert not model.rows


def test_invalid_and_identical_edits_preserve_redo():
    model=StitchTableModel([[0,0,'jump'],[1,2,'stitch']])
    model.setData(model.index(1,0),3)
    model.undo()
    assert not model.setData(model.index(1,0),'nan')
    assert model.setData(model.index(1,0),1)
    model.delete_rows([-1,100])
    model.insert_command(1,'unsupported')
    assert len(model.future)==1 and not model.history
    model.redo(); assert model.rows[1][0]==3


def test_large_model_uses_changed_rows_and_history_limits(app):
    model=StitchTableModel([[0,0,'jump']]+[[i/1000,0,'stitch'] for i in range(100_000)])
    untouched=model.rows[500]
    model.setData(model.index(99_000,1),4)
    assert model.history[-1][3]==2
    assert model.rows[500] is untouched
    model.undo(); assert model.rows[99_000][1]==0
    model.redo(); assert model.rows[99_000][1]==4
    model.history_limit=3
    model.history_row_limit=6
    for value in (5,6,7,8): model.setData(model.index(99_000,1),value)
    assert len(model.history)==3
    for _ in range(3): model.undo()
    assert model.rows[99_000][1]==5
    model.delete_rows(range(100_001))
    assert len(model.history)==1 and not model.future
    model.undo(); assert model.rowCount()==100_001


def test_mixed_edit_sequence_roundtrips_through_all_history():
    from copy import deepcopy
    import random
    randomizer=random.Random(4321)
    model=StitchTableModel([[0,0,'jump'],[10,10,'stitch'],[10,10,'stop']])
    states=[deepcopy(model.rows)]
    for step in range(60):
        count=len(model.history)
        operation=randomizer.randrange(3)
        if operation==0 or len(model.rows)<2:
            model.insert_command(randomizer.randrange(len(model.rows)+1),randomizer.choice(('jump','stitch','trim','stop')))
        elif operation==1:
            model.delete_rows(randomizer.sample(range(len(model.rows)),min(2,len(model.rows))))
        else:
            index=randomizer.randrange(len(model.rows))
            model.setData(model.index(index,2),randomizer.choice(('jump','stitch','trim','stop')))
        if len(model.history)>count: states.append(deepcopy(model.rows))
    for state in reversed(states[:-1]):
        model.undo(); assert model.rows==state
    for state in states[1:]:
        model.redo(); assert model.rows==state


def test_native_dialog_undo_redo_shortcuts_and_selection(app):
    dialog=StitchDialog(DesignObject(),[[0,0,'jump'],[2,3,'stitch'],[2,3,'stop']])
    try:
        dialog.show(); dialog.activateWindow(); dialog.table.setFocus(); app.processEvents()
        assert not dialog.undo_action.isEnabled()
        dialog.model.setData(dialog.model.index(1,0),8)
        assert dialog.undo_button.text()=='Undo move needle'
        QTest.keyClick(dialog.table,Qt.Key.Key_Z,Qt.KeyboardModifier.ControlModifier)
        assert dialog.model.rows[1][0]==2
        assert dialog.table.currentIndex().row()==1
        assert dialog.redo_action.isEnabled()
        dialog.redo_action.trigger()
        assert dialog.model.rows[2]==[8,3,'stop']
        dialog.accept()
        assert dialog.candidate is not None
    finally:
        dialog.close()


def test_undo_commits_active_delegate_then_reverts_that_edit(app):
    dialog=StitchDialog(DesignObject(),[[0,0,'jump'],[2,3,'stitch']])
    try:
        dialog.show(); app.processEvents()
        dialog.model.setData(dialog.model.index(1,0),5)
        index=dialog.model.index(1,0)
        dialog.table.setCurrentIndex(index); dialog.table.edit(index); app.processEvents()
        editor=dialog.table.findChild(QLineEdit)
        editor.setFocus(); editor.selectAll(); QTest.keyClicks(editor,'9.5')
        dialog.undo()
        assert dialog.model.rows[1][0]==5
        dialog.undo(); assert dialog.model.rows[1][0]==2
    finally:
        dialog.reject(); dialog.close()


def test_opening_coordinate_editor_without_change_retains_precision(app):
    value=2.1234567890123
    dialog=StitchDialog(DesignObject(),[[0,0,'jump'],[value,3,'stitch']])
    try:
        dialog.show(); app.processEvents()
        index=dialog.model.index(1,0)
        dialog.table.setCurrentIndex(index); dialog.table.edit(index); app.processEvents()
        dialog.accept()
        assert dialog.model.rows[1][0]==value
        assert not dialog.model.history
    finally:
        dialog.close()


def test_invalid_apply_can_be_undone_and_corrected(app,monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    errors=[]
    monkeypatch.setattr(QMessageBox,'warning',lambda *args:errors.append(args[2]))
    dialog=StitchDialog(DesignObject(),[[0,0,'jump'],[2,3,'stitch']])
    try:
        dialog.model.delete_rows([0])
        dialog.accept()
        assert errors and dialog.candidate is None
        dialog.model.undo()
        dialog.accept()
        assert dialog.candidate is not None
    finally:
        dialog.close()


def test_dialog_shortcuts_do_not_undo_parent_design(app):
    from morale.app import MainWindow
    window=MainWindow()
    dialog=None
    try:
        window.show(); window.select(window.project.objects[0].id)
        window.update_property('color','#123456')
        before=window.project.dumps(); history=len(window.history)
        dialog=StitchDialog(window.project.objects[0],[[0,0,'jump'],[2,3,'stitch']],window)
        dialog.setModal(True); dialog.show(); dialog.activateWindow(); dialog.table.setFocus(); app.processEvents()
        dialog.model.setData(dialog.model.index(1,0),8)
        QTest.keyClick(dialog.table,Qt.Key.Key_Z,Qt.KeyboardModifier.ControlModifier)
        assert dialog.model.rows[1][0]==2
        assert window.project.dumps()==before and len(window.history)==history
    finally:
        if dialog: dialog.reject(); dialog.close()
        window.saved=window.project.dumps(); window.close()
