"""Blanket (E-stitch), meander and cross-stitch paths.

Algorithms after ZigZag's patterns (Apache-2.0; see THIRD_PARTY_NOTICES.md):
blanket prongs point into the shape along its outline; meander is one random
but repeatable walk through grid cells, with backtracking so it stays a single
line; cross-stitch sews rows of half-crosses out and back on a grid shared by
every object, so neighbouring shapes line up. Unlike ZigZag, each pass
alternates diagonals, so cells are not joined by stitches along their edges.
"""
import math
import random

MAX_CELLS = 400_000


def _ring_samples(ring, spacing, closed):
    """Points every ``spacing`` along a ring or line, each with the unit
    direction there and the outline vertices passed on the way to it."""
    route = list(ring) + [ring[0]] if closed else list(ring)
    edges = [(a, b) for a, b in zip(route, route[1:]) if math.dist(a, b) > 1e-9]
    total = sum(math.dist(a, b) for a, b in edges)
    if total <= 1e-9:
        return []
    count = max(1, round(total / spacing))
    step = total / count
    samples, along, target, index = [], 0., 0., 0
    passed = []
    while index < len(edges):
        a, b = edges[index]
        length = math.dist(a, b)
        if target <= along + length + 1e-9:
            t = (target - along) / length
            direction = ((b[0]-a[0]) / length, (b[1]-a[1]) / length)
            samples.append(((a[0] + (b[0]-a[0])*t, a[1] + (b[1]-a[1])*t), direction, passed))
            passed = []
            target += step
            if len(samples) > count:
                break
        else:
            along += length
            passed.append(b)
            index += 1
    return samples


def blanket_paths(rings, spacing, width, closed, inside):
    """E-stitch: along each outline, a prong ``width`` long every ``spacing``,
    pointing into the shape (left of the line for open paths)."""
    paths = []
    for ring in rings:
        samples = _ring_samples(ring, spacing, closed)
        if len(samples) < 2:
            continue
        side = 1
        if closed:
            point, (dx, dy), _ = samples[len(samples) // 2]
            probe = (point[0] - dy * min(width, .5), point[1] + dx * min(width, .5))
            side = 1 if inside(probe) else -1
        path = []
        for k, (point, (dx, dy), passed) in enumerate(samples):
            path.extend(passed)
            path.append(point)
            if closed and k == len(samples) - 1:
                break
            path.append((point[0] - dy * width * side, point[1] + dx * width * side))
            path.append(point)
        paths.append(path)
    return paths


def meander_paths(rings, spacing, region, inside_segment, seed=1):
    """One wandering line through every ``spacing``-sized cell inside the shape
    (one per separate part), with rounded corners, clipped to the outline."""
    xs = [x for ring in rings for x, _ in ring]
    ys = [y for ring in rings for _, y in ring]
    columns = math.ceil((max(xs) - min(xs)) / spacing) + 1
    rows = math.ceil((max(ys) - min(ys)) / spacing) + 1
    if columns * rows > MAX_CELLS:
        raise ValueError("Meander spacing is too small for this shape. Increase the meander spacing.")
    def at(cell):
        return (min(xs) + (cell % columns) * spacing, min(ys) + (cell // columns) * spacing)
    inside = [region.inside(at(cell)) for cell in range(columns * rows)]
    visited = [False] * len(inside)
    rng = random.Random(seed)
    paths = []
    for start in range(len(inside)):
        if not inside[start] or visited[start]:
            continue
        walk, stack = [start], [start]
        visited[start] = True
        while stack:
            here = stack[-1]
            column, row = here % columns, here // columns
            options = [here - 1] * (column > 0) + [here + 1] * (column + 1 < columns) + [here - columns] * (row > 0) + [here + columns] * (row + 1 < rows)
            rng.shuffle(options)
            step = next((n for n in options if inside[n] and not visited[n] and inside_segment(at(here), at(n))), None)
            if step is None:
                stack.pop()
                if stack:
                    walk.append(stack[-1])
            else:
                visited[step] = True
                stack.append(step)
                walk.append(step)
        if len(walk) < 2:
            continue
        points = [at(cell) for cell in walk]
        smooth = [points[0]]
        for a, b in zip(points, points[1:]):
            smooth += [(a[0] + (b[0]-a[0])*.3, a[1] + (b[1]-a[1])*.3), (a[0] + (b[0]-a[0])*.7, a[1] + (b[1]-a[1])*.7)]
        smooth.append(points[-1])
        paths.extend(clip_path(smooth, region))
    return paths


def clip_path(points, region):
    """``points`` split wherever the line leaves the region."""
    paths, current = [], []
    for a, b in zip(points, points[1:]):
        for start, end in region.segment(a, b):
            if current and math.dist(current[-1], start) < 1e-6:
                current.append(end)
            else:
                if len(current) > 1:
                    paths.append(current)
                current = [start, end]
    if len(current) > 1:
        paths.append(current)
    return paths


def cross_paths(rings, cell, inside):
    """An X in every grid cell whose center is inside, sewn as rows of
    half-crosses out and back. The grid is anchored at the hoop center."""
    xs = [x for ring in rings for x, _ in ring]
    ys = [y for ring in rings for _, y in ring]
    c0, c1 = math.floor(min(xs) / cell), math.ceil(max(xs) / cell)
    r0, r1 = math.floor(min(ys) / cell), math.ceil(max(ys) / cell)
    if (c1 - c0) * (r1 - r0) > MAX_CELLS:
        raise ValueError("Cross-stitch cells are too small for this shape. Increase the cell size.")
    paths = []
    for row in range(r0, r1):
        y0, y1 = row * cell, (row + 1) * cell
        cells = [c for c in range(c0, c1) if inside(((c + .5) * cell, (row + .5) * cell))]
        i = 0
        while i < len(cells):
            j = i
            while j + 1 < len(cells) and cells[j + 1] == cells[j] + 1:
                j += 1
            # Out: alternate / and \ so each diagonal starts where the last
            # ended; back: the other diagonal of each cell. Only the turn at
            # the row's end runs along a cell edge.
            path = [(cells[i] * cell, y1)]
            for c in range(cells[i], cells[j] + 1):
                path.append(((c + 1) * cell, y0 if path[-1][1] == y1 else y1))
            path.append(((cells[j] + 1) * cell, y1 if path[-1][1] == y0 else y0))
            for c in range(cells[j], cells[i] - 1, -1):
                path.append((c * cell, y0 if path[-1][1] == y1 else y1))
            paths.append(path)
            i = j + 1
    return paths


def decorative_paths(obj):
    """(paths, longest stitch) for a blanket, meander or cross-stitch object."""
    from .engine import segment_inside
    from .pattern_fill import RegionClip
    rings = obj.rings()
    if obj.stitch_type == "blanket":
        closed = obj.kind != "path"
        region = RegionClip(rings) if closed else None
        paths = blanket_paths(rings, obj.blanket_spacing, obj.blanket_width, closed, region.inside if region else None)
        return paths, max(obj.blanket_spacing, obj.blanket_width) * 1.5
    if obj.kind in {"path", "satin", "stitches"}:
        raise ValueError("Meander and cross-stitch need a closed outline.")
    region = RegionClip(rings)
    if obj.stitch_type == "meander":
        return meander_paths(rings, obj.meander_spacing, region,
                             lambda a, b: segment_inside(a, b, rings[0], rings[1:])), obj.stitch_length
    return cross_paths(rings, obj.cross_cell, region.inside), obj.cross_cell * 1.5
