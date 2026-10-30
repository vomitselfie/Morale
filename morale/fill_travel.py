"""Travel stitches that stay inside a fill instead of jumping across it.

Adapted from ZigZag's fill routing (Apache-2.0; see THIRD_PARTY_NOTICES.md):
travel goes straight where a straight line stays inside the shape, otherwise
the shorter way round a ring just inside the outline, and stays a jump only
when neither works. Morale applies it to the jumps a fill leaves between its
sections and to a fill's chosen entry and exit points.
"""
import math

from .engine import Stitch, segment, segment_inside

TRAVEL_INSET = .5
# Longest travel walk, mm, before a jump (and the trim rules) is used instead.
# Provisional: walks sew under or beside later rows and have not been sew-tested.
TRAVEL_LIMIT = 50.


def _length(ring):
    return sum(math.dist(a, b) for a, b in zip(ring, ring[1:] + ring[:1]))


def _nearest_along(ring, point):
    """(distance to ``ring``, distance along it) of the ring point nearest ``point``."""
    best, along_best, along = math.inf, 0., 0.
    for a, b in zip(ring, ring[1:] + ring[:1]):
        length = math.dist(a, b)
        t = 0 if length == 0 else max(0, min(1, ((point[0]-a[0])*(b[0]-a[0]) + (point[1]-a[1])*(b[1]-a[1])) / length**2))
        distance = math.dist(point, (a[0] + (b[0]-a[0])*t, a[1] + (b[1]-a[1])*t))
        if distance < best:
            best, along_best = distance, along + t*length
        along += length
    return best, along_best


def _walk(ring, start, end, forward):
    """Ring positions from distance ``start`` to ``end`` along it, either way round."""
    total = _length(ring)
    def at(s):
        s %= total
        for a, b in zip(ring, ring[1:] + ring[:1]):
            length = math.dist(a, b)
            if s <= length:
                return a if length == 0 else (a[0] + (b[0]-a[0])*s/length, a[1] + (b[1]-a[1])*s/length)
            s -= length
        return ring[0]
    span = (end - start) % total if forward else (start - end) % total
    vertices, along = [], 0.
    for a, b in zip(ring, ring[1:] + ring[:1]):
        along += math.dist(a, b)
        offset = (along - start) % total if forward else (start - along) % total
        if 1e-9 < offset < span - 1e-9:
            vertices.append((offset, b))
    return [at(start)] + [p for _, p in sorted(vertices)] + [at(end)]


class FillTravel:
    """Inside travel for one fill outline (outer ring then holes, even-odd)."""

    def __init__(self, rings, limit=TRAVEL_LIMIT):
        from .underlay import inset_rings
        self.rings = rings
        self.limit = limit
        try:
            self.inset = [ring for ring in inset_rings(rings, TRAVEL_INSET) if len(ring) >= 3]
        except ValueError:
            self.inset = []

    def path(self, a, b):
        """Positions from ``a`` to ``b`` inside the fill, excluding a and
        including b, or None when travel must jump."""
        if segment_inside(a, b, self.rings[0], self.rings[1:]):
            return [b]
        if not self.inset:
            return None
        def nearest(point):
            return min((_nearest_along(ring, point) + (index,) for index, ring in enumerate(self.inset)))
        _, start, ring_a = nearest(a)
        _, end, ring_b = nearest(b)
        if ring_a != ring_b:
            return None
        ring = self.inset[ring_a]
        total = _length(ring)
        forward = (end - start) % total <= total / 2
        route = _walk(ring, start, end, forward) + [b]
        if sum(math.dist(p, q) for p, q in zip([a] + route, route)) > self.limit:
            return None
        return route

    def stitches(self, a, b, length):
        """Travel stitches from ``a`` to ``b`` no longer than ``length``, or None."""
        route = self.path(a, b)
        if route is None:
            return None
        result, previous = [], a
        for point in route:
            if math.dist(previous, point) > 1e-6:
                result.extend(segment(previous, point, length))
            previous = point
        return result


def travel_inside(stitches, travel, length):
    """Replace jumps longer than ``length`` between sewn stitches with inside travel."""
    result, sewn = [], False
    for stitch in stitches:
        if stitch.command == "jump" and sewn and result:
            previous = (result[-1].x, result[-1].y)
            target = (stitch.x, stitch.y)
            if math.dist(previous, target) > length:
                route = travel.stitches(previous, target, length)
                if route is not None:
                    result.extend(route)
                    continue
        sewn = sewn or stitch.command == "stitch"
        result.append(stitch)
    return result


def reversed_stitches(stitches):
    """The same stitch/jump sequence sewn from its other end."""
    from .generated import GeneratedRun
    return GeneratedRun(stitches, "top", reversible=True).reversed().stitches


def choose_entry(candidates, start=None, end=None):
    """The candidate sequence whose ends best match the requested start and end."""
    def score(stitches):
        first, last = stitches[0], stitches[-1]
        return ((math.dist(start, (first.x, first.y)) if start else 0)
                + (math.dist(end, (last.x, last.y)) if end else 0))
    return min(candidates, key=score)


def enter_and_exit(stitches, travel, length, start=None, end=None):
    """Begin the fill at ``start`` and finish it at ``end`` by inside travel.

    Either end is left as generated when travel from it would have to jump.
    """
    if start and stitches:
        first = (stitches[0].x, stitches[0].y)
        route = travel.stitches(start, first, length) if math.dist(start, first) > 1e-6 else []
        if route is not None:
            stitches = [Stitch(*start, "jump")] + route + stitches[1:]
    if end and stitches:
        last = (stitches[-1].x, stitches[-1].y)
        route = travel.stitches(last, end, length) if math.dist(last, end) > 1e-6 else []
        if route is not None:
            stitches = stitches + route
    return stitches
