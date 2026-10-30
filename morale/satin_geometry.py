"""Satin rail geometry: corner pivots, short stitches and overlap checks."""
import math

# Where landings on one rail come closer than this, alternate stitches stop
# short of that rail by a fraction of the column width, as Ink/Stitch does.
SHORT_STITCH_DISTANCE = .25
SHORT_STITCH_INSET = .15
# Rungs may pivot where they cross within this fraction of their length from
# the same rail.
PIVOT_LIMIT = .45


# Split points move along the stitch by up to this fraction of a piece, cycling
# through these offsets so they do not line up into a groove down the column.
# After ZigZag's satin auto-split (Apache-2.0).
SPLIT_STAGGER = (0, .33, -.33)


def staggered_split(a, b, maximum, index):
    """Positions splitting stitch ``index`` from a to b into pieces no longer
    than ``maximum``, excluding a and including b.

    Each stitch shifts its split points by a different offset; a stitch is cut
    into more pieces when the shifted ones would otherwise exceed ``maximum``.
    """
    length = math.dist(a, b)
    count = max(1, math.ceil(length / maximum))
    offset = SPLIT_STAGGER[index % len(SPLIT_STAGGER)]
    if count > 1 and offset:
        # The longest piece is (1 + |offset|) / count of the stitch.
        while length * (1 + abs(offset)) / count > maximum:
            count += 1
        shift = offset / count
    else:
        shift = 0
    fractions = [i / count + shift for i in range(1, count)] + [1]
    return [(a[0] + (b[0]-a[0])*f, a[1] + (b[1]-a[1])*f) for f in fractions]


def _crossing(a, b, c, d):
    """Parameters (t, u) where segments a-b and c-d meet, ends included."""
    rx, ry, sx, sy = b[0]-a[0], b[1]-a[1], d[0]-c[0], d[1]-c[1]
    denominator = rx*sy - ry*sx
    if abs(denominator) < 1e-12:
        return None
    t = ((c[0]-a[0])*sy - (c[1]-a[1])*sx) / denominator
    u = ((c[0]-a[0])*ry - (c[1]-a[1])*rx) / denominator
    return (t, u) if -1e-9 <= t <= 1+1e-9 and -1e-9 <= u <= 1+1e-9 else None


def clip_rail_loops(rail, limit):
    """Cut the small loop a rail makes past a sharp inner corner.

    Rungs drawn square to each side of a corner overshoot its inner point, so
    the inner rail crosses itself. Points on the loop move to the crossing.
    Only loops up to ``limit`` mm long are cut; longer ones are real overlaps.
    """
    rail = list(rail)
    j = 0
    while j < len(rail) - 3:
        length, k = math.dist(rail[j], rail[j+1]), j + 1
        while k < len(rail) - 1 and length <= limit:
            crossing = _crossing(rail[j], rail[j+1], rail[k], rail[k+1]) if k > j + 1 else None
            if crossing is not None:  # Includes loops closing on a shared vertex.
                t = crossing[0]
                point = (rail[j][0] + (rail[j+1][0]-rail[j][0])*t, rail[j][1] + (rail[j+1][1]-rail[j][1])*t)
                rail[j+1:k+1] = [point] * (k - j)
                break
            length += math.dist(rail[k], rail[k+1])
            k += 1
        j = k if k < len(rail) - 1 and length <= limit else j + 1
    return rail


def pivot_corners(pairs):
    """Turn sharp corners into fans instead of folds.

    Inside a corner tighter than the column is wide, the inner rail loops past
    the corner point and consecutive rungs cross before reaching it, which
    would sew bow ties and overlapping stitches. The loop is cut at the corner
    point and crossing rungs end where they cross, so the stitches fan around
    that point. The input is not changed; cells that still fold or overlap are
    left for ``validate_cells`` to report.
    """
    pairs = [tuple(pair) for pair in pairs]
    if len(pairs) > 2:
        limit = 8 * max(math.dist(left, right) for left, right in pairs)
        lefts = clip_rail_loops([left for left, _ in pairs], limit)
        rights = clip_rail_loops([right for _, right in pairs], limit)
        pairs = list(zip(lefts, rights))
    for i in range(len(pairs) - 1):
        (left, right), (next_left, next_right) = pairs[i], pairs[i+1]
        crossing = _crossing(left, right, next_left, next_right)
        if crossing is None:
            continue
        t, u = crossing
        pivot = (left[0] + (right[0]-left[0])*t, left[1] + (right[1]-left[1])*t)
        # A corner's rungs cross near its inner rail. Rungs crossing mid-column
        # are swapped or folded rails, which a fan would silently cut in half.
        if max(t, u) < PIVOT_LIMIT and max(math.dist(left, pivot), math.dist(next_left, pivot)) > 1e-9:
            pairs[i], pairs[i+1] = (pivot, right), (pivot, next_right)
        elif min(t, u) > 1 - PIVOT_LIMIT and max(math.dist(right, pivot), math.dist(next_right, pivot)) > 1e-9:
            pairs[i], pairs[i+1] = (left, pivot), (next_left, pivot)
    return pairs


def short_stitch_targets(stations, distance=SHORT_STITCH_DISTANCE, inset=SHORT_STITCH_INSET):
    """Needle landings for alternating satin stitches, shortening crowded ones.

    Station ``i`` lands on rail ``i % 2``. A landing closer than ``distance`` to
    the previous full landing on the same rail is moved toward the other rail,
    unless the previous one was already shortened, so a fan alternates full and
    short stitches instead of piling thread on its pivot.
    """
    targets, previous = [], [None, None]
    for i, pair in enumerate(stations):
        side = i % 2
        target, other = pair[side], pair[1-side]
        last = previous[side]
        if last is not None and not last[1] and math.dist(last[0], target) < distance:
            target = (target[0] + (other[0]-target[0])*inset, target[1] + (other[1]-target[1])*inset)
            previous[side] = (pair[side], True)
        else:
            previous[side] = (target, False)
        targets.append(target)
    return targets


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
