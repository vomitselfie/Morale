"""Native route planning with actual generated entry and exit previews."""
from PySide6.QtCore import QPointF,Qt
from PySide6.QtGui import QPainter,QPainterPath,QPen,QColor
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QFormLayout,QComboBox,QCheckBox,QLabel,QPushButton,QDialogButtonBox,QWidget
from .routing import routing_rings,route_object
from .model import Project
from .engine import generate


class RoutePreview(QWidget):
    def __init__(self):
        super().__init__()
        self.stitches=[]
        self.setMinimumSize(380,280)
        self.setAccessibleName('Route preview: entry green, exit red, travel dashed')

    def paintEvent(self,event):
        painter=QPainter(self)
        painter.fillRect(self.rect(),QColor('white'))
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.stitches: return
        xs=[s.x for s in self.stitches]; ys=[s.y for s in self.stitches]
        cx,cy=(min(xs)+max(xs))/2,(min(ys)+max(ys))/2
        scale=min((self.width()-30)/max(.1,max(xs)-min(xs)),(self.height()-30)/max(.1,max(ys)-min(ys)))
        def screen(s): return QPointF(self.width()/2+(s.x-cx)*scale,self.height()/2+(s.y-cy)*scale)
        sewn=QPainterPath(); travel=QPainterPath()
        previous=self.stitches[0]
        for stitch in self.stitches[1:]:
            if stitch.command in {'stitch','jump'}:
                path=sewn if stitch.command=='stitch' else travel
                path.moveTo(screen(previous)); path.lineTo(screen(stitch))
            previous=stitch
        painter.setPen(QPen(QColor('#bcc4c0'),1,Qt.PenStyle.DashLine)); painter.drawPath(travel)
        painter.setPen(QPen(QColor('#405d50'),1)); painter.drawPath(sewn)
        motions=[s for s in self.stitches if s.command in {'stitch','jump'}]
        if motions:
            painter.setPen(QPen(QColor('#16803a'),2)); painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(screen(motions[0]),7,7)
            painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(QColor('#c53838'))
            painter.drawEllipse(screen(motions[-1]),3,3)


class RoutingDialog(QDialog):
    def __init__(self,source,parent=None):
        rings=routing_rings(source)
        super().__init__(parent)
        self.source=source
        self.rings=rings
        self.plan=[(i,0,False) for i in range(len(self.rings))]
        self.candidate=None
        self.setWindowTitle('Path start and direction')
        layout=QVBoxLayout(self)
        note=QLabel('Choose contour order, starting anchor and sewing direction. Open paths and satin columns can change ends. Green ring marks generated entry; red dot marks exit. Satin underlay and finishing stitches are included. Changing lettering routes converts text to editable contours.')
        note.setWordWrap(True); layout.addWidget(note)
        form=QFormLayout()
        self.contour=QComboBox(); self.contour.setAccessibleName('Contour in sewing order')
        self.start=QComboBox(); self.start.setAccessibleName('Starting anchor')
        self.reverse=QCheckBox('Reverse direction')
        form.addRow('Contour',self.contour); form.addRow('Start',self.start); form.addRow(self.reverse)
        layout.addLayout(form)
        row=QHBoxLayout()
        for title,delta in [('Sew contour earlier',-1),('Sew contour later',1)]:
            button=QPushButton(title); button.setEnabled(len(self.rings)>1)
            button.clicked.connect(lambda checked=False,delta=delta:self.move(delta)); row.addWidget(button)
        layout.addLayout(row)
        self.preview=RoutePreview(); layout.addWidget(self.preview,1)
        self.status=QLabel(); self.status.setWordWrap(True); self.status.setTextFormat(Qt.TextFormat.PlainText); layout.addWidget(self.status)
        self.buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept); self.buttons.rejected.connect(self.reject); layout.addWidget(self.buttons)
        self.contour.currentIndexChanged.connect(self.select_contour)
        self.start.currentIndexChanged.connect(self.changed)
        self.reverse.toggled.connect(self.changed)
        self.reload(0)
        self.resize(580,620)

    def reload(self,index):
        self.contour.blockSignals(True); self.contour.clear()
        for ring,_,_ in self.plan: self.contour.addItem(f'Contour {ring+1}')
        self.contour.setCurrentIndex(index); self.contour.blockSignals(False)
        self.select_contour(index)

    def select_contour(self,index):
        ring,start,reverse=self.plan[index]
        self.start.blockSignals(True); self.reverse.blockSignals(True)
        self.start.clear()
        points=self.source.transform(self.rings[ring])
        if self.source.kind in {'path','satin'}:
            self.start.addItem('Endpoint (change with Reverse direction)')
            self.start.setEnabled(False)
        else:
            for i,(x,y) in enumerate(points): self.start.addItem(f'{i+1}: {x:.2f}, {y:.2f} mm')
        self.start.setCurrentIndex(start); self.reverse.setChecked(reverse)
        self.start.blockSignals(False); self.reverse.blockSignals(False)
        self.refresh()

    def changed(self,*args):
        index=self.contour.currentIndex()
        self.plan[index]=(self.plan[index][0],self.start.currentIndex(),self.reverse.isChecked())
        self.refresh()

    def move(self,delta):
        index=self.contour.currentIndex(); target=index+delta
        if 0<=target<len(self.plan):
            self.plan[index],self.plan[target]=self.plan[target],self.plan[index]
            self.reload(target)

    def refresh(self):
        try:
            self.candidate=route_object(self.source,self.plan)
            stitches=generate(Project(objects=[self.candidate]))
            self.preview.stitches=[s for b in stitches for s in b.stitches]
            motions=[s for s in self.preview.stitches if s.command in {'stitch','jump'}]
            self.status.setText(f'Entry: {motions[0].x:.2f}, {motions[0].y:.2f} mm · Exit: {motions[-1].x:.2f}, {motions[-1].y:.2f} mm' if motions else 'No visible stitches.')
        except ValueError as exc:
            self.candidate=None; self.preview.stitches=[]; self.status.setText(str(exc))
        self.preview.update()
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(self.candidate is not None)

    def accept(self):
        if self.candidate is not None: super().accept()
