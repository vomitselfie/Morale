"""Bounded, sampled sewn-path comparison independent of command alignment."""
import math
from collections import defaultdict


def sewn_segments(blocks):
    previous=(0.,0.)
    for block in blocks:
        for stitch in block.stitches:
            point=(stitch.x,stitch.y)
            if stitch.command=='stitch' and point!=previous:yield previous,point
            if stitch.command in {'stitch','jump'}:previous=point


def _directed(tested,reference,tolerance,step,budget):
    cells=defaultdict(list);entries=0
    report={'complete':False,'samples':0,'outside_samples':0,'estimated_outside_length_mm':0.,'locations':[]}
    # Half-cell spacing visits every neighborhood needed by a tolerance-radius
    # query. Exact segment distances, rather than sample distances, decide hits.
    for a,b in reference:
        count=max(1,math.ceil(math.dist(a,b)*2));visited=set()
        if count>budget:return report
        for i in range(count+1):
            t=i/count;key=(math.floor(a[0]+(b[0]-a[0])*t),math.floor(a[1]+(b[1]-a[1])*t))
            if key not in visited:
                cells[key].append((a,b));visited.add(key);entries+=1
                if entries>budget:return report
    operations=0
    for a,b in tested:
        length=math.dist(a,b);count=max(1,math.ceil(length/step))
        for i in range(count):
            if report['samples']>=budget:return report
            t=(i+.5)/count;x=a[0]+(b[0]-a[0])*t;y=a[1]+(b[1]-a[1])*t
            key=(math.floor(x),math.floor(y));found=False
            for dx in (-1,0,1):
                if found:break
                for dy in (-1,0,1):
                    if found:break
                    for c,d in cells.get((key[0]+dx,key[1]+dy),()):
                        operations+=1
                        if operations>budget*40:return report
                        ux,uy=d[0]-c[0],d[1]-c[1];denom=ux*ux+uy*uy
                        fraction=max(0,min(1,((x-c[0])*ux+(y-c[1])*uy)/denom))
                        if (x-c[0]-fraction*ux)**2+(y-c[1]-fraction*uy)**2<=tolerance*tolerance:
                            found=True;break
            report['samples']+=1
            if not found:
                report['outside_samples']+=1;report['estimated_outside_length_mm']+=length/count
                if len(report['locations'])<100:report['locations'].append([x,y])
    report['complete']=True
    return report


def compare_sewn_paths(source,decoded,*,tolerance=.15,step=.25,budget=100_000):
    if not 0<tolerance<=.5 or not math.isfinite(tolerance):raise ValueError('Invalid path comparison tolerance.')
    if not 0<step<=1 or not math.isfinite(step):raise ValueError('Invalid path sampling step.')
    if type(budget) is not int or budget<1:raise ValueError('Invalid path comparison budget.')
    a=list(sewn_segments(source));b=list(sewn_segments(decoded))
    return {'tolerance_mm':tolerance,'sample_spacing_mm':step,
            'decoded_outside_source':_directed(b,a,tolerance,step,budget),
            'source_outside_decoded':_directed(a,b,tolerance,step,budget)}
