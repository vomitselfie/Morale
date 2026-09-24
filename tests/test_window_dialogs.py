from PySide6.QtWidgets import QApplication,QDialog
from morale.app import MainWindow


def test_menu_dialogs_open_with_the_right_classes(monkeypatch):
    # Two different HoopDialog classes once shared one name in the window module.
    app=QApplication.instance() or QApplication([])
    shown=[]
    monkeypatch.setattr(QDialog,'exec',lambda self:shown.append(type(self).__module__+'.'+type(self).__name__) or 0)
    window=MainWindow()
    try:
        window.multihoop_dialog()
        window.custom_hoop()
        assert shown==['morale.hoop_dialog.HoopDialog','morale.measurements.HoopDialog']
    finally:
        window.saved=window.project.dumps();window.close()
