import pytest
from PySide6.QtWidgets import QApplication
from morale.app import MainWindow
from morale.model import Project


@pytest.fixture
def window():
    QApplication.instance() or QApplication([])
    widget = MainWindow()
    yield widget
    widget.saved = widget.project.dumps()
    widget.close()


def count_dumps(monkeypatch):
    calls = []
    original = Project.dumps
    monkeypatch.setattr(Project, "dumps", lambda self: calls.append(1) or original(self))
    return calls


def test_dirty_state_and_title_do_not_serialize(window, monkeypatch):
    calls = count_dumps(monkeypatch)
    for _ in range(5):
        window.update_title()
        assert not window.dirty
    assert not calls
    window.commit(lambda: setattr(window.project, "name", "Changed"))
    calls.clear()
    window.update_title()
    assert window.dirty and window.windowTitle().startswith("●") and not calls


def test_one_edit_serializes_the_project_at_most_twice(window, monkeypatch):
    window.serialized()
    calls = count_dumps(monkeypatch)
    window.commit(lambda: setattr(window.project.objects[0], "x", 3.))
    # One serialization for the new state; the "before" snapshot came from the cache.
    assert len(calls) <= 2
    calls.clear()
    # Repeated reads of an unchanged state reuse the cached serialization.
    window.serialized(); window.serialized(); window.update_title()
    assert window.dirty
    assert not calls


def test_undo_back_to_saved_state_reads_as_saved(window):
    assert not window.dirty
    window.commit(lambda: setattr(window.project, "name", "Changed"))
    assert window.dirty
    window.undo()
    assert not window.dirty and window.project.name != "Changed"
    window.redo()
    assert window.dirty and window.project.name == "Changed"


def test_revisions_are_never_reused_after_undo(window):
    start = window.project_revision
    window.commit(lambda: setattr(window.project, "name", "A"))
    first = window.project_revision
    window.saved = window.serialized()
    window.undo()
    assert window.project_revision == start
    window.commit(lambda: setattr(window.project, "name", "B"))
    # A different state after undo must not look like the saved "A".
    assert window.project_revision not in {start, first} and window.dirty


def test_stale_background_result_is_rejected_by_revision(window):
    window.generation_pending = True
    window.pending_snapshot = window.project_revision
    window.preview_revision = 7
    window.commit(lambda: setattr(window.project, "name", "Newer"))
    # The worker answered for an older revision: the result must not be shown.
    window.generation_pending = True
    window.pending_snapshot = window.project_revision - 1
    window.blocks = []
    window.calculation_ready(window.preview_revision, ["stale"])
    assert window.blocks != ["stale"]


def test_unchanged_commit_keeps_revision_and_history(window):
    revision, history = window.project_revision, len(window.history)
    window.commit(lambda: None)
    assert window.project_revision == revision and len(window.history) == history
