"""Bounded removal of redundant short interior stitches before finishing ties."""
import math


def short_stitch_cleanup(stitches, minimum, maximum, tolerance=.01):
    """Keep controls, run endpoints, reversals, corners and bounded path error.

    This is conservative simplification, not a guarantee that every resulting
    stitch exceeds minimum. Up to 64 removed points are tracked between retained
    points so successive removals cannot accumulate unbounded geometric error.
    """
    if isinstance(minimum,bool) or not isinstance(minimum,(int,float)) or not math.isfinite(minimum) or not 0 <= minimum <= 1:
        raise ValueError("Short-stitch threshold must be between 0 and 1 mm.")
    if minimum == 0:
        return stitches
    if not math.isfinite(maximum) or maximum <= 0:
        raise ValueError("Maximum stitch length must be positive.")
    result=[]
    removed=[]
    for index,current in enumerate(stitches):
        following=stitches[index+1] if index+1<len(stitches) else None
        previous=result[-1] if result else None
        discard=False
        if previous and following and all(s.command=='stitch' for s in (previous,current,following)) and len(removed)<64:
            a,b,c=(previous.x,previous.y),(current.x,current.y),(following.x,following.y)
            incoming,outgoing,chord=math.dist(a,b),math.dist(b,c),math.dist(a,c)
            if min(incoming,outgoing)<minimum and chord<=maximum+1e-9:
                cosine=((b[0]-a[0])*(c[0]-b[0])+(b[1]-a[1])*(c[1]-b[1]))/(incoming*outgoing) if incoming*outgoing>1e-16 else 1
                if cosine>=math.cos(math.radians(20)):
                    def near_segment(p):
                        if chord<1e-12:
                            return math.dist(p,a)<=tolerance
                        t=max(0,min(1,((p[0]-a[0])*(c[0]-a[0])+(p[1]-a[1])*(c[1]-a[1]))/chord**2))
                        return math.dist(p,(a[0]+t*(c[0]-a[0]),a[1]+t*(c[1]-a[1])))<=tolerance
                    discard=all(near_segment(p) for p in [*removed,b])
        if discard:
            removed.append((current.x,current.y))
        else:
            result.append(current)
            removed=[]
    return result
