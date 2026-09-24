"""Visible-item thumbnail loading with one isolated decoder and a small cache."""
from collections import OrderedDict
from pathlib import Path
from PySide6.QtCore import QObject,QTimer,QEvent,QSize
from PySide6.QtGui import QIcon,QPixmap
from PySide6.QtWidgets import QStyle


class ThumbnailLoader(QObject):
    def __init__(self,view,parent=None):
        super().__init__(parent)
        from .library import PreviewRunner
        self.view=view;self.root=None;self.enabled=False;self.expected=None;self.cache=OrderedDict()
        self.runner=PreviewRunner(self);self.runner.ready.connect(self.ready);self.runner.failed.connect(self.failed)
        self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.setInterval(40);self.timer.timeout.connect(self.advance)
        view.viewport().installEventFilter(self);view.verticalScrollBar().valueChanged.connect(self.schedule)
        view.horizontalScrollBar().valueChanged.connect(self.schedule)

    def eventFilter(self,watched,event):
        if event.type() in {QEvent.Type.Resize,QEvent.Type.Show}:self.schedule()
        return False

    def schedule(self,*unused):
        if self.enabled:self.timer.start()

    def stop(self):
        self.timer.stop();self.runner.cancel();self.expected=None

    def reset(self,root):
        self.stop();self.root=Path(root).resolve();self.cache.clear();self.schedule()

    def set_enabled(self,enabled):
        self.enabled=enabled
        if enabled:self.schedule()
        else:self.stop()

    def visible_rows(self):
        rectangle=self.view.viewport().rect()
        return [i for i in range(self.view.count()) if self.view.visualItemRect(self.view.item(i)).intersects(rectangle)][:200]

    def advance(self):
        if not self.enabled or not self.view.isVisible() or self.root is None:return
        visible=self.visible_rows()
        if self.expected and self.expected[0] not in visible:self.stop()
        if self.runner.path is not None:return
        for row in visible:
            item=self.view.item(row);path=self.root/item.text()
            try:
                stat=path.stat();stamp=(stat.st_size,stat.st_mtime_ns)
            except OSError:stamp=None
            key=(str(path),stamp)
            if self.cache.get(row)==key:
                self.cache.move_to_end(row);continue
            self.expected=(row,str(path),stamp)
            if stamp is None:self.failed(str(path),'File is no longer available.');return
            self.runner.load(path);return

    def remember(self,row,key):
        self.cache[row]=key;self.cache.move_to_end(row)
        while len(self.cache)>200:
            old,_=self.cache.popitem(last=False)
            item=self.view.item(old)
            if item is not None:item.setIcon(QIcon());item.setToolTip('')

    def ready(self,path,info,image):
        if not self.expected or self.expected[1]!=path:return
        row,_,stamp=self.expected;self.expected=None
        item=self.view.item(row)
        if item is not None:
            item.setIcon(QIcon(QPixmap.fromImage(image).scaled(QSize(128,128))))
            item.setToolTip(f"{item.text()}\n{info['stitches']:,} stitches · {info['width']:.1f} × {info['height']:.1f} mm")
            self.remember(row,(path,(info['size'],info['mtime_ns'])))
        self.schedule()

    def failed(self,path,message):
        if not self.expected or self.expected[1]!=path:return
        row,_,stamp=self.expected;self.expected=None
        item=self.view.item(row)
        if item is not None:
            item.setIcon(self.view.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxWarning))
            item.setToolTip(f'{item.text()}\nPreview unavailable: {message}')
            self.remember(row,(path,stamp))
        self.schedule()
