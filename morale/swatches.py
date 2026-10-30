"""Test swatches: copies of selected objects with one stitch setting stepped.

Sewing the same part at several values on the real fabric is the quickest way
to choose a setting. The swatches open as their own design, each labelled with
its value. Idea after ZigZag's Test Swatches (Apache-2.0).
"""
from copy import deepcopy
import math
import uuid

from .model import Project

# Setting: (label, low, high, stitch types it changes).
SETTINGS = {
    "spacing": ("Row spacing (mm)", .2, 5, {"fill", "contour", "ripple", "satin"}),
    "pull_compensation": ("Pull compensation (mm per side)", 0, 2, {"fill", "satin"}),
    "stitch_length": ("Stitch length (mm)", .5, 6, {"fill", "contour", "ripple", "running", "triple", "motif", "pattern"}),
    "angle": ("Fill angle (degrees)", -360, 360, {"fill", "pattern"}),
}
MAX_SWATCHES = 9
GAP = 8.  # mm between swatches
LABEL_HEIGHT = 5.  # mm, clamped to the label font's range
# Fonts digitized for small text first.
LABEL_FONTS = ["glacial_tiny", "small_font", "caffeine_tiny", "excalibur_small"]


def swatch_values(start, stop, count):
    if type(count) is not int or not 2 <= count <= MAX_SWATCHES:
        raise ValueError(f"Choose 2 to {MAX_SWATCHES} swatches.")
    return [round(start + (stop - start) * i / (count - 1), 3) for i in range(count)]


def _bounds(objects):
    from .engine import generate
    points = [(s.x, s.y) for block in generate(Project(objects=objects)) for s in block.stitches if s.command in {"stitch", "jump"}]
    if not points:
        raise ValueError("The selected parts have no stitches to test.")
    xs, ys = zip(*points)
    return min(xs), min(ys), max(xs), max(ys)


def _label(text, color, thread):
    from .embroidery_fonts import available_fonts, height_range, load_font, make_font_lettering
    fonts = [f[0] for f in available_fonts()]
    font_id = next((f for f in LABEL_FONTS if f in fonts), fonts[0] if fonts else None)
    if font_id is None:
        return None
    low, high = height_range(load_font(font_id))
    obj = make_font_lettering(text, font_id, min(max(LABEL_HEIGHT, low), high))
    obj.color, obj.thread = color, dict(thread)
    return obj


def build_swatches(project, ids, key, start, stop, count, labels=True):
    """A new design with ``count`` copies of the objects in ``ids``, ``key``
    stepped from ``start`` to ``stop``, laid out in a grid that fits the hoop."""
    if key not in SETTINGS:
        raise ValueError("Choose a setting to test.")
    title, low, high, types = SETTINGS[key]
    for value in (start, stop):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f"{title} must be between {low:g} and {high:g}.")
    values = swatch_values(start, stop, count)
    selected = [obj for obj in project.objects if obj.id in ids and obj.visible]
    if not selected:
        raise ValueError("Select the parts to test first.")
    if not any(obj.stitch_type in types for obj in selected):
        raise ValueError(f"None of the selected parts uses {title.split(' (')[0].lower()}.")
    left, top, right, bottom = _bounds(selected)
    width, height = right - left, bottom - top
    texts = [f"{value:g}" for value in values]
    made = [_label(text, selected[0].color, selected[0].thread) for text in texts] if labels else []
    made = made if made and all(made) else [None] * count
    label_w = max((label.width for label in made if label), default=0)
    label_space = max((label.height + 3 for label in made if label), default=0)
    columns = math.ceil(math.sqrt(count))
    rows = math.ceil(count / columns)
    cell_w, cell_h = max(width, label_w) + GAP, height + label_space + GAP
    total_w, total_h = columns * cell_w - GAP, rows * cell_h - GAP
    if total_w > project.hoop_width - 4 or total_h > project.hoop_height - 4:
        raise ValueError(f"{count} swatches need {total_w:.0f} × {total_h:.0f} mm, but the hoop is "
                         f"{project.hoop_width:g} × {project.hoop_height:g} mm. Choose fewer swatches or smaller parts.")
    result = Project(f"Test swatches: {title.split(' (')[0]}", project.hoop_width, project.hoop_height)
    notes = [f"{title}, left to right and top to bottom:"]
    for index, value in enumerate(values):
        row, column = divmod(index, columns)
        # Place the selection's bounds in its cell; cells are centered in the hoop.
        dx = -total_w / 2 + column * cell_w + (cell_w - GAP - width) / 2 - left
        dy = -total_h / 2 + row * cell_h - top
        group = uuid.uuid4().hex
        text = texts[index]
        for source in selected:
            obj = deepcopy(source)
            obj.id = uuid.uuid4().hex
            obj.group_id = group
            obj.x += dx
            obj.y += dy
            obj.name = f"{source.name} · {text}"
            if obj.stitch_type in types:
                setattr(obj, key, value)
            result.objects.append(obj)
        label = made[index]
        if label is not None:
            label.name = f"Label {text}"
            label.group_id = group
            label.x = -total_w / 2 + column * cell_w + (cell_w - GAP) / 2
            label.y = -total_h / 2 + row * cell_h + height + 3 + label.height / 2
            result.objects.append(label)
        notes.append(f"{index + 1}. {text}")
    result.notes = "\n".join(notes)
    return Project.loads(result.dumps())
