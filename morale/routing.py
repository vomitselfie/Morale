"""Explicit start anchors and direction for editable runs and satin stations,
and chosen start and end points for tatami fills."""
from copy import deepcopy
from .model import Project, drop_lettering


def routing_rings(source):
    if source.kind == 'satin':
        return [source.points[::2]]
    if source.stitch_type not in {'running','triple'} or source.kind == 'stitches':
        raise ValueError('Choose a running/triple outline or satin column. Fill routing and manual-command reversal are separate operations.')
    if source.kind == 'compound':
        return source.contours
    if source.kind in {'path','polygon'}:
        return [source.points]
    local=deepcopy(source)
    local.x=local.y=local.rotation=0
    local.width=local.height=1
    local.flip_x=local.flip_y=False
    return [local.outline()]


def route_object(source, plan):
    """Plan entries (source ring, source start anchor, reverse) also set ring order."""
    rings=routing_rings(source)
    if not isinstance(plan,(list,tuple)) or any(not isinstance(entry,(list,tuple)) or len(entry)!=3 or type(entry[0]) is not int for entry in plan):
        raise ValueError('Each route entry needs a contour index, start anchor and direction.')
    plan=[tuple(entry) for entry in plan]
    if len(plan)!=len(rings) or sorted(entry[0] for entry in plan)!=list(range(len(rings))):
        raise ValueError('The route must contain each contour exactly once.')
    for ring,start,reverse in plan:
        if type(start) is not int or not 0<=start<len(rings[ring]) or type(reverse) is not bool:
            raise ValueError('Choose an existing start anchor and direction.')
        if source.kind in {'path','satin'} and start!=0:
            raise ValueError('Open paths and satin columns start at an end; reverse to change ends.')
    result=deepcopy(source)
    if plan==[(i,0,False) for i in range(len(rings))]:
        return result
    if source.kind=='satin':
        if plan[0][2]:
            result.points=[p for pair in reversed(list(zip(source.points[::2],source.points[1::2]))) for p in pair]
    else:
        routed=[]
        orders=[]
        for ring,start,reverse in plan:
            count=len(rings[ring])
            if source.kind=='path':
                order=list(range(count-1,-1,-1)) if reverse else list(range(count))
            else:
                order=[(start+(-i if reverse else i))%count for i in range(count)]
            orders.append(order)
            routed.append([deepcopy(rings[ring][i]) for i in order])
        if source.kind=='compound':
            result.contours=routed
        else:
            result.points=routed[0]
            if source.kind!='path': result.kind='polygon'
            if source.handles:
                result.handles=[deepcopy(source.handles[i][::-1] if plan[0][2] else source.handles[i]) for i in orders[0]]
        drop_lettering(result)
    return Project.loads(Project(objects=[result]).dumps()).objects[0]


def fill_anchors(source):
    """Corners of a tatami fill's outer outline, normalized like its points."""
    if source.stitch_type != 'fill' or source.kind == 'stitches':
        raise ValueError('Choose a tatami fill to set where it starts and ends.')
    if source.kind == 'compound':
        return [list(point) for point in source.contours[0]]
    local=deepcopy(source)
    local.x=local.y=local.rotation=0
    local.width=local.height=1
    local.flip_x=local.flip_y=False
    return [list(point) for point in local.outline()]


def route_fill(source, start=None, end=None):
    """``source`` starting and ending near outline corners ``start`` and ``end``
    (indexes into fill_anchors), or automatically where None."""
    anchors=fill_anchors(source)
    for index in (start,end):
        if index is not None and (type(index) is not int or not 0<=index<len(anchors)):
            raise ValueError('Choose an existing outline point.')
    result=deepcopy(source)
    result.fill_start=anchors[start] if start is not None else []
    result.fill_end=anchors[end] if end is not None else []
    return Project.loads(Project(objects=[result]).dumps()).objects[0]
