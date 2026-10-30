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
import unicodedata
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
            if low <= high:  # Keep the design size within project dimension limits.
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


def height_range(font,layout='straight'):
    """Metadata-derived design range, within Morale's 500 mm object limit."""
    reference = reference_height(font)
    low, high = reference * font.get("min_scale", 1), reference * font.get("max_scale", 1)
    return max(1., low)*(1.4 if layout=='monogram' else 1), min(500., high)


def _glyph_key(font, char):
    glyphs = font["glyphs"]
    if char in glyphs:
        return char
    # Capitals-only and lowercase-only fonts accept either case.
    for variant in (char.upper(), char.lower()):
        if variant in glyphs:
            return variant
    return None


def _glyph(font,char):
    key=_glyph_key(font,char)
    return font['glyphs'][key] if key is not None else None


def make_font_lettering(text, font_id, height, spacing=100., previous=None, *, layout='straight', curve=60., baseline=None):
    """A lettering object that sews the font's digitized pieces as designed."""
    if not isinstance(text, str) or not text.strip() or len(text) > 80 or any(c in text for c in "\n\r\t"):
        raise ValueError("Enter a single line of 1–80 visible characters.")
    text=unicodedata.normalize('NFC',text)
    if not math.isfinite(spacing) or not 50 <= spacing <= 200:
        raise ValueError("Use character spacing from 50% to 200%.")
    if layout not in {'straight','curved','path','monogram'} or not math.isfinite(curve) or not -180<=curve<=180:
        raise ValueError('Unsupported embroidery font layout or arc angle.')
    if layout=='monogram' and (len(text)!=3 or not text.isalpha()):
        raise ValueError('A monogram requires three letters in left-to-right order; the middle letter is enlarged.')
    if layout=='path':
        from .path_lettering import clean_baseline
        from PySide6.QtGui import QTransform
        if baseline is None:
            if previous is None or previous.lettering.get('layout')!='path':raise ValueError('Select a drawn path for the lettering baseline.')
            baseline=[[x*previous.width,y*previous.height] for x,y in previous.lettering['baseline']]
        elif previous is not None:
            baseline=clean_baseline(baseline)
            transform=QTransform().translate(previous.x,previous.y).rotate(previous.rotation).scale(-1 if previous.flip_x else 1,-1 if previous.flip_y else 1)
            inverse,_=transform.inverted();baseline=[list(inverse.map(*p)) for p in baseline]
        baseline=clean_baseline(baseline)
    font = load_font(font_id)
    low, high = height_range(font,layout)
    if low>high:
        raise ValueError('This font’s designed size range cannot accommodate a monogram with a 1.4× middle letter. Choose another font.')
    if not math.isfinite(height) or not low - 1e-6 <= height <= high + 1e-6:
        raise ValueError(f"{font['name']} has a designed height range of {low:.2f}–{high:.2f} mm. "
                         "Choose a height within that range.")
    missing = [c for c in dict.fromkeys(text) if not c.isspace() and _glyph(font, c) is None]
    if missing:
        raise ValueError(f"{font['name']} has no stitches for: {' '.join(missing)}. Choose another font or remove them.")
    scale = height / reference_height(font)
    pieces, outlines, points, cursor, previous_char = [], [], [], 0., None
    anchors=[]
    for index,char in enumerate(text):
        if char.isspace():
            cursor += font["space_mm"] * scale * spacing / 100
            previous_char = None
            continue
        glyph_key=_glyph_key(font,char)
        glyph = font['glyphs'][glyph_key]
        glyph_scale=scale/(1.4 if layout=='monogram' and index!=1 else 1)
        shift_x=shift_y=0.
        if layout=='monogram':
            glyph_points=[p for piece in glyph['pieces'] for kind,value in piece.items()
                          for ring in (value if kind=='fill' else [value]) for p in ring]
            shift_x=-min(x for x,y in glyph_points)*glyph_scale
            shift_y=-(min(y for x,y in glyph_points)+max(y for x,y in glyph_points))*glyph_scale/2
        if len(glyph['pieces'])>2000:
            raise ValueError(f"{font['name']} character '{char}' exceeds the 2,000-piece lettering limit. Choose another font or remove this character.")
        if len(pieces)+len(glyph['pieces'])>2000:
            raise ValueError('Lettering exceeds 2,000 planned pieces. Shorten the text or use separate lettering objects.')
        if previous_char is not None and layout!='monogram':
            cursor -= font["kerning"].get(f"{previous_char} {glyph_key}", 0.) * scale
        for piece in glyph["pieces"]:
            kind, value = next(iter(piece.items()))
            place = lambda points: [(cursor + shift_x + x * glyph_scale, shift_y + y * glyph_scale) for x, y in points]
            placed = [place(ring) for ring in value] if kind == "fill" else place(value)
            pieces.append({kind: placed})
            anchors.append(cursor+glyph['advance']*scale/2)
            points += [p for ring in placed for p in ring] if kind == "fill" else placed
            if kind == "fill":
                outlines += placed
            elif kind == "rails":
                outlines.append(placed[::2] + placed[1::2][::-1])
        if layout=='monogram':
            cursor+=(max(x for x,y in glyph_points)-min(x for x,y in glyph_points))*glyph_scale+height*.12*spacing/100
        else:cursor += glyph["advance"] * scale * spacing / 100
        previous_char = glyph_key
    if layout=='path' or (layout=='curved' and abs(curve)>.001):
        left=min(x for x,y in points);right=max(x for x,y in points)
        if layout=='path':
            from bisect import bisect_right
            lengths=[0.]
            for a,b in zip(baseline,baseline[1:]):lengths.append(lengths[-1]+math.dist(a,b))
            if right-left>lengths[-1]+1e-8:raise ValueError('The text is longer than the baseline. Reduce letter height/spacing or use a longer path.')
            offset=(lengths[-1]-(right-left))/2
        else:radius=max(.1,right-left)/math.radians(curve);center=(left+right)/2
        outlines=[];points=[]
        for piece,anchor in zip(pieces,anchors):
            if layout=='path':
                distance=offset+anchor-left
                index=min(len(baseline)-2,max(0,bisect_right(lengths,distance)-1))
                a,b=baseline[index:index+2];fraction=(distance-lengths[index])/(lengths[index+1]-lengths[index])
                px=a[0]+fraction*(b[0]-a[0]);py=a[1]+fraction*(b[1]-a[1])
                theta=math.atan2(b[1]-a[1],b[0]-a[0]);c=math.cos(theta);s=math.sin(theta)
            else:
                theta=(anchor-center)/radius;c=math.cos(theta);s=math.sin(theta)
                px=radius*s;py=radius*(1-c)
            def bend(path):
                return [(px+(x-anchor)*c-y*s, py+(x-anchor)*s+y*c) for x,y in path]
            kind,value=next(iter(piece.items()))
            placed=[bend(ring) for ring in value] if kind=='fill' else bend(value)
            piece[kind]=placed
            points += [p for ring in placed for p in ring] if kind=='fill' else placed
            if kind=='fill':outlines+=placed
            elif kind=='rails':outlines.append(placed[::2]+placed[1::2][::-1])
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
    if layout=='path':
        obj.x,obj.y=previous.transform([(cx/previous.width,cy/previous.height)])[0] if previous else (cx,cy)
    obj.name = text[:200]
    obj.kind = "compound"
    obj.stitch_type = "satin"
    obj.width, obj.height = width, total_height
    obj.points, obj.handles, obj.stitch_data = [], [], []
    obj.contours = rings
    obj.lettering = {"text": text, "family": font["name"], "height": height, "spacing": spacing, "layout": layout,
                     "curve": curve, "layout_height": total_height, "embroidery_font": font_id,
                     "columns": [{kind: [normalize(r) for r in value] if kind == "fill" else normalize(value)}
                                 for piece in pieces for kind, value in piece.items()]}
    if layout=='path':obj.lettering['baseline']=normalize(baseline)
    from .engine import generate
    Project.loads(Project(objects=[obj]).dumps())
    generate(Project(objects=[obj]))
    return obj
