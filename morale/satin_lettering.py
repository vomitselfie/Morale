"""Plan satin columns for system-font lettering.

Each glyph component (an outline with its holes) is planned once, when the
lettering is created or edited, with the same column fitting, closed-band and
crotch-splitting tools as artwork conversion. Strokes too wide or too complex
for satin keep a tatami fill; hairlines become running stitches. The plan is
stored with the lettering so stitch generation stays fast.
"""
import math

from .model import Project, DesignObject
from .branch_regions import _locate

JOIN_OVERLAP_MM = .3


def _contains(ring, point):
    inside = False
    for a, b in zip(ring, ring[1:] + ring[:1]):
        if (a[1] > point[1]) != (b[1] > point[1]) and point[0] < a[0] + (b[0] - a[0]) * (point[1] - a[1]) / (b[1] - a[1]):
            inside = not inside
    return inside


def components(rings):
    """Group even-odd rings into outlines with their holes, left to right."""
    depth = [sum(_contains(other, ring[0]) for j, other in enumerate(rings) if j != i) for i, ring in enumerate(rings)]
    outers = [i for i, d in enumerate(depth) if d % 2 == 0]
    groups = {i: [rings[i]] for i in outers}
    for i, d in enumerate(depth):
        if d % 2:
            # The hole belongs to the innermost outline that contains it.
            owners = [o for o in outers if depth[o] == d - 1 and _contains(rings[o], rings[i][0])]
            if owners:
                groups[owners[0]].append(rings[i])
    return sorted(groups.values(), key=lambda group: (min(x for x, _ in group[0]), min(y for _, y in group[0])))


def _object(group, template):
    from .geometry import replace_contours
    obj = DesignObject(kind="compound", x=0, y=0, width=1, height=1, underlay=False,
                       contours=[[[0, 0], [1, 0], [0, 1]]], color=template.color, thread=dict(template.thread))
    return replace_contours(obj, [[tuple(p) for p in ring] for ring in group])


def _area(ring):
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:] + ring[:1])) / 2


def _crosses(p, q, rings):
    """True when segment p-q touches any ring edge away from its own endpoints."""
    dx, dy = q[0] - p[0], q[1] - p[1]
    for ring in rings:
        for a, b in zip(ring, ring[1:] + ring[:1]):
            ex, ey = b[0] - a[0], b[1] - a[1]
            denominator = dx * ey - dy * ex
            if abs(denominator) < 1e-12:
                continue
            t = ((a[0] - p[0]) * ey - (a[1] - p[1]) * ex) / denominator
            u = ((a[0] - p[0]) * dy - (a[1] - p[1]) * dx) / denominator
            if 1e-7 < t < 1 - 1e-7 and -1e-9 <= u <= 1 + 1e-9:
                return True
    return False


def _foot(ring, p):
    """Closest point on ``ring`` to p, as (distance, edge index, point)."""
    best = None
    for index, (a, b) in enumerate(zip(ring, ring[1:] + ring[:1])):
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = dx * dx + dy * dy
        t = max(0., min(1., ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / length)) if length else 0.
        point = (a[0] + t * dx, a[1] + t * dy)
        distance = math.dist(p, point)
        if best is None or distance < best[0]:
            best = (distance, index, point)
    return best


def _bridges(outer, hole, others):
    """Two short cuts from opposite sides of ``hole`` to ``outer``, avoiding other rings."""
    lengths = [0.]
    for a, b in zip(hole, hole[1:] + hole[:1]):
        lengths.append(lengths[-1] + math.dist(a, b))
    perimeter = lengths[-1]
    candidates = sorted((_foot(outer, p) + (i,) for i, p in enumerate(hole)), key=lambda c: c[0])
    rings = [outer, hole, *others]
    chosen = []
    for distance, edge, point, i in candidates:
        if chosen:
            gap = abs(lengths[i] - lengths[chosen[0][2]])
            if min(gap, perimeter - gap) < perimeter * .3:
                continue
        if _crosses(hole[i], point, rings):
            continue
        middle = ((hole[i][0] + point[0]) / 2, (hole[i][1] + point[1]) / 2)
        if not _contains(outer, middle) or any(_contains(r, middle) for r in [hole, *others]):
            continue
        chosen.append((edge, point, i))
        if len(chosen) == 2:
            return chosen
    return None


def cut_holes(group):
    """Open every hole with two cuts to the outline, giving hole-free rings.

    Returns None when a hole cannot be bridged cleanly (for example when other
    holes block every short cut).
    """
    outer = [tuple(p) for p in group[0]]
    if _area(outer) < 0:
        outer.reverse()
    pending = [[tuple(p) for p in hole] for hole in group[1:]]
    for hole in pending:
        if _area(hole) > 0:
            hole.reverse()
    work = [(outer, pending)]
    done = []
    while work:
        outer, holes = work.pop()
        if not holes:
            done.append(outer)
            continue
        hole, others = holes[0], holes[1:]
        bridges = _bridges(outer, hole, others)
        if bridges is None or len(done) + len(work) > 12:
            return None
        (_, point_a, i_a), (_, point_b, i_b) = bridges
        # Locating inserts each foot on whichever (possibly split) edge holds it.
        outer, _ = _locate(outer, point_a)
        outer, _ = _locate(outer, point_b)
        _, j_a = _locate(outer, point_a)
        _, j_b = _locate(outer, point_b)
        if j_a is None or j_b is None or j_a == j_b:
            return None
        n, m = len(outer), len(hole)
        # Outline runs forward (region on the left); the reversed hole does too.
        first = [outer[(j_a + k) % n] for k in range((j_b - j_a) % n + 1)] + [hole[(i_b + k) % m] for k in range((i_a - i_b) % m + 1)]
        second = [outer[(j_b + k) % n] for k in range((j_a - j_b) % n + 1)] + [hole[(i_a + k) % m] for k in range((i_b - i_a) % m + 1)]
        for ring in (first, second):
            if len(ring) < 3 or _area(ring) <= 0:
                return None
            inside = [h for h in others if _contains(ring, h[0])]
            work.append((ring, inside))
    return done


def plan_columns(rings, template=None):
    """Satin, fill and running pieces in world millimetres, in sewing order."""
    from .auto_digitize import choose_stitches
    from .branch_regions import split_branches
    template = template or DesignObject()
    pieces = []
    stats = {"glyph_parts": 0, "satin": 0, "fill": 0, "running": 0}
    for group in components(rings):
        stats["glyph_parts"] += 1
        source = _object(group, template)
        planned, decisions = choose_stitches(Project(objects=[source]))
        if decisions[0]["selected"] == "fill":
            # Holes that are not simple bands (b, e, A, R...) are opened first.
            simple = [group[0]] if len(group) == 1 else cut_holes(group)
            if simple is not None:
                objects, choices = [], []
                for ring in simple:
                    part = _object([ring], template)
                    split, _ = split_branches(Project(objects=[part]), JOIN_OVERLAP_MM)
                    result, chosen = choose_stitches(split)
                    objects += result.objects
                    choices += chosen
                planned, decisions = Project(objects=objects), choices
        for obj, decision in zip(planned.objects, decisions):
            kind = decision["selected"]
            if kind == "satin":
                pieces.append({"rails": [list(p) for p in obj.transform(obj.points)]})
            elif kind == "running":
                pieces.append({"run": [list(p) for p in obj.transform(obj.points)]})
            else:
                pieces.append({"fill": [[list(p) for p in ring] for ring in obj.rings()]})
                kind = "fill"
            stats[kind] += 1
    return pieces, stats


def normalize(obj, points):
    """Inverse of ``DesignObject.transform``: world millimetres to the object frame."""
    angle = math.radians(obj.rotation)
    c, s = math.cos(angle), math.sin(angle)
    sx, sy = (-1 if obj.flip_x else 1) * obj.width, (-1 if obj.flip_y else 1) * obj.height
    return [[((x - obj.x) * c + (y - obj.y) * s) / sx, (-(x - obj.x) * s + (y - obj.y) * c) / sy] for x, y in points]


def attach_columns(obj):
    """Plan satin columns for lettering ``obj`` and store them with it."""
    pieces, stats = plan_columns(obj.rings(), obj)
    columns = []
    for piece in pieces:
        kind, value = next(iter(piece.items()))
        columns.append({kind: [normalize(obj, ring) for ring in value] if kind == "fill" else normalize(obj, value)})
    obj.lettering["columns"] = columns
    return stats
