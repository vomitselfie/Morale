"""Native point editor for polygon, running-path and paired satin rails."""
import math
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPainter, QPainterPath, QColor, QPen
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QPushButton, QDialogButtonBox, QComboBox, QWidget

from .geometry import replace_contours
from .model import Project
from .engine import generate


class PointDialog(QDialog):
    def __init__(self, obj, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Edit points — {obj.name}")
        self.resize(480, 520)
        layout = QVBoxLayout(self)
        self.instructions = QLabel("Coordinates in millimeters. Satin rows alternate left / right rail.")
        self.instructions.setWordWrap(True)
        layout.addWidget(self.instructions)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["X (mm)", "Y (mm)"])
        self.table.setAccessibleName("Editable path coordinates")
        layout.addWidget(self.table)
        if obj.handles:
            self.point_limit = 6000
            self.instructions.setText("Bezier rows repeat: incoming handle, anchor, outgoing handle. Coordinates are in millimeters. Add/remove complete triples to add/remove anchors.")
        for x, y in obj.control_points():
            self.append(x, y)
        row = QHBoxLayout()
        add = QPushButton("Add point")
        add.clicked.connect(lambda: self.append(0, 0))
        remove = QPushButton("Remove selected point")
        remove.clicked.connect(lambda: self.table.removeRow(self.table.currentRow()) if self.table.currentRow() >= 0 else None)
        row.addWidget(add)
        row.addWidget(remove)
        layout.addLayout(row)
        controls = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        controls.accepted.connect(self.accept)
        controls.rejected.connect(self.reject)
        layout.addWidget(controls)

    def append(self, x, y):
        if self.table.rowCount() >= getattr(self, "point_limit", 2000):
            return
        row = self.table.rowCount()
        self.table.insertRow(row)
        for column, value in enumerate((x, y)):
            item = QTableWidgetItem(f"{value:.6f}")
            item.setData(Qt.ItemDataRole.UserRole, value)
            self.table.setItem(row, column, item)

    def points(self):
        try:
            def value(item):
                original = item.data(Qt.ItemDataRole.UserRole)
                return original if original is not None and item.text() == f"{original:.6f}" else float(item.text())
            return [(value(self.table.item(row, 0)), value(self.table.item(row, 1))) for row in range(self.table.rowCount())]
        except (ValueError, AttributeError) as exc:
            raise ValueError("Every point needs numeric X and Y coordinates.") from exc


class ContourPreview(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(150)
        self.setAccessibleName("Contour preview; active outline blue, selected point red")
        self.rings = []
        self.active = 0
        self.point = -1

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#ffffff"))
        points = [p for ring in self.rings for p in ring]
        if not points or not all(math.isfinite(v) and abs(v) <= 1000 for p in points for v in p):
            return
        xs, ys = zip(*points)
        scale = min((self.width() - 24) / max(.1, max(xs) - min(xs)),
                    (self.height() - 24) / max(.1, max(ys) - min(ys)))
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        def screen(point):
            return QPointF(self.width() / 2 + (point[0] - cx) * scale,
                           self.height() / 2 + (point[1] - cy) * scale)
        paths = []
        combined = QPainterPath()
        combined.setFillRule(Qt.FillRule.OddEvenFill)
        for ring in self.rings:
            path = QPainterPath()
            if ring:
                path.moveTo(screen(ring[0]))
                for point in ring[1:]:
                    path.lineTo(screen(point))
                path.closeSubpath()
            paths.append(path)
            combined.addPath(path)
        painter.setPen(QPen(QColor("#6c7d75"), 1))
        painter.setBrush(QColor("#dce9df"))
        painter.drawPath(combined)
        if self.active < len(paths):
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor("#2563bb"), 2))
            painter.drawPath(paths[self.active])
            if 0 <= self.point < len(self.rings[self.active]):
                painter.setBrush(QColor("#cc3d39"))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(screen(self.rings[self.active][self.point]), 4, 4)


class ContourDialog(PointDialog):
    """Edit one contour at a time; rejected edits stay available for correction."""
    def __init__(self, obj, parent=None):
        super().__init__(obj, parent)
        self.source = obj
        self.point_limit = 20_000
        self.rings = obj.rings()
        self.current = 0
        self.instructions.setText("Edit contour coordinates in millimeters. Nested contours form holes and islands. Changing lettering outlines removes text editing parameters. Cancel keeps the original design.")
        self.selector = QComboBox()
        self.selector.setAccessibleName("Contour to edit")
        self.layout().insertWidget(1, self.selector)
        self.message = QLabel()
        self.message.setWordWrap(True)
        self.layout().insertWidget(2, self.message)
        self.preview = ContourPreview()
        self.layout().insertWidget(3, self.preview)
        buttons = QHBoxLayout()
        add = QPushButton("Add contour")
        add.clicked.connect(self.add_contour)
        remove = QPushButton("Remove contour")
        remove.clicked.connect(self.remove_contour)
        buttons.addWidget(add)
        buttons.addWidget(remove)
        self.layout().insertLayout(4, buttons)
        self.populate()
        self.selector.currentIndexChanged.connect(self.switch_contour)
        self.table.itemChanged.connect(self.update_preview)
        self.table.currentCellChanged.connect(self.update_preview)
        self.table.model().rowsRemoved.connect(self.update_preview)
        self.resize(540, 740)

    def update_preview(self, *args):
        rings = list(self.rings)
        try:
            rings[self.current] = self.points()
        except ValueError:
            return
        self.preview.rings = rings
        self.preview.active = self.current
        self.preview.point = self.table.currentRow()
        self.preview.update()

    def populate(self):
        self.table.blockSignals(True)
        self.selector.blockSignals(True)
        self.selector.clear()
        self.selector.addItems([f"Contour {i + 1} ({len(ring)} points)" for i, ring in enumerate(self.rings)])
        self.selector.setCurrentIndex(self.current)
        self.selector.blockSignals(False)
        self.table.setRowCount(0)
        for x, y in self.rings[self.current]:
            self.append(x, y)
        self.table.blockSignals(False)
        self.update_preview()

    def store_current(self):
        try:
            self.rings[self.current] = self.points()
            self.message.clear()
            return True
        except ValueError as exc:
            self.message.setText(str(exc))
            return False

    def switch_contour(self, index):
        if self.store_current():
            self.current = index
            self.populate()
        else:
            self.selector.blockSignals(True)
            self.selector.setCurrentIndex(self.current)
            self.selector.blockSignals(False)

    def add_contour(self):
        if len(self.rings) >= 256:
            self.message.setText("At most 256 contours are supported.")
            return
        if self.store_current():
            x, y = self.source.x, self.source.y
            self.rings.append([(x - 2, y - 2), (x + 2, y - 2), (x, y + 2)])
            self.current = len(self.rings) - 1
            self.populate()

    def remove_contour(self):
        if len(self.rings) == 1:
            self.message.setText("Keep at least one contour. Delete the object to remove it entirely.")
            return
        self.rings.pop(self.current)
        self.current = min(self.current, len(self.rings) - 1)
        self.message.clear()
        self.populate()

    def accept(self):
        if not self.store_current():
            return
        try:
            self.candidate = replace_contours(self.source, self.rings)
            generate(Project(objects=[self.candidate]))
        except ValueError as exc:
            self.message.setText(str(exc))
            return
        super().accept()
