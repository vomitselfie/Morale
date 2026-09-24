"""Editable three-stage appliqué generated from a closed vector outline."""
from copy import deepcopy
import math
import uuid

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainterPath,QPainterPathStroker, QTransform
from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QDoubleSpinBox, QLabel, QDialogButtonBox,QComboBox

from .canvas import Canvas
from .model import DesignObject, Project
from .engine import generate


def cover_components(cover):
    from .auto_digitize import outline_path
    from .geometry import replace_contours
    rings=cover.rings();paths=[outline_path([ring]) for ring in rings]
    parents=[[j for j,path in enumerate(paths) if i!=j and path.contains(paths[i])] for i in range(len(paths))]
    pieces=[]
    for i,ring in enumerate(rings):
        depth=len(parents[i])
        if depth%2:continue
        holes=[rings[j] for j in range(len(rings)) if len(parents[j])==depth+1 and i in parents[j]]
        piece=deepcopy(cover);piece.id=uuid.uuid4().hex
        pieces.append(replace_contours(piece,[ring,*holes]))
    return pieces


def cover_set_valid(cover,pieces,approximate=False):
    """Check the painted union and repeated coverage, not contour XOR alone."""
    from .auto_digitize import outline_path,area,difference_area
    if not pieces:return False
    original=outline_path(cover.rings());union=QPainterPath();total=0.
    for piece in pieces:
        path=outline_path(piece.rings());total+=area(path);union=union.united(path)
    tolerance=max(.02,area(original)*.01) if approximate else max(.0001,area(original)*1e-8)
    return difference_area(original,union)<=tolerance and total-area(union)<=.0001


def applique_stages(source, border_width=2.,cover_mode='fill'):
    if source.kind in {"path", "stitches", "satin"}:
        raise ValueError("Select a closed shape or lettering outline for appliqué.")
    if isinstance(border_width,bool) or not isinstance(border_width,(int,float)) or not .5<=border_width<=6 or not math.isfinite(border_width):
        raise ValueError("Choose a border width between 0.5 and 6 mm.")
    if not isinstance(cover_mode,str) or cover_mode not in {'fill','auto'}:raise ValueError('Choose automatic satin or a tatami cover.')
    stages = []
    for title, instruction in [("Placement", "Stop: place appliqué fabric over the placement outline."),
                               ("Tack-down", "Stop: trim excess appliqué fabric along the tack-down outlines, including intended cutouts, before cover stitching.")]:
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
    # fine detail in millimeters. Optional satin planning follows normalization.
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
    if cover_mode=='auto':
        from .auto_digitize import choose_stitches
        pieces=cover_components(cover)
        if cover_set_valid(cover,pieces):
            planned,decisions=choose_stitches(Project(objects=pieces),overrides={str(i):'satin' for i in range(len(pieces))})
        else:
            planned=Project(objects=[cover]);decisions=[{'reason':'Cover components could not be separated without changing coverage.'}]
        if not cover_set_valid(cover,planned.objects,approximate=True):
            planned=Project(objects=[cover]);decisions=[{'reason':'Planned covers overlap or change the original band too much.'}]
        for index,(piece,decision) in enumerate(zip(planned.objects,decisions),1):
            satin=piece.stitch_type=='satin'
            piece.name=f"{'Satin' if satin else 'Tatami'} cover {index} · {source.name}"[:200]
            piece.stage_note=('Sew the satin cover band; inspect the start/end seam.' if satin else
                              'Sew the tatami cover band. Satin fallback: '+decision['reason'])[:500]
        stages.extend(planned.objects)
    else:stages.append(cover)
    project = Project.loads(Project(objects=stages).dumps())
    generate(project)
    return project.objects


class AppliqueDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create appliqué stages")
        layout = QVBoxLayout(self)
        text = QLabel("Replace the selected closed outline with three editable stages:\n\n1. Placement run; stop to place fabric.\n2. Tack-down run; stop to trim excess fabric.\n3. Cover borders, including cutout edges.\n\nAutomatic mode uses satin where rail geometry can be validated, with named tatami fallbacks. Separate borders become separate objects. Check operator stops and test on scrap fabric.")
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
        self.cover_mode=QComboBox();self.cover_mode.addItem('Automatic satin (tatami fallback)','auto');self.cover_mode.addItem('Tatami cover band','fill')
        self.cover_mode.setAccessibleName('Appliqué cover stitch type');form.addRow('Cover stitches',self.cover_mode)
        layout.addLayout(form)
        controls = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        controls.accepted.connect(self.accept)
        controls.rejected.connect(self.reject)
        layout.addWidget(controls)
        self.resize(450, 330)
