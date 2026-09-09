"""Lossless mirroring and geometry-based alignment in design coordinates."""
from copy import deepcopy
import math


def bounds(obj):
    points = obj.transform([row[:2] for row in obj.stitch_data]) if obj.kind == "stitches" else [point for ring in obj.rings() for point in ring]
    if not points:
        raise ValueError("The object has no geometry to align.")
    xs, ys = zip(*points)
    return min(xs), min(ys), max(xs), max(ys)


def mirror(obj, axis):
    if axis not in {"horizontal", "vertical"}:
        raise ValueError("Choose horizontal or vertical mirroring.")
    result = deepcopy(obj)
    if axis == "horizontal":
        result.flip_x = not result.flip_x
        if result.stitch_type == "pattern":
            result.pattern_flip_x = not result.pattern_flip_x
    else:
        result.flip_y = not result.flip_y
        if result.stitch_type == "pattern":
            result.pattern_flip_y = not result.pattern_flip_y
        if result.density_gradient:
            result.gradient_reverse = not result.gradient_reverse
    # Reflect about the object's center in canvas coordinates, including rotation.
    result.rotation = -result.rotation
    result.angle = -result.angle
    return result


def align_to_hoop(obj, width, height, alignment):
    left, top, right, bottom = bounds(obj)
    dx = dy = 0
    if alignment == "left":
        dx = -width / 2 - left
    elif alignment == "right":
        dx = width / 2 - right
    elif alignment == "top":
        dy = -height / 2 - top
    elif alignment == "bottom":
        dy = height / 2 - bottom
    elif alignment == "horizontal center":
        dx = -(left + right) / 2
    elif alignment == "vertical center":
        dy = -(top + bottom) / 2
    elif alignment == "center":
        dx, dy = -(left + right) / 2, -(top + bottom) / 2
    else:
        raise ValueError("Unknown alignment.")
    result = deepcopy(obj)
    result.x += dx
    result.y += dy
    return result


def arrange_selection(objects, operation, value, width, height):
    if not objects:
        return []
    if len(objects) == 1 and operation in {"mirror", "align"}:
        return [mirror(objects[0], value) if operation == "mirror" else align_to_hoop(objects[0], width, height, value)]
    boxes = [bounds(obj) for obj in objects]
    left, top = min(box[0] for box in boxes), min(box[1] for box in boxes)
    right, bottom = max(box[2] for box in boxes), max(box[3] for box in boxes)
    cx, cy = (left + right) / 2, (top + bottom) / 2
    result = deepcopy(objects)
    if operation == "mirror":
        result = [mirror(obj, value) for obj in objects]
        for obj in result:
            if value == "horizontal":
                obj.x = 2 * cx - obj.x
            else:
                obj.y = 2 * cy - obj.y
    elif operation == "align":
        deltas = {"left": (-width / 2 - left, 0), "right": (width / 2 - right, 0),
                  "top": (0, -height / 2 - top), "bottom": (0, height / 2 - bottom),
                  "horizontal center": (-cx, 0), "vertical center": (0, -cy), "center": (-cx, -cy)}
        if value not in deltas:
            raise ValueError("Unknown alignment.")
        dx, dy = deltas[value]
        for obj in result:
            obj.x += dx
            obj.y += dy
    elif operation == "align_objects":
        for obj, box in zip(result, boxes):
            if value == "left": obj.x += left - box[0]
            elif value == "right": obj.x += right - box[2]
            elif value == "top": obj.y += top - box[1]
            elif value == "bottom": obj.y += bottom - box[3]
            elif value == "horizontal center": obj.x += cx - (box[0] + box[2]) / 2
            elif value == "vertical center": obj.y += cy - (box[1] + box[3]) / 2
            else: raise ValueError("Unknown alignment.")
    elif operation == "distribute":
        if len(objects) < 3:
            raise ValueError("Select at least three objects to distribute their centers.")
        if value not in {"horizontal", "vertical"}:
            raise ValueError("Choose horizontal or vertical distribution.")
        axis = 0 if value == "horizontal" else 1
        centers = [(box[axis] + box[axis + 2]) / 2 for box in boxes]
        order = sorted(range(len(objects)), key=lambda index: centers[index])
        lo, hi = centers[order[0]], centers[order[-1]]
        for rank, index in enumerate(order):
            delta = lo + (hi - lo) * rank / (len(order) - 1) - centers[index]
            if axis == 0: result[index].x += delta
            else: result[index].y += delta
    else:
        raise ValueError("Unknown arrangement operation.")
    return result


def transform_selection(objects, scale=1., rotation=0., origin="selection", scale_y=None):
    """Scale in canvas axes, then rotate about the requested common center."""
    if not objects:
        raise ValueError("Select at least one object to transform.")
    if not math.isfinite(scale) or not .05 <= scale <= 10 or not math.isfinite(rotation) or not -360 <= rotation <= 360:
        raise ValueError("Use a scale of 5–1000% and rotation between −360° and 360°.")
    scale_y = scale if scale_y is None else scale_y
    if not math.isfinite(scale_y) or not .05 <= scale_y <= 10:
        raise ValueError("Use a vertical scale of 5–1000%.")
    if origin not in {"selection", "hoop"}:
        raise ValueError("Choose selection center or sewing-field center.")
    rotation = (rotation + 180) % 360 - 180
    result = deepcopy(objects)
    if scale == scale_y == 1 and rotation == 0:
        return result
    boxes = [bounds(obj) for obj in objects]
    cx = (min(b[0] for b in boxes) + max(b[2] for b in boxes)) / 2 if origin == "selection" else 0.
    cy = (min(b[1] for b in boxes) + max(b[3] for b in boxes)) / 2 if origin == "selection" else 0.
    c, s = math.cos(math.radians(rotation)), math.sin(math.radians(rotation))
    if scale != scale_y:
        def affine(point):
            x, y = (point[0]-cx)*scale, (point[1]-cy)*scale_y
            return cx + x*c - y*s, cy + x*s + y*c
        return [_affine_object(obj, affine, scale, scale_y, rotation) for obj in objects]
    for obj in result:
        x, y = obj.x - cx, obj.y - cy
        obj.x, obj.y = cx + scale * (x * c - y * s), cy + scale * (x * s + y * c)
        obj.width *= scale
        obj.height *= scale
        obj.rotation = (obj.rotation + rotation + 180) % 360 - 180
        obj.angle = (obj.angle + rotation + 180) % 360 - 180
    return result


def _affine_object(source, affine, sx, sy, rotation):
    """Bake shear into editable points rather than approximating it with rotation."""
    from .model import Project
    result = deepcopy(source)
    if source.handles:
        rings = [source.control_points()]
    elif source.kind == "stitches":
        rings = [source.transform([row[:2] for row in source.stitch_data])]
    elif source.kind in {"path", "polygon", "satin"}:
        rings = [source.control_points()]
    else:
        rings = source.rings()
    rings = [[affine(p) for p in ring] for ring in rings]
    xs, ys = zip(*(p for ring in rings for p in ring))
    result.x, result.y = (min(xs)+max(xs))/2, (min(ys)+max(ys))/2
    result.width, result.height = max(.1,max(xs)-min(xs)), max(.1,max(ys)-min(ys))
    normalized = [[[max(-.5,min(.5,(x-result.x)/result.width)), max(-.5,min(.5,(y-result.y)/result.height))] for x,y in ring] for ring in rings]
    result.rotation = 0
    result.motif_reflected ^= result.flip_x ^ result.flip_y
    result.flip_x = result.flip_y = False
    result.lettering = {}
    angle = math.radians(source.angle)
    result.angle = (math.degrees(math.atan2(sy*math.sin(angle), sx*math.cos(angle)))+rotation+180)%360-180
    if source.handles:
        controls = normalized[0]
        result.points = controls[1::3]
        result.handles = [[controls[i],controls[i+2]] for i in range(0,len(controls),3)]
    elif source.kind == "stitches":
        result.stitch_data = [[*p,row[2]] for p,row in zip(normalized[0],source.stitch_data)]
    elif source.kind == "compound":
        result.contours = normalized
    else:
        result.points = normalized[0]
        if source.kind in {"ellipse", "rectangle", "leaf"}:
            result.kind = "polygon"
    return Project.loads(Project(objects=[result]).dumps()).objects[0]
