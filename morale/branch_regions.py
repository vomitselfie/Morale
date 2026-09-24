"""Partition suitable branching silhouettes at changes in cross-section topology."""
from copy import deepcopy
import math
import uuid
from PySide6.QtGui import QPainterPath,QTransform
from .model import Project
from .geometry import replace_contours
from .auto_digitize import choose_stitches,outline_path,difference_area


def _partition(obj,angle):
    c,s=math.cos(angle),math.sin(angle)
    local=[(x*c+y*s,-x*s+y*c) for x,y in obj.rings()[0]]
    levels=sorted({round(y,6) for x,y in local})
    if len(levels)>2000:return None
    bands=[]
    for low,high in zip(levels,levels[1:]):
        if high-low<.03:continue
        y=(low+high)/2
        hits=sorted(a[0]+(b[0]-a[0])*(y-a[1])/(b[1]-a[1]) for a,b in zip(local,local[1:]+local[:1])
                    if min(a[1],b[1])<=y<max(a[1],b[1]) and a[1]!=b[1])
        if len(hits)%2:return None
        widths=[b-a for a,b in zip(hits[::2],hits[1::2])]
        if widths:bands.append((low,high,len(widths),max(widths)))
    cuts=[]
    for a,b in zip(bands,bands[1:]):
        topology=a[2]!=b[2]
        abrupt=min(a[3],b[3])>=1 and max(a[3],b[3])>6 and max(a[3],b[3])>2*min(a[3],b[3])
        if topology or abrupt:cuts.append((a[1]+b[0])/2)
    if not cuts or len(cuts)>12:return None
    path=QTransform.fromScale(100,100).map(outline_path([local]))
    bounds=path.boundingRect();pieces=[]
    for low,high in zip([levels[0]-1]+cuts,cuts+[levels[-1]+1]):
        clip=QPainterPath();clip.addRect(bounds.left()-1,low*100,bounds.width()+2,(high-low)*100)
        part=path.intersected(clip).simplified()
        for polygon in part.toSubpathPolygons():
            points=[(p.x()/100,p.y()/100) for p in polygon]
            if len(points)>1 and math.dist(points[0],points[-1])<1e-6:points.pop()
            # Qt clipping can leave zero-area backtracking tails along a cut.
            # Remove collinear excursions before they can become stitch rails.
            changed=True
            while changed and len(points)>=3:
                changed=False
                for i,b in enumerate(points):
                    a=points[i-1];following=points[(i+1)%len(points)]
                    if abs((b[0]-a[0])*(following[1]-b[1])-(b[1]-a[1])*(following[0]-b[0]))<1e-8:
                        points.pop(i);changed=True;break
            if len(points)<3:continue
            ring=[(x*c-y*s,x*s+y*c) for x,y in points]
            candidate=deepcopy(obj);candidate.kind='compound';candidate.contours=[]
            candidate.points=[];candidate.handles=[]
            try:candidate=replace_contours(candidate,[ring])
            except ValueError:return None
            candidate.id=uuid.uuid4().hex;pieces.append(candidate)
    if not 2<=len(pieces)<=24:return None
    combined=outline_path([ring for obj in pieces for ring in obj.rings()])
    if difference_area(outline_path(obj.rings()),combined)>.02:return None
    try:_,decisions=choose_stitches(Project(objects=pieces))
    except ValueError:return None
    # Splitting should create useful columns, not merely fragment the artwork.
    columns=sum(d['selected'] in {'satin','running'} for d in decisions)
    if columns<2:return None
    return pieces,columns


def split_branches(project):
    Project.loads(project.dumps());result=deepcopy(project);result.objects=[];splits=[]
    for index,obj in enumerate(project.objects):
        pieces=None
        eligible=(obj.visible and obj.stitch_type=='fill' and not(obj.stop_after or obj.color_break or obj.stage_note or obj.group_id))
        if eligible and len(obj.rings())==1 and len(obj.rings()[0])<=2000:
            _,decision=choose_stitches(Project(objects=[obj]))
            if decision[0]['selected']=='fill':
                ring=obj.rings()[0];cx=sum(x for x,y in ring)/len(ring);cy=sum(y for x,y in ring)/len(ring)
                xx=sum((x-cx)**2 for x,y in ring);yy=sum((y-cy)**2 for x,y in ring);xy=sum((x-cx)*(y-cy) for x,y in ring)
                principal=.5*math.atan2(2*xy,xx-yy)
                candidates=[p for angle in (0,math.pi/2,principal,principal+math.pi/2) if (p:=_partition(obj,angle)) is not None]
                if candidates:pieces=max(candidates,key=lambda p:(p[1]/len(p[0]),-len(p[0])))[0]
        if pieces and len(result.objects)+len(pieces)+len(project.objects)-index-1<=500:
            for part,piece in enumerate(pieces,1):piece.name=f'{obj.name} · branch {part}'[:200]
            splits.append({'source_region':index,'pieces':len(pieces)})
            result.objects.extend(pieces)
        else:result.objects.append(deepcopy(obj))
    Project.loads(result.dumps())
    return result,splits
