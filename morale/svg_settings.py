"""Stitch settings written into SVG layer and object names.

Naming a layer or object ``logo fill a=45 s=0.35`` in Illustrator, Inkscape or
Affinity sets how it is stitched when Morale imports the SVG. Settings on a
group apply to everything inside it; inner names override outer ones. Tokens
prefixed ``stroke.`` apply only to an object's outline. The vocabulary follows
ZigZag's layer-name tokens (Apache-2.0); Morale supports the subset below.

    fill | tatami, satin, run | running, contour, ripple, blanket, meander,
    cross, skip   stitch type
    a=DEG  fill angle          s=MM   row spacing       l=MM  stitch length
    pc=MM  pull compensation   u=0|1  underlay          w=MM  satin width of a stroke
    ul=center|zigzag|center+zigzag|edge|sparse|edge+sparse|none   underlay passes
    r=3    triple (bean) running stitch                  t=RRGGBB  thread color
    st=T, en=T  where a fill starts and ends, 0–1 along its outline
    style=satin|s|zigzag  satin top stitches      cell=MM  cross-stitch size
    trim, stop  trim or operator stop after the object
"""
import math
import re

SHAPES = {"path", "rect", "circle", "ellipse", "line", "polyline", "polygon"}
ATTRIBUTE = "data-morale-settings"
NAME_ATTRIBUTE = "data-morale-name"
INKSCAPE_LABEL = "{http://www.inkscape.org/namespaces/inkscape}label"
TYPES = {"fill": "fill", "tatami": "fill", "satin": "satin", "run": "running", "running": "running",
         "contour": "contour", "ripple": "ripple", "skip": "skip", "off": "skip", "nostitch": "skip",
         "blanket": "blanket", "estitch": "blanket", "meander": "meander",
         "cross": "cross", "crossstitch": "cross", "cross-stitch": "cross"}
NUMBERS = {  # token: (setting, low, high)
    "a": ("angle", -360, 360), "angle": ("angle", -360, 360),
    "s": ("spacing", .2, 5), "spacing": ("spacing", .2, 5), "d": ("spacing", .2, 5), "density": ("spacing", .2, 5),
    "l": ("stitch_length", .5, 6), "len": ("stitch_length", .5, 6), "length": ("stitch_length", .5, 6),
    "pc": ("pull_compensation", 0, 2), "pull": ("pull_compensation", 0, 2),
    "w": ("width", .4, 12), "width": ("width", .4, 12),
    "r": ("repeats", 1, 9), "repeats": ("repeats", 1, 9),
    "cell": ("cross_cell", 1, 10),
    "st": ("start", 0, 1), "start": ("start", 0, 1), "en": ("end", 0, 1), "end": ("end", 0, 1),
}
FLAGS = {"1": True, "on": True, "yes": True, "true": True, "0": False, "off": False, "no": False, "false": False}
UNDERLAY = {"center": "auto", "zigzag": "zigzag", "center+zigzag": "center_zigzag", "zigzag+center": "center_zigzag",
            "edge": "edge", "sparse": "sparse", "edge+sparse": "edge_sparse", "sparse+edge": "edge_sparse"}


def decode(name):
    """Undo Illustrator's id escapes, such as ``_x3D_`` for '='."""
    return re.sub(r"_x([0-9A-Fa-f]{2,4})_", lambda m: chr(int(m.group(1), 16)), name)


def element_name(node):
    return node.get(INKSCAPE_LABEL) or node.get("data-name") or node.get("id") or ""


def annotate(root):
    """Give every shape the names of its groups and itself, outermost first."""
    def visit(node, names):
        tag = node.tag.split("}")[-1]
        own = element_name(node)
        here = names + [own] if own else names
        if tag in SHAPES and here:
            node.set(ATTRIBUTE, " ".join(decode(name) for name in here))
            if own:
                node.set(NAME_ATTRIBUTE, decode(own))
        for child in node:
            visit(child, here)
    visit(root, [])


def parse(text):
    """(settings, outline settings, name words, notices) from annotated names.

    Later tokens override earlier ones, so inner names win. Unknown words form
    the object's name; malformed settings are reported, never guessed.
    """
    base, stroke, words, notices = {}, {}, [], []
    for raw in re.split(r"[\s_,;]+", text or ""):
        if not raw:
            continue
        token = raw.lower()
        target = base
        if token.startswith("stroke."):
            token, target = token[7:], stroke
        if token in TYPES:
            target["type"] = TYPES[token]
        elif token in {"trim", "stop"}:
            target[token] = True
        elif "=" in token:
            key, value = token.split("=", 1)
            if key in NUMBERS:
                setting, low, high = NUMBERS[key]
                try:
                    number = float(value)
                except ValueError:
                    number = math.nan
                if math.isfinite(number) and low <= number <= high:
                    target[setting] = number
                else:
                    notices.append(f"Ignored “{raw}” in an SVG name: use {low:g} to {high:g}.")
            elif key in {"u", "underlay"} and value in FLAGS:
                target["underlay"] = FLAGS[value]
            elif key == "ul" and (value in UNDERLAY or value == "none"):
                target["underlay_style"] = UNDERLAY.get(value)
            elif key in {"t", "thread"} and re.fullmatch(r"#?[0-9a-f]{6}", value):
                target["color"] = "#" + value.lstrip("#")
            elif key == "style" and value in {"satin", "plain", "s", "zigzag"}:
                target["satin_style"] = "plain" if value == "satin" else value
            elif key in {"trim", "stop"} and value in FLAGS:
                target[key] = FLAGS[value]
            else:
                notices.append(f"Ignored “{raw}” in an SVG name: Morale does not use this setting.")
        else:
            words.append(raw)
    return base, stroke, words, notices


def point_along(ring, fraction):
    """The point ``fraction`` (0–1) of the way round closed ``ring``."""
    edges = list(zip(ring, ring[1:] + ring[:1]))
    total = sum(math.dist(a, b) for a, b in edges)
    remaining = fraction % 1 * total
    for a, b in edges:
        length = math.dist(a, b)
        if remaining <= length and length:
            t = remaining / length
            return [a[0] + (b[0]-a[0])*t, a[1] + (b[1]-a[1])*t]
        remaining -= length
    return list(ring[0])


def apply(obj, settings, notices):
    """Set the numeric and finishing settings of ``obj`` from parsed ``settings``."""
    for key in ("angle", "spacing", "stitch_length", "pull_compensation", "color", "cross_cell"):
        if key in settings:
            setattr(obj, key, settings[key])
    if "underlay" in settings:
        obj.underlay = settings["underlay"]
    if "satin_style" in settings and obj.stitch_type == "satin":
        obj.satin_style = settings["satin_style"]
    if "underlay_style" in settings:
        style = settings["underlay_style"]
        satin = obj.stitch_type == "satin"
        if style is None:
            obj.underlay = False
        elif (style in {"auto", "zigzag", "center_zigzag"}) == satin:
            obj.underlay, obj.underlay_style = True, style
        else:
            notices.append(f"{obj.name}: that underlay suits {'fills' if satin else 'satin columns'}; kept the default.")
    if settings.get("repeats", 1) >= 3 and obj.stitch_type == "running":
        obj.stitch_type = "triple"
    if "trim" in settings:
        obj.trim_after = settings["trim"]
    if "stop" in settings:
        obj.stop_after = settings["stop"]
    if obj.stitch_type == "fill":
        outer = obj.contours[0] if obj.kind == "compound" else None
        if outer:
            if "start" in settings:
                obj.fill_start = point_along(outer, settings["start"])
            if "end" in settings:
                obj.fill_end = point_along(outer, settings["end"])
