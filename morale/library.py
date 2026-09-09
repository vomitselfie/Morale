"""Native folder browsing with one cancellable preview subprocess."""
import json
from pathlib import Path
import sys
import tempfile

from PySide6.QtCore import QObject,Signal,QProcess,QProcessEnvironment,QTimer,QDir,QSortFilterProxyModel,Qt
from PySide6.QtGui import QImage,QPixmap
from PySide6.QtWidgets import QFileSystemModel,QDialog,QVBoxLayout,QHBoxLayout,QPushButton,QLabel,QLineEdit,QTreeView,QFileDialog,QSplitter,QWidget

from .formats import IMPORT_FORMATS


class PreviewRunner(QObject):
    ready=Signal(str,object,object)
    failed=Signal(str,str)

    def __init__(self,parent=None,timeout_ms=30000):
        super().__init__(parent)
        self.process=QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.read_output)
        self.process.finished.connect(self.finished)
        self.process.errorOccurred.connect(self.process_error)
        self.timer=QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(timeout_ms)
        self.timer.timeout.connect(self.timeout)
        self.path=None
        self.directory=None
        self.log=b''

    def command(self,path,directory):
        if getattr(sys,'frozen',False):
            return sys.executable,['--preview-worker',path,directory]
        return sys.executable,['-m','morale.preview_worker',path,directory]

    def load(self,path):
        self.cancel()
        self.path=str(Path(path).resolve())
        self.directory=tempfile.TemporaryDirectory(prefix='morale-preview-')
        self.log=b''
        program,args=self.command(self.path,self.directory.name)
        environment=QProcessEnvironment.systemEnvironment()
        environment.insert('QT_QPA_PLATFORM','offscreen')
        self.process.setProcessEnvironment(environment)
        self.process.start(program,args)
        if self.path is not None:
            self.timer.start()

    def read_output(self):
        self.log=(self.log+bytes(self.process.readAllStandardOutput()))[-8192:]

    def clean(self):
        if self.directory:
            self.directory.cleanup()
            self.directory=None

    def cancel(self):
        self.path=None
        self.timer.stop()
        if self.process.state()!=QProcess.ProcessState.NotRunning:
            self.process.kill()
            self.process.waitForFinished(1000)
        self.clean()

    def timeout(self):
        path=self.path
        self.cancel()
        if path:
            self.failed.emit(path,'Preview timed out. The file was not opened.')

    def process_error(self,error):
        if error==QProcess.ProcessError.FailedToStart and self.path:
            path=self.path
            message=self.process.errorString()
            self.cancel()
            self.failed.emit(path,message)

    def finished(self,code,status):
        self.timer.stop()
        if self.path is None:
            return
        path=self.path
        self.path=None
        error=None
        try:
            self.read_output()
            if code!=0:
                error_file=Path(self.directory.name)/'preview.error.json'
                message=self.log.decode('utf-8',errors='replace').strip() or 'Preview process failed.'
                if error_file.exists() and error_file.stat().st_size<=65536:
                    message=json.loads(error_file.read_text(encoding='utf-8')).get('error',message)
                raise ValueError(message)
            root=Path(self.directory.name)
            info=json.loads((root/'preview.json').read_text(encoding='utf-8'))
            image=QImage(str(root/'preview.png'))
            if image.isNull():
                raise ValueError('Preview image could not be decoded.')
        except (OSError,ValueError) as exc:
            error=str(exc)
        finally:
            self.clean()
        if error is None:
            self.ready.emit(path,info,image)
        else:
            self.failed.emit(path,error)


class FileFilter(QSortFilterProxyModel):
    def filterAcceptsRow(self,row,parent):
        index=self.sourceModel().index(row,0,parent)
        return self.sourceModel().isDir(index) or super().filterAcceptsRow(row,parent)


class LibraryDialog(QDialog):
    def __init__(self,parent=None,folder=None):
        super().__init__(parent)
        self.setWindowTitle('Browse embroidery designs')
        self.selected_path=None
        self.preview_path=None
        self.preview_info=None
        self.runner=PreviewRunner(self)
        self.runner.ready.connect(self.show_preview)
        self.runner.failed.connect(self.preview_failed)
        layout=QVBoxLayout(self)
        row=QHBoxLayout()
        self.folder_label=QLabel()
        self.folder_label.setTextFormat(Qt.TextFormat.PlainText)
        self.folder_label.setWordWrap(True)
        row.addWidget(self.folder_label,1)
        choose=QPushButton('Choose folder…')
        choose.clicked.connect(self.choose_folder)
        row.addWidget(choose)
        layout.addLayout(row)
        self.search=QLineEdit()
        self.search.setPlaceholderText('Filter filenames; expand folders to browse')
        self.search.setAccessibleName('Search design filenames')
        layout.addWidget(self.search)
        split=QSplitter()
        self.model=QFileSystemModel(self)
        self.model.setReadOnly(True)
        self.model.setFilter(QDir.Filter.AllDirs|QDir.Filter.Files|QDir.Filter.NoDotAndDotDot)
        self.model.setNameFilters(['*.morale',*[f'*{ext}' for ext in sorted(IMPORT_FORMATS)]])
        self.model.setNameFilterDisables(False)
        self.proxy=FileFilter(self)
        self.proxy.setSourceModel(self.model)
        self.proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.proxy.setFilterKeyColumn(0)
        self.search.textChanged.connect(self.proxy.setFilterFixedString)
        self.tree=QTreeView()
        self.tree.setModel(self.proxy)
        self.tree.setAccessibleName('Embroidery design files and folders')
        self.tree.setColumnWidth(0,280)
        for column in (1,2,3):
            self.tree.hideColumn(column)
        self.tree.selectionModel().currentChanged.connect(self.selection_changed)
        self.tree.doubleClicked.connect(lambda index:self.open_selected() if not self.model.isDir(self.proxy.mapToSource(index)) else None)
        split.addWidget(self.tree)
        panel=QWidget()
        right=QVBoxLayout(panel)
        self.image=QLabel('Select a design to preview')
        self.image.setMinimumSize(360,360)
        self.image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image.setAccessibleName('Selected design preview')
        right.addWidget(self.image)
        self.details=QLabel('Previews run separately, with a 30-second limit. Only the selected file is decoded.')
        self.details.setTextFormat(Qt.TextFormat.PlainText)
        self.details.setWordWrap(True)
        right.addWidget(self.details)
        right.addStretch()
        split.addWidget(panel)
        layout.addWidget(split,1)
        buttons=QHBoxLayout()
        cancel_preview=QPushButton('Cancel preview')
        cancel_preview.clicked.connect(self.cancel_preview)
        buttons.addWidget(cancel_preview)
        refresh=QPushButton('Refresh preview')
        refresh.clicked.connect(lambda:self.selection_changed(self.tree.currentIndex(),None))
        buttons.addWidget(refresh)
        buttons.addStretch()
        self.open_button=QPushButton('Open selected design')
        self.open_button.setEnabled(False)
        self.open_button.clicked.connect(self.open_selected)
        buttons.addWidget(self.open_button)
        close=QPushButton('Close')
        close.clicked.connect(self.reject)
        buttons.addWidget(close)
        layout.addLayout(buttons)
        self.resize(920,650)
        self.set_folder(folder or str(Path.home()))

    def set_folder(self,folder):
        self.cancel_preview()
        self.folder=str(Path(folder).resolve())
        self.folder_label.setText(self.folder)
        self.search.clear()
        index=self.model.setRootPath(self.folder)
        self.tree.setRootIndex(self.proxy.mapFromSource(index))
        self.image.setText('Select a design to preview')
        self.details.setText('Select a Morale project or machine file. Previews run separately, with a 30-second limit.')

    def choose_folder(self):
        folder=QFileDialog.getExistingDirectory(self,'Browse design folder',self.folder)
        if folder:
            self.set_folder(folder)

    def cancel_preview(self):
        self.runner.cancel()
        self.preview_path=None
        self.preview_info=None
        self.open_button.setEnabled(False)
        self.image.clear()
        self.details.setText('Preview cancelled. Select a file to load another preview.')

    def selection_changed(self,index,previous):
        self.cancel_preview()
        source=self.proxy.mapToSource(index)
        if source.isValid() and not self.model.isDir(source):
            path=self.model.filePath(source)
            self.details.setText(f'Loading {Path(path).name}…')
            self.runner.load(path)

    def show_preview(self,path,info,image):
        self.preview_path=path
        self.preview_info=info
        self.image.setPixmap(QPixmap.fromImage(image))
        self.details.setText(f"{info['name']}\n{info['stitches']:,} stitches · {info['colors']} RGB colors\n{info['width']:.1f} × {info['height']:.1f} mm command bounds\n\n"+'\n'.join(info['notes']))
        self.open_button.setEnabled(True)

    def preview_failed(self,path,message):
        self.details.setText(f'{Path(path).name}\n{message}')
        self.open_button.setEnabled(False)

    def open_selected(self):
        if not self.preview_path:
            return
        try:
            current=Path(self.preview_path).stat()
            if (current.st_size,current.st_mtime_ns)!=(self.preview_info['size'],self.preview_info['mtime_ns']):
                raise ValueError('The file changed. Use Refresh preview before opening it.')
            self.selected_path=self.preview_path
            self.accept()
        except (OSError,ValueError) as exc:
            self.details.setText(str(exc))
            self.open_button.setEnabled(False)

    def done(self,result):
        self.runner.cancel()
        super().done(result)

    def reject(self):
        self.runner.cancel()
        super().reject()

    def accept(self):
        self.runner.cancel()
        super().accept()

    def closeEvent(self,event):
        self.runner.cancel()
        super().closeEvent(event)

    def close(self):
        self.runner.cancel()
        return super().close()
