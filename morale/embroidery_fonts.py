"""Purpose-digitized embroidery fonts, converted from the Ink/Stitch font library.

Each font lives in ``morale/fonts/<id>/`` as gzipped ``font.json.gz`` (see
``scripts/import_inkstitch_fonts.py``) with its own LICENSE. Glyph pieces are
satin rails, fill outlines and running lines in millimetres, with the origin at
the left of the glyph on the baseline and y pointing down.
"""
from copy import deepcopy
from functools import lru_cache
import gzip
import json
import math
from pathlib import Path

from .model import DesignObject, Project

FONT_DIR = Path(__file__).parent / "fonts"


@lru_cache(maxsize=None)
def available_fonts():
    """(id, name, license, letter_case) for every shipped font, sorted by name."""
    fonts = []
    if FONT_DIR.is_dir():
        for path in sorted(FONT_DIR.glob("*/font.json.gz")):
            try:
                header = load_font(path.parent.name)
            except (OSError, ValueError):
                continue
            low, high = height_range(header)
            if low <= high:  # Fonts only usable beyond the 1–100 mm limit are left out.
                fonts.append((header["id"], header["name"], header["license"], header.get("letter_case", "")))
    return tuple(sorted(fonts, key=lambda font: font[1].lower()))


@lru_cache(maxsize=8)
def load_font(font_id):
    if not isinstance(font_id, str) or not font_id or "/" in font_id or "\\" in font_id or font_id.startswith("."):
        raise ValueError("Unknown embroidery font.")
    path = FONT_DIR / font_id / "font.json.gz"
    if not path.is_file():
        raise ValueError("This embroidery font is not installed.")
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        font = json.load(stream)
    if font.get("format") != "morale-embroidery-font" or font.get("version") != 1:
        raise ValueError("Unsupported embroidery font file.")
    return font


def reference_height(font):
    """The height the font was digitized for, measured like the height control."""
    return font.get("cap_height_mm") or font.get("size_mm") or 20.


def height_range(font):
    """Letter heights the font sews well at, within Morale's 1–100 mm lettering limit."""
    reference = reference_height(font)
    low, high = reference * font.get("min_scale", 1), reference * font.get("max_scale", 1)
    return max(1., low), min(100., high)


def _glyph(font, char):
    glyphs = font["glyphs"]
    if char in glyphs:
        return glyphs[char]
    # Capitals-only and lowercase-only fonts accept either case.
    for variant in (char.upper(), char.lower()):
        if variant in glyphs:
            return glyphs[variant]
    return None


def make_font_lettering(text, font_id, height, spacing=100., previous=None):
    """A lettering object that sews the font's digitized pieces as designed."""
    if not isinstance(text, str) or not text.strip() or len(text) > 80 or any(c in text for c in "\n\r\t"):
        raise ValueError("Enter a single line of 1–80 visible characters.")
    if not math.isfinite(spacing) or not 50 <= spacing <= 200:
        raise ValueError("Use character spacing from 50% to 200%.")
    font = load_font(font_id)
    low, high = height_range(font)
    if not math.isfinite(height) or not low - 1e-6 <= height <= high + 1e-6:
        raise ValueError(f"{font['name']} is digitized for letters from {low:.0f} to {high:.0f} mm high. "
                         "Other sizes would sew too densely or too loosely.")
    missing = [c for c in dict.fromkeys(text) if not c.isspace() and _glyph(font, c) is None]
    if missing:
        raise ValueError(f"{font['name']} has no stitches for: {' '.join(missing)}. Choose another font or remove them.")
    scale = height / reference_height(font)
    pieces, outlines, points, cursor, previous_char = [], [], [], 0., None
    for char in text:
        if char.isspace():
            cursor += font["space_mm"] * scale * spacing / 100
            previous_char = None
            continue
        glyph = _glyph(font, char)
        if previous_char is not None:
            cursor -= font["kerning"].get(f"{previous_char} {char}", 0.) * scale
        for piece in glyph["pieces"]:
            kind, value = next(iter(piece.items()))
            place = lambda points: [(cursor + x * scale, y * scale) for x, y in points]
            placed = [place(ring) for ring in value] if kind == "fill" else place(value)
            pieces.append({kind: placed})
            points += [p for ring in placed for p in ring] if kind == "fill" else placed
            if kind == "fill":
                outlines += placed
            elif kind == "rails":
                outlines.append(placed[::2] + placed[1::2][::-1])
        cursor += glyph["advance"] * scale * spacing / 100
        previous_char = char
    xs, ys = [x for x, _ in points], [y for _, y in points]
    width, total_height = max(xs) - min(xs), max(ys) - min(ys)
    if width > 500 or total_height > 500:
        raise ValueError("Lettering exceeds 500 mm. Reduce height or text length.")
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    width, total_height = max(.1, width), max(.1, total_height)

    def normalize(path):
        return [[(x - cx) / width, (y - cy) / total_height] for x, y in path]
    # Outlines are for display and selection; very long text falls back to its
    # bounding box to stay within project contour limits.
    rings = [normalize(ring) for ring in outlines if len(ring) >= 3]
    # Running-stitch fonts have no outlines; their bounding box stands in on screen.
    if not rings or len(rings) > 256 or sum(map(len, rings)) > 20_000:
        rings = [normalize([(min(xs), min(ys)), (max(xs), min(ys)), (max(xs), max(ys)), (min(xs), max(ys))])]
    obj = deepcopy(previous) if previous else DesignObject(underlay=True)
    obj.name = text[:200]
    obj.kind = "compound"
    obj.stitch_type = "satin"
    obj.width, obj.height = width, total_height
    obj.points, obj.handles, obj.stitch_data = [], [], []
    obj.contours = rings
    obj.lettering = {"text": text, "family": font["name"], "height": height, "spacing": spacing, "layout": "straight",
                     "curve": 60, "layout_height": total_height, "embroidery_font": font_id,
                     "columns": [{kind: [normalize(r) for r in value] if kind == "fill" else normalize(value)}
                                 for piece in pieces for kind, value in piece.items()]}
    from .engine import generate
    Project.loads(Project(objects=[obj]).dumps())
    generate(Project(objects=[obj]))
    return obj
