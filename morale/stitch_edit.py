"""Virtual native stitch table and geometry-safe conversion to manual objects."""
from copy import deepcopy
import math

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, QPointF, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QAction, QKeySequence
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableView,
    QPushButton, QComboBox, QDialogButtonBox, QStyledItemDelegate, QWidget, QMessageBox, QApplication, QDoubleSpinBox)

from .model import Project

COMMANDS = ("stitch", "jump", "trim", "stop")


def normalize_controls(rows):
    """Trim/stop are non-motion events and remain at the previous needle position."""
    position = (0., 0.)
    for row in rows:
        if row[2] in {"stitch", "jump"}:
            position = row[0], row[1]
        else:
            row[0], row[1] = position


def manual_object(obj, rows):
    if not rows or len(rows) > 250_000:
        raise ValueError("Keep between 1 and 250,000 commands in an object.")
    clean = []
    for row in rows:
        if not isinstance(row, (list, tuple)) or len(row) != 3 or not isinstance(row[2], str) or row[2] not in COMMANDS:
            raise ValueError("Choose stitch, jump, trim, or stop for every row.")
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or abs(v) > 1000 for v in row[:2]):
            raise ValueError("Coordinates must be finite millimeters within ±1,000.")
        clean.append(list(row))
    if clean[0][2] != "jump":
        raise ValueError("Start the object with a jump to its first needle position.")
    normalize_controls(clean)
    xs, ys = zip(*[(s[0], s[1]) for s in clean])
    candidate = deepcopy(obj)
    candidate.x, candidate.y = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    candidate.width, candidate.height = max(.1, max(xs) - min(xs)), max(.1, max(ys) - min(ys))
    candidate.rotation = 0
    candidate.flip_x = candidate.flip_y = False
    candidate.kind, candidate.stitch_type = "stitches", "manual"
    candidate.points = []
    candidate.handles = []
    candidate.contours = []
    candidate.lettering = {}
    candidate.underlay = candidate.tie_in = candidate.tie_off = candidate.trim_after = candidate.connect_fill = False
    candidate.stop_after = False
    candidate.stitch_data = [[(x - candidate.x) / candidate.width, (y - candidate.y) / candidate.height, command] for x, y, command in clean]
    Project.loads(Project(objects=[candidate]).dumps())
    return candidate


class StitchTableModel(QAbstractTableModel):
    historyChanged = Signal()
    historyRestored = Signal(int)
    history_limit = 100
    history_row_limit = 500_000

    def __init__(self, rows, parent=None):
        super().__init__(parent)
        self.rows = deepcopy(rows)
        self.history = []
        self.future = []

    def _splice(self, index, before, after):
        if len(before) == len(after):
            self.rows[index:index+len(before)] = after
            if after:
                self.dataChanged.emit(self.index(index, 0), self.index(index+len(after)-1, 2))
            return
        if before:
            self.beginRemoveRows(QModelIndex(), index, index+len(before)-1)
            del self.rows[index:index+len(before)]
            self.endRemoveRows()
        if after:
            self.beginInsertRows(QModelIndex(), index, index+len(after)-1)
            self.rows[index:index] = after
            self.endInsertRows()

    def _record(self, splices, label, focus):
        if not splices:
            return
        for splice in splices:
            self._splice(*splice)
        # Store normalization in the same action. Rows in history are never
        # mutated: a coordinate/command change always replaces the row value.
        position = (0., 0.)
        start = None
        before, after = [], []
        repairs = []
        for index, row in enumerate(self.rows):
            if row[2] in {"stitch", "jump"}:
                position = tuple(row[:2])
            changed = row[2] in {"trim", "stop"} and tuple(row[:2]) != position
            if changed:
                if start is None: start = index
                before.append(row)
                after.append([*position, row[2]])
            elif start is not None:
                repairs.append((start,before,after))
                start, before, after = None, [], []
        if start is not None:
            repairs.append((start,before,after))
        for splice in repairs:
            self._splice(*splice)
        splices += repairs
        cost = sum(len(before)+len(after) for _,before,after in splices)
        self.history.append((splices,label,focus,cost))
        self.future.clear()
        retained = sum(entry[3] for entry in self.history)
        while len(self.history)>1 and (len(self.history)>self.history_limit or retained>self.history_row_limit):
            retained -= self.history.pop(0)[3]
        self.historyChanged.emit()

    def undo(self):
        if not self.history: return
        entry = self.history.pop()
        for index,before,after in reversed(entry[0]):
            self._splice(index,after,before)
        self.future.append(entry)
        self.historyChanged.emit()
        self.historyRestored.emit(min(entry[2],len(self.rows)-1))

    def redo(self):
        if not self.future: return
        entry = self.future.pop()
        for splice in entry[0]:
            self._splice(*splice)
        self.history.append(entry)
        self.historyChanged.emit()
        self.historyRestored.emit(min(entry[2],len(self.rows)-1))

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else 3

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            return ("X (mm)", "Y (mm)", "Command")[section] if orientation == Qt.Orientation.Horizontal else section + 1

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if index.isValid() and role in {Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole}:
            value = self.rows[index.row()][index.column()]
            return value if role == Qt.ItemDataRole.EditRole or index.column() == 2 else f"{value:.3f}"

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        flags = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
        if index.column() == 2 or self.rows[index.row()][2] in {"stitch", "jump"}:
            flags |= Qt.ItemFlag.ItemIsEditable
        return flags

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if not index.isValid() or role != Qt.ItemDataRole.EditRole or not self.flags(index) & Qt.ItemFlag.ItemIsEditable:
            return False
        if index.column() == 2:
            if value not in COMMANDS:
                return False
        else:
            try:
                value = float(value)
            except (ValueError, TypeError):
                return False
            if not math.isfinite(value) or abs(value) > 1000:
                return False
        if self.rows[index.row()][index.column()] == value:
            return True
        before = self.rows[index.row()]
        after = list(before)
        after[index.column()] = value
        self._record([(index.row(),[before],[after])], "change command" if index.column()==2 else "move needle", index.row())
        return True

    def insert_command(self, index, command):
        if len(self.rows) >= 250_000 or command not in COMMANDS:
            return
        index = max(0, min(index, len(self.rows)))
        previous = self.rows[index - 1][:2] if index else [0., 0.]
        following = self.rows[index][:2] if index < len(self.rows) else previous
        position = previous if command in {"trim", "stop"} else [(a + b) / 2 for a, b in zip(previous, following)]
        self._record([(index,[],[[*position,command]])], "insert command", index)

    def delete_rows(self, indices):
        indices = sorted({i for i in indices if 0 <= i < len(self.rows)})
        if not indices: return
        ranges = []
        start = previous = indices[0]
        for index in indices[1:]:
            if index != previous+1:
                ranges.append((start,previous+1))
                start = index
            previous = index
        ranges.append((start,previous+1))
        splices = [(start,self.rows[start:end],[]) for start,end in reversed(ranges)]
        self._record(splices, "delete commands", indices[0])


class CommandDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QComboBox(parent)
        editor.addItems(COMMANDS)
        return editor

    def setEditorData(self, editor, index):
        editor.setCurrentText(index.data(Qt.ItemDataRole.EditRole))

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText())


class CoordinateDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QDoubleSpinBox(parent)
        editor.setRange(-1000, 1000)
        editor.setDecimals(6)
        editor.setSingleStep(.1)
        editor.setKeyboardTracking(False)
        return editor

    def setEditorData(self, editor, index):
        original = float(index.data(Qt.ItemDataRole.EditRole))
        editor.setProperty("originalCoordinate", original)
        editor.setValue(original)
        editor.setProperty("originalDisplayCoordinate", editor.value())

    def setModelData(self, editor, model, index):
        editor.interpretText()
        original = editor.property("originalCoordinate")
        value = editor.value()
        if original is not None and value == editor.property("originalDisplayCoordinate"):
            value = original
        model.setData(index, value)


class StitchDetail(QWidget):
    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model
        self.selected = 0
        self.setMinimumHeight(170)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#fffdf8"))
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rows = self.model.rows
        if not rows:
            return
        center = max(0, min(self.selected, len(rows) - 1))
        start, end = max(0, center - 25), min(len(rows), center + 26)
        subset = rows[start:end]
        xs, ys = zip(*[s[:2] for s in subset])
        scale = min((self.width() - 40) / max(1, max(xs) - min(xs)), (self.height() - 40) / max(1, max(ys) - min(ys)))
        def point(row):
            return QPointF(self.width() / 2 + (row[0] - (min(xs) + max(xs)) / 2) * scale,
                           self.height() / 2 + (row[1] - (min(ys) + max(ys)) / 2) * scale)
        for a, b in zip(subset, subset[1:]):
            if b[2] not in {"stitch", "jump"}:
                continue
            painter.setPen(QPen(QColor("#346d54") if b[2] == "stitch" else QColor("#b38b51"), 1.5,
                                Qt.PenStyle.SolidLine if b[2] == "stitch" else Qt.PenStyle.DashLine))
            painter.drawLine(point(a), point(b))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#d2685b"))
        painter.drawEllipse(point(rows[center]), 5, 5)
        painter.setPen(QColor("#506953"))
        painter.drawText(10, 17, f"Command {center + 1}: {rows[center][2]} · nearby 50 commands · dashed = jump")


class StitchDialog(QDialog):
    def __init__(self, obj, rows, parent=None):
        super().__init__(parent)
        self.obj = obj
        self.candidate = None
        self.setWindowTitle(f"Edit stitches — {obj.name}")
        self.resize(700, 740)
        layout = QVBoxLayout(self)
        explanation = QLabel("Edit individual needle commands in millimeters. Trims/stops stay at the preceding position. Use Undo/Redo here to correct edits before applying.\nApplying converts this object to manual stitches; the main window's Undo restores its previous geometry.")
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        self.model = StitchTableModel(rows, self)
        history = QHBoxLayout()
        self.undo_action = QAction("Undo", self)
        self.redo_action = QAction("Redo", self)
        self.undo_action.setShortcuts(QKeySequence.StandardKey.Undo)
        self.redo_action.setShortcuts(QKeySequence.StandardKey.Redo)
        self.undo_action.triggered.connect(self.undo)
        self.redo_action.triggered.connect(self.redo)
        self.undo_button = QPushButton("Undo")
        self.redo_button = QPushButton("Redo")
        for action,button in ((self.undo_action,self.undo_button),(self.redo_action,self.redo_button)):
            action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            self.addAction(action)
            button.clicked.connect(action.trigger)
            history.addWidget(button)
        layout.addLayout(history)
        self.model.historyChanged.connect(self.refresh_history)
        self.refresh_history()
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setItemDelegateForColumn(0, CoordinateDelegate(self.table))
        self.table.setItemDelegateForColumn(1, CoordinateDelegate(self.table))
        self.table.setItemDelegateForColumn(2, CommandDelegate(self.table))
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.ExtendedSelection)
        self.table.setAccessibleName("Editable stitch commands")
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)
        self.detail = StitchDetail(self.model)
        layout.addWidget(self.detail)
        self.table.selectionModel().currentRowChanged.connect(self.select_row)
        self.model.historyRestored.connect(self.restore_row)
        self.model.dataChanged.connect(lambda *args: self.detail.update())
        self.model.rowsRemoved.connect(lambda *args: self.detail.update())
        self.model.rowsInserted.connect(lambda *args: self.detail.update())
        row = QHBoxLayout()
        self.command = QComboBox()
        self.command.addItems(COMMANDS)
        self.command.setAccessibleName("Command to insert")
        row.addWidget(self.command)
        add = QPushButton("Insert before selection")
        add.clicked.connect(self.insert)
        row.addWidget(add)
        remove = QPushButton("Delete selected commands")
        remove.clicked.connect(lambda: self.model.delete_rows([i.row() for i in self.table.selectionModel().selectedRows()]))
        row.addWidget(remove)
        layout.addLayout(row)
        controls = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        controls.accepted.connect(self.accept)
        controls.rejected.connect(self.reject)
        layout.addWidget(controls)
        if rows:
            self.table.selectRow(0)

    def refresh_history(self):
        for entries,action,button,title in ((self.model.history,self.undo_action,self.undo_button,"Undo"),(self.model.future,self.redo_action,self.redo_button,"Redo")):
            text = f"{title} {entries[-1][1]}" if entries else title
            action.setText(text)
            action.setEnabled(bool(entries))
            button.setText(text)
            button.setEnabled(bool(entries))

    def restore_row(self, row):
        if row >= 0:
            self.table.selectRow(row)
            self.table.scrollTo(self.model.index(row,0))
        self.detail.selected = max(0,row)
        self.detail.update()

    def commit_editor(self):
        focused = QApplication.focusWidget()
        if focused and self.isAncestorOf(focused):
            focused.clearFocus()

    def undo(self):
        self.commit_editor()
        self.model.undo()

    def redo(self):
        self.commit_editor()
        self.model.redo()

    def select_row(self, current, previous):
        self.detail.selected = max(0, current.row())
        self.detail.update()

    def insert(self):
        index = self.table.currentIndex().row()
        self.model.insert_command(index if index >= 0 else len(self.model.rows), self.command.currentText())

    def accept(self):
        # Moving focus commits the active table delegate before validation.
        focused = QApplication.focusWidget()
        if focused:
            focused.clearFocus()
        try:
            self.candidate = manual_object(self.obj, self.model.rows)
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid stitch edit", str(exc))
            return
        super().accept()
