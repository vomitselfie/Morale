"""Geometry-based stitch suggestions for traced regions, in physical millimeters."""
from copy import deepcopy
import math

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainterPath

from .model import Project
from .engine import generate


def outline_path(rings):
    path=QPainterPath(); path.setFillRule(Qt.FillRule.OddEvenFill)
    for ring in rings:
        path.moveTo(*ring[0])
        for point in ring[1:]: path.lineTo(*point)
        path.closeSubpath()
    return path


def is_closed_band(obj):
    rings=obj.rings()
    if len(rings)!=2:return False
    a,b=(outline_path([ring]) for ring in rings)
    return a.contains(b) or b.contains(a)


def area(path,split_crossings=False):
    # Qt's odd-even output can contain nested contours with equal winding.
    # Integrate paired crossings instead of summing signed contour areas.
    rings=[[(p.x(),p.y()) for p in polygon] for polygon in path.toSubpathPolygons()]
    edges=[(a,b) for ring in rings for a,b in zip(ring,ring[1:]+ring[:1]) if a[1]!=b[1]]
    levels={y for ring in rings for x,y in ring}
    if split_crossings:
        ordered=sorted(edges,key=lambda edge:min(edge[0][1],edge[1][1]))
        for index,(a,b) in enumerate(ordered):
            for c,d in ordered[index+1:]:
                if min(c[1],d[1])>=max(a[1],b[1]): break
                if max(a[0],b[0])<min(c[0],d[0]) or max(c[0],d[0])<min(a[0],b[0]): continue
                ux,uy=b[0]-a[0],b[1]-a[1]; vx,vy=d[0]-c[0],d[1]-c[1]
                determinant=ux*vy-uy*vx
                if abs(determinant)<1e-12: continue
                t=((c[0]-a[0])*vy-(c[1]-a[1])*vx)/determinant
                u=((c[0]-a[0])*uy-(c[1]-a[1])*ux)/determinant
                if 0<t<1 and 0<u<1: levels.add(a[1]+t*uy)
    levels=sorted(levels)
    # Sweep upward, keeping only edges that span the current band.
    ordered=sorted(edges,key=lambda edge:min(edge[0][1],edge[1][1]))
    active=[]; position=0; total=0
    for low,high in zip(levels,levels[1:]):
        y=(low+high)/2
        while position<len(ordered) and min(ordered[position][0][1],ordered[position][1][1])<=y:
            active.append(ordered[position]); position+=1
        active=[(a,b) for a,b in active if max(a[1],b[1])>y]
        hits=sorted(a[0]+(b[0]-a[0])*(y-a[1])/(b[1]-a[1]) for a,b in active)
        total+=(high-low)*sum(b-a for a,b in zip(hits[::2],hits[1::2]))
    return total


def difference_area(a,b):
    # Odd-even parity across both paths is their symmetric difference. Avoid Qt
    # boolean operations on nearly coincident boundaries; integrate directly.
    combined=QPainterPath(a); combined.addPath(b)
    return area(combined,split_crossings=True)


def column_pairs(obj):
    """Slice a single monotone region across its principal axis.

    Holes, branching, wide regions and inaccurate reconstructions are rejected.
    A later skeleton/branching planner can handle shapes that fold around this axis.
    """
    rings=obj.rings()
    if len(rings)!=1: return None,'Holes or separate contours require fill.'
    ring=rings[0]
    # Uniform boundary samples avoid bias from densely flattened curve segments.
    samples=[]
    for a,b in zip(ring,ring[1:]+ring[:1]):
        count=max(1,math.ceil(math.dist(a,b)/.5))
        if len(samples)+count>20000: return None,'Contour is too complex for automatic rails.'
        samples.extend((a[0]+(b[0]-a[0])*i/count,a[1]+(b[1]-a[1])*i/count) for i in range(count))
    cx=sum(p[0] for p in samples)/len(samples); cy=sum(p[1] for p in samples)/len(samples)
    xx=sum((x-cx)**2 for x,y in samples); yy=sum((y-cy)**2 for x,y in samples)
    xy=sum((x-cx)*(y-cy) for x,y in samples)
    angle=.5*math.atan2(2*xy,xx-yy); c=math.cos(angle); s=math.sin(angle)
    local=[((x-cx)*c+(y-cy)*s,-(x-cx)*s+(y-cy)*c) for x,y in ring]
    lo=min(x for x,y in local); hi=max(x for x,y in local); length=hi-lo
    if length<1: return None,'Region is too short for an automatic column.'
    # Include vertices as stations so corners are not bridged by coarse sampling.
    epsilon=min(.0001,length/10000)
    stations=sorted({lo+epsilon,hi-epsilon,*[x for x,y in local if lo+epsilon<x<hi-epsilon],
                     *[lo+length*i/math.ceil(length/.5) for i in range(1,math.ceil(length/.5))]})
    distinct=[]
    for station in stations:
        if not distinct or station-distinct[-1]>1e-6: distinct.append(station)
    stations=distinct
    if len(stations)>1000: return None,'Contour is too complex for automatic rails.'
    pairs=[]; widths=[]
    for x in stations:
        hits=[]
        for a,b in zip(local,local[1:]+local[:1]):
            if (a[0]<=x<b[0]) or (b[0]<=x<a[0]):
                hits.append(a[1]+(b[1]-a[1])*(x-a[0])/(b[0]-a[0]))
        hits.sort()
        if len(hits)!=2: return None,'Branching or folded contour requires fill.'
        widths.append(hits[1]-hits[0])
        pairs.extend((cx+x*c-y*s,cy+x*s+y*c) for y in hits)
    maximum=max(widths)
    if maximum>6: return None,f'Column spans {maximum:.2f} mm; keep fill above 6 mm.'
    if length<maximum*2: return None,'Broad compact region suits fill.'
    reconstructed=outline_path([pairs[::2]+list(reversed(pairs[1::2]))])
    original=outline_path(rings)
    difference=difference_area(original,reconstructed)
    if difference>max(.02,area(original)*.01): return None,'Rail reconstruction changes too much of the outline.'
    return (pairs,maximum),f'Unbranched column, maximum width {maximum:.2f} mm.'


def choose_stitches(project,mode='auto',overrides=None,seams=None):
    Project.loads(project.dumps())
    if not isinstance(mode,str) or mode not in {'auto','fill'}: raise ValueError('Choose automatic stitches or all fill.')
    overrides={} if overrides is None else overrides
    if not isinstance(overrides,dict) or any(not isinstance(k,str) or not k.isdecimal() or int(k)>=len(project.objects)
           or not isinstance(v,str) or v not in {'auto','fill','satin','running'} for k,v in overrides.items()):
        raise ValueError('Invalid region stitch overrides.')
    seams={} if seams is None else seams
    if not isinstance(seams,dict) or any(not isinstance(k,str) or not k.isdecimal() or int(k)>=len(project.objects)
            or isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<=v<100 for k,v in seams.items()):
        raise ValueError('Band seam positions must be percentages from 0 up to 100 (exclusive).')
    result=deepcopy(project); decisions=[]
    for index,source in enumerate(project.objects):
        requested=overrides.get(str(index),mode)
        seam=seams.get(str(index),0);closed=is_closed_band(source)
        candidate=deepcopy(source); selected='fill'; reason='Fill selected.'; width=None
        fixed=source.stitch_type in {'running','triple'}
        if fixed:
            selected=source.stitch_type;reason='Vector stroke retained as a running outline; border width is not inferred.'
        elif requested!='fill':
            column,reason=column_pairs(source)
            if column is None:
                from .curved_columns import curved_pairs,closed_pairs
                column=closed_pairs(source,seam) if closed else curved_pairs(source)
                if column is not None: reason=f"{'Closed band' if closed else 'Curved ribbon'}, maximum rail span {column[1]:.2f} mm."
                if closed and column is not None: reason+=f' Seam {seam:g}% around the outer boundary.'
            if column is not None:
                pairs,width=column
                selected=('running' if width<.8 else 'satin') if requested=='auto' else requested
                points=[((a[0]+b[0])/2,(a[1]+b[1])/2) for a,b in zip(pairs[::2],pairs[1::2])] if selected=='running' else pairs
                candidate.kind='path' if selected=='running' else 'satin'
                candidate.stitch_type=selected
                candidate.rotation=0; candidate.flip_x=candidate.flip_y=False
                xs,ys=zip(*points)
                candidate.x=(min(xs)+max(xs))/2; candidate.y=(min(ys)+max(ys))/2
                candidate.width=max(.1,max(xs)-min(xs)); candidate.height=max(.1,max(ys)-min(ys))
                candidate.points=[[max(-.5,min(.5,(x-candidate.x)/candidate.width)),max(-.5,min(.5,(y-candidate.y)/candidate.height))] for x,y in points]
                candidate.contours=[]; candidate.handles=[]; candidate.lettering={}
                candidate.underlay=source.underlay and selected=='satin'
                try:
                    Project.loads(Project(objects=[candidate]).dumps())
                    generate(Project(objects=[candidate]))
                except ValueError:
                    candidate=deepcopy(source); selected='fill'; reason='Rail geometry needs manual correction; kept fill.'
                else:
                    if selected=='running': reason+=' Centerline running stitches replace the filled width.'
        result.objects[index]=candidate
        decisions.append({'region':index,'requested':requested,'selected':selected,'reason':reason,'width_mm':width,
                          'closed_band':closed,'seam_percent':seam,'fixed_stitch':fixed})
    Project.loads(result.dumps()); generate(result)
    return result,decisions
