"""Actual-size tiled placement PDFs using millimeter page coordinates."""
from dataclasses import dataclass
import math
import os
from pathlib import Path
import tempfile

from PySide6.QtCore import Qt, QRectF, QPointF, QMarginsF
from PySide6.QtGui import QPdfWriter, QPageSize, QPageLayout, QPainter, QPainterPath, QPen, QColor, QFont
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QComboBox, QCheckBox, QDialogButtonBox

from .canvas import Canvas
from .engine import generate
from .model import Project

PAPERS = {"A4": (210., 297., QPageSize.PageSizeId.A4),
          "Letter": (215.9, 279.4, QPageSize.PageSizeId.Letter)}


@dataclass
class TemplatePlan:
    paper: str
    columns: int
    rows: int
    left: float
    top: float
    width: float
    height: float
    overlap: float = 10

    def tiles(self):
        return [(column, row, QRectF(self.left + column*(self.width-self.overlap),
                 self.top + row*(self.height-self.overlap), self.width, self.height))
                for row in range(self.rows) for column in range(self.columns)]


def template_plan(project, blocks, paper="A4"):
    if paper not in PAPERS:
        raise ValueError("Choose A4 or Letter paper.")
    width, height, _ = PAPERS[paper]
    width, height = width-30, height-60
    points = [(-project.hoop_width/2,-project.hoop_height/2), (project.hoop_width/2,project.hoop_height/2)]
    points += [p for obj in project.objects if obj.visible for ring in obj.rings() for p in ring]
    points += [(s.x,s.y) for block in blocks for s in block.stitches]
    xs,ys = zip(*points)
    columns = max(1, math.ceil((max(xs)-min(xs)-10)/(width-10)))
    rows = max(1, math.ceil((max(ys)-min(ys)-10)/(height-10)))
    if columns*rows > 100:
        raise ValueError("The placement template exceeds 100 pages. Move distant objects closer before printing.")
    return TemplatePlan(paper,columns,rows,(min(xs)+max(xs)-width-(columns-1)*(width-10))/2,
                        (min(ys)+max(ys)-height-(rows-1)*(height-10))/2,width,height)


def registration_marks(plan):
    """Shared marks lie in each pair of adjacent pages' overlap bands."""
    marks = set()
    for c,r,tile in plan.tiles():
        if c+1 < plan.columns:
            x = tile.right()-plan.overlap/2
            marks.update([(x,tile.top()+20), (x,tile.bottom()-20)])
        if r+1 < plan.rows:
            y = tile.bottom()-plan.overlap/2
            marks.update([(tile.left()+20,y), (tile.right()-20,y)])
    return sorted(marks)


def paint_template(painter, project, blocks, plan, column, row, tile, stitches=True):
    # The caller scales the painter once: one logical unit is one millimeter.
    page_width,page_height,_ = PAPERS[plan.paper]
    font = QFont("sans-serif")
    font.setPixelSize(4)
    painter.setFont(font)
    painter.setPen(QColor("#202020"))
    painter.drawText(QRectF(15,10,page_width-30,7), Qt.AlignmentFlag.AlignLeft,
                     painter.fontMetrics().elidedText(project.name,Qt.TextElideMode.ElideRight,int(page_width-30)))
    font.setPixelSize(3)
    painter.setFont(font)
    painter.drawText(QPointF(15,23),f"Morale · actual size · row {row+1}/{plan.rows}, column {column+1}/{plan.columns} · {plan.paper}")
    def ink(color):
        color = QColor(color)
        return color.darker(180) if color.lightness() > 180 else color
    frame = QRectF(15,30,plan.width,plan.height)
    painter.save()
    painter.setClipRect(frame)
    painter.translate(frame.left()-tile.left(),frame.top()-tile.top())
    painter.setPen(QPen(QColor("#aaaaaa"),.15,Qt.PenStyle.DashLine))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRect(QRectF(-project.hoop_width/2,-project.hoop_height/2,project.hoop_width,project.hoop_height))
    if stitches:
        for block in blocks:
            path = QPainterPath()
            for stitch in block.stitches:
                if stitch.command == "stitch":
                    path.lineTo(stitch.x,stitch.y)
                else:
                    path.moveTo(stitch.x,stitch.y)
            painter.setPen(QPen(ink(block.color),.15))
            painter.drawPath(path)
    else:
        for obj in project.objects:
            if not obj.visible:
                continue
            if obj.kind == "stitches":
                # Manual designs have no source outline: retain their sewn paths.
                path = QPainterPath()
                for block in blocks:
                    if block.object_id == obj.id:
                        for stitch in block.stitches:
                            if stitch.command == "stitch":
                                path.lineTo(stitch.x,stitch.y)
                            else:
                                path.moveTo(stitch.x,stitch.y)
            else:
                path = Canvas.outline_path(obj)
            painter.setPen(QPen(ink(obj.color),.25))
            painter.drawPath(path)
    painter.setPen(QPen(QColor("#202020"),.2))
    for x,y in [(0,0), *registration_marks(plan)]:
        painter.drawLine(QPointF(x-3,y),QPointF(x+3,y))
        painter.drawLine(QPointF(x,y-3),QPointF(x,y+3))
    painter.restore()
    painter.setPen(QPen(QColor("#777777"),.15,Qt.PenStyle.DotLine))
    painter.drawRect(frame)
    painter.setPen(QPen(QColor("#202020"),.2))
    y = page_height-18
    painter.drawLine(QPointF(15,y),QPointF(65,y))
    for x in range(15,66,10):
        painter.drawLine(QPointF(x,y-1),QPointF(x,y+1))
    painter.drawText(QPointF(15,y-3),"Scale check: 50 mm")
    painter.drawText(QPointF(75,y),"Print at 100% / Actual size. Disable Fit to page.")
    painter.drawText(QPointF(15,page_height-8),"Match crosses in 10 mm overlaps; trim blank margins. Verify the ruler before placement.")
    painter.drawText(QPointF(15,27),f"{'Generated stitches' if stitches else 'Source outlines'} · light thread colors darkened for print visibility.")


def export_template(project, destination, paper="A4", stitches=True):
    Project.loads(project.dumps())
    blocks = generate(project)
    plan = template_plan(project,blocks,paper)
    destination = Path(destination)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent,suffix=".pdf",delete=False) as stream:
            temporary = Path(stream.name)
        writer = QPdfWriter(str(temporary))
        writer.setResolution(300)
        writer.setPageLayout(QPageLayout(QPageSize(PAPERS[paper][2]),QPageLayout.Orientation.Portrait,QMarginsF(0,0,0,0)))
        writer.setTitle(project.name)
        writer.setCreator("Morale embroidery studio")
        painter = QPainter()
        if not painter.begin(writer):
            raise OSError("Could not create the placement PDF.")
        try:
            for index,(column,row,tile) in enumerate(plan.tiles()):
                if index and not writer.newPage():
                    raise OSError("Could not create a template page.")
                painter.save()
                painter.scale(writer.resolution()/25.4,writer.resolution()/25.4)
                paint_template(painter,project,blocks,plan,column,row,tile,stitches)
                painter.restore()
        finally:
            ended = painter.end()
        del writer
        if not ended or temporary.stat().st_size < 100:
            raise OSError("Placement PDF could not be finalized.")
        os.replace(temporary,destination)
        return plan
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


class TemplateDialog(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export placement template")
        layout = QVBoxLayout(self)
        text = QLabel("Create an actual-size PDF with 10 mm page overlaps and alignment crosses. Print at 100% / Actual size and measure the 50 mm ruler before using it on fabric.")
        text.setWordWrap(True)
        layout.addWidget(text)
        self.paper = QComboBox()
        self.paper.addItems(PAPERS)
        self.paper.setAccessibleName("Template paper size")
        layout.addWidget(self.paper)
        self.stitches = QCheckBox("Show generated stitches (otherwise source outlines)")
        self.stitches.setChecked(True)
        layout.addWidget(self.stitches)
        controls = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        controls.accepted.connect(self.accept)
        controls.rejected.connect(self.reject)
        layout.addWidget(controls)
        self.resize(440,220)
