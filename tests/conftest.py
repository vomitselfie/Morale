"""Shared test safeguards for headless runs on every platform."""
import os

import pytest


@pytest.fixture(autouse=True)
def fail_on_unexpected_message_box(monkeypatch):
    """Turn an unexpected modal message box into a test failure.

    Offscreen Qt cannot click a modal box, so a warning that only appears on
    one platform would otherwise hang the run. Tests that expect a box replace
    these functions themselves, which takes precedence over this guard.
    """
    from PySide6.QtWidgets import QMessageBox
    shown = []

    def record(kind):
        def show(parent, title, text, *args, **kwargs):
            shown.append(f"{kind}: {title}: {text}")
            return QMessageBox.StandardButton.Cancel
        return show

    for kind in ("warning", "critical", "information", "question"):
        monkeypatch.setattr(QMessageBox, kind, record(kind))
    yield
    if shown:
        pytest.fail("Unexpected message box:\n" + "\n".join(shown), pytrace=False)


def pytest_runtest_logstart(nodeid, location):
    # CI names the test that was running if the process is killed by a timeout.
    path = os.environ.get("MORALE_TEST_PROGRESS")
    if path:
        with open(path, "a", encoding="utf-8") as stream:
            stream.write(nodeid + "\n")
