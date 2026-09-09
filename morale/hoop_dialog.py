"""Cancellable multi-hoop planning and exclusive ZIP bundle export."""
import json
from pathlib import Path
import sys
import tempfile
from PySide6.QtCore import Qt,QProcess,QProcessEnvironment,QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QFormLayout,QDoubleSpinBox,QCheckBox,QComboBox,QLabel,QPushButton,QDialogButtonBox,QListWidget,QFileDialog,QMessageBox
from .formats import EXPORT_FORMATS
from .hoop_bundle import save_archive


class HoopDialog(QDialog):
    def __init__(self,project,parent=None):
        super().__init__(parent)
        self.source=project.dumps(); self.directory=None; self.manifest=None
        self.setWindowTitle('Split design for multiple hoopings'); self.resize(760,820)
        layout=QVBoxLayout(self)
        note=QLabel('Divide the design into overlapping hoop placements with nonoverlapping sewn areas. Seams add needle points; travel is regenerated. Review the map and each tile before sewing. Alignment crosses are temporary and require physical alignment checks. The current design stays intact.')
        note.setWordWrap(True); layout.addWidget(note)
        form=QFormLayout()
        self.width=QDoubleSpinBox(); self.height=QDoubleSpinBox(); self.margin=QDoubleSpinBox()
        for widget,title,value,low,high in ((self.width,'Hoop width',project.hoop_width,20,500),(self.height,'Hoop height',project.hoop_height,20,500),(self.margin,'Margin on each side',8,4,30)):
            widget.setRange(low,high); widget.setValue(value); widget.setSuffix(' mm'); widget.setAccessibleName(title); form.addRow(title,widget)
        self.registration=QCheckBox('Add paired removable alignment crosses'); self.registration.setChecked(True); form.addRow(self.registration)
        self.extension=QComboBox(); self.extension.addItem('Native projects only','')
        for extension in sorted(EXPORT_FORMATS): self.extension.addItem(extension[1:].upper(),extension)
        self.extension.setAccessibleName('Optional machine file format'); form.addRow('Also export machine files',self.extension)
        layout.addLayout(form)
        row=QHBoxLayout(); self.generate_button=QPushButton('Generate placement plan'); self.generate_button.clicked.connect(self.generate)
        cancel=QPushButton('Cancel generation'); cancel.clicked.connect(self.invalidate)
        row.addWidget(self.generate_button); row.addWidget(cancel); layout.addLayout(row)
        self.preview=QLabel('Generate a plan to review the placement map.'); self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter); self.preview.setMinimumSize(400,330); layout.addWidget(self.preview,1)
        self.tiles=QListWidget(); self.tiles.setMaximumHeight(120); self.tiles.setAccessibleName('Hoop placements and center coordinates'); layout.addWidget(self.tiles)
        self.status=QLabel('Planning runs in a separate process with a 60-second limit.'); self.status.setWordWrap(True); self.status.setTextFormat(Qt.TextFormat.PlainText); layout.addWidget(self.status)
        self.save_button=QPushButton('Save reviewed bundle (ZIP)…'); self.save_button.setEnabled(False); self.save_button.clicked.connect(self.save); layout.addWidget(self.save_button)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Close); buttons.rejected.connect(self.reject); layout.addWidget(buttons)
        self.process=QProcess(self); self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.finished.connect(self.worker_finished); self.process.errorOccurred.connect(self.process_error)
        self.timer=QTimer(self); self.timer.setSingleShot(True); self.timer.setInterval(60_000); self.timer.timeout.connect(self.timeout)
        for widget in (self.width,self.height,self.margin): widget.valueChanged.connect(self.invalidate)
        self.registration.toggled.connect(self.invalidate); self.extension.currentIndexChanged.connect(self.invalidate)

    def cleanup(self):
        self.timer.stop()
        if self.process.state()!=QProcess.ProcessState.NotRunning:
            self.process.kill(); self.process.waitForFinished(1000)
        if self.directory: self.directory.cleanup(); self.directory=None

    def invalidate(self,*args):
        self.manifest=None; self.save_button.setEnabled(False)
        self.cleanup(); self.tiles.clear(); self.preview.setText('Generate a new plan.'); self.status.setText('Plan invalidated or generation cancelled.')

    def generate(self):
        self.invalidate(); self.directory=tempfile.TemporaryDirectory(prefix='morale-hoops-')
        root=Path(self.directory.name); source=root/'input.morale'; source.write_text(self.source,encoding='utf-8')
        options={'width':self.width.value(),'height':self.height.value(),'margin':self.margin.value(),'registration':self.registration.isChecked(),'extension':self.extension.currentData()}
        args=[str(source),str(root),json.dumps(options)]
        command=['--hoop-worker',*args] if getattr(sys,'frozen',False) else ['-m','morale.hoop_bundle','--worker',*args]
        environment=QProcessEnvironment.systemEnvironment(); environment.insert('QT_QPA_PLATFORM','offscreen'); self.process.setProcessEnvironment(environment)
        self.status.setText('Generating tiles, alignment marks and placement map…'); self.process.start(sys.executable,command)
        if self.directory is not None: self.timer.start()

    def worker_finished(self,code,status):
        self.timer.stop()
        if self.directory is None: return
        root=Path(self.directory.name)
        try:
            if code!=0:
                error=root/'error.json'
                message=json.loads(error.read_text(encoding='utf-8'))['error'] if error.exists() else 'The planning process failed.'
                raise ValueError(message)
            self.manifest=json.loads((root/'bundle'/'plan.json').read_text(encoding='utf-8'))
            image=QPixmap(str(root/'bundle'/'placement.png'))
            if image.isNull(): raise ValueError('Could not read the placement preview.')
            self.preview.setPixmap(image.scaled(700,400,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
            for tile in self.manifest['tiles']:
                self.tiles.addItem(f"{tile['id']} · center {tile['center'][0]:.3f}, {tile['center'][1]:.3f} mm · {tile['stitches']:,} stitches")
            self.status.setText(f"{len(self.manifest['tiles'])} placements. Bundle includes the source, tile projects, placement PDF/PNG, alignment coordinates and instructions. Review exported machine travel and seam starts/ends; no seam tie stitches are added.")
            self.save_button.setEnabled(True)
        except (OSError,ValueError,KeyError) as exc:
            self.manifest=None; self.save_button.setEnabled(False); self.status.setText(str(exc))

    def process_error(self,error):
        if error==QProcess.ProcessError.FailedToStart:
            message=self.process.errorString(); self.invalidate(); self.status.setText(message)

    def timeout(self):
        self.invalidate(); self.status.setText('Planning timed out. Simplify the design or use larger hoops.')

    def save(self):
        if self.manifest is None or self.directory is None: return
        path,_=QFileDialog.getSaveFileName(self,'Save new multi-hoop bundle','multihoop-plan.zip','ZIP bundles (*.zip)',options=QFileDialog.Option.DontConfirmOverwrite)
        if path:
            try:
                save_archive(Path(self.directory.name)/'bundle',path)
                self.status.setText(f'Saved bundle: {path}')
            except OSError as exc:
                QMessageBox.warning(self,'Bundle not saved',f'Choose a new filename. Existing files are never overwritten. {exc}')

    def reject(self): self.cleanup(); super().reject()
    def closeEvent(self,event): self.cleanup(); super().closeEvent(event)
    def close(self): self.cleanup(); return super().close()
