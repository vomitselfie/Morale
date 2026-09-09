"""Closed-outline operations in world millimeters, persisted as editable contours."""
from copy import deepcopy
import math
import uuid

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainterPath

from .model import Project


def replace_contours(source, rings):
    """Rebase edited world coordinates without applying the old transform twice."""
    if source.kind != "compound":
        raise ValueError("Select a compound shape to edit its contours.")
    if not isinstance(rings, (list, tuple)) or not 1 <= len(rings) <= 256:
        raise ValueError("Keep between 1 and 256 contours.")
    if any(not isinstance(ring, (list, tuple)) or len(ring) < 3 for ring in rings):
        raise ValueError("Each contour needs at least three points.")
    if sum(len(ring) for ring in rings) > 20_000:
        raise ValueError("Compound shape exceeds 20,000 points.")
    for ring in rings:
        for point in ring:
            if not isinstance(point, (list, tuple)) or len(point) != 2 or any(
                isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or abs(v) > 1000
                for v in point
            ):
                raise ValueError("Points must be finite X/Y coordinates within ±1,000 mm.")
    candidate = deepcopy(source)
    if [[tuple(p) for p in ring] for ring in rings] == source.rings():
        return candidate
    xs, ys = zip(*(point for ring in rings for point in ring))
    candidate.x, candidate.y = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    candidate.width, candidate.height = max(.1, max(xs) - min(xs)), max(.1, max(ys) - min(ys))
    candidate.rotation = 0
    candidate.motif_reflected ^= candidate.flip_x ^ candidate.flip_y
    candidate.flip_x = candidate.flip_y = False
    candidate.contours = [[[(x - candidate.x) / candidate.width, (y - candidate.y) / candidate.height]
                           for x, y in ring] for ring in rings]
    candidate.lettering = {}
    return Project.loads(Project(objects=[candidate]).dumps()).objects[0]


def combine_outlines(objects, operation):
    """The caller supplies sewing order; the first object supplies settings."""
    if operation not in {"union", "subtract", "intersection"}:
        raise ValueError("Unknown outline operation.")
    if len(objects) < 2:
        raise ValueError("Select at least two closed shapes.")
    if any(obj.kind not in {"ellipse", "rectangle", "leaf", "polygon", "compound"} for obj in objects):
        raise ValueError("Outline operations require closed vector shapes, not paths, satin rails, or manual stitches.")
    if any(not obj.visible for obj in objects):
        raise ValueError("Show all selected shapes before combining their outlines.")
    # Validate before passing coordinates into Qt's geometric routines.
    Project.loads(Project(objects=objects).dumps())
    paths = []
    for obj in objects:
        path = QPainterPath()
        path.setFillRule(Qt.FillRule.OddEvenFill)
        for ring in obj.rings():
            path.moveTo(*ring[0])
            for point in ring[1:]:
                path.lineTo(*point)
            path.closeSubpath()
        paths.append(path)
    result = paths[0]
    for path in paths[1:]:
        if operation == "union":
            result = result.united(path)
        elif operation == "subtract":
            result = result.subtracted(path)
        else:
            result = result.intersected(path)
    # Simplification normalizes intersecting edges into odd-even contours.
    result = result.simplified()
    bounds = result.boundingRect()
    if result.isEmpty() or bounds.width() < .1 or bounds.height() < .1:
        raise ValueError("The operation leaves no usable area. Original shapes were kept.")
    contours = []
    for polygon in result.toSubpathPolygons():
        ring = [[(p.x() - bounds.center().x()) / bounds.width(),
                 (p.y() - bounds.center().y()) / bounds.height()] for p in polygon]
        if len(ring) > 1 and ring[0] == ring[-1]:
            ring.pop()
        if len(ring) >= 3:
            contours.append(ring)
    candidate = deepcopy(objects[0])
    candidate.id = uuid.uuid4().hex
    candidate.name = f"{operation.title()} · {candidate.name}"[:200]
    candidate.kind = "compound"
    candidate.x, candidate.y = bounds.center().x(), bounds.center().y()
    candidate.width, candidate.height = bounds.width(), bounds.height()
    candidate.rotation = 0
    candidate.motif_reflected ^= candidate.flip_x ^ candidate.flip_y
    candidate.flip_x = candidate.flip_y = False
    candidate.points = []
    candidate.handles = []
    candidate.stitch_data = []
    candidate.lettering = {}
    candidate.contours = contours
    # Keep membership only when all sources belong to the same flat group.
    candidate.group_id = objects[0].group_id if len({o.group_id for o in objects}) == 1 else ""
    return Project.loads(Project(objects=[candidate]).dumps()).objects[0]
