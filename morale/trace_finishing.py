"""Plan editable tie/trim settings after traced regions have been ordered."""
from copy import deepcopy
import math
from .model import Project
from .engine import generate
from .threads import thread_key


def finish_regions(project,threshold=5,internal=False):
    if type(internal) is not bool:raise ValueError('Invalid internal trim setting.')
    if isinstance(threshold,bool) or not isinstance(threshold,(int,float)) or not math.isfinite(threshold) or not .5<=threshold<=50:
        raise ValueError('Choose a transfer trim threshold from 0.5 to 50 mm.')
    Project.loads(project.dumps());result=deepcopy(project)
    objects={o.id:o for o in result.objects};runs=[]
    if internal:
        for obj in result.objects:
            if obj.visible and obj.kind!='stitches':obj.jump_trim=threshold
    for block in generate(project):
        if any(s.command=='stitch' for s in block.stitches):
            points=[(s.x,s.y) for s in block.stitches if s.command in {'stitch','jump'}]
            runs.append((objects[block.object_id],block,points[0],points[-1]))
    boundaries=[]
    if runs:
        if runs[0][0].kind!='stitches':runs[0][0].tie_in=True
        if runs[-1][0].kind!='stitches':runs[-1][0].tie_off=True;runs[-1][0].trim_after=True
    for previous,current in zip(runs,runs[1:]):
        a,old,_,end=previous;b,new,start,_=current
        distance=math.dist(end,start)
        change=thread_key(old)!=thread_key(new) or b.color_break
        reason='thread change' if change else 'stop' if a.stop_after else 'long transfer' if distance>threshold else ''
        if reason:
            if a.kind!='stitches':a.tie_off=True;a.trim_after=True
            if b.kind!='stitches':b.tie_in=True
            boundaries.append({'from':a.id,'to':b.id,'distance_mm':distance,'reason':reason})
    Project.loads(result.dumps());generate(result)
    return result,{'threshold_mm':threshold,'boundaries':boundaries,'internal_trims':internal,
        'tie_in_objects':sum(o.tie_in for o in result.objects if o.visible and o.kind!='stitches'),
        'tie_off_objects':sum(o.tie_off for o in result.objects if o.visible and o.kind!='stitches'),
        'trim_objects':sum(o.trim_after for o in result.objects if o.visible and o.kind!='stitches')}
