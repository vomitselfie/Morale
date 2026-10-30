"""SVG gradient brushes for painting validated geometry before color tracing.

This module does not load files or bypass SVG import validation.
"""
import math
import re
from copy import deepcopy
import svgelements as svg
from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor,QBrush,QLinearGradient,QRadialGradient,QGradient,QTransform


def resolve_gradient(root, ident):
    """Resolve a local gradient template without mutating the source XML.

    Only gradient attributes participate in template inheritance. In particular,
    a template's CSS color must not leak into stops cloned by its consumer.
    """
    nodes=list(root.iter())
    if len(nodes)>10_000:raise ValueError('SVG exceeds 10,000 XML elements.')
    contexts={}
    pending=[(root,{'color':'black','color-interpolation':'sRGB'},0)]
    while pending:
        node,parent,depth=pending.pop()
        if depth>64:raise ValueError('SVG gradient style nesting exceeds 64 levels.')
        context=dict(parent);own=properties(node)
        for key,initial in (('color','black'),('color-interpolation','sRGB')):
            value=own.get(key,'inherit')
            if value=='initial':context[key]=initial
            elif value not in {'inherit','unset'}:context[key]=value
        contexts[id(node)]=context
        pending.extend((child,context,depth+1) for child in node)
    ids={}
    for node in nodes:
        key=node.get('id')
        if key:
            if key in ids:raise ValueError('SVG contains duplicate IDs.')
            ids[key]=node
    common={'gradientUnits','gradientTransform','spreadMethod'}
    coordinates={'linearGradient':{'x1','y1','x2','y2'},
                 'radialGradient':{'cx','cy','r','fx','fy','fr'}}
    descriptive={'title','desc','metadata'}
    def resolve(key,stack):
        if key in stack:raise ValueError('SVG contains a circular gradient reference.')
        if len(stack)>=64:raise ValueError('SVG gradient reference nesting exceeds 64 levels.')
        node=ids.get(key)
        if node is None:raise ValueError('SVG gradient reference must name an existing local gradient.')
        kind=node.tag.split('}')[-1]
        if kind not in coordinates:raise ValueError('SVG paint reference must name a gradient.')
        result=deepcopy(node)
        for attribute,value in contexts[id(node)].items():
            result.set(attribute,value)
            result.set('style',result.get('style','')+f';{attribute}:{value}')
        href=result.attrib.pop('href',result.get('{http://www.w3.org/1999/xlink}href'))
        result.attrib.pop('{http://www.w3.org/1999/xlink}href',None)
        children=[child for child in result if child.tag.split('}')[-1] not in descriptive]
        if any(child.tag.split('}')[-1]!='stop' for child in children):
            raise ValueError('Unsupported SVG gradient child.')
        for child in list(result):result.remove(child)
        if href is not None:
            if not href.startswith('#') or len(href)==1:
                raise ValueError('SVG gradient templates must use local references.')
            template=resolve(href[1:],stack+(key,))
            inherited=common | (coordinates[kind] if template.tag.split('}')[-1]==kind else set())
            for attribute in inherited:
                if attribute not in result.attrib and attribute in template.attrib:
                    result.set(attribute,template.get(attribute))
            if not children:children=list(template)
        result.extend(deepcopy(children))
        return result
    return resolve(ident,())


def properties(node):
    return {**node.attrib,**{key.strip():value.strip() for part in node.get('style','').split(';') if ':' in part for key,value in [part.split(':',1)]}}


def number(value,percent=1.):
    text=str(value).strip()
    try:result=float(text[:-1])*percent/100 if text.endswith('%') else float(text)
    except ValueError as exc:raise ValueError('SVG gradient coordinates must be numbers or percentages.') from exc
    if not math.isfinite(result):raise ValueError('SVG gradient values must be finite.')
    return result


def linear_brush(node,bounds,viewport,world=None):
    if node.tag.split('}')[-1]!='linearGradient':raise ValueError('Expected an SVG linear gradient.')
    return gradient_brush(node,bounds,viewport,world)


def coordinate(value,percent=1.):
    """Resolve absolute SVG lengths at 96 pixels/inch in the local user space."""
    text=str(value).strip()
    match=re.fullmatch(r'([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)(px|mm|cm|in|pt|pc|Q)',text)
    if match:
        factors={'px':1.,'mm':96/25.4,'cm':96/2.54,'in':96.,'pt':96/72,'pc':16.,'Q':96/101.6}
        return number(number(match[1])*factors[match[2]])
    return number(value,percent)


def gradient_brush(node,bounds,viewport,world=None):
    """Create a brush in document space, using the original uncut object bounds."""
    kind=node.tag.split('}')[-1]
    if kind not in {'linearGradient','radialGradient'}:raise ValueError('Expected an SVG gradient.')
    attrs=properties(node)
    if 'href' in attrs or '{http://www.w3.org/1999/xlink}href' in attrs:
        raise ValueError('Resolve inherited SVG gradients before creating a brush.')
    interpolation=attrs.get('color-interpolation','sRGB')
    if interpolation not in {'sRGB','linearRGB','auto'}:raise ValueError('Unsupported SVG gradient color interpolation.')
    units=attrs.get('gradientUnits','objectBoundingBox')
    if units not in {'objectBoundingBox','userSpaceOnUse'}:raise ValueError('Unsupported SVG gradient units.')
    if not all(math.isfinite(v) and v>0 for v in viewport):raise ValueError('Invalid SVG gradient viewport.')
    spreads={'pad':QGradient.Spread.PadSpread,'repeat':QGradient.Spread.RepeatSpread,'reflect':QGradient.Spread.ReflectSpread}
    spread=attrs.get('spreadMethod','pad')
    if spread not in spreads:raise ValueError('Unsupported SVG gradient spread method.')
    matrix=svg.Matrix(attrs.get('gradientTransform',''))
    if not all(math.isfinite(v) for v in (matrix.a,matrix.b,matrix.c,matrix.d,matrix.e,matrix.f)):
        raise ValueError('SVG gradient transform must be finite.')
    transform=QTransform(matrix.a,matrix.b,matrix.c,matrix.d,matrix.e,matrix.f)
    if not all(math.isfinite(v) for v in (bounds.left(),bounds.top(),bounds.width(),bounds.height())):
        raise ValueError('SVG gradient bounds must be finite.')
    if units=='objectBoundingBox':
        if bounds.width()<=0 or bounds.height()<=0:return QBrush(QColor(0,0,0,0))
        transform=transform*QTransform(bounds.width(),0,0,bounds.height(),bounds.left(),bounds.top())
    if world is not None:
        if not world.isAffine() or not all(math.isfinite(v) for v in (world.m11(),world.m12(),world.m21(),world.m22(),world.dx(),world.dy())):
            raise ValueError('SVG gradient world transform must be finite and affine.')
        transform=transform*world
    if not transform.isInvertible():return QBrush(QColor(0,0,0,0))
    extent=(1.,1.) if units=='objectBoundingBox' else viewport
    if kind=='linearGradient':
        x1=coordinate(attrs.get('x1','0%'),extent[0]);y1=coordinate(attrs.get('y1','0%'),extent[1])
        x2=coordinate(attrs.get('x2','100%'),extent[0]);y2=coordinate(attrs.get('y2','0%'),extent[1])
        degenerate=x1==x2 and y1==y2
        gradient=QLinearGradient(x1,y1,x2,y2)
    else:
        cx=coordinate(attrs.get('cx','50%'),extent[0]);cy=coordinate(attrs.get('cy','50%'),extent[1])
        fx=coordinate(attrs.get('fx',cx),extent[0]);fy=coordinate(attrs.get('fy',cy),extent[1])
        radius_basis=math.hypot(*extent)/math.sqrt(2)
        radius=coordinate(attrs.get('r','50%'),radius_basis)
        focal_radius=coordinate(attrs.get('fr','0%'),radius_basis)
        if radius<0 or focal_radius<0:raise ValueError('SVG gradient radii must be nonnegative.')
        degenerate=False
        # The extended constructor preserves an external focus instead of Qt's
        # simple radial constructor, which moves it inside the end circle.
        gradient=QRadialGradient(QPointF(cx,cy),radius,QPointF(fx,fy),focal_radius)
    stops=[];last=0.
    for child in node:
        if child.tag.split('}')[-1]!='stop':raise ValueError('Unsupported SVG gradient child.')
        values=properties(child);offset=max(last,min(1.,max(0.,number(values.get('offset','0')))))
        raw=values.get('stop-color','black')
        if raw=='currentColor':raw=values.get('color',attrs.get('color','black'))
        color=svg.Color(raw)
        if color.value is None:raise ValueError('Unsupported SVG gradient stop color.')
        rgba=QColor(color.red,color.green,color.blue,color.alpha)
        rgba.setAlphaF(rgba.alphaF()*max(0.,min(1.,number(values.get('stop-opacity','1')))))
        stops.append((offset,rgba));last=offset
        if len(stops)>256:raise ValueError('SVG gradient exceeds 256 stops.')
    if not stops:return QBrush(QColor(0,0,0,0))
    if len(stops)==1:return QBrush(stops[0][1])
    if kind=='radialGradient' and cx==fx and cy==fy and radius==focal_radius:
        return QBrush(QColor(0,0,0,0))
    if degenerate:return QBrush(stops[-1][1])
    # Qt replaces stops at identical offsets. Preserve the incoming color just
    # before the boundary and the last declared color at the boundary itself.
    # One representable float step avoids a visible artificial transition band.
    qt_stops=[];index=0
    while index<len(stops):
        offset,first=stops[index];end=index+1
        while end<len(stops) and stops[end][0]==offset:end+=1
        if end-index>1 and offset>0:
            before=math.nextafter(offset,0.)
            if not qt_stops or before>qt_stops[-1][0]:qt_stops.append((before,first))
        qt_stops.append((offset,stops[end-1][1]));index=end
    if interpolation=='linearRGB':qt_stops=linear_light_stops(qt_stops)
    gradient.setStops(qt_stops)
    # SVG interpolates RGB and alpha independently, not premultiplied colors.
    gradient.setInterpolationMode(QGradient.InterpolationMode.ComponentInterpolation)
    gradient.setSpread(spreads[spread])
    brush=QBrush(gradient);brush.setTransform(transform)
    return brush


def linear_light_stops(stops):
    """Approximate linear-light RGB with adaptive sRGB stops for Qt painting."""
    def linear(v):return v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4
    def encoded(v):return 12.92*v if v<=.0031308 else 1.055*v**(1/2.4)-.055
    result=[stops[0]]
    for (start,left),(end,right) in zip(stops,stops[1:]):
        a=left.getRgbF();b=right.getRgbF()
        al=[linear(v) for v in a[:3]];bl=[linear(v) for v in b[:3]]
        def sample(t):
            return tuple(encoded(x+(y-x)*t) for x,y in zip(al,bl))+(a[3]+(b[3]-a[3])*t,)
        def subdivide(lo,hi,lc,rc,depth):
            mid=(lo+hi)/2;mc=sample(mid)
            error=max(abs(mc[i]-(lc[i]+rc[i])/2) for i in range(3))
            if error>.25/255 and depth<12 and end-start>1e-12:
                subdivide(lo,mid,lc,mc,depth+1);subdivide(mid,hi,mc,rc,depth+1)
            else:
                if len(result)>=16384:raise ValueError('SVG linear-light gradient exceeds the rendering stop limit.')
                result.append((start+(end-start)*hi,QColor.fromRgbF(*rc)))
        subdivide(0.,1.,a,b,0)
    return result
