"""Rigid shaped-glyph clusters placed along a saved polyline baseline."""
from bisect import bisect_right
from copy import deepcopy
import math
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextLayout,QPainterPath,QTransform
from .model import DesignObject,Project
from .engine import generate


def clean_baseline(points):
    if not isinstance(points,(list,tuple)) or not 2<=len(points)<=2000:raise ValueError('Choose a baseline with 2–2,000 points.')
    result=[]
    for point in points:
        if not isinstance(point,(list,tuple)) or len(point)!=2 or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or abs(v)>2000 for v in point):
            raise ValueError('Baseline points must be finite millimeter coordinates within ±2,000.')
        if not result or math.dist(result[-1],point)>1e-8:result.append(list(point))
    if len(result)<2:raise ValueError('The lettering baseline has no length.')
    return result


def layout_on_path(text,font,height,baseline):
    layout=QTextLayout(text,font);layout.beginLayout();line=layout.createLine();line.setLineWidth(1_000_000);layout.endLayout()
    flags=QTextLayout.GlyphRunRetrievalFlag
    groups={}
    for run in layout.glyphRuns(0,-1,flags.RetrieveGlyphIndexes|flags.RetrieveGlyphPositions|flags.RetrieveStringIndexes):
        glyphs,positions,indices=run.glyphIndexes(),run.positions(),run.stringIndexes()
        if not len(glyphs)==len(positions)==len(indices):raise ValueError('The font returned incomplete glyph positions.')
        for glyph,position,index in zip(glyphs,positions,indices):
            outline=run.rawFont().pathForGlyph(glyph)
            if outline.isEmpty():continue
            if index not in groups:groups[index]=QPainterPath();groups[index].setFillRule(Qt.FillRule.WindingFill)
            groups[index].addPath(QTransform().translate(position.x(),position.y()-line.ascent()).map(outline))
    flat=QPainterPath();flat.setFillRule(Qt.FillRule.WindingFill)
    for group in groups.values():flat.addPath(group)
    bounds=flat.boundingRect()
    if bounds.isEmpty():raise ValueError('The font produced no usable outlines.')
    scale=height/bounds.height();lengths=[0.]
    for a,b in zip(baseline,baseline[1:]):lengths.append(lengths[-1]+math.dist(a,b))
    width=bounds.width()*scale
    if width>lengths[-1]+1e-8:raise ValueError('The text is longer than the baseline. Reduce letter height/spacing or use a longer path.')
    offset=(lengths[-1]-width)/2;result=QPainterPath();result.setFillRule(Qt.FillRule.WindingFill)
    for group in groups.values():
        center=group.boundingRect().center().x();distance=offset+(center-bounds.left())*scale
        index=min(len(baseline)-2,max(0,bisect_right(lengths,distance)-1))
        a,b=baseline[index:index+2];fraction=(distance-lengths[index])/(lengths[index+1]-lengths[index])
        x=a[0]+fraction*(b[0]-a[0]);y=a[1]+fraction*(b[1]-a[1]);angle=math.degrees(math.atan2(b[1]-a[1],b[0]-a[0]))
        transform=QTransform().translate(x,y).rotate(angle).scale(scale,scale).translate(-center,0)
        result.addPath(transform.map(group))
    return QTransform().scale(.05,.05).map(QTransform().scale(20,20).map(result).simplified())


def make_path_lettering(text,family,height=15.,spacing=100.,previous=None,*,baseline=None,stitch_type=None):
    from .lettering import lettering_font
    font,actual_family=lettering_font(text,family,height,spacing)
    if baseline is None:
        if previous is None or previous.lettering.get('layout')!='path':raise ValueError('Select a drawn path for the lettering baseline.')
        baseline=[[x*previous.width,y*previous.height] for x,y in previous.lettering['baseline']]
    elif previous is not None:
        baseline=clean_baseline(baseline)
        transform=QTransform().translate(previous.x,previous.y).rotate(previous.rotation).scale(-1 if previous.flip_x else 1,-1 if previous.flip_y else 1)
        inverse,_=transform.inverted();baseline=[list(inverse.map(*p)) for p in baseline]
    baseline=clean_baseline(baseline)
    path=layout_on_path(text,font,height,baseline)
    rings=[]
    for polygon in path.toSubpathPolygons(QTransform().scale(20,20)):
        ring=[[p.x()/20,p.y()/20] for p in polygon]
        if len(ring)>1 and ring[0]==ring[-1]:ring.pop()
        if len(ring)>=3:rings.append(ring)
    if not rings or len(rings)>256 or sum(map(len,rings))>20_000:raise ValueError('Path lettering exceeds the supported outline complexity. Use shorter text or a simpler font.')
    xs,ys=zip(*(p for ring in rings for p in ring));cx=(min(xs)+max(xs))/2;cy=(min(ys)+max(ys))/2
    width=max(.1,max(xs)-min(xs));total_height=max(.1,max(ys)-min(ys))
    obj=deepcopy(previous) if previous is not None else DesignObject()
    obj.x,obj.y=previous.transform([(cx/previous.width,cy/previous.height)])[0] if previous is not None else (cx,cy)
    obj.kind='compound';obj.name=text[:200];obj.width=width;obj.height=total_height
    obj.points=[];obj.handles=[];obj.stitch_data=[]
    obj.contours=[[[(x-cx)/width,(y-cy)/total_height] for x,y in ring] for ring in rings]
    obj.lettering={'text':text,'family':actual_family,'height':height,'spacing':spacing,'layout':'path','curve':60,'layout_height':total_height,
                  'baseline':[[(x-cx)/width,(y-cy)/total_height] for x,y in baseline]}
    from .lettering import finish_lettering
    return finish_lettering(obj,previous,stitch_type)
