"""Artwork and generated stitches rendered in a shared physical coordinate frame."""
import math
from PySide6.QtCore import QRectF,Qt,QPointF
from PySide6.QtGui import QImage,QPainter,QPainterPath,QPen,QColor,QTransform
from .model import Project
from .engine import generate
from .stitch_rendering import draw_stitch_path


def frame_transform(frame):
    scale=min(620/frame.width(),620/frame.height())
    transform=QTransform();transform.translate(320,320);transform.scale(scale,scale);transform.translate(-frame.center().x(),-frame.center().y())
    return transform


def aligned_panels(info,source,vector,*,blocks=None,marked_starts=()):
    if blocks is None:blocks=generate(Project.loads(info['project']))
    width,height=info['trace_stats']['artwork_size_mm']
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not 0<v<=1000 or not math.isfinite(v) for v in (width,height)):
        raise ValueError('Invalid physical artwork dimensions for the review.')
    page=QRectF(-width/2,-height/2,width,height)
    points=[(s.x,s.y) for b in blocks for s in b.stitches if s.command in {'stitch','jump'}]
    left=min([page.left(),*[x for x,y in points]]);right=max([page.right(),*[x for x,y in points]])
    top=min([page.top(),*[y for x,y in points]]);bottom=max([page.bottom(),*[y for x,y in points]])
    padding=max(.5,max(right-left,bottom-top)*.025)
    frame=QRectF(left-padding,top-padding,right-left+2*padding,bottom-top+2*padding)
    transform=frame_transform(frame);scale=transform.m11()
    page_rect=transform.mapRect(page);panels=[]
    for mode in ('source','vectors','stitches'):
        image=QImage(640,640,QImage.Format.Format_RGB32);image.fill(QColor('white'))
        painter=QPainter(image);painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        try:
            if mode=='source':painter.drawImage(page_rect,source)
            elif mode=='vectors':
                if vector is not None:
                    vector.setAspectRatioMode(Qt.AspectRatioMode.IgnoreAspectRatio);vector.render(painter,page_rect)
                else:
                    painter.setPen(QColor('#666666'));painter.drawText(QRectF(25,280,590,80),Qt.TextFlag.TextWordWrap,'This conversion mode did not supply a prepared SVG.')
            else:
                painter.setTransform(transform);previous=(0.,0.)
                for block in blocks:
                    path=QPainterPath()
                    for stitch in block.stitches:
                        point=(stitch.x,stitch.y)
                        if stitch.command=='stitch':path.moveTo(*previous);path.lineTo(*point)
                        if stitch.command in {'stitch','jump'}:previous=point
                    draw_stitch_path(painter,path,block.color,1/scale)
                painter.setBrush(Qt.BrushStyle.NoBrush);painter.setPen(QPen(QColor('#1765df'),1.5/scale))
                for block in blocks:
                    if block.object_id not in marked_starts:continue
                    first=next((s for s in block.stitches if s.command=='stitch'),None)
                    if first is not None:painter.drawEllipse(QPointF(first.x,first.y),6/scale,6/scale)
                painter.resetTransform()
            painter.setBrush(Qt.BrushStyle.NoBrush);painter.setPen(QPen(QColor('#a8a8a8'),1,Qt.PenStyle.DashLine));painter.drawRect(page_rect)
        finally:painter.end()
        panels.append(image)
    return panels,frame
