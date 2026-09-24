"""Native pan, zoom and overlay inspection of aligned conversion images."""
from PySide6.QtCore import Qt,QRectF
from PySide6.QtGui import QPixmap,QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtSvgWidgets import QGraphicsSvgItem
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QComboBox,QSlider,QLabel,QPushButton,QDialogButtonBox,QGraphicsScene,QGraphicsView,QGraphicsOpacityEffect,QCheckBox


class ArtworkCompareDialog(QDialog):
    def __init__(self,panels,parent=None,*,geometry=None):
        super().__init__(parent)
        if set(panels)!={'source','vectors','stitches'} or any(image.isNull() or image.width()!=640 or image.height()!=640 for image in panels.values()):
            raise ValueError('Aligned preview images are missing or damaged.')
        self.panels={key:image.copy() for key,image in panels.items()}
        self.setWindowTitle('Inspect artwork conversion')
        layout=QVBoxLayout(self)
        note=QLabel('Compare at the same scale. Drag to pan; zoom to inspect. Blend vectors or stitches over the sampled source. The dashed border marks the artwork page. Light stitches have a contrast outline.')
        note.setWordWrap(True);layout.addWidget(note)
        controls=QHBoxLayout();self.mode=QComboBox();self.mode.setAccessibleName('Comparison layer')
        for title,key in [('Sampled source','source'),('Traced vectors','vectors'),('Embroidery stitches','stitches')]:self.mode.addItem(title,key)
        controls.addWidget(self.mode)
        controls.addWidget(QLabel('Layer opacity'))
        self.opacity=QSlider(Qt.Orientation.Horizontal);self.opacity.setRange(0,100);self.opacity.setValue(100)
        self.opacity.setAccessibleName('Comparison layer opacity');controls.addWidget(self.opacity,1)
        for title,slot in [('−',self.zoom_out),('+',self.zoom_in),('Fit',self.fit)]:
            button=QPushButton(title);button.setAccessibleName({'−':'Zoom out','+':'Zoom in','Fit':'Fit comparison'}[title]);button.clicked.connect(slot);controls.addWidget(button)
        layout.addLayout(controls)
        self.highlight_long=QCheckBox('Highlight sewn spans longer than 6 mm')
        self.highlight_long.setToolTip('Orange highlights use the conversion review threshold, not a machine or fabric limit. Jumps are excluded.')
        layout.addWidget(self.highlight_long)
        self.scene=QGraphicsScene(self);self.scene.setSceneRect(QRectF(0,0,640,640))
        self.source=self.scene.addPixmap(QPixmap.fromImage(self.panels['source']))
        self.overlay=self.scene.addPixmap(QPixmap.fromImage(self.panels['stitches']))
        self.vector_layers={}
        for key,svg in (geometry or {}).items():
            if key not in {'vectors','stitches','long_spans'}:raise ValueError('Unknown inspection geometry layer.')
            renderer=QSvgRenderer(svg.encode('utf-8'),self)
            if not renderer.isValid() or renderer.viewBoxF()!=QRectF(0,0,640,640):raise ValueError('Invalid inspection geometry.')
            item=QGraphicsSvgItem();item.setSharedRenderer(renderer);item.setCachingEnabled(False)
            effect=QGraphicsOpacityEffect(self);effect.setOpacity(1);item.setGraphicsEffect(effect)
            self.scene.addItem(item);item.setVisible(False);self.vector_layers[key]=item
            if key=='long_spans':item.setZValue(10)
        self.view=QGraphicsView(self.scene);self.view.setAccessibleName('Aligned artwork comparison')
        self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.view.setToolTip('Vector and stitch geometry stays sharp while zooming when available. The sampled source and legacy preview layers retain their image resolution.')
        layout.addWidget(self.view,1)
        close=QDialogButtonBox(QDialogButtonBox.StandardButton.Close);close.rejected.connect(self.reject);layout.addWidget(close)
        self.highlight_long.toggled.connect(self.update_layer)
        self.mode.currentIndexChanged.connect(self.update_layer);self.opacity.valueChanged.connect(self.update_layer)
        self.mode.setCurrentIndex(2);self.resize(820,740);self._first_show=True

    def showEvent(self,event):
        super().showEvent(event)
        if self._first_show:self.fit();self._first_show=False

    def update_layer(self):
        key=self.mode.currentData();self.overlay.setVisible(key!='source' and key not in self.vector_layers);self.opacity.setEnabled(key!='source')
        self.highlight_long.setEnabled(key=='stitches' and 'long_spans' in self.vector_layers)
        for name,item in self.vector_layers.items():
            if name=='long_spans':
                item.setVisible(key=='stitches' and self.highlight_long.isChecked());item.graphicsEffect().setOpacity(1)
            else:item.setVisible(name==key);item.graphicsEffect().setOpacity(self.opacity.value()/100)
        if key!='source':self.overlay.setPixmap(QPixmap.fromImage(self.panels[key]))
        self.overlay.setOpacity(self.opacity.value()/100)

    def fit(self):self.view.fitInView(self.scene.sceneRect(),Qt.AspectRatioMode.KeepAspectRatio)
    def zoom_in(self):
        if self.view.transform().m11()<8:self.view.scale(1.25,1.25)
    def zoom_out(self):
        if self.view.transform().m11()>.1:self.view.scale(.8,.8)
