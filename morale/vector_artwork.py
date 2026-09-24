"""Direct SVG artwork input for the assisted digitizing preview."""
import io
import math
import re
from pathlib import Path
import xml.etree.ElementTree as ET
import svgelements as svg
from PySide6.QtCore import Qt,QRectF
from PySide6.QtGui import QImage,QPainter,QColorSpace,QPainterPath,QPainterPathStroker,QTransform
from PySide6.QtSvg import QSvgRenderer
from .svg_import import checked_xml,import_svg_text,paint_order
from .model import Project
from .svg_dashes import configure_dashes


def stroke_outline(element):
    """Outline before applying the SVG transform, including nonuniform scales."""
    path=svg.Path(element)
    if len(path)>6000:raise ValueError('SVG path exceeds 6,000 segments.')
    values=element.values
    if values.get('vector-effect','none')!='none':
        raise ValueError('Convert SVG vector effects to plain paths before expanding strokes.')
    caps={'butt':Qt.PenCapStyle.FlatCap,'round':Qt.PenCapStyle.RoundCap,'square':Qt.PenCapStyle.SquareCap}
    joins={'miter':Qt.PenJoinStyle.SvgMiterJoin,'round':Qt.PenJoinStyle.RoundJoin,'bevel':Qt.PenJoinStyle.BevelJoin}
    cap=values.get('stroke-linecap','butt');join=values.get('stroke-linejoin','miter')
    if cap not in caps or join not in joins:raise ValueError('Unsupported SVG stroke cap or join; convert it to a plain path first.')
    width=float(element.stroke_width);limit=float(values.get('stroke-miterlimit',4))
    if not math.isfinite(width) or width<0 or not math.isfinite(limit) or limit<1:
        raise ValueError('Invalid SVG stroke width or miter limit.')
    if width==0:return ''
    geometry=QPainterPath()
    for segment in path:
        if isinstance(segment,svg.Move):geometry.moveTo(segment.end.x,segment.end.y)
        elif isinstance(segment,svg.Close):geometry.closeSubpath()
        else:
            parts=segment.as_cubic_curves() if isinstance(segment,svg.Arc) else [segment]
            for part in parts:
                if isinstance(part,svg.CubicBezier):geometry.cubicTo(part.control1.x,part.control1.y,part.control2.x,part.control2.y,part.end.x,part.end.y)
                elif isinstance(part,svg.QuadraticBezier):geometry.quadTo(part.control.x,part.control.y,part.end.x,part.end.y)
                else:geometry.lineTo(part.end.x,part.end.y)
    stroker=QPainterPathStroker();stroker.setWidth(width);stroker.setCapStyle(caps[cap]);stroker.setJoinStyle(joins[join])
    # SvgMiterJoin applies SVG's half-width ratio and bevel fallback itself.
    stroker.setMiterLimit(limit);stroker.setCurveThreshold(.01)
    dots=configure_dashes(stroker,geometry,values,width)
    m=element.transform
    if stroker.dashPattern():
        # Qt flattens curves while dashing; enlarge first for sub-unit fidelity.
        stroker.setWidth(width*20)
        stroke=QTransform().scale(.05,.05).map(stroker.createStroke(QTransform().scale(20,20).map(geometry)))
    else:stroke=stroker.createStroke(geometry)
    stroke.addPath(dots)
    outlined=QTransform(m.a,m.b,m.c,m.d,m.e,m.f).map(stroke)
    commands=[];index=0
    while index<outlined.elementCount():
        part=outlined.elementAt(index)
        if part.isCurveTo():
            points=[outlined.elementAt(index+i) for i in range(3)]
            commands.append('C'+' '.join(f'{p.x:.12g} {p.y:.12g}' for p in points));index+=3
        else:
            commands.append(('M' if part.isMoveTo() else 'L')+f'{part.x:.12g} {part.y:.12g}');index+=1
    return ' '.join(commands)


def vector_artwork(path,width=80,resolution=512,expand_strokes=False,**unused):
    if type(expand_strokes) is not bool:raise ValueError('Invalid SVG stroke expansion setting.')
    if isinstance(width,bool) or not isinstance(width,(int,float)) or not math.isfinite(width) or not 1<=width<=300:
        raise ValueError('Choose an artwork width from 1 to 300 mm.')
    if type(resolution) is not int or resolution not in {64,128,256,512,1024}:raise ValueError('Invalid SVG preview resolution.')
    path=Path(path)
    if path.stat().st_size>2_000_000:raise ValueError('SVG artwork is limited to 2 MB.')
    text,notes=checked_xml(path.read_text(encoding='utf-8-sig'),allow_dashes=expand_strokes)
    document=svg.SVG.parse(io.StringIO(text),ppi=96,reify=not expand_strokes,width=300,height=150,on_error='raise')
    page_width,page_height=float(document.width),float(document.height)
    if not all(math.isfinite(v) and v>0 for v in (page_width,page_height)):raise ValueError('SVG page dimensions must be positive.')
    height=width*page_height/page_width
    if not .1<=height<=500:raise ValueError('Resulting SVG height must be between 0.1 and 500 mm.')
    root=ET.Element('svg',{'xmlns':'http://www.w3.org/2000/svg','width':f'{width:.12g}mm',
        'height':f'{height:.12g}mm','viewBox':f'0 0 {page_width:.12g} {page_height:.12g}'})
    for element in document.elements():
        if not isinstance(element,svg.Shape) or element.values.get('visibility') in {'hidden','collapse'} or element.values.get('display')=='none':continue
        order=paint_order(element.values.get("paint-order","normal"))
        outline=stroke_outline(element) if expand_strokes and element.stroke.value is not None and element.stroke.alpha else None
        path_shape=svg.Path(element);path_shape.reify()
        attrs={'d':path_shape.d(),'fill':'none','stroke':'none','fill-rule':element.values.get('fill-rule','nonzero'),
               'opacity':str(element.values.get('opacity',1))}
        if element.values.get('id'):
            attrs['id']=f'shape-{len(root)+1}-'+re.sub(r'[^\w.-]','_',str(element.values['id']))[:100]
        for key,paint in (('fill',element.fill),('stroke',element.stroke)):
            if paint.value is not None:
                attrs[key]=paint.hex[:7];attrs[key+'-opacity']=str(paint.alpha/255)
        attrs['stroke-width']=str(element.stroke_width)
        for key,default in (('stroke-linecap','butt'),('stroke-linejoin','miter'),('stroke-miterlimit','4')):
            attrs[key]=str(element.values.get(key,default))
        if outline is not None:
            stroke_attrs={'d':outline,'fill':attrs['stroke'],'fill-opacity':attrs.get('stroke-opacity','1'),
                          'opacity':attrs['opacity'],'fill-rule':'nonzero','stroke':'none'}
            if 'id' in attrs:stroke_attrs['id']=attrs['id']+'-border'
            attrs['stroke']='none'
            for paint in order:
                if paint=='fill' and element.fill.value is not None and element.fill.alpha:ET.SubElement(root,'path',attrs)
                if paint=='stroke' and outline:ET.SubElement(root,'path',stroke_attrs)
        elif order.index('stroke')<order.index('fill'):
            # Explicit layers also preserve paint order in Qt's SVG preview.
            stroke_attrs={**attrs,'fill':'none'}
            if 'id' in attrs:stroke_attrs['id']=attrs['id']+'-outline'
            if element.stroke.value is not None and element.stroke.alpha:ET.SubElement(root,'path',stroke_attrs)
            if element.fill.value is not None and element.fill.alpha:ET.SubElement(root,'path',{**attrs,'stroke':'none'})
        else:ET.SubElement(root,'path',attrs)
    if expand_strokes:
        notes.append('SVG strokes, including supported dash patterns, were expanded into filled borders before stitch selection. Fills and borders may overlap; inspect stitch density at their edges.')
    vector=ET.tostring(root,encoding='unicode')
    imported=import_svg_text(vector,center_artwork=False)
    project=Project(name=path.stem[:200],objects=imported.objects)
    renderer=QSvgRenderer(vector.encode())
    if not renderer.isValid():raise ValueError('Could not render the normalized SVG.')
    factor=resolution/max(page_width,page_height)
    image=QImage(max(1,round(page_width*factor)),max(1,round(page_height*factor)),QImage.Format.Format_RGBA8888)
    image.fill(Qt.GlobalColor.transparent);image.setColorSpace(QColorSpace.NamedColorSpace.SRgb)
    painter=QPainter(image);renderer.render(painter,QRectF(0,0,image.width(),image.height()));painter.end()
    return project,image,{'method':'svg','svg':vector,'resolution':[image.width(),image.height()],
        'palette':len({obj.color.lower() for obj in project.objects}),'artwork_size_mm':[width,height],
        'notes':list(dict.fromkeys(notes+imported.notices)),'color_profile':{'source':'SVG sRGB colors','target':'sRGB','assumed':False,'converted':False}}
