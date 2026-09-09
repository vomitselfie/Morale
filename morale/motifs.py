"""Rigid repeated motifs placed by distance along an editable guide outline."""
from bisect import bisect_right
import math
import json
import os
from pathlib import Path
import tempfile

PATTERNS={
    'diamond':[[(-.5,0),(0,-.5),(.5,0),(0,.5),(-.5,0)]],
    'box':[[(-.5,-.5),(.5,-.5),(.5,.5),(-.5,.5),(-.5,-.5)]],
    'cross':[[(-.5,-.5),(.5,.5)],[(-.5,.5),(.5,-.5)]],
}


def validate_custom(paths):
    if not isinstance(paths,list) or not 1<=len(paths)<=64:
        raise ValueError('A custom motif needs 1–64 paths.')
    count=0
    moving=False
    for path in paths:
        if not isinstance(path,list) or len(path)<2:
            raise ValueError('Each motif path needs at least two points.')
        count+=len(path)
        if count>2000:
            raise ValueError('Custom motifs support at most 2,000 points. Simplify the source outline.')
        for point in path:
            if not isinstance(point,(list,tuple)) or len(point)!=2 or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not -.5<=v<=.5 for v in point):
                raise ValueError('Invalid normalized motif point.')
        moving=moving or any(math.dist(a,b)>1e-9 for a,b in zip(path,path[1:]))
    if not moving:
        raise ValueError('A motif must contain a nonzero line.')


def capture_motif(obj):
    if obj.kind=='stitches':
        raise ValueError('Capture an editable vector outline. Manual stitches have no source outline.')
    paths=[list(ring) for ring in obj.rings()]
    if obj.kind!='path':
        paths=[ring+[ring[0]] for ring in paths]
    xs,ys=zip(*(p for path in paths for p in path))
    cx,cy=(min(xs)+max(xs))/2,(min(ys)+max(ys))/2
    width,height=max(.1,max(xs)-min(xs)),max(.1,max(ys)-min(ys))
    paths=[[[max(-.5,min(.5,(x-cx)/width)),max(-.5,min(.5,(y-cy)/height))] for x,y in path] for path in paths]
    validate_custom(paths)
    return {'format':'morale-motif','version':1,'name':obj.name,'paths':paths}


def validate_packet(packet):
    if not isinstance(packet,dict) or packet.get('format')!='morale-motif' or type(packet.get('version')) is not int or packet['version']!=1:
        raise ValueError('Not a supported Morale motif file.')
    if not isinstance(packet.get('name'),str) or len(packet['name'])>200:
        raise ValueError('Invalid motif name.')
    validate_custom(packet.get('paths'))
    return packet


def load_motif(path):
    path=Path(path)
    if path.stat().st_size>500_000:
        raise ValueError('Motif files are limited to 500 KB.')
    try:
        return validate_packet(json.loads(path.read_text(encoding='utf-8')))
    except RecursionError as exc:
        raise ValueError('Motif nesting exceeds the supported limit.') from exc


def save_motif(packet,path):
    validate_packet(packet)
    path=Path(path)
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent,mode='w',encoding='utf-8',delete=False) as stream:
            temporary=Path(stream.name)
            json.dump(packet,stream,ensure_ascii=False,allow_nan=False)
        os.replace(temporary,path)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


def motif_paths(obj):
    if obj.motif_pattern=='custom':
        validate_custom(obj.custom_motif_paths)
        patterns=obj.custom_motif_paths
    elif obj.motif_pattern in PATTERNS:
        patterns=PATTERNS[obj.motif_pattern]
    else:
        raise ValueError('Choose a supported motif pattern.')
    sign=-1 if obj.flip_x ^ obj.flip_y ^ obj.motif_reflected else 1
    for value in (obj.motif_width,obj.motif_height,obj.motif_spacing):
        if not math.isfinite(value) or not .5<=value<=30:
            raise ValueError('Motif size and spacing must be between 0.5 and 30 mm.')
    repeats=0
    for ring in obj.rings():
        route=ring+[ring[0]] if obj.kind!='path' else ring
        segments=[]
        ends=[]
        total=0
        for a,b in zip(route,route[1:]):
            length=math.dist(a,b)
            if length>1e-9:
                segments.append((a,b,length))
                total+=length
                ends.append(total)
        if total<obj.motif_width or not segments:
            continue
        closed=obj.kind!='path'
        count=max(1,int(total//obj.motif_spacing)) if closed else int((total-obj.motif_width)//obj.motif_spacing)+1
        repeats+=count
        if repeats>5000:
            raise ValueError('Motif repetition exceeds 5,000 instances. Increase spacing or simplify the guide.')
        step=total/count if closed else obj.motif_spacing
        first=step/2 if closed else (total-(count-1)*step)/2
        for index in range(count):
            distance=first+index*step
            which=min(bisect_right(ends,distance),len(segments)-1)
            a,b,length=segments[which]
            before=ends[which-1] if which else 0
            t=(distance-before)/length
            x,y=a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t
            tx,ty=(b[0]-a[0])/length,(b[1]-a[1])/length
            for pattern in patterns:
                yield [(x+u*obj.motif_width*tx-sign*v*obj.motif_height*ty,
                        y+u*obj.motif_width*ty+sign*v*obj.motif_height*tx) for u,v in pattern]
