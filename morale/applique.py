"""Editable three-stage appliqué generated from a closed vector outline."""
from copy import deepcopy
import math
import uuid

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainterPathStroker, QTransform
from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QDoubleSpinBox, QLabel, QDialogButtonBox

from .canvas import Canvas
from .model import DesignObject, Project
from .engine import generate


def applique_stages(source, border_width=2.):
    if source.kind in {"path", "stitches", "satin"}:
        raise ValueError("Select a closed shape or lettering outline for appliqué.")
    if not math.isfinite(border_width) or not .5 <= border_width <= 6:
        raise ValueError("Choose a border width between 0.5 and 6 mm.")
    stages = []
    for title, instruction in [("Placement", "Stop: place appliqué fabric over the placement outline."),
                               ("Tack-down", "Stop: trim excess appliqué fabric outside the tack-down line before the cover border.")]:
        obj = deepcopy(source)
        obj.id = uuid.uuid4().hex
        obj.name = f"{title} · {source.name}"[:200]
        obj.stitch_type = "running"
        obj.lettering = {}
        obj.underlay = False
        obj.tie_in = obj.tie_off = obj.trim_after = obj.stop_after = True
        obj.stage_note = instruction
        obj.color_break = source.color_break if not stages else False
        stages.append(obj)
    # Work at enlarged coordinates so flattening the rounded border retains
    # fine detail in millimeters. The cover is a filled band, not satin routing.
    path = QTransform().scale(20, 20).map(Canvas.outline_path(source))
    stroker = QPainterPathStroker()
    stroker.setWidth(border_width * 20)
    stroker.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    stroker.setCapStyle(Qt.PenCapStyle.RoundCap)
    band = stroker.createStroke(path).simplified()
    bounds = band.boundingRect()
    if bounds.isEmpty():
        raise ValueError("The selected outline cannot produce a cover border.")
    contours = []
    for polygon in band.toSubpathPolygons():
        ring = [[(point.x() - bounds.center().x()) / bounds.width(), (point.y() - bounds.center().y()) / bounds.height()] for point in polygon]
        if len(ring) > 1 and ring[0] == ring[-1]:
            ring.pop()
        if len(ring) >= 3:
            contours.append(ring)
    cover = DesignObject(name=f"Cover border · {source.name}"[:200], kind="compound",
                         x=bounds.center().x() / 20, y=bounds.center().y() / 20,
                         width=bounds.width() / 20, height=bounds.height() / 20,
                         color=source.color, thread=dict(source.thread), contours=contours,
                         visible=source.visible,
                         group_id=source.group_id,
                         spacing=source.spacing, stitch_length=source.stitch_length, angle=source.angle,
                         underlay=False, connect_fill=True, tie_in=True, tie_off=True, trim_after=True,
                         stage_note="Sew the tatami cover band. This is a fill border, not an automatically routed satin edge.")
    stages.append(cover)
    project = Project.loads(Project(objects=stages).dumps())
    generate(project)
    return project.objects


class AppliqueDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create appliqué stages")
        layout = QVBoxLayout(self)
        text = QLabel("Replace the selected closed outline with three editable objects:\n\n1. Placement run; stop to place fabric.\n2. Tack-down run; stop to trim excess fabric.\n3. Tatami cover band.\n\nStages retain the selected thread color. Check how your machine represents operator stops and test the sequence on scrap fabric.")
        text.setWordWrap(True)
        layout.addWidget(text)
        form = QFormLayout()
        self.border_width = QDoubleSpinBox()
        self.border_width.setRange(.5, 6)
        self.border_width.setValue(2)
        self.border_width.setSingleStep(.1)
        self.border_width.setSuffix(" mm")
        self.border_width.setAccessibleName("Appliqué cover width")
        form.addRow("Cover width", self.border_width)
        layout.addLayout(form)
        controls = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        controls.accepted.connect(self.accept)
        controls.rejected.connect(self.reject)
        layout.addWidget(controls)
        self.resize(450, 330)
