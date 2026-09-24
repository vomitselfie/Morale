"""Preserve oversized sewn paths before the writer's displacement encoding."""
import math
import pyembroidery as emb


def subdivide_sewn_spans(pattern,maximum,limit=250_000):
    """Lengths and coordinates use embroidery encoder units (0.1 mm)."""
    if isinstance(maximum,bool) or not isinstance(maximum,(int,float)) or not math.isfinite(maximum) or maximum<=0:
        raise ValueError('The writer must declare a positive finite stitch limit.')
    previous=(0.,0.);plans=[];count=len(pattern.stitches)
    if count>limit:raise ValueError('Export exceeds the 250,000-command encoding limit.')
    for index,(x,y,encoded) in enumerate(pattern.stitches):
        command=encoded & emb.COMMAND_MASK
        if command==emb.STITCH:
            pieces=max(1,math.ceil(math.dist(previous,(x,y))/maximum))
            if pieces>1:
                count+=pieces-1
                if count>limit:raise ValueError('Preserving long sewn spans exceeds the 250,000-command export limit. Reduce the design before exporting.')
                plans.append((index,pieces,previous,(x,y)))
        if command in {emb.STITCH,emb.JUMP}:previous=(x,y)
    result=pattern.copy()
    # Build once; repeated insertion is quadratic for stitch-heavy designs.
    plans={index:(pieces,start,end) for index,pieces,start,end in plans};rows=[]
    for index,row in enumerate(pattern.stitches):
        if index in plans:
            pieces,start,end=plans[index]
            rows.extend([[start[0]+(end[0]-start[0])*i/pieces,start[1]+(end[1]-start[1])*i/pieces,row[2]] for i in range(1,pieces)])
        rows.append(list(row))
    result.stitches=rows
    return result,count-len(pattern.stitches)
