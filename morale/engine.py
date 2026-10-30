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


def satin(points, spacing, maximum, compensation=0, strict=True):
    """Alternate rails sampled at half row spacing, splitting long spans.

    ``strict`` turns corners whose rungs cross into fans, then rejects rail cells
    that still fold, cross or overlap earlier cells. Hand-digitized lettering
    turns tight curves with slightly concave cells, which sew as designed, so
    lettering columns pass ``strict=False``. Crowded landings on the inside of
    curves are shortened (see satin_geometry.short_stitch_targets), and stitches
    longer than ``maximum`` are split at staggered points.
    """
    from .satin_geometry import pivot_corners, short_stitch_targets, staggered_split, validate_cells
    if isinstance(compensation, bool) or not math.isfinite(compensation) or not 0 <= compensation <= 2:
        raise ValueError("Pull compensation must be between 0 and 2 mm per side.")
    if len(points) < 4 or len(points) % 2:
        raise ValueError("Satin needs at least two complete rail pairs.")
    pairs = list(zip(points[::2], points[1::2]))
    if strict:
        pairs = pivot_corners(pairs)
        validate_cells(pairs)
    stations = [pairs[0]]
    for (left, right), (next_left, next_right) in zip(pairs, pairs[1:]):
        distance = max(math.dist(left, next_left), math.dist(right, next_right))
        count = max(1, math.ceil(distance / (spacing / 2)))
        if len(stations) + count > MAX_STITCHES:
            raise ValueError("Satin exceeds the preview command limit.")
        for i in range(1, count + 1):
            t = i / count
            stations.append(((left[0] + (next_left[0] - left[0]) * t, left[1] + (next_left[1] - left[1]) * t),
                             (right[0] + (next_right[0] - right[0]) * t, right[1] + (next_right[1] - right[1]) * t)))
    if compensation:
        expanded = []
        for left, right in stations:
            width = math.dist(left, right)
            if width <= 1e-9:
                expanded.append((left, right))  # Retain a true tapered tip.
                continue
            dx, dy = (right[0]-left[0])*compensation/width, (right[1]-left[1])*compensation/width
            expanded.append(((left[0]-dx, left[1]-dy), (right[0]+dx, right[1]+dy)))
        if strict:
            expanded = pivot_corners(expanded)
            try:validate_cells(expanded)
            except ValueError as exc:
                raise ValueError(f'Pull compensation produces invalid satin rails: {exc} Reduce compensation or split the column.') from exc
        stations = expanded
    result = [Stitch(*stations[0][0], "jump")]
    for index, target in enumerate(short_stitch_targets(stations)):
        previous = (result[-1].x, result[-1].y)
        if math.dist(previous, target) > .001:
            result.extend(Stitch(x, y) for x, y in staggered_split(previous, target, maximum, index))
        if len(result) > MAX_STITCHES:
            raise ValueError("Satin exceeds the preview command limit.")
    return result


def insert_jump_trims(stitches,threshold):
    if isinstance(threshold,bool) or not isinstance(threshold,(int,float)) or not math.isfinite(threshold) or not 0<=threshold<=50:
        raise ValueError('Internal jump trim threshold must be between 0 and 50 mm.')
    if not threshold:return stitches
    additions={};last_sewn=None;previous=(0.,0.);start=None;distance=0
    for index,stitch in enumerate(stitches):
        point=(stitch.x,stitch.y)
        if stitch.command=='stitch':
            if start is not None and last_sewn is not None and distance>threshold:
                additions[start]=Stitch(*last_sewn,'trim')
            last_sewn=point;previous=point;start=None;distance=0
        elif stitch.command=='jump':
            if last_sewn is not None:
                if start is None:start=index
                distance+=math.dist(previous,point)
            previous=point
        elif stitch.command=='trim':
            last_sewn=None;start=None;distance=0
    result=[]
    for index,stitch in enumerate(stitches):
        if index in additions:result.append(additions[index])
        result.append(stitch)
    return result


def finish_stitches(stitches, tie_in=False, tie_off=False, trim_after=False, jump_trim=0):
    """Add small reversible locking runs to each sewn run, preserving jumps."""
    result = []
    run = []
    anchor = None
    pending_lock=False

    def lock(a, b):
        distance = math.dist((a.x, a.y), (b.x, b.y))
        if distance < .05:
            return []
        t = min(.6, distance / 2) / distance
        near = Stitch(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t)
        return [near, Stitch(a.x, a.y), near, Stitch(a.x, a.y)]

    def flush(force_off=False):
        nonlocal pending_lock
        if not run:
            return
        start = anchor if anchor is not None else run[0]
        if tie_in or pending_lock:
            first = next((s for s in run if math.dist((s.x, s.y), (start.x, start.y)) >= .05), None)
            if first:
                result.extend(lock(start, first))
        result.extend(run)
        if tie_off or force_off:
            candidates = ([anchor] if anchor else []) + run[:-1]
            previous = next((s for s in reversed(candidates) if math.dist((s.x, s.y), (run[-1].x, run[-1].y)) >= .05), None)
            if previous:
                result.extend(lock(run[-1], previous))
        run.clear()
        pending_lock=False

    for stitch in insert_jump_trims(stitches,jump_trim):
        if stitch.command == "stitch":
            run.append(stitch)
        else:
            flush(force_off=bool(jump_trim and stitch.command=='trim'))
            result.append(stitch)
            if jump_trim and stitch.command=='trim':pending_lock=True
            anchor = stitch
    flush()
    if trim_after and any(s.command == "stitch" for s in result):
        result.append(Stitch(result[-1].x, result[-1].y, "trim"))
    return result


def generate_underlay(obj):
    from .underlay import inset_rings
    if not obj.underlay:
        return []
    style = obj.underlay_style
    if obj.kind == "satin":
        passes, _ = satin_underlay_runs(obj, obj.transform(obj.points), style)
        return [s for run in passes for s in run.stitches]
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


def satin_underlay_runs(obj, rails, style):
    """Satin underlay passes in their natural direction, and the center run that
    can bring the needle back to the column start."""
    from .generated import GeneratedRun
    from .underlay import inset_rails
    if style not in {"auto", "zigzag", "center_zigzag"}:
        raise ValueError("Satin underlay supports center run, zigzag, or both.")
    center_points = [((a[0]+b[0])/2, (a[1]+b[1])/2) for a, b in zip(rails[::2], rails[1::2])]
    center = GeneratedRun(running(center_points, obj.stitch_length, closed=False), "underlay", reversible=True)
    passes = [center] if style in {"auto", "center_zigzag"} else []
    if style in {"zigzag", "center_zigzag"}:
        supports = inset_rails(rails, obj.underlay_inset)
        # Fully collapsed support rails form a center run, not invalid satin.
        if all(math.dist(a, b) < 1e-8 for a, b in zip(supports[::2], supports[1::2])):
            if not passes:
                passes = [center]
        else:
            passes.append(GeneratedRun(satin(supports, obj.underlay_spacing, obj.satin_max), "underlay", reversible=True))
    return passes, center


def satin_column_runs(obj, rails, style, strict=True):
    """Underlay and top passes for one satin column, planned so that the column
    starts and ends where its top pass does (see generated.plan_column)."""
    from .generated import GeneratedRun, plan_column
    top = GeneratedRun(satin(rails, obj.spacing, obj.satin_max, obj.pull_compensation, strict=strict), "top", reversible=True)
    if not obj.underlay:
        return [top]
    passes, center = satin_underlay_runs(obj, rails, style)
    return plan_column(passes, top, center)


def lettering_columns(obj):
    """Sew planned satin-lettering pieces in text order."""
    from .generated import GeneratedRun
    runs = []
    for piece in obj.lettering["columns"]:
        if "rails" in piece:
            runs += satin_column_runs(obj, obj.transform(piece["rails"]), "auto", strict=False)
        elif "run" in piece:
            runs.append(GeneratedRun(running(obj.transform(piece["run"]), obj.stitch_length, closed=False), "top"))
        else:
            rings = [obj.transform(ring) for ring in piece["fill"]]
            runs.append(GeneratedRun(fill(rings[0], obj.spacing, obj.stitch_length, obj.angle, obj.connect_fill, rings[1:], obj.pull_compensation), "top"))
        if sum(len(run.stitches) for run in runs) > MAX_STITCHES:
            raise ValueError("Satin lettering exceeds the preview command limit.")
    return runs


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


def tatami(obj, rings):
    """Tatami fill with its chosen entry and exit and any inside travel."""
    from .fill_travel import FillTravel, choose_entry, enter_and_exit, reversed_stitches, travel_inside
    def rows(angle):
        return fill(rings[0], obj.spacing, obj.stitch_length, angle, obj.connect_fill, rings[1:], obj.pull_compensation,
                    obj.gradient_end_spacing if obj.density_gradient else None, obj.gradient_reverse)
    stitches = rows(obj.angle)
    start = obj.transform([obj.fill_start])[0] if obj.fill_start else None
    end = obj.transform([obj.fill_end])[0] if obj.fill_end else None
    if (start or end) and stitches:
        # Sew from either end, and (without a density gradient, which is anchored
        # to one side) with rows laid from the opposite side.
        candidates = [stitches, reversed_stitches(stitches)]
        if not obj.density_gradient:
            opposite = rows(obj.angle + 180)
            if opposite:
                candidates += [opposite, reversed_stitches(opposite)]
        stitches = choose_entry(candidates, start, end)
    if obj.route_fill:
        from .fill_routing import route_fill_runs
        stitches = route_fill_runs(stitches)
    # Inside travel joins routed sections; unrouted rows would walk round every
    # hole or notch they cross.
    sectioned = obj.connect_fill and obj.route_fill
    if sectioned or start or end:
        travel = FillTravel(rings)
        if sectioned:
            stitches = travel_inside(stitches, travel, obj.stitch_length)
        stitches = enter_and_exit(stitches, travel, obj.stitch_length, start, end)
    return stitches


def generate_object(obj):
    """An object's stitches as structured passes, before cleanup and finishing."""
    from .generated import GeneratedObject, GeneratedRun
    rings = obj.rings()
    if obj.kind == "compound" and obj.stitch_type == "satin":
        return GeneratedObject(obj.id, lettering_columns(obj))
    if obj.kind == "satin":
        return GeneratedObject(obj.id, satin_column_runs(obj, obj.transform(obj.points), obj.underlay_style))
    underlay = []
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
    else:
        underlay = generate_underlay(obj)
        stitches = []
        if obj.stitch_type == "ripple":
            from .ripple_fill import ripple_paths
            for path in ripple_paths(obj):
                stitches.append(Stitch(*path[0],"jump"))
                for a,b in zip(path,path[1:]):
                    stitches += segment(a,b,obj.stitch_length)
                    if len(stitches)>MAX_STITCHES:
                        raise ValueError("Ripple fill exceeds the preview command limit.")
        elif obj.stitch_type == "contour":
            stitches += contour_fill(rings,obj.spacing,obj.stitch_length)
        else:
            stitches += tatami(obj, rings)
    runs = [GeneratedRun(underlay, "underlay")] if underlay else []
    if stitches:
        runs.append(GeneratedRun(stitches, "top"))
    return GeneratedObject(obj.id, runs)


def generate(project):
    blocks = []
    total = 0
    for obj in project.objects:
        if not obj.visible:
            continue
        rings = obj.rings()
        stitches = generate_object(obj).stitches()
        if obj.kind != "stitches":
            segment_allowed=None
            if obj.stitch_type in {'ripple','contour','pattern'} and obj.minimum_stitch:
                from .pattern_fill import RegionClip
                cleanup_region=RegionClip(rings)
                def segment_allowed(a,b):
                    return sum(math.dist(start,end) for start,end in cleanup_region.segment(a,b))>=math.dist(a,b)-1e-8
            stitches = short_stitch_cleanup(stitches,obj.minimum_stitch,obj.satin_max if obj.stitch_type == "satin" else obj.stitch_length,
                                            segment_allowed=segment_allowed)
            stitches = finish_stitches(stitches, obj.tie_in, obj.tie_off, obj.trim_after, obj.jump_trim)
            if obj.stop_after and stitches:
                stitches.append(Stitch(stitches[-1].x, stitches[-1].y, "stop"))
        total += len(stitches)
        if total > MAX_STITCHES:
            raise ValueError("Design exceeds the 250,000-command preview limit.")
        blocks.append(Block(obj.id, obj.color, stitches, obj.color_break, dict(obj.thread)))
    return blocks


def preflight(project, blocks):
    """Messages for problems that must block export (see design_check for the full review)."""
    from .design_check import check_hoop
    return [issue.message for issue in check_hoop(project, blocks) if issue.severity == "error"]
