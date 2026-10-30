"""Circular ripple rows clipped to editable even-odd outlines."""
import math
from .pattern_fill import RegionClip


def ripple_paths(obj):
    if obj.kind in {'path','satin','stitches'}:
        raise ValueError('Ripple fill requires a closed outline.')
    if not .2 <= obj.spacing <= 5 or not .5 <= obj.stitch_length <= 6:
        raise ValueError('Invalid ripple spacing or stitch length.')
    rings=obj.rings()
    region=RegionClip(rings)
    for value in (obj.ripple_center_x,obj.ripple_center_y):
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not -100<=value<=100:
            raise ValueError('Ripple center must be between -100 and 100 percent.')
    center=obj.transform([(obj.ripple_center_x/100,obj.ripple_center_y/100)])[0]
    angle=math.radians(obj.rotation)
    c,s=math.cos(angle),math.sin(angle)
    sx,sy=(-1 if obj.flip_x else 1),(-1 if obj.flip_y else 1)
    def circle_point(r,theta):
        x,y=sx*r*math.cos(theta),sy*r*math.sin(theta)
        return center[0]+x*c-y*s,center[1]+x*s+y*c
    radius=max(math.dist(center,p) for ring in rings for p in ring)
    for layer in range(math.ceil(radius/obj.spacing)):
        r=(layer+.5)*obj.spacing
        if r>radius:break
        # Bound both needle span and chord deviation from the ideal circle.
        step=min(obj.stitch_length,2*math.sqrt(max(0,2*r*.02-.02**2)))
        count=max(12,math.ceil(2*math.pi*r/step))
        if count*len(region.edges)>30_000_000-region.work:
            raise ValueError('Ripple clipping is too complex. Increase spacing or simplify the outline.')
        direction=-1 if layer%2 else 1
        run=[]
        first=circle_point(r,0)
        a=first
        for i in range(1,count+1):
            theta=direction*2*math.pi*i/count
            b=circle_point(r,theta) if i<count else first
            parts=region.segment(a,b)
            if not parts and run:
                yield run;run=[]
            for start,end in parts:
                if run and math.dist(run[-1],start)>1e-8:
                    yield run;run=[]
                if not run:run=[start]
                run.append(end)
            a=b
        if run:yield run


def preserve_center(source,candidate,transform=None):
    """Keep the ripple's world anchor when geometry is rebased for editing."""
    if source.stitch_type!='ripple':return
    center=source.transform([(source.ripple_center_x/100,source.ripple_center_y/100)])[0]
    if transform is not None:center=transform(center)
    x,y=center[0]-candidate.x,center[1]-candidate.y
    angle=math.radians(candidate.rotation)
    c,s=math.cos(angle),math.sin(angle)
    values=((x*c+y*s)/candidate.width*100*(-1 if candidate.flip_x else 1),
            (-x*s+y*c)/candidate.height*100*(-1 if candidate.flip_y else 1))
    if any(not math.isfinite(v) or abs(v)>100+1e-8 for v in values):
        raise ValueError('This edit would move the ripple center beyond its supported range. Move the ripple center closer to the outline first.')
    candidate.ripple_center_x,candidate.ripple_center_y=(max(-100,min(100,v)) for v in values)
