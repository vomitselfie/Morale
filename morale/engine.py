"""Basic running/tatami stitch generation; all coordinates are millimeters."""
from dataclasses import dataclass, field
import math
from .cleanup import short_stitch_cleanup

MAX_STITCHES = 250_000


@dataclass(frozen=True)
class Stitch:
    x: float
    y: float
    command: str = "stitch"


@dataclass
class Block:
    object_id: str
    color: str
    stitches: list[Stitch]
    color_break: bool = False
    thread: dict = field(default_factory=dict)


def segment(a, b, length):
    count = max(1, math.ceil(math.dist(a, b) / length))
    return [Stitch(a[0] + (b[0] - a[0]) * i / count, a[1] + (b[1] - a[1]) * i / count) for i in range(1, count + 1)]


def running(points, length, closed=True):
    if not points:
        return []
    result = [Stitch(*points[0], "jump")]
    route = points + [points[0]] if closed else points
    # Resample along the path, avoiding a short stitch at every flattened curve vertex.
    previous = route[0]
    remaining = length
    for index, target in enumerate(route[1:], 1):
        distance = math.dist(previous, target)
        while distance >= remaining and distance > 1e-9:
            ratio = remaining / distance
            previous = (previous[0] + (target[0] - previous[0]) * ratio, previous[1] + (target[1] - previous[1]) * ratio)
            result.append(Stitch(*previous))
            distance = math.dist(previous, target)
            remaining = length
        remaining -= distance
        previous = target
        if index < len(route) - 1:
            incoming = (target[0] - route[index - 1][0], target[1] - route[index - 1][1])
            outgoing = (route[index + 1][0] - target[0], route[index + 1][1] - target[1])
            magnitude = math.hypot(*incoming) * math.hypot(*outgoing)
            # Preserve deliberate corners while resampling smooth curves.
            if magnitude > 1e-9 and (incoming[0] * outgoing[0] + incoming[1] * outgoing[1]) / magnitude < math.cos(math.radians(20)):
                if math.dist((result[-1].x, result[-1].y), target) > .05:
                    result.append(Stitch(*target))
                remaining = length
    if math.dist((result[-1].x, result[-1].y), route[-1]) > .05:
        result.append(Stitch(*route[-1]))
    return result


def segment_inside(a, b, polygon, holes=()):
    """Test all edge-delimited intervals, rather than sampling a few points."""
    def cross(u, v):
        return u[0] * v[1] - u[1] * v[0]
    edges = [edge for ring in [polygon, *holes] for edge in zip(ring, ring[1:] + ring[:1])]
    def inside(point):
        x, y = point
        result = False
        for c, d in edges:
            edge = (d[0] - c[0], d[1] - c[1])
            relative = (x - c[0], y - c[1])
            if abs(cross(edge, relative)) < 1e-8 and min(c[0], d[0]) - 1e-8 <= x <= max(c[0], d[0]) + 1e-8 and min(c[1], d[1]) - 1e-8 <= y <= max(c[1], d[1]) + 1e-8:
                return True
            if (c[1] > y) != (d[1] > y) and x < c[0] + (y - c[1]) * (d[0] - c[0]) / (d[1] - c[1]):
                result = not result
        return result
    direction = (b[0] - a[0], b[1] - a[1])
    cuts = [0., 1.]
    for c, d in edges:
        edge = (d[0] - c[0], d[1] - c[1])
        denominator = cross(direction, edge)
        if abs(denominator) < 1e-10:
            continue
        relative = (c[0] - a[0], c[1] - a[1])
        t, u = cross(relative, edge) / denominator, cross(relative, direction) / denominator
        if 0 < t < 1 and 0 <= u <= 1:
            cuts.append(t)
    cuts.sort()
    return inside(a) and inside(b) and all(inside((a[0] + direction[0] * (left + right) / 2, a[1] + direction[1] * (left + right) / 2)) for left, right in zip(cuts, cuts[1:]))


def fill(points, spacing, length, angle, connect=False, holes=(), compensation=0, end_spacing=None, reverse_gradient=False):
    if isinstance(compensation, bool) or not math.isfinite(compensation) or not 0 <= compensation <= 2:
        raise ValueError("Pull compensation must be between 0 and 2 mm per side.")
    a = math.radians(angle)
    c, s = math.cos(a), math.sin(a)
    rotated = [(x * c + y * s, -x * s + y * c) for x, y in points]
    rotated_holes = [[(x * c + y * s, -x * s + y * c) for x, y in ring] for ring in holes]
    all_points = rotated + [p for ring in rotated_holes for p in ring]
    low, high = min(y for _, y in all_points), max(y for _, y in all_points)
    stitches = []
    from .density import fill_rows
    edges = [edge for ring in [rotated, *rotated_holes] for edge in zip(ring, ring[1:] + ring[:1])]
    for row,y in enumerate(fill_rows(low,high,spacing,end_spacing,reverse_gradient)):
        cuts = sorted(x1 + (y - y1) * (x2 - x1) / (y2 - y1)
                      for (x1, y1), (x2, y2) in edges if min(y1, y2) <= y < max(y1, y2))
        spans = list(zip(cuts[::2], cuts[1::2]))
        if compensation:
            expanded = []
            for left, right in spans:
                if right - left <= 1e-9:
                    continue
                left, right = left - compensation, right + compensation
                if expanded and left <= expanded[-1][1]:
                    expanded[-1] = (expanded[-1][0], max(right, expanded[-1][1]))
                else:
                    expanded.append((left, right))
            spans = expanded
        if row % 2:
            spans.reverse()
        for left, right in spans:
            start, end = ((right, y), (left, y)) if row % 2 else ((left, y), (right, y))
            previous = (stitches[-1].x, stitches[-1].y) if stitches else None
            if connect and previous is not None and math.dist(previous, start) <= length * 2 and segment_inside(previous, start, rotated, rotated_holes):
                if math.dist(previous, start) > .001:
                    stitches.extend(segment(previous, start, length))
            else:
                stitches.append(Stitch(*start, "jump"))
            stitches.extend(segment(start, end, length))
        if len(stitches) > MAX_STITCHES:
            raise ValueError("This fill exceeds the 250,000-command preview limit. Increase spacing or reduce its size.")
    return [Stitch(p.x * c - p.y * s, p.x * s + p.y * c, p.command) for p in stitches]


def triple_run(stitches):
    result = []
    previous = None
    for stitch in stitches:
        result.append(stitch)
        if previous is not None and stitch.command == "stitch":
            result.extend([Stitch(previous.x, previous.y), stitch])
        previous = stitch
    return result


def satin(points, spacing, maximum, compensation=0):
    """Alternate rails sampled at half row spacing, splitting long spans."""
    if isinstance(compensation, bool) or not math.isfinite(compensation) or not 0 <= compensation <= 2:
        raise ValueError("Pull compensation must be between 0 and 2 mm per side.")
    if len(points) < 4 or len(points) % 2:
        raise ValueError("Satin needs at least two complete rail pairs.")
    pairs = list(zip(points[::2], points[1::2]))
    stations = [pairs[0]]
    winding = None
    for (left, right), (next_left, next_right) in zip(pairs, pairs[1:]):
        quad = [left, right, next_right, next_left]
        turns = []
        for i in range(4):
            a, b, c = quad[i], quad[(i + 1) % 4], quad[(i + 2) % 4]
            turn = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
            if abs(turn) > 1e-8:
                turns.append(1 if turn > 0 else -1)
        if turns:
            if min(turns) != max(turns) or winding is not None and turns[0] != winding:
                raise ValueError("Satin rails cross or fold back. Keep left/right pairs in order and avoid concave rail cells.")
            winding = turns[0]
        elif max(math.dist(left, right), math.dist(next_left, next_right)) > .01:
            raise ValueError("Satin rail pairs overlap without forward progress.")
        distance = max(math.dist(left, next_left), math.dist(right, next_right))
        count = max(1, math.ceil(distance / (spacing / 2)))
        if len(stations) + count > MAX_STITCHES:
            raise ValueError("Satin exceeds the preview command limit.")
        for i in range(1, count + 1):
            t = i / count
            stations.append(((left[0] + (next_left[0] - left[0]) * t, left[1] + (next_left[1] - left[1]) * t),
                             (right[0] + (next_right[0] - right[0]) * t, right[1] + (next_right[1] - right[1]) * t)))
    if winding is None:
        raise ValueError("Satin rails enclose no area.")
    if compensation:
        expanded = []
        for left, right in stations:
            width = math.dist(left, right)
            if width <= 1e-9:
                expanded.append((left, right))  # Retain a true tapered tip.
                continue
            dx, dy = (right[0]-left[0])*compensation/width, (right[1]-left[1])*compensation/width
            expanded.append(((left[0]-dx, left[1]-dy), (right[0]+dx, right[1]+dy)))
        stations = expanded
    result = [Stitch(*stations[0][0], "jump")]
    for i, pair in enumerate(stations):
        target = pair[i % 2]
        previous = (result[-1].x, result[-1].y)
        if math.dist(previous, target) > .001:
            result.extend(segment(previous, target, maximum))
        if len(result) > MAX_STITCHES:
            raise ValueError("Satin exceeds the preview command limit.")
    return result


def finish_stitches(stitches, tie_in=False, tie_off=False, trim_after=False):
    """Add small reversible locking runs to each sewn run, preserving jumps."""
    result = []
    run = []
    anchor = None

    def lock(a, b):
        distance = math.dist((a.x, a.y), (b.x, b.y))
        if distance < .05:
            return []
        t = min(.6, distance / 2) / distance
        near = Stitch(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t)
        return [near, Stitch(a.x, a.y), near, Stitch(a.x, a.y)]

    def flush():
        if not run:
            return
        start = anchor if anchor is not None else run[0]
        if tie_in:
            first = next((s for s in run if math.dist((s.x, s.y), (start.x, start.y)) >= .05), None)
            if first:
                result.extend(lock(start, first))
        result.extend(run)
        if tie_off:
            candidates = ([anchor] if anchor else []) + run[:-1]
            previous = next((s for s in reversed(candidates) if math.dist((s.x, s.y), (run[-1].x, run[-1].y)) >= .05), None)
            if previous:
                result.extend(lock(run[-1], previous))
        run.clear()

    for stitch in stitches:
        if stitch.command == "stitch":
            run.append(stitch)
        else:
            flush()
            result.append(stitch)
            anchor = stitch
    flush()
    if trim_after and any(s.command == "stitch" for s in result):
        result.append(Stitch(result[-1].x, result[-1].y, "trim"))
    return result


def generate_underlay(obj):
    from .underlay import inset_rings, inset_rails
    if not obj.underlay:
        return []
    style = obj.underlay_style
    if obj.kind == "satin":
        if style not in {"auto", "zigzag", "center_zigzag"}:
            raise ValueError("Satin underlay supports center run, zigzag, or both.")
        rails = obj.transform(obj.points)
        center = [((a[0]+b[0])/2,(a[1]+b[1])/2) for a,b in zip(rails[::2],rails[1::2])]
        result = running(center,obj.stitch_length,closed=False) if style in {"auto","center_zigzag"} else []
        if style in {"zigzag","center_zigzag"}:
            supports = inset_rails(rails,obj.underlay_inset)
            # Fully collapsed support rails form a center run, not invalid satin.
            if all(math.dist(a,b)<1e-8 for a,b in zip(supports[::2],supports[1::2])):
                if not result:
                    result = running(center,obj.stitch_length,closed=False)
            else:
                result += satin(supports,obj.underlay_spacing,obj.satin_max)
        return result
    if style not in {"auto", "edge", "sparse", "edge_sparse"}:
        raise ValueError("Fill underlay supports edge run, sparse fill, or both.")
    rings = inset_rings(obj.rings(),obj.underlay_inset)
    if not rings:
        return []
    result = []
    if style in {"auto","edge","edge_sparse"}:
        for ring in rings:
            if obj.underlay_inset == 0:
                result += running(ring,obj.stitch_length)
            else:
                # Resampling across a rounded inset corner can cut back toward
                # the source boundary. Retain the inset polygon vertices.
                result.append(Stitch(*ring[0],"jump"))
                for a,b in zip(ring,ring[1:]+ring[:1]):
                    result += segment(a,b,obj.stitch_length)
                    if len(result)>MAX_STITCHES:
                        raise ValueError("Inset underlay exceeds the preview command limit.")
    if style in {"sparse","edge_sparse"}:
        result += fill(rings[0],obj.underlay_spacing,obj.stitch_length,obj.angle+90,False,rings[1:])
    return result


def contour_fill(rings,spacing,length):
    from .underlay import OffsetGeometry
    if not math.isfinite(spacing) or not .2 <= spacing <= 5:
        raise ValueError("Contour spacing must be between 0.2 and 5 mm.")
    geometry=OffsetGeometry(rings)
    result=[]
    for layer in range(math.ceil(geometry.maximum_depth/spacing)+1):
        distance=spacing*(layer+.5)
        if distance>geometry.maximum_depth+1e-8:
            break
        contours=geometry.inset(distance)
        if not contours:
            break
        for ring in contours:
            result.append(Stitch(*ring[0],"jump"))
            for a,b in zip(ring,ring[1:]+ring[:1]):
                result += segment(a,b,length)
                if len(result)>MAX_STITCHES:
                    raise ValueError("Contour fill exceeds the preview command limit. Increase spacing or reduce the shape size.")
    return result


def generate(project):
    blocks = []
    total = 0
    for obj in project.objects:
        if not obj.visible:
            continue
        points = obj.outline()
        rings = obj.rings()
        if obj.kind == "stitches":
            positions = obj.transform([(s[0], s[1]) for s in obj.stitch_data])
            stitches = [Stitch(x, y, raw[2]) for (x, y), raw in zip(positions, obj.stitch_data)]
        elif obj.stitch_type in {"motif", "pattern"}:
            from .motifs import motif_paths
            from .pattern_fill import pattern_fill_paths
            stitches=[]
            for path in (pattern_fill_paths(obj) if obj.stitch_type == "pattern" else motif_paths(obj)):
                stitches.append(Stitch(*path[0],"jump"))
                for a,b in zip(path,path[1:]):
                    stitches += segment(a,b,obj.stitch_length)
                    if len(stitches)>MAX_STITCHES:
                        raise ValueError("Motif stitches exceed the preview command limit.")
        elif obj.stitch_type in {"running", "triple"}:
            stitches = [s for ring in rings for s in running(ring, obj.stitch_length, obj.kind != "path")]
            if obj.stitch_type == "triple":
                stitches = triple_run(stitches)
        elif obj.kind == "satin":
            rails = obj.transform(obj.points)
            stitches = generate_underlay(obj)
            stitches += satin(rails, obj.spacing, obj.satin_max, obj.pull_compensation)
        else:
            stitches = generate_underlay(obj)
            if obj.stitch_type == "contour":
                stitches += contour_fill(rings,obj.spacing,obj.stitch_length)
            else:
                stitches += fill(rings[0], obj.spacing, obj.stitch_length, obj.angle, obj.connect_fill, rings[1:], obj.pull_compensation,
                                 obj.gradient_end_spacing if obj.density_gradient else None, obj.gradient_reverse)
        if obj.kind != "stitches":
            stitches = short_stitch_cleanup(stitches,obj.minimum_stitch,obj.satin_max if obj.kind == "satin" else obj.stitch_length)
            stitches = finish_stitches(stitches, obj.tie_in, obj.tie_off, obj.trim_after)
            if obj.stop_after and stitches:
                stitches.append(Stitch(stitches[-1].x, stitches[-1].y, "stop"))
        total += len(stitches)
        if total > MAX_STITCHES:
            raise ValueError("Design exceeds the 250,000-command preview limit.")
        blocks.append(Block(obj.id, obj.color, stitches, obj.color_break, dict(obj.thread)))
    return blocks


def preflight(project, blocks):
    issues = []
    points = [s for b in blocks for s in b.stitches]
    if not any(s.command == "stitch" for s in points):
        issues.append("The design has no stitches to export.")
    outline = [p for obj in project.objects if obj.visible for ring in obj.rings() for p in ring]
    if any(abs(x) > project.hoop_width / 2 + .001 or abs(y) > project.hoop_height / 2 + .001
           for x, y in outline + [(s.x, s.y) for s in points]):
        issues.append("The design extends beyond the selected hoop. Move or resize the objects before export.")
    return issues
