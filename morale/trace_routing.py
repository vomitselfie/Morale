"""Reduce inter-object travel while preserving overlap and thread-run order."""
from copy import deepcopy
import math
from .engine import generate
from .model import Project
from PySide6.QtGui import QPainterPath,QPainterPathStroker
from .auto_digitize import outline_path


def sewn_footprint(obj,block):
    # Keep complex regions conservatively locked by their bounding boxes.
    rings=obj.rings()
    if sum(map(len,rings))+len(block.stitches)>2000:
        return None
    drawing=QPainterPath();previous=None
    for stitch in block.stitches:
        point=(stitch.x,stitch.y)
        if stitch.command=='stitch' and previous is not None:
            drawing.moveTo(*previous);drawing.lineTo(*point)
        if stitch.command in {'stitch','jump'}:previous=point
    stroker=QPainterPathStroker();stroker.setWidth(.002)
    shape=outline_path(rings).united(stroker.createStroke(drawing))
    shape=shape.united(stroker.createStroke(shape))
    return shape

def layering_valid(objects,blocks,order):
    """Check reversed layer pairs against the final generated geometry."""
    bounds={};shapes={}
    for i,obj in enumerate(objects):
        block=blocks.get(obj.id)
        if block is None:continue
        points=[p for ring in obj.rings() for p in ring]+[(s.x,s.y) for s in block.stitches if s.command in {'stitch','jump'}]
        if points:
            xs,ys=zip(*points);bounds[i]=(min(xs),min(ys),max(xs),max(ys))
    for position,a in enumerate(order):
        for b in order[position+1:]:
            if a<b or a not in bounds or b not in bounds:continue
            x,y,r,bottom=bounds[a];xx,yy,rr,bb=bounds[b]
            if r<xx-.001 or rr<x-.001 or bottom<yy-.001 or bb<y-.001:continue
            for i in (a,b):
                if i not in shapes:shapes[i]=sewn_footprint(objects[i],blocks[objects[i].id])
            if shapes[a] is None or shapes[b] is None or shapes[a].intersects(shapes[b]):return False
    return True


def reduce_travel(project,reverse=False):
    if type(reverse) is not bool:raise ValueError('Invalid stitch-direction optimization setting.')
    Project.loads(project.dumps())
    blocks={block.object_id:block for block in generate(project)}
    endpoints={}; bounds={}
    for i,obj in enumerate(project.objects):
        block=blocks.get(obj.id)
        points=[(s.x,s.y) for s in block.stitches if s.command in {'stitch','jump'}] if block else []
        if points:
            endpoints[i]=(points[0],points[-1])
            geometry=[p for ring in obj.rings() for p in ring]+points
            xs,ys=zip(*geometry);bounds[i]=(min(xs),min(ys),max(xs),max(ys))
    footprints={}
    def footprint(i):
        if i in footprints:return footprints[i]
        obj=project.objects[i];block=blocks[obj.id]
        shape=sewn_footprint(obj,block)
        footprints[i]=shape
        return shape
    def cost(order):
        previous=(0,0); distance=0
        for i in order:
            if i in endpoints:
                start,end=endpoints[i];distance+=math.dist(previous,start);previous=end
        return distance
    def locked(i):
        obj=project.objects[i]
        return (i not in endpoints or obj.color_break or obj.stop_after or obj.stage_note or obj.group_id
                or obj.kind=='stitches')
    def same_thread(a,b):
        return a.color.lower()==b.color.lower() and a.thread==b.thread
    def overlap(a,b):
        x,y,r,bottom=bounds[a]; xx,yy,rr,bb=bounds[b]
        if r<xx-.001 or rr<x-.001 or bottom<yy-.001 or bb<y-.001:return False
        first,second=footprint(a),footprint(b)
        return first is None or second is None or first.intersects(second)
    original=list(range(len(project.objects))); order=[]; index=0; previous=(0,0)
    while index<len(original):
        if locked(index):
            order.append(index)
            if index in endpoints: previous=endpoints[index][1]
            index+=1;continue
        end=index+1
        while end<len(original) and not locked(end) and same_thread(project.objects[index],project.objects[end]): end+=1
        remaining=set(range(index,end))
        predecessors={i:{j for j in range(index,i) if overlap(i,j)} for i in remaining}
        while remaining:
            eligible=[i for i in remaining if not(predecessors[i]&remaining)]
            chosen=min(eligible,key=lambda i:(math.dist(previous,endpoints[i][0]),i))
            order.append(chosen);remaining.remove(chosen);previous=endpoints[chosen][1]
        index=end
    before=cost(original);after=cost(order)
    choices={};variants={}
    if reverse:
        from .routing import route_object
        for i in endpoints:
            obj=project.objects[i];variants[i]=[(obj,endpoints[i])]
            closed=(obj.kind=='path' and obj.points[0]==obj.points[-1]) or (obj.kind=='satin' and obj.points[:2]==obj.points[-2:])
            if locked(i) or closed or obj.kind not in {'path','satin'} or obj.stitch_type not in {'running','triple','satin'}:continue
            try:
                candidate=route_object(obj,[(0,0,True)])
                stitches=generate(Project(objects=[candidate]))[0].stitches
                points=[(s.x,s.y) for s in stitches if s.command in {'jump','stitch'}]
                if points:variants[i].append((candidate,(points[0],points[-1])))
            except ValueError:continue
        def directions(sequence):
            active=[i for i in sequence if i in endpoints];previous=[(0.,(0.,0.))];parents=[]
            for i in active:
                current=[];links=[]
                for obj,(start,end) in variants[i]:
                    score,parent=min((score+math.dist(position,start),j) for j,(score,position) in enumerate(previous))
                    current.append((score,end));links.append(parent)
                previous=current;parents.append(links)
            if not active:return 0,{}
            score,selected=min((score,j) for j,(score,position) in enumerate(previous))
            plan={}
            for i,links in zip(reversed(active),reversed(parents)):
                plan[i]=selected;selected=links[selected]
            return score,plan
        candidates=[]
        for sequence in (original,order):
            score,plan=directions(sequence);candidates.append((score,sequence,plan))
        after,order,choices=min(candidates,key=lambda candidate:candidate[0])
    status='improved';reason=''
    # Include travel to the next run: a locally shorter route can hurt globally.
    if after>=before-1e-6:
        order=original;after=before;choices={};status='unchanged'
    result=deepcopy(project)
    result.objects=[deepcopy(variants[i][choices[i]][0]) if choices.get(i) else result.objects[i] for i in order]
    try:
        final_blocks={block.object_id:block for block in generate(result)}
        if any(choices.values()) and order!=original:
            by_id={obj.id:obj for obj in result.objects}
            final_objects=[by_id[obj.id] for obj in project.objects]
            if not layering_valid(final_objects,final_blocks,order):
                raise ValueError('Reversed stitches conflict with the candidate layer order.')
    except ValueError as exc:
        result=deepcopy(project);order=original;after=before;choices={}
        status='rejected';reason=str(exc)
    return result,{'status':status,'reason':reason,'before_mm':before,'after_mm':after,'order':order,
                   'moved_regions':sum(a!=b for a,b in zip(original,order)),
                   'reversed_regions':[i for i in order if choices.get(i)]}
