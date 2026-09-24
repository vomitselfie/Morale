"""Reorder disconnected fill runs without changing their sewn segment geometry."""
import math
from .engine import Stitch


def route_fill_runs(stitches,limit=2000):
    runs=[]
    for stitch in stitches:
        if stitch.command=='jump':runs.append([stitch])
        elif stitch.command=='stitch' and runs:runs[-1].append(stitch)
        else:return stitches
    if not 3<=len(runs)<=limit or any(len(run)<2 for run in runs):return stitches
    def point(s):return s.x,s.y
    def travel(sequence):return sum(math.dist(point(a[-1]),point(b[0])) for a,b in zip(sequence,sequence[1:]))
    result=[runs[0]];remaining=set(range(1,len(runs)-1))
    while remaining:
        position=point(result[-1][-1])
        _,index,reverse=min((math.dist(position,point(runs[i][-1] if reverse else runs[i][0])),i,reverse) for i in remaining for reverse in (False,True))
        remaining.remove(index);run=runs[index]
        if reverse:
            reversed_points=list(reversed(run))
            run=[Stitch(reversed_points[0].x,reversed_points[0].y,'jump')]+[Stitch(s.x,s.y) for s in reversed_points[1:]]
        result.append(run)
    result.append(runs[-1])
    if travel(result)>=travel(runs)-1e-6:return stitches
    return [stitch for run in result for stitch in run]
