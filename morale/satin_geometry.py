"""Global overlap checks for locally convex satin rail cells."""
import math


def validate_cells(pairs):
    """Reject local folds and positive-area overlap between separate cells."""
    winding=None
    for (left,right),(next_left,next_right) in zip(pairs,pairs[1:]):
        quad=[left,right,next_right,next_left];turns=[]
        for i in range(4):
            a,b,c=quad[i],quad[(i+1)%4],quad[(i+2)%4]
            turn=(b[0]-a[0])*(c[1]-b[1])-(b[1]-a[1])*(c[0]-b[0])
            if abs(turn)>1e-8:turns.append(1 if turn>0 else -1)
        if turns:
            if min(turns)!=max(turns) or winding is not None and turns[0]!=winding:
                raise ValueError('Satin rails cross or fold back. Keep left/right pairs in order and avoid concave rail cells.')
            winding=turns[0]
        elif max(math.dist(left,right),math.dist(next_left,next_right))>.01:
            raise ValueError('Satin rail pairs overlap without forward progress.')
    if winding is None:raise ValueError('Satin rails enclose no area.')
    overlap=overlapping_cells(pairs)
    if overlap is not None:
        raise ValueError(f'Satin rail cells {overlap[0]+1} and {overlap[1]+1} overlap. Split the column or adjust its rails.')


def overlapping_cells(pairs):
    cells=[]
    for index,((left,right),(next_left,next_right)) in enumerate(zip(pairs,pairs[1:])):
        quad=[left,right,next_right,next_left]
        area=abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(quad,quad[1:]+quad[:1])))/2
        if area<=1e-10:continue
        xs,ys=zip(*quad)
        cells.append((min(xs),max(xs),min(ys),max(ys),index,quad))
    # Sweep the longer design axis so vertical columns prune as efficiently
    # as horizontal ones. The exact convex-cell test remains in world space.
    if not cells:return None
    width=max(c[1] for c in cells)-min(c[0] for c in cells)
    height=max(c[3] for c in cells)-min(c[2] for c in cells)
    axis=2 if height>width else 0
    active=[]
    for cell in sorted(cells,key=lambda c:c[axis]):
        xmin,xmax,ymin,ymax,index,quad=cell
        active=[other for other in active if other[axis+1]>cell[axis]+1e-8]
        for other in active:
            if abs(index-other[4])<=1 or min(ymax,other[3])-max(ymin,other[2])<=1e-8:continue
            separated=False
            for polygon in (quad,other[5]):
                for a,b in zip(polygon,polygon[1:]+polygon[:1]):
                    dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
                    if length<=1e-10:continue
                    nx,ny=-dy/length,dx/length
                    p=[x*nx+y*ny for x,y in quad];q=[x*nx+y*ny for x,y in other[5]]
                    if min(max(p),max(q))-max(min(p),min(q))<=1e-8:
                        separated=True;break
                if separated:break
            if not separated:return other[4],index
        active.append(cell)
    return None
