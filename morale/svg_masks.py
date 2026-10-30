"""Bounded alpha/luminance compositing for rendered SVG mask layers.

Coordinate helpers preserve original shape bounds. Reference resolution and
mask-child rendering remain the responsibility of the SVG renderer.
"""
from PySide6.QtGui import QImage


def apply_mask(source,mask,*,mode='luminance',interpolation='sRGB'):
    """Return masked pixels without modifying either input image."""
    if mode not in {'alpha','luminance'}:raise ValueError('Unsupported SVG mask type.')
    if interpolation not in {'sRGB','linearRGB','auto'}:raise ValueError('Unsupported SVG mask color interpolation.')
    if source.isNull() or mask.isNull() or source.size()!=mask.size():
        raise ValueError('SVG mask and artwork must have matching nonempty dimensions.')
    if source.width()*source.height()>4_194_304:
        raise ValueError('SVG mask layers are limited to four megapixels.')
    result=source.convertToFormat(QImage.Format.Format_RGBA8888)
    sampled=mask.convertToFormat(QImage.Format.Format_RGBA8888)
    # bits() detaches result from implicitly shared source storage before writing.
    pixels=result.bits();values=sampled.constBits()
    if interpolation=='linearRGB':
        channels=[v/255/12.92 if v/255<=.04045 else ((v/255+.055)/1.055)**2.4 for v in range(256)]
    else:channels=[v/255 for v in range(256)]
    for y in range(result.height()):
        output_row=y*result.bytesPerLine();mask_row=y*sampled.bytesPerLine()
        for x in range(result.width()):
            offset=output_row+x*4;index=mask_row+x*4
            coverage=values[index+3]/255
            if mode=='luminance':
                coverage*=.2125*channels[values[index]]+.7154*channels[values[index+1]]+.0721*channels[values[index+2]]
            pixels[offset+3]=round(pixels[offset+3]*coverage)
    return result.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)


def mask_geometry(node,bounds,viewport,world):
    """Return document-space mask region and mask-content transform.

    Bounds are the original, unclipped bounds in the referencing element's user
    space. This function does not fetch references or render mask children.
    """
    import math
    from PySide6.QtGui import QPainterPath,QTransform
    from .svg_gradients import coordinate,properties
    attrs=properties(node)
    if node.tag.split('}')[-1]!='mask':raise ValueError('Expected an SVG mask.')
    units=attrs.get('maskUnits','objectBoundingBox')
    content_units=attrs.get('maskContentUnits','userSpaceOnUse')
    if units not in {'objectBoundingBox','userSpaceOnUse'} or content_units not in {'objectBoundingBox','userSpaceOnUse'}:
        raise ValueError('Unsupported SVG mask coordinate units.')
    if not all(math.isfinite(v) and v>0 for v in viewport):raise ValueError('Invalid SVG mask viewport.')
    if not all(math.isfinite(v) for v in (bounds.left(),bounds.top(),bounds.width(),bounds.height())):
        raise ValueError('SVG mask bounds must be finite.')
    if not world.isAffine() or not all(math.isfinite(v) for v in (world.m11(),world.m12(),world.m21(),world.m22(),world.dx(),world.dy())):
        raise ValueError('SVG mask transform must be finite and affine.')
    extent=(1.,1.) if units=='objectBoundingBox' else viewport
    x=coordinate(attrs.get('x','-10%'),extent[0]);y=coordinate(attrs.get('y','-10%'),extent[1])
    width=coordinate(attrs.get('width','120%'),extent[0]);height=coordinate(attrs.get('height','120%'),extent[1])
    if width<0 or height<0:raise ValueError('SVG mask dimensions must be nonnegative.')
    box=QTransform(bounds.width(),0,0,bounds.height(),bounds.left(),bounds.top())
    region=QPainterPath()
    if width>0 and height>0 and world.isInvertible() and not (
        'objectBoundingBox' in {units,content_units} and (bounds.width()<=0 or bounds.height()<=0)
    ):region.addRect(x,y,width,height)
    region=(box*world if units=='objectBoundingBox' else world).map(region)
    content=box*world if content_units=='objectBoundingBox' else QTransform(world)
    return region,content


def render_mask(node,bounds,viewport,world,page_size,*,resolution=512,definitions=(),_mask_stack=(),_mask_budget=None):
    """Render one mask's children into an aligned document-sized image.

    Local resources can be supplied as definition elements. Nested masks share
    the document reference stack and total mask-rendering pixel budget.
    """
    from copy import deepcopy
    import xml.etree.ElementTree as ET
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QPainter
    from .svg_gradients import properties
    from .svg_render import render_svg_artwork
    region,content=mask_geometry(node,bounds,viewport,world)
    attrs=properties(node)
    mode=attrs.get('mask-type','luminance')
    if mode not in {'alpha','luminance'}:raise ValueError('Unsupported SVG mask type.')
    interpolation=attrs.get('color-interpolation','sRGB')
    if interpolation not in {'sRGB','linearRGB','auto'}:raise ValueError('Unsupported SVG mask color interpolation.')
    root=ET.Element('svg',width=str(page_size[0]),height=str(page_size[1]))
    resources=ET.SubElement(root,'defs')
    resources.extend(deepcopy(list(definitions)))
    extent=(1.,1.) if attrs.get('maskContentUnits')=='objectBoundingBox' else viewport
    wrapper=ET.SubElement(root,'svg',width=str(extent[0]),height=str(extent[1]),overflow='visible',
                          transform=f'matrix({content.m11()} {content.m12()} {content.m21()} {content.m22()} {content.dx()} {content.dy()})')
    # Keep presentation styles on a group; mask geometry attributes must not
    # leak into the nested viewport used to resolve content percentages.
    group=ET.SubElement(wrapper,'g')
    for key in ('color','fill','fill-opacity','fill-rule','stroke','stroke-opacity','stroke-width','opacity','color-interpolation'):
        if key in attrs:group.set(key,attrs[key])
    group.extend(deepcopy(list(node)))
    # The original definitions remain available for external references. Give
    # cloned mask content fresh IDs so its internal references stay local.
    import re
    occupied={item.get('id') for item in root.iter() if item.get('id')}
    mapping={};serial=0
    for item in group.iter():
        ident=item.get('id')
        if not ident:continue
        if ident in mapping:raise ValueError('SVG mask content contains duplicate IDs.')
        while True:
            serial+=1;candidate=f'morale-mask-content-{serial}'
            if candidate not in occupied:break
        occupied.add(candidate);mapping[ident]=candidate;item.set('id',candidate)
    def reference(match):
        ident=match.group(2)
        return f'url(#{mapping[ident]})' if ident in mapping else match.group(0)
    for item in group.iter():
        for key,value in list(item.attrib.items()):
            if key in {'href','{http://www.w3.org/1999/xlink}href'} and value.startswith('#'):
                item.set(key,'#'+mapping.get(value[1:],value[1:]))
            elif key!='id':item.set(key,re.sub(r"url\(\s*(['\"]?)#([^\s'\"()]+)\1\s*\)",reference,value))
    rendered,_=render_svg_artwork(ET.tostring(root,encoding='unicode'),resolution=resolution,_mask_stack=_mask_stack,_mask_budget=_mask_budget)
    clipped=QImage(rendered.size(),rendered.format());clipped.fill(Qt.GlobalColor.transparent)
    painter=QPainter(clipped)
    try:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.scale(rendered.width()/page_size[0],rendered.height()/page_size[1])
        painter.setClipPath(region)
        painter.resetTransform();painter.drawImage(0,0,rendered)
    finally:painter.end()
    return clipped,mode,interpolation
