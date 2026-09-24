"""Pair opposite outline chains to follow curved, open embroidery ribbons."""
import math
from bisect import bisect_right


def _chain(points):
    distances=[0.]
    for a,b in zip(points,points[1:]): distances.append(distances[-1]+math.dist(a,b))
    return points,distances


def _at(chain,t):
    points,distances=chain; distance=t*distances[-1]
    index=min(len(points)-2,max(0,bisect_right(distances,distance)-1))
    a,b=points[index:index+2]
    fraction=(distance-distances[index])/(distances[index+1]-distances[index])
    return (a[0]+fraction*(b[0]-a[0]),a[1]+fraction*(b[1]-a[1]))


def _simplify(points,tolerance=.005):
    keep={0,len(points)-1}; stack=[(0,len(points)-1)]
    while stack:
        start,end=stack.pop()
        if end-start<2: continue
        a,b=points[start],points[end]; dx=b[0]-a[0]; dy=b[1]-a[1]; length=dx*dx+dy*dy
        worst=0; chosen=None
        for index in range(start+1,end):
            p=points[index]; t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/length)) if length else 0
            distance=math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy)
            if distance>worst: worst=distance; chosen=index
        if worst>tolerance:
            keep.add(chosen); stack.extend(((start,chosen),(chosen,end)))
    return [points[i] for i in sorted(keep)]


def curved_pairs(obj):
    from .auto_digitize import outline_path,area,difference_area
    from .engine import satin
    rings=obj.rings()
    if len(rings)!=1: return None
    ring=[]
    for point in rings[0]:
        if not ring or math.dist(point,ring[-1])>1e-6: ring.append(point)
    if len(ring)>1 and math.dist(ring[0],ring[-1])<1e-6: ring.pop()
    if len(ring)<4 or len(ring)>2000: return None
    split=max(range(1,len(ring)),key=lambda i:math.dist(ring[0],ring[i]))
    ring=_simplify(ring[:split+1])[:-1]+_simplify(ring[split:]+[ring[0]])[:-1]
    def turn(index):
        # Fitted curves round cap corners across many tiny segments. Measure
        # tangents over a physical neighborhood instead of a single segment.
        b=ring[index]
        def neighbor(direction):
            distance=0; previous=b
            for step in range(1,len(ring)):
                point=ring[(index+direction*step)%len(ring)]
                distance+=math.dist(previous,point)
                if distance>=.4: return point
                previous=point
            return previous
        a,c=neighbor(-1),neighbor(1)
        u=(b[0]-a[0],b[1]-a[1]); v=(c[0]-b[0],c[1]-b[1])
        return abs(math.atan2(u[0]*v[1]-u[1]*v[0],u[0]*v[0]+u[1]*v[1]))
    caps=[]
    for index in range(len(ring)):
        width=math.dist(ring[index],ring[(index+1)%len(ring)])
        sharpness=min(turn(index),turn((index+1)%len(ring)))
        if .1<=width<=6 and sharpness>=math.pi/4: caps.append((sharpness,index))
    # Cap pairing is bounded even for heavily notched artwork.
    caps=sorted(index for _,index in sorted(caps,reverse=True)[:12])
    best=None; original=outline_path(rings); original_area=area(original)
    for position,start in enumerate(caps):
        for end in caps[position+1:]:
            left=ring[start+1:end+1]
            right=list(reversed(ring[end+1:]+ring[:start+1]))
            if len(left)<2 or len(right)<2: continue
            chains=[_chain(left),_chain(right)]
            lengths=[chain[1][-1] for chain in chains]
            if min(lengths)<1 or max(lengths)>4*min(lengths): continue
            count=math.ceil(max(lengths)/.5)
            if count>900: continue
            fractions=sorted({0.,1.,*[i/count for i in range(1,count)],
                *[distance/chain[1][-1] for chain in chains for distance in chain[1]]})
            stations=[]
            for t in fractions:
                if not stations or t-stations[-1]>1e-7: stations.append(t)
            if len(stations)>1000: continue
            pairs=[point for t in stations for point in (_at(chains[0],t),_at(chains[1],t))]
            maximum=max(math.dist(a,b) for a,b in zip(pairs[::2],pairs[1::2]))
            if maximum>6 or min(lengths)<maximum*2: continue
            try: satin(pairs,.45,6)
            except ValueError: continue
            reconstructed=outline_path([pairs[::2]+list(reversed(pairs[1::2]))])
            error=difference_area(original,reconstructed)
            if error>max(.02,original_area*.01): continue
            if best is None or maximum<best[1]: best=(pairs,maximum)
    return best


def closed_pairs(obj,seam_percent=0):
    for tolerance in (.005,.02,.05,.1):
        result=_closed_pairs(obj,tolerance,seam_percent)
        if result is not None: return result
    return None


def _closed_pairs(obj,tolerance,seam_percent):
    """Open a two-contour band at a shared seam and pair its boundary loops."""
    from PySide6.QtCore import QPointF
    from .auto_digitize import outline_path,area,difference_area
    from .engine import satin
    rings=obj.rings()
    if len(rings)!=2 or sum(map(len,rings))>20_000: return None
    cleaned=[]
    for ring in rings:
        points=[]
        for p in ring:
            if not points or math.dist(points[-1],p)>1e-6: points.append(p)
        if len(points)>1 and math.dist(points[0],points[-1])<1e-6: points.pop()
        if len(points)<3: return None
        split=max(range(1,len(points)),key=lambda i:math.dist(points[0],points[i]))
        points=_simplify(points[:split+1],tolerance)[:-1]+_simplify(points[split:]+[points[0]],tolerance)[:-1]
        signed=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(points,points[1:]+points[:1]))
        if signed<0: points.reverse()
        cleaned.append(points)
    if sum(map(len,cleaned))>2000: return None
    outer,inner=sorted(cleaned,key=lambda ring:area(outline_path([ring])),reverse=True)
    boundary=outline_path([outer])
    if not all(boundary.contains(QPointF(*p)) for p in inner): return None
    start=max(range(len(outer)),key=lambda i:(outer[i][0],outer[i][1]))
    outer=outer[start:]+outer[:start]
    if seam_percent:
        chain=_chain(outer+[outer[0]])
        seam=_at(chain,seam_percent/100)
        index=min(len(outer)-1,bisect_right(chain[1],seam_percent/100*chain[1][-1])-1)
        rotated=[seam]+outer[index+1:]+outer[:index+1]
        outer=[p for i,p in enumerate(rotated) if not i or math.dist(rotated[i-1],p)>1e-6]
        if math.dist(outer[-1],outer[0])<1e-6: outer.pop()
    origin=outer[0]; nearest=None
    for index,(a,b) in enumerate(zip(inner,inner[1:]+inner[:1])):
        dx=b[0]-a[0]; dy=b[1]-a[1]; length=dx*dx+dy*dy
        t=max(0,min(1,((origin[0]-a[0])*dx+(origin[1]-a[1])*dy)/length))
        p=(a[0]+t*dx,a[1]+t*dy); distance=math.dist(origin,p)
        if nearest is None or distance<nearest[0]: nearest=(distance,index,p)
    _,index,seam=nearest
    inner=[seam]+inner[index+1:]+inner[:index+1]+[seam]
    inner=[p for i,p in enumerate(inner) if not i or math.dist(inner[i-1],p)>1e-6]
    if math.dist(inner[-1],inner[0])>1e-6: inner.append(inner[0])
    chains=[_chain(outer+[outer[0]]),_chain(inner)]
    lengths=[chain[1][-1] for chain in chains]
    if min(lengths)<1 or max(lengths)>4*min(lengths): return None
    count=math.ceil(max(lengths)/.5)
    if count>900: return None
    fractions=sorted({0.,1.,*[i/count for i in range(1,count)],
        *[distance/chain[1][-1] for chain in chains for distance in chain[1]]})
    stations=[]
    for t in fractions:
        if not stations or t-stations[-1]>1e-7: stations.append(t)
    if len(stations)>1000: return None
    pairs=[point for t in stations for point in (_at(chains[0],t),_at(chains[1],t))]
    # Exact closure avoids a tiny unsewn gap at the seam after serialization.
    pairs[-2:]=pairs[:2]
    maximum=max(math.dist(a,b) for a,b in zip(pairs[::2],pairs[1::2]))
    if maximum>6 or min(lengths)<maximum*2: return None
    try: satin(pairs,.45,6)
    except ValueError: return None
    reconstructed=outline_path([pairs[::2]+list(reversed(pairs[1::2]))])
    original=outline_path(rings)
    if difference_area(original,reconstructed)>max(.02,area(original)*.01): return None
    return pairs,maximum
