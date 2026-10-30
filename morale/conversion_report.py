"""Printable review of a generated artwork conversion, not a sew-out template."""
import base64
import os
from pathlib import Path
import tempfile
from PySide6.QtCore import QRectF,QPointF,Qt
from PySide6.QtGui import QImage,QPainter,QPdfWriter,QPageSize,QPageLayout,QFont,QTextLayout,QTextOption
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
    if info.get('source_digest'):
        text+='\n\nSource artwork SHA-256 (at conversion):\n'+info['source_digest']
    decisions=stats.get('stitch_decisions',[])
    order=stats.get('sewing_order') or (stats.get('routing') or {}).get('order') or list(range(len(decisions)))
    selection=[]
    for decision in decisions:
        region=decision['region']
        position=f' (sew {order.index(region)+1})' if region in order else ''
        line=f"Artwork region {region+1}{position}: {decision['selected']} — {decision['reason']}"
        if decision.get('fallback'):line=f"FALLBACK (requested {decision['requested']}): "+line
        if decision['selected'] in {'fill','satin'} and decision.get('spacing_mm') is not None:
            line+=f" Spacing: {decision['spacing_mm']:g} mm."
        if decision['selected']=='fill' and decision.get('angle_degrees') is not None:
            line+=f" Fill angle: {decision['angle_degrees']:g} degrees."
        selection.append(line)
    text+='\n\nStitch selection (original artwork regions)\n'+'\n'.join(selection)
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
    # Keep layouts alive while their QTextLine handles are painted. Each line
    # belongs to one page; drawing sliced QTextDocuments can repeat boundary text.
    layouts=[];text_pages=[[]];y=0
    option=QTextOption();option.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
    for paragraph in text.split('\n'):
        layout=QTextLayout(paragraph or ' ',QFont('Sans',10),writer)
        layout.setTextOption(option);layouts.append(layout);layout.beginLayout()
        while True:
            line=layout.createLine()
            if not line.isValid():break
            line.setLineWidth(width-2*margin)
            if y+line.height()>body_height:
                text_pages.append([]);y=0
            if len(text_pages)>200:
                layout.endLayout()
                raise ValueError('Conversion review exceeds 200 text pages.')
            text_pages[-1].append((line,y));y+=line.height()
        layout.endLayout()
    pages=len(text_pages)
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
        painter.setFont(QFont('Sans',10))
        for i,lines in enumerate(text_pages):
            page('Conversion measurements'+(' · continued' if i else ''))
            for line,y in lines:line.draw(painter,QPointF(margin,42+y))
    finally:
        painter.end();del painter;del writer
