"""Plan thread colours across a whole design rather than one colour at a time.

Independent nearest matching can send two clearly different artwork colours to
the same thread, merging regions. ``plan_threads`` keeps them apart with a
minimum-cost assignment, and ``group_thread_runs`` reorders non-overlapping
regions so each thread is sewn in fewer runs.
"""
from copy import deepcopy
import math

from .auto_digitize import outline_path, area
from .perceptual_color import distance_squared as oklab_squared

# Oklab x100 distance below which two artwork colours may share one thread.
MERGE_DISTANCE = 2.0


def _assign(costs):
    """Minimum-cost assignment of every row to a distinct column (rows <= columns).

    Hungarian algorithm with potentials, O(rows² x columns).
    """
    rows, columns = len(costs), len(costs[0])
    u, v = [0.] * (rows + 1), [0.] * (columns + 1)
    owner, way = [0] * (columns + 1), [0] * (columns + 1)
    for row in range(1, rows + 1):
        owner[0] = row
        column = 0
        minimum = [math.inf] * (columns + 1)
        used = [False] * (columns + 1)
        while True:
            used[column] = True
            current, delta, following = owner[column], math.inf, 0
            for j in range(1, columns + 1):
                if used[j]:
                    continue
                reduced = costs[current - 1][j - 1] - u[current] - v[j]
                if reduced < minimum[j]:
                    minimum[j], way[j] = reduced, column
                if minimum[j] < delta:
                    delta, following = minimum[j], j
            for j in range(columns + 1):
                if used[j]:
                    u[owner[j]] += delta
                    v[j] -= delta
                else:
                    minimum[j] -= delta
            column = following
            if owner[column] == 0:
                break
        while column:
            previous = way[column]
            owner[column] = owner[previous]
            column = previous
    result = [None] * rows
    for j in range(1, columns + 1):
        if owner[j]:
            result[owner[j] - 1] = j - 1
    return result


def _weights(project):
    """Visible area per source colour; outlines and manual stitches count lightly."""
    weights = {}
    for obj in project.objects:
        if obj.kind != "stitches" and obj.stitch_type in {"fill", "satin"}:
            size = area(outline_path(obj.rings()))
        else:
            size = 1.
        weights[obj.color.lower()] = weights.get(obj.color.lower(), 0.) + size
    total = sum(weights.values()) or 1.
    # A floor keeps small details from being traded away entirely.
    return {color: .25 + value / total for color, value in weights.items()}


def plan_threads(project, entries, score):
    """Map each source colour to a thread, keeping distinct colours on distinct threads.

    Colours within MERGE_DISTANCE (Oklab) of each other form one group and share a
    thread. Groups receive distinct threads minimizing weighted total distance
    under ``score``. With no conflicts this equals independent nearest matching.
    Returns {source: (entry, info)}.
    """
    weights = _weights(project)
    sources = sorted(weights)
    groups = []
    for color in sources:
        joined = [group for group in groups if any(math.sqrt(oklab_squared(color, other)) <= MERGE_DISTANCE for other in group)]
        merged = [color] + [c for group in joined for c in group]
        groups = [group for group in groups if group not in joined] + [merged]
    groups = [sorted(group) for group in groups]
    distances = {}

    def distance(color, entry):
        key = (color, entry.color)
        if key not in distances:
            distances[key] = math.sqrt(score(color, entry.color))
        return distances[key]

    nearest = {color: min(entries, key=lambda entry: distance(color, entry)) for color in sources}
    plan = {}
    distinct_entries = {entry.color.lower(): entry for entry in entries}
    if len(groups) > len(distinct_entries):
        # Too few threads to keep every colour apart; fall back to nearest.
        for color in sources:
            plan[color] = (nearest[color], {"nearest_color": nearest[color].color.lower(), "adjusted": False,
                                            "shared_with": [], "reason": "Chart has fewer colours than the artwork."})
        return plan
    # Candidate columns: each group's closest threads, enough for any displacement.
    depth = len(groups) + 3
    candidates = {}
    for group in groups:
        ranked = sorted(distinct_entries.values(), key=lambda entry: sum(weights[c] * distance(c, entry) for c in group))
        for entry in ranked[:depth]:
            candidates[entry.color.lower()] = entry
    columns = list(candidates.values())
    costs = [[sum(weights[c] * distance(c, entry) for c in group) for entry in columns] for group in groups]
    chosen = _assign(costs)
    for group, column in zip(groups, chosen):
        entry = columns[column]
        for color in group:
            plan[color] = (entry, {"nearest_color": nearest[color].color.lower(),
                                   "adjusted": entry.color.lower() != nearest[color].color.lower(),
                                   "shared_with": [c for c in group if c != color], "reason": ""})
    return plan


def _thread_key(obj):
    return obj.color.lower(), tuple(sorted(obj.thread.items()))


def thread_changes(objects):
    keys = [_thread_key(obj) for obj in objects]
    return sum(a != b for a, b in zip(keys, keys[1:]))


def group_thread_runs(project):
    """Sew each thread in fewer runs without changing any overlapping pair's order.

    Objects with stops, colour breaks, appliqué stages, groups or manual stitches
    are barriers that stay in place; reordering happens between them.
    """
    from .engine import generate
    from .model import Project
    from .trace_routing import sewn_footprint
    Project.loads(project.dumps())
    blocks = {block.object_id: block for block in generate(project)}
    objects = project.objects
    bounds, footprints = {}, {}
    for i, obj in enumerate(objects):
        block = blocks.get(obj.id)
        points = [p for ring in obj.rings() for p in ring]
        if block:
            points += [(s.x, s.y) for s in block.stitches if s.command in {"stitch", "jump"}]
        xs, ys = zip(*points)
        bounds[i] = (min(xs), min(ys), max(xs), max(ys))

    def overlap(a, b):
        x, y, r, bottom = bounds[a]
        xx, yy, rr, bb = bounds[b]
        if r < xx - .001 or rr < x - .001 or bottom < yy - .001 or bb < y - .001:
            return False
        for i in (a, b):
            if i not in footprints:
                block = blocks.get(objects[i].id)
                footprints[i] = sewn_footprint(objects[i], block) if block else None
        # Complex or ungenerated objects are treated as overlapping (kept in order).
        return footprints[a] is None or footprints[b] is None or footprints[a].intersects(footprints[b])

    def barrier(i):
        obj = objects[i]
        return bool(obj.color_break or obj.stop_after or obj.stage_note or obj.group_id or obj.kind == "stitches")

    order, index, current = [], 0, None
    while index < len(objects):
        if barrier(index):
            order.append(index)
            current = _thread_key(objects[index])
            index += 1
            continue
        end = index
        while end < len(objects) and not barrier(end):
            end += 1
        remaining = list(range(index, end))
        predecessors = {i: {j for j in range(index, i) if overlap(i, j)} for i in remaining}
        placed = set()
        while remaining:
            available = [i for i in remaining if predecessors[i] <= placed]
            same = [i for i in available if _thread_key(objects[i]) == current]
            chosen = same[0] if same else available[0]
            order.append(chosen)
            placed.add(chosen)
            remaining.remove(chosen)
            current = _thread_key(objects[chosen])
        index = end
    before = thread_changes(objects)
    after = thread_changes([objects[i] for i in order])
    result = deepcopy(project)
    stats = {"before_changes": before, "after_changes": before, "moved_regions": 0, "order": list(range(len(objects)))}
    if after < before:
        result.objects = [deepcopy(objects[i]) for i in order]
        stats.update(after_changes=after, moved_regions=sum(i != j for i, j in enumerate(order)), order=order)
    Project.loads(result.dumps())
    return result, stats
