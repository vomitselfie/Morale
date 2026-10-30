"""Resolve local user-space SVG fill clips before the embroidery parser."""
from copy import deepcopy
import io
import math
import re
import xml.etree.ElementTree as ET
import svgelements as svg
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainterPath,QTransform


def geometry(element):
    path=svg.Path(element);path.reify()
    if len(path)>6000:raise ValueError('SVG clipping shape exceeds 6,000 segments.')
    result=QPainterPath()
    for segment in path:
        if isinstance(segment,svg.Move):result.moveTo(segment.end.x,segment.end.y)
        elif isinstance(segment,svg.Close):result.closeSubpath()
        else:
            for part in (segment.as_cubic_curves() if isinstance(segment,svg.Arc) else [segment]):
                if isinstance(part,svg.CubicBezier):result.cubicTo(part.control1.x,part.control1.y,part.control2.x,part.control2.y,part.end.x,part.end.y)
                elif isinstance(part,svg.QuadraticBezier):result.quadTo(part.control.x,part.control.y,part.end.x,part.end.y)
                else:result.lineTo(part.end.x,part.end.y)
    for i in range(result.elementCount()):
        point=result.elementAt(i)
        if not all(math.isfinite(v) and abs(v)<=4_000_000 for v in (point.x,point.y)):
            raise ValueError('SVG clipping coordinates exceed the supported limit.')
    return result


def fill_rule(value):
    if value not in ('nonzero','evenodd'):raise ValueError('Unsupported SVG clipping fill rule.')
    return Qt.FillRule.OddEvenFill if value=='evenodd' else Qt.FillRule.WindingFill


def path_data(path):
    # Enlarge Boolean geometry so Qt's curve flattening retains sub-pixel detail.
    # Boolean results can retain touching outer/hole edges. Canonicalize them
    # into separate regions so SVG antialiasing cannot paint phantom seams.
    polygons=path.simplified().toSubpathPolygons();commands=[];count=0
    for polygon in polygons:
        count+=len(polygon)
        if count>20000:raise ValueError('Clipped SVG shape exceeds 20,000 points.')
        if len(polygon)<3:continue
        commands.append('M'+' L'.join(f'{p.x()/20:.12g} {p.y()/20:.12g}' for p in polygon)+' Z')
    return ' '.join(commands)


def resolve_fill_clips(root,reference_shapes=None,*,paint_sink=None,layer_sink=None):
    """Flatten clips, optionally deliver each visible paint with its source shape.

    The sink receives document-space geometry, the uncut source element, paint
    name and local viewport dimensions. Keeping the source lets gradient
    rendering use its original bounds even when the visible geometry is smaller.
    """
    reference_shapes=reference_shapes or {}
    definitions={n.get('id'):n for n in root.iter() if n.tag.split('}')[-1]=='clipPath' and n.get('id')}
    document=svg.SVG.parse(io.StringIO(ET.tostring(root,encoding='unicode')),ppi=96,reify=False,width=300,height=150,on_error='raise')
    def position_viewports(item):
        if isinstance(item,svg.SVG) and item is not document and item.viewbox is None:
            m=item.transform;x=float(item.x);y=float(item.y)
            dx=m.a*x+m.c*y;dy=m.b*x+m.d*y
            def shift(node):
                node.transform=svg.Matrix(node.transform)
                node.transform.post_translate(dx,dy)
                if isinstance(node,(svg.Group,svg.SVG,svg.Use)):
                    for child in node:shift(child)
            shift(item)
        if isinstance(item,(svg.Group,svg.SVG,svg.Use)):
            for child in item:position_viewports(child)
    position_viewports(document)
    output=ET.Element('svg',{'xmlns':'http://www.w3.org/2000/svg','width':str(document.width),'height':str(document.height)})
    viewbox=root.get('viewBox','').replace(',',' ').split()
    viewport=(float(viewbox[2]),float(viewbox[3])) if len(viewbox)==4 else (float(document.width),float(document.height))
    cache={};active=set();scale=QTransform().scale(20,20)
    def clip_geometry(reference,element,precision_floor=1,viewport_size=None):
        viewport_size=viewport if viewport_size is None else viewport_size
        match=re.fullmatch(r'url\(\s*[\'\"]?#([^\s\'\"()]+)[\'\"]?\s*\)',reference)
        if not match or match[1] not in definitions:raise ValueError('SVG clip-path requires an existing local clipPath reference.')
        ident=match[1]
        node=definitions[ident]
        units=node.get('clipPathUnits','userSpaceOnUse')
        if units not in {'userSpaceOnUse','objectBoundingBox'}:raise ValueError('Unsupported SVG clipPathUnits.')
        precision=max(precision_floor,1000 if units=='objectBoundingBox' else 1)
        cache_key=(ident,precision,viewport_size)
        if ident in active:raise ValueError('SVG contains a circular clip reference.')
        if cache_key not in cache:
            if len(active)>=64:raise ValueError('SVG clip reference nesting exceeds 64 levels.')
            active.add(ident)
            referenced={}
            children=list(node.iter())
            for child in list(children):
                if child.tag.split('}')[-1]!='use':continue
                href=child.get('href',child.get('{http://www.w3.org/1999/xlink}href',''))
                if not href.startswith('#') or href[1:] not in reference_shapes:
                    raise ValueError('SVG clip use references must name a local basic shape or path.')
                target=reference_shapes[href[1:]]
                referenced[href[1:]]=target
                children.append(target)
            for child in children:
                tag=child.tag.split('}')[-1]
                if tag in {'svg','clipPath'} and child is not node:
                    raise ValueError('Convert referenced or nested SVG clip geometry to plain paths before import.')
            wrapper=ET.Element('svg',{'width':'1' if units=='objectBoundingBox' else str(viewport_size[0]),'height':'1' if units=='objectBoundingBox' else str(viewport_size[1])})
            defs=ET.SubElement(wrapper,'defs')
            for target in referenced.values():defs.append(deepcopy(target))
            group=deepcopy(node);group.tag='g';group.attrib.pop('id',None);wrapper.append(group)
            percent_width,percent_height=(1.,1.) if units=='objectBoundingBox' else viewport_size
            for child in wrapper.iter():
                properties={**child.attrib,**{key.strip():value.strip() for part in child.get('style','').split(';') if ':' in part for key,value in [part.split(':',1)]}}
                for key in ('x','x1','x2','cx','width','rx','y','y1','y2','cy','height','ry','r'):
                    raw=properties.get(key,'')
                    if not raw.endswith('%'):continue
                    basis=math.hypot(percent_width,percent_height)/math.sqrt(2) if key=='r' else (percent_width if key in {'x','x1','x2','cx','width','rx'} else percent_height)
                    try:value=float(raw[:-1])*basis/100
                    except ValueError as exc:raise ValueError('Invalid SVG clip percentage.') from exc
                    if not math.isfinite(value):raise ValueError('SVG clip percentages must be finite.')
                    child.set(key,str(value));child.set('style',child.get('style','')+f';{key}:{value}')
            clip_doc=svg.SVG.parse(io.StringIO(ET.tostring(wrapper,encoding='unicode')),ppi=96,reify=False,on_error='raise')
            area=QPainterPath()
            clip_scale=QTransform().scale(20*precision,20*precision)
            def clipped_parts(item,inherited=None):
                nonlocal area
                if item.values.get('display')=='none':return
                restriction=inherited
                own=item.values.get('attributes',{}).get('clip-path','none')
                if own!='none':
                    local=clip_geometry(own,item,precision,viewport_size)
                    if local is not None:
                        local=QTransform().scale(precision,precision).map(local)
                        restriction=local if restriction is None else restriction.intersected(local)
                if isinstance(item,svg.Shape):
                    if item.values.get('visibility') in {'hidden','collapse'}:return
                    part=geometry(item);part.setFillRule(fill_rule(item.values.get('clip-rule','nonzero')))
                    part=clip_scale.map(part)
                    if restriction is not None:part=part.intersected(restriction)
                    area=area.united(part)
                    if area.elementCount()>20000:raise ValueError("SVG clip geometry exceeds 20,000 elements.")
                elif isinstance(item,(svg.Group,svg.SVG,svg.Use)):
                    for child in item:clipped_parts(child,restriction)
            clipped_parts(clip_doc)
            cache[cache_key]=QTransform().scale(1/precision,1/precision).map(area)
            active.remove(ident)
        m=element.transform
        if isinstance(element,svg.SVG) and element.viewbox is not None:
            m=svg.Matrix(element.viewbox.transform(element))*m
        # Clip coordinates use the referencing element's current user space.
        transform=QTransform(m.a,m.b,m.c,m.d,m.e*20,m.f*20)
        area=cache[cache_key]
        if units=='objectBoundingBox':
            inverse,valid=QTransform(m.a,m.b,m.c,m.d,m.e,m.f).inverted()
            if not valid:return QPainterPath()
            rectangles=[]
            def collect(item):
                if item.values.get('display')=='none':return
                if isinstance(item,svg.Shape):
                    path=inverse.map(geometry(item))
                    if path.elementCount():rectangles.append(path.boundingRect())
                elif isinstance(item,(svg.Group,svg.SVG,svg.Use)):
                    for child in item:collect(child)
            collect(element)
            if not rectangles:return QPainterPath()
            left=min(r.left() for r in rectangles);top=min(r.top() for r in rectangles)
            width=max(r.right() for r in rectangles)-left;height=max(r.bottom() for r in rectangles)-top
            # SVG ignores object-bounding-box effects on zero-area geometry.
            if width<=0 or height<=0:return None
            area=QTransform(width,0,0,height,left*20,top*20).map(area)
        return transform.map(area)
    def walk(element,inherited=None,viewport_size=viewport):
        if isinstance(element,svg.SVG):
            viewport_size=(float(element.viewbox.width),float(element.viewbox.height)) if element.viewbox is not None else (float(element.width),float(element.height))
        opacity=float(element.values.get('attributes',{}).get('opacity',1))
        layered=layer_sink is not None and 0<opacity<1
        mask=element.values.get('attributes',{}).get('data-morale-mask','') if layer_sink is not None else ''
        if layered:layer_sink('begin',opacity)
        if mask:layer_sink('mask-begin',mask,element,viewport_size)
        try:walk_contents(element,inherited,viewport_size)
        finally:
            if mask:layer_sink('mask-end',None)
            if layered:layer_sink('end',opacity)
    def walk_contents(element,inherited=None,viewport_size=viewport):
        if isinstance(element,svg.SVG):
            viewport_size=(float(element.viewbox.width),float(element.viewbox.height)) if element.viewbox is not None else (float(element.width),float(element.height))
        values=element.values
        own=values.get('attributes',{}).get('clip-path','none')
        area=inherited
        attributes=values.get('attributes',{})
        overflow=attributes.get('overflow')
        crop=overflow in {'hidden','scroll'} or ('slice' in attributes.get('preserveAspectRatio','') and overflow!='visible')
        if isinstance(element,svg.SVG) and crop:
            x,y=(float(element.x),float(element.y)) if element.viewbox is not None else (0.,0.)
            rectangle=QPainterPath();rectangle.addRect(x,y,float(element.width),float(element.height))
            m=element.transform
            local=QTransform(m.a,m.b,m.c,m.d,m.e*20,m.f*20).map(scale.map(rectangle))
            area=local if area is None else area.intersected(local)
        if own!='none':
            local=clip_geometry(own,element,viewport_size=viewport_size)
            if local is not None:area=local if area is None else area.intersected(local)
        if isinstance(element,svg.Shape):
            if values.get('display')=='none' or values.get('visibility') in {'hidden','collapse'} or float(values.get('opacity',1))==0:return
            attrs={'fill':element.fill.hex[:7] if element.fill.value is not None else 'none',
                   'stroke':element.stroke.hex[:7] if element.stroke.value is not None else 'none',
                   'fill-opacity':str((element.fill.alpha or 0)/255),'stroke-opacity':str((element.stroke.alpha or 0)/255),
                   'opacity':str(values.get('opacity',1))}
            for key in ('id','fill-rule','paint-order','stroke-width','stroke-linecap','stroke-linejoin','stroke-miterlimit','stroke-dasharray','stroke-dashoffset','pathLength','vector-effect'):
                if key in values:attrs[key]=str(values[key])
            if area is not None or paint_sink is not None:
                from .svg_import import paint_order
                from .vector_artwork import stroke_outline
                for paint_name in paint_order(values.get('paint-order','normal')):
                    if paint_name=='markers':continue
                    paint=getattr(element,paint_name)
                    if paint.value is None or not paint.alpha:continue
                    if paint_name=='stroke':
                        if element.stroke_width<=0:continue
                        shape=geometry(svg.Path(stroke_outline(element)))
                        shape.setFillRule(Qt.FillRule.WindingFill)
                    else:
                        shape=geometry(element);shape.setFillRule(fill_rule(values.get('fill-rule','nonzero')))
                    clipped=scale.map(shape)
                    if area is not None:clipped=clipped.intersected(area)
                    if clipped.isEmpty():continue
                    if paint_sink is not None:
                        visible=QTransform().scale(1/20,1/20).map(clipped)
                        paint_sink(visible,element,paint_name,viewport_size)
                        continue
                    clipped_attrs={'d':path_data(clipped),'stroke':'none','fill':paint.hex[:7],
                                   'fill-rule':'evenodd','fill-opacity':str(paint.alpha/255),'opacity':attrs['opacity']}
                    if 'id' in attrs:clipped_attrs['id']=attrs['id']+('-border' if paint_name=='stroke' else '')
                    ET.SubElement(output,'path',clipped_attrs)
                return
            else:
                attrs['d']=svg.Path(element).d(transformed=False)
                m=element.transform
                attrs['transform']=f'matrix({m.a} {m.b} {m.c} {m.d} {m.e} {m.f})'
            ET.SubElement(output,'path',attrs)
        elif isinstance(element,(svg.Group,svg.SVG,svg.Use)):
            for child in element:walk(child,area,viewport_size)
    walk(document)
    return output
