"""Bounded fill-angle search using actual generated travel at fixed object order."""
from copy import deepcopy
import math
from .model import Project
from .engine import generate


def movement(stitches):
    points=[s for s in stitches if s.command in {'stitch','jump'}]
    if not points:return None
    travel=sum(math.hypot(b.x-a.x,b.y-a.y) for a,b in zip(points,points[1:]) if b.command=='jump')
    return (points[0].x,points[0].y),(points[-1].x,points[-1].y),points[0].command=='jump',travel


def travel_cost(states):
    previous=(0.,0.);total=0.
    for state in states:
        if state is None:continue
        entry,exit,initial_jump,internal=state
        total+=internal+(math.dist(previous,entry) if initial_jump else 0)
        previous=exit
    return total


def choose_fill_angles(project,evaluation_limit=512,command_limit=2_000_000):
    Project.loads(project.dumps())
    if type(evaluation_limit) is not int or evaluation_limit<1 or type(command_limit) is not int or command_limit<1:
        raise ValueError('Invalid fill-angle search budget.')
    result=deepcopy(project)
    blocks={b.object_id:b for b in generate(project)}
    states=[movement(blocks[o.id].stitches) if o.id in blocks else None for o in project.objects]
    counts=[len(blocks[o.id].stitches) if o.id in blocks else 0 for o in project.objects]
    before=current=travel_cost(states);evaluations=commands=0;changes=[];complete=True
    for index,source in enumerate(project.objects):
        if not(source.visible and source.stitch_type=='fill') or source.density_gradient or source.lettering or source.stage_note or source.group_id:
            continue
        points=[p for ring in source.rings() for p in ring]
        cx=sum(x for x,y in points)/len(points);cy=sum(y for x,y in points)/len(points)
        xx=sum((x-cx)**2 for x,y in points);yy=sum((y-cy)**2 for x,y in points);xy=sum((x-cx)*(y-cy) for x,y in points)
        principal=math.degrees(.5*math.atan2(2*xy,xx-yy))%180
        angles=sorted({float(a) for a in range(0,360,30)}|{(principal+a)%360 for a in (0,90,180,270)})
        best=source;best_state=states[index];best_cost=current;best_count=counts[index]
        for angle in angles:
            if abs((angle-source.angle)%360)<1e-6:continue
            if evaluations>=evaluation_limit or commands>=command_limit:complete=False;break
            candidate=deepcopy(source);candidate.angle=angle;evaluations+=1
            try:candidate_blocks=generate(Project(objects=[candidate]))
            except ValueError:continue
            candidate_count=sum(len(b.stitches) for b in candidate_blocks);commands+=candidate_count
            if commands>command_limit:complete=False;break
            if sum(counts)-counts[index]+candidate_count>250_000:continue
            if not any(s.command=='stitch' for b in candidate_blocks for s in b.stitches):continue
            candidate_state=movement(candidate_blocks[0].stitches) if candidate_blocks else None
            trial=list(states);trial[index]=candidate_state;cost=travel_cost(trial)
            if cost<best_cost-1e-6:best=candidate;best_state=candidate_state;best_cost=cost;best_count=candidate_count
        if best is not source:
            result.objects[index]=best;states[index]=best_state;counts[index]=best_count
            changes.append({'region':index,'from_degrees':source.angle,'to_degrees':best.angle,'travel_saved_mm':current-best_cost})
            current=best_cost
        if not complete:break
    Project.loads(result.dumps());generate(result)
    return result,{'before_mm':before,'after_mm':current,'changes':changes,'complete':complete,
                   'evaluations':evaluations,'generated_commands':commands}
