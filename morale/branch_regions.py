"""Partition suitable branching silhouettes at changes in cross-section topology."""
from copy import deepcopy
import math
import uuid
from PySide6.QtGui import QPainterPath,QTransform
from .model import Project
from .geometry import replace_contours
from bisect import bisect_right
from .auto_digitize import choose_stitches,outline_path,difference_area,area,column_pairs
from .curved_columns import curved_pairs


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


def _piece(obj,ring):
    candidate=deepcopy(obj);candidate.kind='compound';candidate.contours=[]
    candidate.points=[];candidate.handles=[]
    candidate=replace_contours(candidate,[ring]);candidate.id=uuid.uuid4().hex
    return candidate


def _ring_area(ring):
    return sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(ring,ring[1:]+ring[:1]))/2


def _clean(ring):
    points=[]
    for p in ring:
        if not points or math.dist(points[-1],p)>1e-6:points.append(tuple(p))
    if len(points)>1 and math.dist(points[0],points[-1])<1e-6:points.pop()
    return points


def _concave_corners(ring,radius=.6,threshold=math.radians(35),spacing=1.5):
    """Inside corners where branches meet, measured over a physical neighborhood.

    Traced curves round a crotch across many short segments, so the tangent on
    each side is taken about ``radius`` millimeters away from the vertex.
    """
    lengths=[0.]
    for a,b in zip(ring,ring[1:]+ring[:1]):lengths.append(lengths[-1]+math.dist(a,b))
    total=lengths[-1];orientation=1 if _ring_area(ring)>0 else -1
    def at(distance):
        distance%=total;index=min(len(ring)-1,max(0,bisect_right(lengths,distance)-1))
        a,b=ring[index],ring[(index+1)%len(ring)];span=lengths[index+1]-lengths[index]
        f=(distance-lengths[index])/span if span else 0
        return (a[0]+f*(b[0]-a[0]),a[1]+f*(b[1]-a[1]))
    scored=[]
    for index,b in enumerate(ring):
        a,c=at(lengths[index]-radius),at(lengths[index]+radius)
        u=(b[0]-a[0],b[1]-a[1]);v=(c[0]-b[0],c[1]-b[1])
        turn=math.atan2(u[0]*v[1]-u[1]*v[0],u[0]*v[0]+u[1]*v[1])*orientation
        if -turn>=threshold:scored.append((-turn,index))
    corners=[]
    for turn,index in sorted(scored,reverse=True):
        # Keep the sharpest vertex of each rounded crotch.
        if all(min(abs(lengths[index]-lengths[j]),total-abs(lengths[index]-lengths[j]))>spacing for j in corners):
            corners.append(index)
        if len(corners)==16:break
    return [ring[i] for i in corners]


def _locate(ring,p):
    for index,q in enumerate(ring):
        if math.dist(p,q)<1e-7:return ring,index
    for index,(a,b) in enumerate(zip(ring,ring[1:]+ring[:1])):
        dx,dy=b[0]-a[0],b[1]-a[1];length=dx*dx+dy*dy
        if not length:continue
        t=((p[0]-a[0])*dx+(p[1]-a[1])*dy)/length
        if 0<t<1 and math.hypot(a[0]+t*dx-p[0],a[1]+t*dy-p[1])<1e-7:
            return ring[:index+1]+[p]+ring[index+1:],index+1
    return ring,None


def _contains(ring,p):
    inside=False
    for a,b in zip(ring,ring[1:]+ring[:1]):
        if (a[1]>p[1])!=(b[1]>p[1]) and p[0]<a[0]+(b[0]-a[0])*(p[1]-a[1])/(b[1]-a[1]):inside=not inside
    return inside


def _interior_chord(ring,p,q):
    """True when segment p-q crosses the region without touching its boundary."""
    if math.dist(p,q)<.05:return False
    dx,dy=q[0]-p[0],q[1]-p[1]
    for a,b in zip(ring,ring[1:]+ring[:1]):
        ex,ey=b[0]-a[0],b[1]-a[1];denominator=dx*ey-dy*ex
        if abs(denominator)<1e-12:
            # Parallel edges only matter when they run along the chord itself.
            if abs((a[0]-p[0])*dy-(a[1]-p[1])*dx)<1e-9*math.hypot(dx,dy):
                ts=sorted(((c[0]-p[0])*dx+(c[1]-p[1])*dy)/(dx*dx+dy*dy) for c in (a,b))
                if ts[0]<1-1e-7 and ts[1]>1e-7:return False
            continue
        t=((a[0]-p[0])*ey-(a[1]-p[1])*ex)/denominator
        u=((a[0]-p[0])*dy-(a[1]-p[1])*dx)/denominator
        if -1e-9<=u<=1+1e-9 and 1e-7<t<1-1e-7:return False
    return all(_contains(ring,(p[0]+f*dx,p[1]+f*dy)) for f in (.25,.5,.75))


def _encloses_arm(ring,p,q):
    """A useful cut separates boundary much longer than itself on both sides."""
    ring,_=_locate(ring,p);ring,j=_locate(ring,q);_,i=_locate(ring,p)
    if i is None or j is None:return False
    if i>j:i,j=j,i
    arc=sum(math.dist(a,b) for a,b in zip(ring[i:j],ring[i+1:j+1]))
    perimeter=sum(math.dist(a,b) for a,b in zip(ring,ring[1:]+ring[:1]))
    return min(arc,perimeter-arc)>=2*math.dist(p,q)


def _chords(ring,corners,longest):
    """Candidate cuts from each inside corner to another corner or across the arm."""
    found=set()
    for index,p in enumerate(corners):
        for q in corners[index+1:]:
            if math.dist(p,q)<=longest and _interior_chord(ring,p,q) and _encloses_arm(ring,p,q):found.add((p,q))
        feet=[]
        for a,b in zip(ring,ring[1:]+ring[:1]):
            dx,dy=b[0]-a[0],b[1]-a[1];length=dx*dx+dy*dy
            if not length:continue
            t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/length))
            foot=(a[0]+t*dx,a[1]+t*dy);distance=math.dist(p,foot)
            if .3<distance<=longest:feet.append((distance,foot))
        chosen=[]
        for distance,foot in sorted(feet):
            if any(math.dist(foot,other)<.5 for other in chosen):continue
            if _interior_chord(ring,p,foot) and _encloses_arm(ring,p,foot):
                chosen.append(foot);found.add((p,foot))
            if len(chosen)==3:break
    return sorted(found,key=lambda chord:math.dist(*chord))[:48]


def _split_ring(ring,p,q):
    ring,_=_locate(ring,p);ring,j=_locate(ring,q);_,i=_locate(ring,p)
    if i is None or j is None or i==j:return None
    if i>j:i,j=j,i
    first,second=ring[i:j+1],ring[j:]+ring[:i+1]
    if len(first)<3 or len(second)<3 or min(abs(_ring_area(first)),abs(_ring_area(second)))<.05:return None
    return first,second


def _chord_partition(obj):
    """Cut a branching silhouette along short interior chords between its crotches.

    Pieces share exact cut edges, so coverage is preserved without clipping.
    Cuts are chosen greedily by the column area they create.
    """
    ring=_clean(obj.rings()[0])
    if len(ring)<4:return None
    corners=_concave_corners(ring)
    if not corners:return None
    chords=_chords(ring,corners,8)
    cache={};budget=[400]
    def column(piece):
        key=tuple((round(x,6),round(y,6)) for x,y in piece)
        if key not in cache:
            if budget[0]<=0:return False
            budget[0]-=1
            try:candidate=_piece(obj,piece)
            except ValueError:cache[key]=False;return False
            found,_=column_pairs(candidate)
            if found is None:found=curved_pairs(candidate)
            # Narrow slivers would become running lines and drop filled width.
            cache[key]=found is not None and found[1]>=.8
        return cache[key]
    pieces=[ring];cuts=[]
    while len(cuts)<12:
        best=None
        for index,piece in enumerate(pieces):
            if column(piece):continue
            for p,q in chords:
                if (p,q) in cuts or _locate(piece,p)[1] is None or _locate(piece,q)[1] is None:continue
                if not _interior_chord(piece,p,q):continue
                parts=_split_ring(piece,p,q)
                if parts is None:continue
                if min(abs(_ring_area(part)) for part in parts)<.3:continue
                gain=sum(abs(_ring_area(part)) for part in parts if column(part))
                # The shortest useful cut crosses an arm; longer cuts tend to
                # shave slivers off broad fill regions.
                rank=(round(math.dist(p,q),3),-gain)
                if gain>=.3 and (best is None or rank<best[0]):best=(rank,index,parts,(p,q))
        if best is None:break
        _,index,parts,chord=best
        pieces[index:index+1]=parts;cuts.append(chord)
    if not cuts or not 2<=len(pieces)<=24:return None
    return [_piece(obj,piece) for piece in pieces]


def _score(obj,pieces):
    combined=outline_path([ring for piece in pieces for ring in piece.rings()])
    total=area(outline_path(obj.rings()))
    if any(area(outline_path(piece.rings()))<.3 for piece in pieces):return None
    if difference_area(outline_path(obj.rings()),combined)>.02:return None
    try:_,decisions=choose_stitches(Project(objects=pieces))
    except ValueError:return None
    # Running centerlines drop the filled width, so only satin earns coverage.
    columns=[piece for piece,decision in zip(pieces,decisions) if decision['selected']=='satin']
    if not columns:return None
    return sum(area(outline_path(piece.rings())) for piece in columns)/total,len(columns)


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
                candidates=[p[0] for angle in (0,math.pi/2,principal,principal+math.pi/2) if (p:=_partition(obj,angle)) is not None]
                if (chorded:=_chord_partition(obj)) is not None:candidates.append(chorded)
                scored=[(score,candidate) for candidate in candidates if (score:=_score(obj,candidate)) is not None]
                # Prefer the most column coverage, then the fewest pieces.
                if scored:pieces=max(scored,key=lambda s:(round(s[0][0],3),-len(s[1])))[1]
        if pieces and len(result.objects)+len(pieces)+len(project.objects)-index-1<=500:
            for part,piece in enumerate(pieces,1):piece.name=f'{obj.name} · branch {part}'[:200]
            splits.append({'source_region':index,'pieces':len(pieces)})
            result.objects.extend(pieces)
        else:result.objects.append(deepcopy(obj))
    Project.loads(result.dumps())
    return result,splits
