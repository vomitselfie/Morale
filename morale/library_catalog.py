"""Native, cancellable design-catalog preparation and atomic PDF output."""
from pathlib import Path
import os
import tempfile
from PySide6.QtCore import Qt,QTimer,QRectF,QPointF
from PySide6.QtGui import QPdfWriter,QPageSize,QPainter,QFont,QColor,QTextLayout,QTextOption
from PySide6.QtWidgets import QDialog,QVBoxLayout,QLabel,QPushButton,QHBoxLayout,QFileDialog,QMessageBox


def check_destination(path,entries):
    destination=Path(path)
    for entry in entries:
        source=Path(entry['path'])
        same=destination.resolve()==source.resolve()
        if not same:
            try:same=destination.samefile(source)
            except FileNotFoundError:pass
        if same:raise ValueError('Choose a PDF destination different from every source design.')


def save_catalog(path,entries):
    if not 1<=len(entries)<=100:raise ValueError('Choose 1–100 designs for a catalog.')
    check_destination(path,entries)
    with tempfile.NamedTemporaryFile(dir=Path(path).parent,suffix='.pdf',delete=False) as stream:temporary=Path(stream.name)
    painter=None
    try:
        writer=QPdfWriter(str(temporary));writer.setResolution(72);writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        writer.setTitle('Morale design catalog');painter=QPainter(writer)
        if not painter.isActive():raise OSError('Could not start catalog printing.')
        width,height=writer.width(),writer.height();cell_w=width/2;cell_h=(height-70)/3
        for index,entry in enumerate(entries):
            slot=index%6
            if slot==0:
                if index and not writer.newPage():raise OSError('Could not add a catalog page.')
                painter.setPen(QColor('#222222'));painter.setFont(QFont('Sans Serif',14))
                painter.drawText(QRectF(0,0,width,24),'Morale design catalog')
                painter.setFont(QFont('Sans Serif',8))
                painter.drawText(QRectF(0,26,width,24),f"Preview snapshots · not actual size · thumbnail page {index//6+1} of {(len(entries)+5)//6}")
            x=(slot%2)*cell_w;y=55+(slot//2)*cell_h
            painter.setPen(QColor('#cccccc'));painter.drawRect(QRectF(x+3,y+3,cell_w-6,cell_h-6))
            painter.setPen(QColor('#222222'));painter.setFont(QFont('Sans Serif',9))
            name=f"{index+1}. {Path(entry['path']).name}"
            name=painter.fontMetrics().elidedText(name,Qt.TextElideMode.ElideMiddle,int(cell_w-20))
            painter.drawText(QRectF(x+10,y+8,cell_w-20,28),name)
            info=entry.get('info');image=entry.get('image')
            if info is not None and image is not None:
                target=QRectF(x+10,y+40,cell_w-20,cell_h-112)
                size=image.size().scaled(int(target.width()),int(target.height()),Qt.AspectRatioMode.KeepAspectRatio)
                painter.drawImage(QRectF(target.center().x()-size.width()/2,target.center().y()-size.height()/2,size.width(),size.height()),image)
                detail=f"{info['width']:.1f} × {info['height']:.1f} mm command bounds\n{info['stitches']:,} stitches · {info['colors']} RGB colors"
            else:detail='Preview unavailable · see file index for details.'
            painter.setFont(QFont('Sans Serif',8))
            painter.drawText(QRectF(x+10,y+cell_h-68,cell_w-20,42),Qt.TextFlag.TextWordWrap,detail)
            parent=painter.fontMetrics().elidedText(str(Path(entry['path']).parent),Qt.TextElideMode.ElideMiddle,int(cell_w-20))
            painter.drawText(QRectF(x+10,y+cell_h-23,cell_w-20,15),parent)
        index_page=0;y=height
        def index_header():
            nonlocal index_page,y
            if not writer.newPage():raise OSError('Could not add catalog index page.')
            index_page+=1;painter.setFont(QFont('Sans Serif',14));painter.setPen(QColor('#222222'))
            painter.drawText(QRectF(0,0,width,24),f'Catalog file index · page {index_page}')
            painter.setFont(QFont('Sans Serif',9));y=38
        for index,entry in enumerate(entries):
            paragraphs=[f"{index+1}. {entry['path']}"]
            if 'error' in entry:paragraphs+=('Preview unavailable: '+entry['error']).splitlines()
            for paragraph in paragraphs:
                font=QFont('Sans Serif',9);layout=QTextLayout(paragraph,font)
                option=QTextOption();option.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere);layout.setTextOption(option)
                layout.beginLayout()
                while True:
                    line=layout.createLine()
                    if not line.isValid():break
                    line.setLineWidth(width-10)
                    if y+line.height()>height-12:index_header()
                    line.draw(painter,QPointF(0,y));y+=line.height()+2
                layout.endLayout()
            y+=10
        ended=painter.end();painter=None
        if not ended:raise OSError("Could not finish catalog printing.")
        writer=None
        check_destination(path,entries)
        os.replace(temporary,path)
    except Exception:
        if painter is not None:painter.end()
        painter=None
        raise
    finally:
        writer=None
        temporary.unlink(missing_ok=True)


class CatalogDialog(QDialog):
    def __init__(self,paths,parent=None):
        super().__init__(parent)
        self.paths=list(dict.fromkeys(str(Path(p).resolve()) for p in paths))
        if not 1<=len(self.paths)<=100:raise ValueError('Choose 1–100 designs for a catalog.')
        from .library import PreviewRunner
        self.runner=PreviewRunner(self);self.runner.ready.connect(self.ready);self.runner.failed.connect(self.failed)
        self.entries=[];self.expected=None;self.cancelled=False
        self.setWindowTitle('Design catalog');layout=QVBoxLayout(self)
        self.status=QLabel('Preparing previews…');self.status.setTextFormat(Qt.TextFormat.PlainText);self.status.setWordWrap(True);layout.addWidget(self.status)
        row=QHBoxLayout();self.save=QPushButton('Save PDF…');self.save.setEnabled(False);self.save.clicked.connect(self.export);row.addWidget(self.save)
        close=QPushButton('Cancel / Close');close.clicked.connect(self.reject);row.addWidget(close);layout.addLayout(row)
        self.resize(480,150);QTimer.singleShot(0,self.advance)

    def advance(self):
        if self.cancelled:return
        if len(self.entries)==len(self.paths):
            failures=sum('error' in e for e in self.entries)
            self.status.setText(f"{len(self.entries)} designs prepared; {failures} previews unavailable. Failed files will be listed in the PDF.")
            self.save.setEnabled(True);return
        self.expected=self.paths[len(self.entries)]
        self.status.setText(f"Preview {len(self.entries)+1} of {len(self.paths)}: {Path(self.expected).name}")
        self.runner.load(self.expected)

    def ready(self,path,info,image):
        if self.cancelled or path!=self.expected:return
        try:
            stat=Path(path).stat()
            if (stat.st_size,stat.st_mtime_ns)!=(info['size'],info['mtime_ns']):raise ValueError('File changed during preview; rebuild the catalog.')
        except (OSError,ValueError) as exc:self.failed(path,str(exc));return
        self.entries.append({'path':path,'info':dict(info),'image':image.scaled(320,320,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation)})
        self.expected=None;QTimer.singleShot(0,self.advance)

    def failed(self,path,message):
        if self.cancelled or path!=self.expected:return
        self.entries.append({'path':path,'error':message});self.expected=None;QTimer.singleShot(0,self.advance)

    def export(self):
        if self.cancelled or len(self.entries)!=len(self.paths):return
        path,_=QFileDialog.getSaveFileName(self,'Save design catalog','design-catalog.pdf','PDF (*.pdf)')
        if not path:return
        if not Path(path).suffix:path+='.pdf'
        try:save_catalog(path,self.entries)
        except (OSError,ValueError) as exc:QMessageBox.warning(self,'Design catalog',str(exc));return
        self.status.setText(f'Catalog saved: {path}')

    def done(self,result):
        self.cancelled=True;self.expected=None;self.runner.cancel();super().done(result)
