"""Align a moving selection's outline bounds to visible stationary objects."""
from PySide6.QtCore import QPointF,QRectF


def object_bounds(obj):
    if obj.kind=='stitches':
        points=obj.transform([(x,y) for x,y,command in obj.stitch_data if command in {'stitch','jump'}])
    else:points=[point for ring in obj.rings() for point in ring]
    if not points:return QRectF(obj.x,obj.y,0,0)
    xs,ys=zip(*points)
    return QRectF(min(xs),min(ys),max(xs)-min(xs),max(ys)-min(ys))


def snap_bounds(moving,targets,delta,tolerance):
    if not moving or not targets:return QPointF(delta),(None,None)
    left=min(r.left() for r in moving);right=max(r.right() for r in moving)
    top=min(r.top() for r in moving);bottom=max(r.bottom() for r in moving)
    axes=((left,(left+right)/2,right),(top,(top+bottom)/2,bottom))
    result=QPointF(delta);guides=[]
    for axis,anchors in enumerate(axes):
        offset=delta.x() if axis==0 else delta.y();choices=[]
        for box in targets:
            edges=(box.left(),box.center().x(),box.right()) if axis==0 else (box.top(),box.center().y(),box.bottom())
            for target in edges:
                for anchor in anchors:
                    adjustment=target-anchor-offset
                    if abs(adjustment)<=tolerance:choices.append((abs(adjustment),target,adjustment))
        if choices:
            _,target,adjustment=min(choices)
            if axis==0:result.setX(offset+adjustment)
            else:result.setY(offset+adjustment)
            guides.append(target)
        else:guides.append(None)
    return result,tuple(guides)
