"""Compare source commands with a decoded file without inventing alignment."""
from collections import Counter
import math
from pathlib import Path

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QPainter, QPainterPath, QPen, QColor
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QCheckBox, QPushButton, QDialogButtonBox, QWidget, QHeaderView

from .engine import generate
from .formats import import_machine
from .threads import thread_key, usage


def command_metrics(blocks):
    commands=[s for b in blocks for s in b.stitches]
    counts=Counter(s.command for s in commands)
    sewn=[s for s in commands if s.command=='stitch']
    bounds=(min(s.x for s in sewn),min(s.y for s in sewn),max(s.x for s in sewn),max(s.y for s in sewn)) if sewn else None
    colors=[]
    prior=None
    for block in blocks:
        if not block.stitches:
            continue
        key=thread_key(block)
        if key!=prior or block.color_break:
            colors.append(block.color.lower())
        prior=key
    lengths=usage(blocks)
    return {'counts':dict(counts),'sewn_bounds_mm':bounds,'thread_rgb':colors,
            'sewn_path_m':sum(r['sewn_m'] for r in lengths),'travel_path_m':sum(r['travel_m'] for r in lengths)}


def compare_commands(source,decoded):
    a=[s for b in source for s in b.stitches]
    b=[s for block in decoded for s in block.stitches]
    same=len(a)==len(b) and all(x.command==y.command for x,y in zip(a,b))
    return {'source':command_metrics(source),'decoded':command_metrics(decoded),
            'same_command_sequence':same,
            'maximum_indexed_displacement_mm':max((math.dist((x.x,x.y),(y.x,y.y)) for x,y in zip(a,b)),default=0) if same else None}


def load_comparison(project,path):
    source=generate(project)
    imported=import_machine(path)
    decoded=generate(imported.project)
    return source,decoded,compare_commands(source,decoded),imported.notes


def command_paths(blocks):
    sewn,travel=QPainterPath(),QPainterPath()
    previous=(0.,0.)
    for block in blocks:
        for stitch in block.stitches:
            point=(stitch.x,stitch.y)
            if stitch.command in {'stitch','jump'}:
                path=sewn if stitch.command=='stitch' else travel
                path.moveTo(*previous)
                path.lineTo(*point)
                previous=point
    return sewn,travel


class ComparisonView(QWidget):
    def __init__(self,source,decoded):
        super().__init__()
        self.setMinimumSize(420,320)
        self.setAccessibleName('Source and decoded command overlay; green source, purple decoded')
        self.paths=[command_paths(source),command_paths(decoded)]
        self.visible=[True,True]
        self.travel=False
        self.scale=5
        self.pan=QPointF()
        self.dragging=None
        rects=[path.boundingRect() for pair in self.paths for path in pair if not path.isEmpty()]
        left,top=min((r.left() for r in rects),default=0),min((r.top() for r in rects),default=0)
        right,bottom=max((r.right() for r in rects),default=0),max((r.bottom() for r in rects),default=0)
        bounds=QRectF(left,top,right-left,bottom-top)
        self.bounds=bounds.adjusted(-3,-3,3,3)
        self.center=self.bounds.center()

    def fit(self):
        self.scale=min((self.width()-40)/max(1,self.bounds.width()),(self.height()-40)/max(1,self.bounds.height()))
        self.pan=QPointF()
        self.update()

    def paintEvent(self,event):
        painter=QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(),QColor('#fffdf8'))
        painter.translate(self.width()/2+self.pan.x(),self.height()/2+self.pan.y())
        painter.scale(self.scale,self.scale)
        painter.translate(-self.center)
        for index,(sewn,travel) in enumerate(self.paths):
            if not self.visible[index]:
                continue
            color=QColor('#23815c' if index==0 else '#9d3eac')
            color.setAlpha(190)
            painter.setPen(QPen(color,1.5/self.scale))
            painter.drawPath(sewn)
            if self.travel:
                painter.setPen(QPen(color,1/self.scale,Qt.PenStyle.DashLine))
                painter.drawPath(travel)

    def wheelEvent(self,event):
        origin=QPointF(self.width()/2,self.height()/2)
        before=(event.position()-origin-self.pan)/self.scale
        self.scale=max(.1,min(100,self.scale*(1.15 if event.angleDelta().y()>0 else 1/1.15)))
        self.pan=event.position()-origin-before*self.scale
        self.update()

    def mousePressEvent(self,event):
        if event.button() in {Qt.MouseButton.LeftButton,Qt.MouseButton.MiddleButton}:
            self.dragging=event.position()

    def mouseMoveEvent(self,event):
        if self.dragging is not None:
            self.pan+=event.position()-self.dragging
            self.dragging=event.position()
            self.update()

    def mouseReleaseEvent(self,event):
        self.dragging=None


class ComparisonDialog(QDialog):
    def __init__(self,project,path,parent=None):
        source,decoded,report,notices=load_comparison(project,path)
        super().__init__(parent)
        self.report=report
        self.setWindowTitle(f"Compare machine file — {Path(path).name}")
        layout=QVBoxLayout(self)
        text=QLabel('Green: current design · Purple: decoded machine file. Coordinates remain in their original positions; no automatic alignment. Drag to pan, scroll to zoom.')
        text.setWordWrap(True)
        layout.addWidget(text)
        self.view=ComparisonView(source,decoded)
        layout.addWidget(self.view,1)
        controls=QHBoxLayout()
        self.source_toggle=QCheckBox('Current design')
        self.decoded_toggle=QCheckBox('Decoded file')
        self.travel_toggle=QCheckBox('Travel paths')
        for index,toggle in enumerate([self.source_toggle,self.decoded_toggle]):
            toggle.setChecked(True)
            toggle.toggled.connect(lambda checked,i=index:self.set_visible(i,checked))
            controls.addWidget(toggle)
        self.travel_toggle.toggled.connect(self.set_travel)
        controls.addWidget(self.travel_toggle)
        fit=QPushButton('Fit both')
        fit.clicked.connect(self.view.fit)
        controls.addWidget(fit)
        layout.addLayout(controls)
        rows=[]
        a,b=self.report['source'],self.report['decoded']
        for command in ['stitch','jump','trim','stop']:
            rows.append((command.title()+' commands',str(a['counts'].get(command,0)),str(b['counts'].get(command,0))))
        for label,key in [('Thread runs','thread_rgb'),('Sewn path (m)','sewn_path_m'),('Travel path (m)','travel_path_m'),('Sewn-point bounds (mm)','sewn_bounds_mm')]:
            def display(value):
                if key=='thread_rgb':
                    return str(len(value))
                if key=='sewn_bounds_mm':
                    return ', '.join(f'{v:.2f}' for v in value) if value else 'No sewn points'
                return f'{value:.4f}'
            rows.append((label,display(a[key]),display(b[key])))
        self.table=QTableWidget(len(rows),3)
        self.table.setHorizontalHeaderLabels(['Metric','Current design','Decoded file'])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAccessibleName('Command comparison metrics')
        for r,row in enumerate(rows):
            for c,value in enumerate(row):
                self.table.setItem(r,c,QTableWidgetItem(value))
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setMaximumHeight(255)
        layout.addWidget(self.table)
        delta=self.report['maximum_indexed_displacement_mm']
        comparison=f'Command types and counts match. Maximum point-by-point difference: {delta:.4f} mm.' if delta is not None else 'Command sequences differ; point-by-point differences are not calculated.'
        note=QLabel(comparison+f" Thread RGB order: {'same' if a['thread_rgb']==b['thread_rgb'] else 'different'}.\nMatching metrics do not establish equivalent sewing. Writers and readers can normalize controls, colors, and travel. Physical machine behavior remains unverified.")
        note.setWordWrap(True)
        layout.addWidget(note)
        self.setToolTip('\n'.join(notices))
        close=QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(self.reject)
        layout.addWidget(close)
        self.resize(900,850)

    def showEvent(self,event):
        super().showEvent(event)
        self.view.fit()

    def set_visible(self,index,checked):
        self.view.visible[index]=checked
        self.view.update()

    def set_travel(self,checked):
        self.view.travel=checked
        self.view.update()
