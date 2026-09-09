"""Rectangular motif lattices clipped to even-odd editable regions."""
import math
from .motifs import PATTERNS,validate_custom


class RegionClip:
    def __init__(self,rings):
        self.edges=[(a,b) for ring in rings for a,b in zip(ring,ring[1:]+ring[:1])]
        self.work=0

    def budget(self):
        self.work+=len(self.edges)
        if self.work>30_000_000:
            raise ValueError('Motif clipping is too complex. Simplify the outline/motif or increase spacing.')

    def inside(self,p):
        self.budget()
        x,y=p; inside=False
        for (ax,ay),(bx,by) in self.edges:
            cross=(bx-ax)*(y-ay)-(by-ay)*(x-ax)
            if abs(cross)<1e-9 and min(ax,bx)-1e-9<=x<=max(ax,bx)+1e-9 and min(ay,by)-1e-9<=y<=max(ay,by)+1e-9:
                return True
            if (ay>y)!=(by>y) and x<ax+(y-ay)*(bx-ax)/(by-ay): inside=not inside
        return inside

    def segment(self,a,b):
        self.budget()
        dx,dy=b[0]-a[0],b[1]-a[1]
        length2=dx*dx+dy*dy
        if length2<1e-18: return []
        cuts=[0.,1.]
        for c,d in self.edges:
            ex,ey=d[0]-c[0],d[1]-c[1]
            denominator=dx*ey-dy*ex
            rx,ry=c[0]-a[0],c[1]-a[1]
            if abs(denominator)>1e-12:
                t=(rx*ey-ry*ex)/denominator
                u=(rx*dy-ry*dx)/denominator
                if 0<t<1 and -1e-10<=u<=1+1e-10: cuts.append(t)
            elif abs(rx*dy-ry*dx)<1e-9:
                for p in (c,d):
                    t=((p[0]-a[0])*dx+(p[1]-a[1])*dy)/length2
                    if 0<t<1: cuts.append(t)
        cuts.sort()
        result=[]
        for lo,hi in zip(cuts,cuts[1:]):
            if hi-lo<1e-10: continue
            middle=(lo+hi)/2
            if self.inside((a[0]+middle*dx,a[1]+middle*dy)):
                result.append(((a[0]+lo*dx,a[1]+lo*dy),(a[0]+hi*dx,a[1]+hi*dy)))
        return result


def pattern_fill_paths(obj):
    if obj.kind in {'path','satin','stitches'}: raise ValueError('Motif fills require a closed outline.')
    if obj.motif_pattern=='custom':
        validate_custom(obj.custom_motif_paths); patterns=obj.custom_motif_paths
    elif obj.motif_pattern in PATTERNS: patterns=PATTERNS[obj.motif_pattern]
    else: raise ValueError('Choose a supported motif pattern.')
    for value in (obj.motif_width,obj.motif_height,obj.motif_spacing,obj.motif_row_spacing):
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not .5<=value<=30:
            raise ValueError('Motif size and spacing must be between 0.5 and 30 mm.')
    c,s=math.cos(math.radians(obj.angle)),math.sin(math.radians(obj.angle))
    rings=[[(x*c+y*s,-x*s+y*c) for x,y in ring] for ring in obj.rings()]
    xs,ys=zip(*(p for ring in rings for p in ring))
    cx,cy=(min(xs)+max(xs))/2,(min(ys)+max(ys))/2
    nx=math.floor(((max(xs)-min(xs))+obj.motif_width)/2/obj.motif_spacing)
    ny=math.floor(((max(ys)-min(ys))+obj.motif_height)/2/obj.motif_row_spacing)
    tiles=(2*nx+1)*(2*ny+1)
    if tiles>5000: raise ValueError('Motif fill exceeds 5,000 candidate tiles. Increase spacing or reduce the shape.')
    region=RegionClip(rings)
    segments=sum(len(path)-1 for path in patterns)
    if tiles*segments*len(region.edges)>30_000_000:
        raise ValueError('Motif clipping is too complex. Simplify the outline/motif or increase spacing.')
    sx,sy=(-1 if obj.pattern_flip_x else 1),(-1 if obj.pattern_flip_y else 1)
    def world(p): return p[0]*c-p[1]*s,p[0]*s+p[1]*c
    for row,iy in enumerate(range(-ny,ny+1)):
        columns=range(-nx,nx+1) if row%2==0 else range(nx,-nx-1,-1)
        for ix in columns:
            x,y=cx+ix*obj.motif_spacing,cy+iy*obj.motif_row_spacing
            for pattern in patterns:
                points=[(x+sx*u*obj.motif_width,y+sy*v*obj.motif_height) for u,v in pattern]
                run=[]
                for a,b in zip(points,points[1:]):
                    parts=region.segment(a,b)
                    if not parts and run:
                        yield [world(p) for p in run]; run=[]
                    for start,end in parts:
                        if run and math.dist(run[-1],start)>1e-8:
                            yield [world(p) for p in run]; run=[]
                        if not run: run=[start]
                        run.append(end)
                if run: yield [world(p) for p in run]
