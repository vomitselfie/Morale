"""Cubic curves with bounded adaptive subdivision in world millimeters."""
from copy import deepcopy
import math


def move_control(controls, index, target, mode="free"):
    """Move a world-space control, optionally coupling the opposite handle."""
    if mode not in {"free", "smooth", "symmetric"}:
        raise ValueError("Unknown Bezier handle drag mode.")
    result = list(controls)
    target = tuple(target)
    if index % 3 == 1:
        old = controls[index]
        for neighbor in (index-1, index+1):
            result[neighbor] = tuple(h + t - a for h, t, a in zip(controls[neighbor], target, old))
    elif mode != "free":
        anchor_index = index - index % 3 + 1
        opposite = anchor_index + (1 if index % 3 == 0 else -1)
        anchor = controls[anchor_index]
        distance = math.dist(anchor, target)
        if mode == "symmetric":
            result[opposite] = tuple(2*a-t for a, t in zip(anchor, target))
        elif distance > 1e-12:
            length = math.dist(anchor, controls[opposite])
            result[opposite] = tuple(a - (t-a)*length/distance for a, t in zip(anchor, target))
        # A collapsed smooth handle has no direction: retain its opposite.
    result[index] = target
    return result


def flatten_cubics(controls, closed, tolerance=.03):
    result = [controls[1]]
    def midpoint(a, b):
        return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    def segment(a, b, c, d, depth=0):
        # Control polygon excess also catches collinear reversals and loops.
        length = math.dist(a, b) + math.dist(b, c) + math.dist(c, d)
        chord = math.dist(a, d)
        dx, dy = d[0] - a[0], d[1] - a[1]
        deviation = max(abs(dx * (p[1] - a[1]) - dy * (p[0] - a[0])) / chord for p in (b, c)) if chord else length
        if deviation <= tolerance and length - chord <= tolerance or depth >= 16:
            result.append(d)
            if len(result) > 30_000:
                raise ValueError("Curve exceeds the 30,000-point geometry limit.")
            return
        ab, bc, cd = midpoint(a, b), midpoint(b, c), midpoint(c, d)
        abc, bcd = midpoint(ab, bc), midpoint(bc, cd)
        middle = midpoint(abc, bcd)
        segment(a, ab, abc, middle, depth + 1)
        segment(middle, bcd, cd, d, depth + 1)
    count = len(controls) // 3
    for i in range(count if closed else count - 1):
        j = (i + 1) % count
        segment(controls[3*i + 1], controls[3*i + 2], controls[3*j], controls[3*j + 1])
    if closed and result[-1] == result[0]:
        result.pop()
    return result


def edit_controls(source, controls):
    from .model import Project
    if source.kind not in {"path", "polygon"}:
        raise ValueError("Bezier handles require an open path or closed polygon.")
    minimum = 6 if source.kind == "path" else 9
    if not minimum <= len(controls) <= 6000 or len(controls) % 3:
        raise ValueError("Bezier rows must form complete incoming / anchor / outgoing triples.")
    if any(len(p) != 2 or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or abs(v) > 1000 for v in p) for p in controls):
        raise ValueError("Bezier coordinates must be finite and within ±1,000 mm.")
    candidate = deepcopy(source)
    if source.handles and controls == source.control_points():
        return candidate
    xs, ys = zip(*controls)
    candidate.x, candidate.y = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    candidate.width, candidate.height = max(.1, max(xs) - min(xs)), max(.1, max(ys) - min(ys))
    normalized = [[max(-.5, min(.5, (x - candidate.x) / candidate.width)),
                   max(-.5, min(.5, (y - candidate.y) / candidate.height))] for x, y in controls]
    candidate.points = normalized[1::3]
    candidate.handles = [[normalized[i], normalized[i+2]] for i in range(0, len(normalized), 3)]
    candidate.rotation = 0
    candidate.motif_reflected ^= candidate.flip_x ^ candidate.flip_y
    candidate.flip_x = candidate.flip_y = False
    return Project.loads(Project(objects=[candidate]).dumps()).objects[0]


def enable_handles(source):
    if source.handles:
        return deepcopy(source)
    if source.kind not in {"path", "polygon"}:
        raise ValueError("Select a polygon or running path first.")
    points = source.transform(source.points)
    controls = []
    for i, anchor in enumerate(points):
        previous = points[i-1] if i or source.kind == "polygon" else anchor
        following = points[(i+1) % len(points)] if i+1 < len(points) or source.kind == "polygon" else anchor
        controls.extend([tuple(a + (b-a) / 3 for a, b in zip(anchor, previous)), anchor,
                         tuple(a + (b-a) / 3 for a, b in zip(anchor, following))])
    return edit_controls(source, controls)
