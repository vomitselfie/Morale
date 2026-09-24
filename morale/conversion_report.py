"""Printable review of a generated artwork conversion, not a sew-out template."""
import base64
import math
import os
from pathlib import Path
import tempfile
from PySide6.QtCore import QRectF,Qt
from PySide6.QtGui import QImage,QPainter,QPdfWriter,QPageSize,QPageLayout,QFont,QTextDocument
from PySide6.QtSvg import QSvgRenderer
from .trace_quality import quality_text
from .review_panels import aligned_panels


def save_conversion_review(path,source_name,info,stitches,fabric=None):
    source=QImage.fromData(base64.b64decode(info['raster_png']))
    maps=[QImage.fromData(base64.b64decode(info[key])) for key in ('density_png','thread_density_png')]
    if any(image.isNull() for image in [source,stitches,*maps]):raise ValueError('Generate a complete preview before saving its review.')
    # Reviews from before coverage measurement keep their two density pages.
    if info.get('layers_png'):
        layers=QImage.fromData(base64.b64decode(info['layers_png']))
        if layers.isNull():raise ValueError('The coverage review image is damaged.')
        maps.append(layers)
    vector=QSvgRenderer(info['trace_svg'].encode()) if info.get('trace_svg') else None
    if vector is not None and not vector.isValid():raise ValueError('The prepared SVG is invalid.')
    stats=info['trace_stats'];quality=dict(stats['quality'])
    if fabric is not None and quality.get('layers'):quality['fabric']=fabric
    text=quality_text(quality)
    decisions=stats.get('stitch_decisions',[])
    text+='\n\nStitch selection\n'+'\n'.join(f"Region {d['region']+1}: {d['selected']} — {d['reason']}" for d in decisions)
    if len(text)>2_000_000:raise ValueError('Conversion review text exceeds the supported limit.')
    path=Path(path);temporary=None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent,suffix='.pdf',delete=False) as stream:temporary=Path(stream.name)
        _write(temporary,Path(source_name).name,info,source,vector,stitches,maps,text)
        os.replace(temporary,path)
    finally:
        if temporary is not None:temporary.unlink(missing_ok=True)


def _write(path,name,info,source,vector,stitches,maps,text):
    panels,frame=aligned_panels(info,source,vector)
    writer=QPdfWriter(str(path));writer.setResolution(72);writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setPageOrientation(QPageLayout.Orientation.Landscape);writer.setTitle('Morale artwork conversion review');writer.setCreator('Morale')
    width,height=writer.width(),writer.height();margin=14;body_height=height-85
    document=QTextDocument();document.setDefaultFont(QFont('Sans',10));document.setPlainText(text);document.setTextWidth(width-2*margin)
    pages=max(1,math.ceil(document.size().height()/body_height))
    if pages>200:
        del writer
        raise ValueError('Conversion review exceeds 200 text pages.')
    painter=QPainter(writer)
    if not painter.isActive():
        del painter;del writer
        raise OSError('Could not create the conversion PDF.')
    number=0
    def page(title):
        nonlocal number
        if number and not writer.newPage():raise OSError('Could not add a review page.')
        number+=1;painter.setFont(QFont('Sans',13));painter.setPen(Qt.GlobalColor.black)
        painter.drawText(QRectF(margin,5,width-2*margin,25),title)
        painter.setFont(QFont('Sans',9));painter.drawText(QRectF(margin,height-23,width-2*margin,20),f'Morale · {number}/{pages+1+len(maps)} · Review only; not an actual-size placement template or sew-out validation.')
    def picture(image,rect):
        fitted=QRectF(0,0,image.width(),image.height());fitted.setSize(fitted.size().scaled(rect.size(),Qt.AspectRatioMode.KeepAspectRatio));fitted.moveCenter(rect.center())
        painter.drawImage(fitted,image)
    try:
        page('Artwork conversion · '+name[:100])
        painter.setFont(QFont('Sans',10))
        painter.drawText(QRectF(margin,34,width-2*margin,25),f"{info['stitches']:,} stitches · {info['colors']} RGB colors · {len(info['trace_stats'].get('stitch_decisions',[]))} regions")
        column=(width-2*margin-24)/3
        for i,(label,image) in enumerate(zip(('Sampled artwork','Prepared vectors','Generated stitches'),panels)):
            x=margin+i*(column+12);painter.drawText(QRectF(x,70,column,24),label);rect=QRectF(x,98,column,260)
            picture(image,rect)
        painter.drawText(QRectF(margin,375,width-2*margin,55),Qt.TextFlag.TextWordWrap,
                         f'All three panels share one physical frame: X {frame.left():.2f} to {frame.right():.2f} mm, Y {frame.top():.2f} to {frame.bottom():.2f} mm. Dashed lines mark the original artwork page. Light stitches have a preview-only contrast outline. Prepared artwork retains source colors; cleanup, overlap removal and stitch choices affect the embroidery.')
        for title,image in zip(('Needle-penetration review','Sewn-thread-length review','Coverage-layers review'),maps):
            page(title);picture(image,QRectF(margin,37,width-2*margin,height-68))
        for i in range(pages):
            page('Conversion measurements'+(' · continued' if i else ''))
            painter.save();painter.translate(margin,42-i*body_height)
            document.drawContents(painter,QRectF(0,i*body_height,width-2*margin,body_height));painter.restore()
    finally:
        painter.end();del painter;del writer
