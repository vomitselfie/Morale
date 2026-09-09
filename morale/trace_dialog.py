"""Preview raster digitizing in a cancellable subprocess before applying it."""
import base64
import json
import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage,QPixmap
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QFormLayout,QLabel,QSpinBox,QDoubleSpinBox,QComboBox,QCheckBox,QPushButton,QDialogButtonBox

from .library import PreviewRunner
from .model import Project


class TraceRunner(PreviewRunner):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.options={}

    def command(self,path,directory):
        args=[path,directory,json.dumps(self.options)]
        return (sys.executable,['--trace-worker',*args]) if getattr(sys,'frozen',False) else (sys.executable,['-m','morale.raster_trace','--worker',*args])


class TraceDialog(QDialog):
    def __init__(self,path,parent=None):
        super().__init__(parent)
        self.path=path
        self.project=None
        self.runner=TraceRunner(self)
        self.runner.ready.connect(self.ready)
        self.runner.failed.connect(self.failed)
        self.setWindowTitle('Digitize raster artwork')
        layout=QVBoxLayout(self)
        text=QLabel('Reduce raster artwork to solid-color regions and editable fill outlines. Preview and correct the result before sewing. Flat artwork is the starting use case; photographic detail and automatic satin/running-stitch inference remain in development.')
        text.setWordWrap(True)
        layout.addWidget(text)
        form=QFormLayout()
        self.width=QDoubleSpinBox()
        self.width.setRange(1,300)
        self.width.setValue(80)
        self.width.setSuffix(' mm')
        self.width.setAccessibleName('Traced artwork width')
        form.addRow('Artwork width',self.width)
        self.colors=QSpinBox()
        self.colors.setRange(1,16)
        self.colors.setValue(6)
        self.colors.setAccessibleName('Maximum trace colors')
        form.addRow('Maximum colors',self.colors)
        self.resolution=QComboBox()
        for size in (64,128,256): self.resolution.addItem(f'{size} pixels',size)
        self.resolution.setCurrentIndex(1)
        self.resolution.setAccessibleName('Trace sampling resolution')
        form.addRow('Longest sampled side',self.resolution)
        self.minimum=QSpinBox()
        self.minimum.setRange(1,100)
        self.minimum.setValue(4)
        self.minimum.setAccessibleName('Minimum region pixels')
        form.addRow('Omit regions below (pixels)',self.minimum)
        self.white=QCheckBox('Exclude near-white background')
        self.white.setChecked(True)
        form.addRow(self.white)
        layout.addLayout(form)
        images=QHBoxLayout()
        self.original=QLabel('Sampled source')
        self.preview=QLabel('Generated stitch preview')
        for label in (self.original,self.preview):
            label.setMinimumSize(320,320)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            images.addWidget(label)
        layout.addLayout(images,1)
        self.status=QLabel('Generate a preview. Changing settings invalidates the previous result. Each worker has a 30-second limit.')
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.status)
        row=QHBoxLayout()
        generate=QPushButton('Generate preview')
        generate.clicked.connect(self.generate)
        row.addWidget(generate)
        stop=QPushButton('Cancel tracing')
        stop.clicked.connect(self.invalidate)
        row.addWidget(stop)
        self.buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText('Add traced objects')
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        row.addWidget(self.buttons)
        layout.addLayout(row)
        for widget in (self.width,self.colors,self.minimum): widget.valueChanged.connect(self.invalidate)
        self.resolution.currentIndexChanged.connect(self.invalidate)
        self.white.toggled.connect(self.invalidate)
        self.resize(820,780)

    def invalidate(self,*args):
        self.runner.cancel()
        self.project=None
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        self.preview.setText('Generate a new preview')
        self.status.setText('Preview invalidated or tracing cancelled. Generate a preview to apply these settings.')

    def generate(self):
        self.invalidate()
        self.runner.options={'width':self.width.value(),'colors':self.colors.value(),'resolution':self.resolution.currentData(),
                             'ignore_white':self.white.isChecked(),'minimum_region':self.minimum.value()}
        self.status.setText('Tracing in a separate process…')
        self.runner.load(self.path)

    def ready(self,path,info,image):
        try:
            self.project=Project.loads(info['project'])
            original=QImage.fromData(base64.b64decode(info['raster_png']))
            if original.isNull(): raise ValueError('The sampled source preview is damaged.')
            self.original.setPixmap(QPixmap.fromImage(original).scaled(320,320,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.FastTransformation))
            self.preview.setPixmap(QPixmap.fromImage(image).scaled(320,320,Qt.AspectRatioMode.KeepAspectRatio))
            stats=info['trace_stats']
            self.status.setText(f"{len(self.project.objects)} editable color objects · {info['stitches']:,} stitches · {stats['resolution'][0]} × {stats['resolution'][1]} sampled pixels · {stats['omitted_pixels']} small-region pixels omitted. Pixel boundaries can be stair-stepped; edit contours after adding.")
            self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)
        except (KeyError,ValueError) as exc:
            self.failed(path,str(exc))

    def failed(self,path,message):
        self.project=None
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        self.status.setText(message)

    def accept(self):
        if self.project is not None:
            self.runner.cancel()
            super().accept()

    def reject(self):
        self.runner.cancel()
        super().reject()

    def closeEvent(self,event):
        self.runner.cancel()
        super().closeEvent(event)

    def close(self):
        self.runner.cancel()
        return super().close()
