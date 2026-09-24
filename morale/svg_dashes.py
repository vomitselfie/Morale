"""SVG dash lengths translated to Qt's stroke-width-relative pattern units."""
import math
import re
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainterPath,QTransform

_LENGTH=re.compile(r'([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)(px|mm|cm|in|pt|pc|Q)?\Z')
_UNITS={'':1,'px':1,'mm':96/25.4,'cm':96/2.54,'in':96,'pt':96/72,'pc':16,'Q':96/101.6}


def length(value):
    match=_LENGTH.fullmatch(str(value).strip())
    if match is None:
        raise ValueError('SVG dashes require numbers or absolute lengths; convert percentage/font-relative dashes to paths first.')
    result=float(match[1])*_UNITS[match[2] or '']
    if not math.isfinite(result):raise ValueError('SVG dash lengths must be finite.')
    return result


def configure_dashes(stroker,geometry,values,width):
    raw=str(values.get('stroke-dasharray','none')).strip()
    if raw=='none':return QPainterPath()
    tokens=re.split(r'[\s,]+',raw)
    if not raw or raw.startswith(',') or raw.endswith(',') or re.search(r',\s*,',raw) or len(tokens)>256:
        raise ValueError('SVG dash patterns require 1–256 lengths.')
    pattern=[length(token) for token in tokens]
    if any(v<0 for v in pattern):raise ValueError('SVG dash lengths cannot be negative.')
    if len(pattern)%2:pattern*=2
    total=sum(pattern)
    if not math.isfinite(total):raise ValueError('SVG dash pattern is too large.')
    if total==0:return QPainterPath()  # SVG defines an all-zero pattern as a solid stroke.
    offset=length(values.get('stroke-dashoffset',0))%total
    # pathLength is an element attribute, not an inherited presentation style.
    attributes=values.get('attributes',values)
    if 'pathLength' in attributes:
        raw_length=str(attributes['pathLength']).strip()
        match=_LENGTH.fullmatch(raw_length)
        if match is None or match[2] is not None:
            raise ValueError('SVG pathLength must be a unitless positive number.')
        authored=float(match[1])
        if not math.isfinite(authored) or authored<=0:
            raise ValueError('SVG pathLength must be finite and positive; convert zero-calibrated paths to outlines first.')
        actual=QTransform.fromScale(20,20).map(geometry).length()/20
        factor=actual/authored
        scaled=[v*factor for v in pattern]
        if not math.isfinite(factor) or factor<=0 or any(not math.isfinite(v) or (old>0 and v==0) for old,v in zip(pattern,scaled)):
            raise ValueError('SVG pathLength calibration exceeds supported precision.')
        pattern=scaled;total=sum(pattern);offset*=factor
        if not math.isfinite(total) or not math.isfinite(offset):raise ValueError('SVG pathLength calibration is too large.')
    # Bound the work before Qt allocates the expanded outline. Each subpath
    # restarts the pattern; control polygons conservatively bound curve length.
    bound=0.;previous=None;subpaths=0
    for i in range(geometry.elementCount()):
        point=geometry.elementAt(i)
        if point.isMoveTo():subpaths+=1
        elif previous is not None:bound+=math.hypot(point.x-previous.x,point.y-previous.y)
        previous=point
    estimate=(bound/total+subpaths+1)*len(pattern)/2
    if not math.isfinite(estimate) or estimate>2000:
        raise ValueError('SVG dashes exceed 2,000 candidate pieces. Increase dash spacing or simplify the path.')
    relative=[v/width for v in pattern]
    if any(not math.isfinite(v) for v in relative) or not math.isfinite(offset/width):
        raise ValueError('SVG dash lengths are too large relative to stroke width.')
    stroker.setDashPattern(relative)
    stroker.setDashOffset(offset/width)

    dots=QPainterPath();dots.setFillRule(Qt.FillRule.WindingFill)
    if stroker.capStyle()==Qt.PenCapStyle.FlatCap or not any(v==0 for v in pattern[::2]):return dots
    # Qt omits zero-length dashes. SVG round/square caps make visible dots.
    parts=[];part=None;i=0
    while i<geometry.elementCount():
        e=geometry.elementAt(i)
        if e.isMoveTo():
            part=QPainterPath();part.moveTo(e.x,e.y);parts.append(part)
        elif e.isCurveTo():
            b,c=geometry.elementAt(i+1),geometry.elementAt(i+2)
            part.cubicTo(e.x,e.y,b.x,b.y,c.x,c.y);i+=2
        else:part.lineTo(e.x,e.y)
        i+=1
    zero_positions=[];cursor=0.
    for i,value in enumerate(pattern):
        if i%2==0 and value==0:zero_positions.append(cursor)
        cursor+=value
    for part in parts:
        size=part.length()
        for position in zero_positions:
            start=(position-offset)%total
            for repeat in range(max(0,math.floor((size-start)/total)+1)):
                distance=start+repeat*total;t=part.percentAtLength(distance);point=part.pointAtPercent(t)
                dot=QPainterPath()
                if stroker.capStyle()==Qt.PenCapStyle.RoundCap:dot.addEllipse(point,width/2,width/2)
                else:
                    dot.addRect(-width/2,-width/2,width,width)
                    dot=QTransform().translate(point.x(),point.y()).rotate(-part.angleAtPercent(t)).map(dot)
                dots.addPath(dot)
    return dots
