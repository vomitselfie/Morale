"""Render local SVG artwork through validated geometry, including gradients."""
import math
from copy import deepcopy
import re
import xml.etree.ElementTree as ET

import svgelements as svg
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QImage, QPainter, QPainterPath, QTransform

from .svg_clipping import geometry
from .svg_gradients import gradient_brush, properties, resolve_gradient
from .svg_import import checked_xml


def render_svg_artwork(text, *, resolution=512, _mask_stack=(), _mask_budget=None):
    """Return a bounded raster and validation notes without modifying artwork.

    Gradient references become collision-free temporary solid paint identifiers
    for the geometry parser. The renderer restores their actual brushes only
    after clipping, with the original source coordinate system still available.
    """
    if _mask_budget is None:_mask_budget=[67_108_864]
    if type(resolution) is not int or not 64<=resolution<=2048:
        raise ValueError('SVG rendering resolution must be between 64 and 2048.')
    if len(text.encode('utf-8'))>2_000_000:raise ValueError('SVG artwork is limited to 2 MB.')
    if '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():
        raise ValueError('SVG document types and entity declarations are not supported.')
    root=ET.fromstring(text)
    from .svg_styles import apply_styles
    apply_styles(root)
    nodes=list(root.iter())
    if len(nodes)>10_000:raise ValueError('SVG exceeds 10,000 XML elements.')
    masks={};resources=[]
    initial={'color':'black','fill':'black','fill-opacity':'1','fill-rule':'nonzero',
             'stroke':'none','stroke-opacity':'1','stroke-width':'1','color-interpolation':'sRGB'}
    def contextual_copy(node,context):
        result=deepcopy(node)
        for key,value in context.items():
            result.set(key,value);result.set('style',result.get('style','')+f';{key}:{value}')
        return result
    def collect_resources(node,parent,inside_defs=False,depth=0):
        if depth>64:raise ValueError('SVG style nesting exceeds 64 levels.')
        context=dict(parent);own=properties(node)
        for key,default in initial.items():
            value=own.get(key,'inherit')
            if value=='initial':context[key]=default
            elif value not in {'inherit','unset'}:context[key]=value
        kind=node.tag.split('}')[-1]
        if kind=='mask' and node.get('id'):masks[node.get('id')]=contextual_copy(node,context)
        resource=kind in {'defs','mask','linearGradient','radialGradient','clipPath','symbol'}
        if resource and not inside_defs:resources.append(contextual_copy(node,context))
        for child in node:collect_resources(child,context,inside_defs or resource,depth+1)
    collect_resources(root,initial)
    for node in nodes:
        value=properties(node).get('mask','none')
        node.set('data-morale-mask','')
        node.set('style',node.get('style','')+';data-morale-mask:')
        if value!='none':
            match=re.fullmatch(r"url\(\s*['\"]?#([^\s'\"()]+)['\"]?\s*\)",value)
            if not match or match[1] not in masks:raise ValueError('SVG mask must reference an existing local mask.')
            node.set('mask','none')
            node.set('style',node.get('style','')+f';mask:none;data-morale-mask:{match[1]}')
            node.set('data-morale-mask',match[1])
    references=[];occupied={0};gradients={}
    for node in nodes:
        inherited_color=properties(node).get('color')
        if inherited_color:
            color=svg.Color(inherited_color)
            if color.value is not None:occupied.add(int(color.hex[1:7],16))
        for key in ('fill','stroke'):
            value=properties(node).get(key)
            if value is None:continue
            if 'url(' in value.lower():
                match=re.fullmatch(r'url\(\s*[\'\"]?#([^\s\'\"()]+)[\'\"]?\s*\)',value)
                if not match:raise ValueError('SVG gradient paint must use a local reference without fallback paint.')
                references.append((node,key,match[1]))
            else:
                color=svg.Color(value)
                if color.value is not None:occupied.add(int(color.hex[1:7],16))
    marker=1;markers={}
    for node,key,ident in references:
        if ident not in markers:
            while marker in occupied:marker+=1
            occupied.add(marker)
            gradients[marker]=resolve_gradient(root,ident)
            markers[ident]=marker;marker+=1
        color=f'#{markers[ident]:06x}'
        node.set(key,color)
        node.set('style',node.get('style','')+f';{key}:{color}')
    for parent in nodes:
        for child in list(parent):
            if child.tag.split('}')[-1] in {'linearGradient','radialGradient','mask'}:parent.remove(child)
    paints=[]
    normalized,notes=checked_xml(ET.tostring(root,encoding='unicode'),allow_dashes=True,
                                 paint_sink=lambda *args:paints.append(args),
                                 layer_sink=lambda *args:paints.append(args))
    page=ET.fromstring(normalized)
    width=float(page.get('width'));height=float(page.get('height'))
    if not all(math.isfinite(v) and v>0 for v in (width,height)):
        raise ValueError('SVG page dimensions must be positive and finite.')
    factor=resolution/max(width,height)
    image=QImage(max(1,round(width*factor)),max(1,round(height*factor)),QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    # Build brushes before beginning paint so exceptions cannot leave a live
    # QPainter attached to a destroyed image during Python stack unwinding.
    prepared=[]
    for entry in paints:
        if isinstance(entry[0],str) and entry[0]=='mask-begin':
            _,ident,element,viewport=entry
            if ident in _mask_stack or len(_mask_stack)>=16:raise ValueError('SVG mask reference cycle or nesting limit exceeded.')
            from .svg_masks import render_mask
            m=element.transform
            if isinstance(element,svg.SVG) and element.viewbox is not None:m=svg.Matrix(element.viewbox.transform(element))*m
            world=QTransform(m.a,m.b,m.c,m.d,m.e,m.f)
            inverse,valid=world.inverted()
            original=QPainterPath()
            def collect(item):
                if item.values.get('display')=='none':return
                if isinstance(item,svg.Shape):original.addPath(inverse.map(geometry(item)))
                elif isinstance(item,(svg.Group,svg.SVG,svg.Use)):
                    for child in item:collect(child)
            if valid:collect(element)
            _mask_budget[0]-=image.width()*image.height()
            if _mask_budget[0]<0:raise ValueError('SVG masks exceed the rendering pixel budget.')
            mask_data=render_mask(masks[ident],original.boundingRect(),viewport,world,(width,height),
                                  resolution=resolution,definitions=resources,_mask_stack=_mask_stack+(ident,),_mask_budget=_mask_budget)
            prepared.append(('begin',mask_data));continue
        if len(entry)==2:
            prepared.append(entry);continue
        visible,element,paint_name,viewport=entry
        paint=getattr(element,paint_name)
        ident=int(paint.hex[1:7],16)
        if ident in gradients:
            m=element.transform;world=QTransform(m.a,m.b,m.c,m.d,m.e,m.f)
            inverse,valid=world.inverted()
            if not valid:continue
            original=inverse.map(geometry(element)).boundingRect()
            brush=gradient_brush(gradients[ident],original,viewport,world)
            opacity=paint.alpha/255
        else:
            brush=QBrush(QColor(paint.red,paint.green,paint.blue,paint.alpha))
            opacity=1.
        prepared.append((visible,brush,opacity))
    def begin_paint(target):
        painter=QPainter(target)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.scale(image.width()/width,image.height()/height)
        return painter
    stack=[(image,begin_paint(image),1.)]
    try:
        for entry in prepared:
            if len(entry)==2:
                action,opacity=entry
                if action=='begin':
                    if (len(stack)+1)*image.width()*image.height()>67_108_864:
                        raise ValueError('SVG opacity layers exceed the rendering memory limit.')
                    layer=QImage(image.size(),image.format());layer.fill(Qt.GlobalColor.transparent)
                    stack.append((layer,begin_paint(layer),opacity))
                else:
                    layer,painter,opacity=stack.pop();painter.end()
                    if isinstance(opacity,tuple):
                        from .svg_masks import apply_mask
                        mask,mode,interpolation=opacity
                        layer=apply_mask(layer,mask,mode=mode,interpolation=interpolation);opacity=1.
                    parent=stack[-1][1];parent.save()
                    parent.resetTransform();parent.setOpacity(opacity)
                    parent.drawImage(0,0,layer);parent.restore()
            else:
                visible,brush,opacity=entry
                painter=stack[-1][1];painter.setOpacity(opacity)
                painter.fillPath(visible,brush)
    finally:
        for _,painter,_ in reversed(stack):painter.end()
    return image,notes


def trace_svg_artwork(path, **settings):
    """Render SVG paints and reduce them to editable color regions."""
    from pathlib import Path
    from tempfile import TemporaryDirectory
    from .raster_trace import trace_image
    source=Path(path)
    if source.stat().st_size>2_000_000:raise ValueError('SVG artwork is limited to 2 MB.')
    image,notes=render_svg_artwork(source.read_text(encoding='utf-8-sig'),
                                   resolution=settings.get('resolution',128))
    with TemporaryDirectory(prefix='morale-svg-render-') as directory:
        raster=Path(directory)/'artwork.png'
        if not image.save(str(raster),'PNG'):raise ValueError('Could not encode rendered SVG artwork.')
        project,preview,stats=trace_image(raster,**settings)
    project.name=source.stem
    stats.setdefault('notes',[]).extend(notes)
    stats['notes'].append('SVG paints were rasterized and reduced to editable thread-color regions.')
    stats['source_kind']='rendered_svg'
    return project,preview,stats
