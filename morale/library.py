"""Native folder browsing with one cancellable preview subprocess."""
import json
import math
from pathlib import Path
import sys
import tempfile

from PySide6.QtCore import QObject,Signal,QProcess,QProcessEnvironment,QTimer,QDir,QSortFilterProxyModel,Qt,QSize
from PySide6.QtGui import QImage,QPixmap,QImageReader
from PySide6.QtWidgets import QFileSystemModel,QDialog,QVBoxLayout,QHBoxLayout,QPushButton,QLabel,QLineEdit,QTreeView,QFileDialog,QSplitter,QWidget,QStackedWidget,QListWidget,QAbstractItemView

from .formats import IMPORT_FORMATS


def read_preview_result(root):
    """Validate shared worker output before any desktop consumer sees it."""
    root=Path(root);metadata=root/'preview.json';picture=root/'preview.png'
    if metadata.stat().st_size>64_000_000:raise ValueError('Preview metadata exceeds 64 MB.')
    try:info=json.loads(metadata.read_text(encoding='utf-8'))
    except RecursionError as exc:raise ValueError('Preview metadata nesting exceeds the supported limit.') from exc
    if not isinstance(info,dict):raise ValueError('Preview metadata must be an object.')
    if not isinstance(info.get('name'),str) or len(info['name'])>200:raise ValueError('Invalid preview name.')
    for key,maximum in [('stitches',250_000),('colors',500)]:
        value=info.get(key)
        if type(value) is not int or not 0<=value<=maximum:raise ValueError(f'Invalid preview {key}.')
    for key in ('width','height'):
        value=info.get(key)
        if isinstance(value,bool) or not isinstance(value,(int,float)) or value<0 or value>20_000 or not math.isfinite(value):raise ValueError(f'Invalid preview {key}.')
    if type(info.get('size')) is not int or info['size']<0 or type(info.get('mtime_ns')) is not int:raise ValueError('Invalid preview file fingerprint.')
    notes=info.get('notes')
    if not isinstance(notes,list) or len(notes)>10_000 or any(not isinstance(note,str) or len(note)>8192 for note in notes):raise ValueError('Invalid preview notes.')
    if picture.stat().st_size>8_000_000:raise ValueError('Preview image exceeds 8 MB.')
    reader=QImageReader(str(picture));size=reader.size()
    if reader.format()!=b'png' or not 1<=size.width()<=2048 or not 1<=size.height()<=2048:
        raise ValueError('Preview must be a PNG image no larger than 2048 × 2048 pixels.')
    image=reader.read()
    if image.isNull():raise ValueError('Preview image could not be decoded.')
    return info,image


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

    def read_result(self,root):
        return read_preview_result(root)

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
            info,image=self.read_result(root)
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


class SearchRunner(PreviewRunner):
    found=Signal(object)

    def timeout(self):
        path=self.path;self.cancel()
        if path:self.failed.emit(path,'Folder search timed out. Choose a smaller folder and search again.')

    def command(self,path,directory):
        if getattr(sys,'frozen',False):return sys.executable,['--library-search-worker',path,directory,self.query]
        return sys.executable,['-m','morale.library_search',path,directory,self.query]

    def finished(self,code,status):
        self.timer.stop()
        if self.path is None:return
        path=self.path;self.path=None
        try:
            self.read_output();root=Path(self.directory.name)
            if code:
                error=root/'search.error.json'
                raise ValueError(json.loads(error.read_text()).get('error','Search failed.') if error.exists() else 'Search process failed.')
            result_path=root/'search.json'
            if result_path.stat().st_size>5_000_000:raise ValueError('Search results exceeded the size limit.')
            result=json.loads(result_path.read_text(encoding='utf-8'))
            if result['root']!=path or len(result['matches'])>5000:raise ValueError('Invalid search results.')
            self.found.emit(result)
        except (OSError,ValueError,KeyError,TypeError) as exc:self.failed.emit(path,str(exc))
        finally:self.clean()


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
        self.search_runner=SearchRunner(self)
        self.search_runner.found.connect(self.show_search)
        self.search_runner.failed.connect(self.search_failed)
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
        self.search.setPlaceholderText('Filter filenames, or search subfolders by relative path')
        self.search.setAccessibleName('Search design filenames')
        layout.addWidget(self.search)
        search_row=QHBoxLayout()
        self.find_button=QPushButton('Search subfolders');self.find_button.clicked.connect(self.search_subfolders);search_row.addWidget(self.find_button)
        cancel_search=QPushButton('Cancel search');cancel_search.clicked.connect(self.cancel_search);search_row.addWidget(cancel_search)
        browse=QPushButton('Folder view');browse.clicked.connect(self.folder_view);search_row.addWidget(browse)
        self.thumbnail_button=QPushButton('Thumbnails');self.thumbnail_button.setCheckable(True)
        self.thumbnail_button.setToolTip('Load up to 200 visible search-result thumbnails in a separate decoder. Scroll to load more; switch off to cancel.')
        self.thumbnail_button.toggled.connect(self.set_thumbnail_view);search_row.addWidget(self.thumbnail_button)
        self.catalog_results_button=QPushButton("Catalog results…");self.catalog_results_button.clicked.connect(self.catalog_results)
        self.catalog_results_button.setToolTip("Catalog selected results, or all results when none are selected. Up to 100 designs; clear the selection to include the whole result list.")
        search_row.addWidget(self.catalog_results_button)
        layout.addLayout(search_row)
        self.search_status=QLabel();self.search_status.setWordWrap(True);self.search_status.setTextFormat(Qt.TextFormat.PlainText);layout.addWidget(self.search_status)
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
        self.file_views=QStackedWidget();self.file_views.addWidget(self.tree)
        self.results=QListWidget();self.results.setAccessibleName('Designs found in subfolders')
        self.results.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.results.itemSelectionChanged.connect(lambda:self.catalog_results_button.setText(f'Catalog selection ({len(self.results.selectedItems())})…' if self.results.selectedItems() else 'Catalog results…'))
        self.results.currentTextChanged.connect(self.search_selection_changed)
        self.results.itemDoubleClicked.connect(self.open_selected)
        self.file_views.addWidget(self.results);split.addWidget(self.file_views)
        from .library_thumbnails import ThumbnailLoader
        self.thumbnails=ThumbnailLoader(self.results,self)
        panel=QWidget()
        right=QVBoxLayout(panel)
        self.image=QLabel('Select a design to preview')
        self.image.setMinimumSize(360,360)
        self.image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image.setAccessibleName('Selected design preview')
        right.addWidget(self.image)
        self.details=QLabel('Previews run separately, with a 30-second limit. Enable thumbnails to preview visible search results.')
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
        refresh.clicked.connect(self.refresh_preview)
        buttons.addWidget(refresh)
        catalog=QPushButton("Create PDF catalog…");catalog.clicked.connect(self.create_catalog);buttons.addWidget(catalog)
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

    def create_catalog(self):
        paths,_=QFileDialog.getOpenFileNames(self,'Choose designs for catalog',self.folder,
            'Embroidery designs ('+' '.join(['*.morale',*[f'*{ext}' for ext in sorted(IMPORT_FORMATS)]])+')')
        if not paths:return
        self.open_catalog(paths)

    def catalog_results(self):
        if self.file_views.currentIndex()!=1 or self.results.count()==0:
            self.search_status.setText('Search subfolders to find designs for a catalog.');return
        rows=sorted(self.results.row(item) for item in self.results.selectedItems())
        if not rows:rows=list(range(self.results.count()))
        if len(rows)>100:
            self.search_status.setText(f'{len(rows)} designs exceed the 100-design catalog limit. Narrow the search or select up to 100 results.');return
        paths=[str(Path(self.folder)/self.results.item(i).text()) for i in rows]
        self.open_catalog(paths)

    def open_catalog(self,paths):
        from .library_catalog import CatalogDialog
        try:dialog=CatalogDialog(paths,self)
        except ValueError as exc:
            self.details.setText(str(exc));return
        dialog.exec()

    def set_folder(self,folder):
        self.thumbnails.reset(folder)
        self.search_runner.cancel();self.results.clear();self.file_views.setCurrentIndex(0);self.search_status.clear()
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
        if self.file_views.currentIndex()!=0:return
        self.cancel_preview()
        source=self.proxy.mapToSource(index)
        if source.isValid() and not self.model.isDir(source):
            path=self.model.filePath(source)
            self.details.setText(f'Loading {Path(path).name}…')
            self.runner.load(path)

    def search_subfolders(self):
        query=self.search.text().strip()
        if not query or len(query)>200:
            self.search_status.setText('Enter 1–200 characters to search filenames and relative paths.');return
        self.cancel_preview();self.thumbnails.reset(self.folder);self.results.clear();self.file_views.setCurrentIndex(1)
        self.search_runner.query=query;self.search_runner.load(self.folder)
        self.search_status.setText('Searching subfolders… File contents are not decoded.')

    def show_search(self,result):
        if result['root']!=self.folder:return
        self.results.addItems(result['matches'])
        self.thumbnails.schedule()
        suffix=' Search limit reached; narrow the query or folder.' if not result['complete'] else ''
        self.search_status.setText(f"{len(result['matches'])} designs found for “{result['query']}”; {result['entries_examined']} entries examined; {result['unreadable_entries']} unreadable entries.{suffix}")

    def search_failed(self,path,message):self.search_status.setText(message)

    def cancel_search(self):
        self.search_runner.cancel();self.search_status.setText('Search cancelled.')

    def folder_view(self):
        self.thumbnails.stop()
        self.search_runner.cancel();self.cancel_preview();self.file_views.setCurrentIndex(0);self.search_status.clear()

    def set_thumbnail_view(self,enabled):
        self.results.setViewMode(QListWidget.ViewMode.IconMode if enabled else QListWidget.ViewMode.ListMode)
        self.results.setMovement(QListWidget.Movement.Static)
        self.results.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.results.setIconSize(QSize(128,128) if enabled else QSize(16,16))
        self.results.setGridSize(QSize(170,175) if enabled else QSize())
        self.results.setWordWrap(enabled)
        self.thumbnails.set_enabled(enabled)

    def search_selection_changed(self,relative):
        self.cancel_preview()
        if relative and self.file_views.currentIndex()==1:self.runner.load(str(Path(self.folder)/relative))

    def refresh_preview(self):
        if self.file_views.currentIndex()==1:
            self.thumbnails.cache.pop(self.results.currentRow(),None);self.thumbnails.schedule()
            item=self.results.currentItem();self.search_selection_changed(item.text() if item else '')
        else:self.selection_changed(self.tree.currentIndex(),None)

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
        self.thumbnails.stop()
        self.search_runner.cancel()
        self.runner.cancel()
        super().done(result)

    def reject(self):
        self.thumbnails.stop()
        self.search_runner.cancel()
        self.runner.cancel()
        super().reject()

    def accept(self):
        self.thumbnails.stop()
        self.search_runner.cancel()
        self.runner.cancel()
        super().accept()

    def closeEvent(self,event):
        self.thumbnails.stop()
        self.search_runner.cancel()
        self.runner.cancel()
        super().closeEvent(event)

    def close(self):
        self.thumbnails.stop()
        self.search_runner.cancel()
        self.runner.cancel()
        return super().close()
