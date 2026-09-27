"""Convert Ink/Stitch embroidery fonts into Morale's compact font format.

    python scripts/import_inkstitch_fonts.py SOURCE_DIR OUTPUT_DIR [FONT_ID ...]

SOURCE_DIR is the ``src`` folder of https://github.com/inkstitch/embroidery-fonts.
Each converted font becomes OUTPUT_DIR/<id>/font.json.gz plus its LICENSE. Fonts whose
licenses forbid commercial use or derivatives are skipped, because Morale's GPL
allows both. Rail/rung handling follows Ink/Stitch's SatinColumn (GPL-3.0).
"""
import gzip
import json
import math
from pathlib import Path
import re
import shutil
import sys
import xml.etree.ElementTree as ET

from svgelements import Matrix, Path as SvgPath, Move, Line, Close

MM_PER_PX = 25.4 / 96
ALLOWED = ("sil open font license", "cc-by-sa", "scc-by-sa", "cc by-sa", "public domain", "mublic domain")
BLOCKED = ("-nc", " nc", "noncommercial", "-nd", " nd")
# Basic Latin, Latin-1 and Latin Extended-A letters plus common punctuation.
CHARACTERS = set(chr(c) for c in range(0x20, 0x7F)) | set(chr(c) for c in range(0xA1, 0x180)) | set("–—‘’‚“”„•…€")
NS = {"svg": "http://www.w3.org/2000/svg", "inkscape": "http://www.inkscape.org/namespaces/inkscape",
      "sodipodi": "http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd", "inkstitch": "http://inkstitch.org/namespace"}
LABEL = "{%s}label" % NS["inkscape"]


def usable_license(text):
    text = (text or "").lower()
    return any(a in text for a in ALLOWED) and not any(b in text for b in BLOCKED)


def subpaths(d, matrix, tolerance_px=.25):
    """Flatten an SVG path into polylines (one per subpath) in document pixels."""
    # Multiplying only records the transform; reify() applies it to the points.
    path = (SvgPath(d) * matrix).reify()
    result, current = [], []
    for segment in path:
        if isinstance(segment, Move):
            if len(current) > 1:
                result.append(current)
            current = [(segment.end.x, segment.end.y)]
        elif isinstance(segment, (Line, Close)):
            if segment.end is not None:
                current.append((segment.end.x, segment.end.y))
        else:
            length = segment.length(error=1e-3)
            steps = max(2, min(64, math.ceil(length / (tolerance_px * 8))))
            for i in range(1, steps + 1):
                p = segment.point(i / steps)
                current.append((p.x, p.y))
    if len(current) > 1:
        result.append(current)
    return [dedupe(s) for s in result if len(dedupe(s)) > 1]


def dedupe(points):
    out = []
    for p in points:
        if not out or math.dist(out[-1], p) > 1e-6:
            out.append(p)
    return out


def length(points):
    return sum(math.dist(a, b) for a, b in zip(points, points[1:]))


def segments_intersect(a, b):
    """True when polylines a and b cross or touch."""
    def cross(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    for p1, p2 in zip(a, a[1:]):
        for q1, q2 in zip(b, b[1:]):
            d1, d2 = cross(q1, q2, p1), cross(q1, q2, p2)
            d3, d4 = cross(p1, p2, q1), cross(p1, p2, q2)
            if (d1 * d2 <= 0) and (d3 * d4 <= 0) and not (d1 == d2 == 0):
                return True
    return False


def project(rail, point):
    """Arc-length position on ``rail`` closest to ``point``."""
    best, travelled = (math.inf, 0.), 0.
    for a, b in zip(rail, rail[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        span = math.hypot(dx, dy)
        t = max(0., min(1., ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / (span * span))) if span else 0.
        distance = math.dist(point, (a[0] + t * dx, a[1] + t * dy))
        if distance < best[0]:
            best = (distance, travelled + t * span)
        travelled += span
    return best[1]


def line_gap(rail, point):
    return math.dist(point, at(rail, project(rail, point)))


def at(rail, position):
    travelled = 0.
    for a, b in zip(rail, rail[1:]):
        span = math.dist(a, b)
        if travelled + span >= position or b is rail[-1]:
            t = 0. if not span else max(0., min(1., (position - travelled) / span))
            return (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
        travelled += span
    return rail[-1]


def satin_pairs(paths, spacing_px):
    """Left/right rail stations for a satin column, following Ink/Stitch's rules."""
    if len(paths) < 2:
        return None
    if len(paths) == 2:
        rails, rungs = paths, []
    else:
        counts = [sum(segments_intersect(p, q) for q in paths if q is not p) for p in paths]
        if len(paths) == 3:
            candidates = [i for i, c in enumerate(counts) if c == 1 and length(paths[i]) > .1]
        else:
            candidates = [i for i, c in enumerate(counts) if c > 2 and length(paths[i]) > .1]
        indices = candidates if len(candidates) == 2 else sorted(range(len(paths)), key=lambda i: -length(paths[i]))[:2]
        rails = [paths[i] for i in indices]
        rungs = [p for i, p in enumerate(paths) if i not in indices]
    first, second = rails
    if math.dist(first[0], second[-1]) + math.dist(first[-1], second[0]) < math.dist(first[0], second[0]) + math.dist(first[-1], second[-1]):
        second = second[::-1]
    total = (length(first), length(second))
    anchors = [(0., 0.)]
    if rungs:
        for rung in rungs:
            # The rung end nearer the first rail anchors it; the other end the second.
            start, end = rung[0], rung[-1]
            if line_gap(first, end) < line_gap(first, start):
                start, end = end, start
            anchors.append((project(first, start), project(second, end)))
    elif len(first) == len(second):
        # Old-style satin: nodes pair up in order.
        run_a = run_b = 0.
        for (a0, a1), (b0, b1) in zip(zip(first, first[1:]), zip(second, second[1:])):
            run_a += math.dist(a0, a1); run_b += math.dist(b0, b1)
            anchors.append((run_a, run_b))
        anchors.pop()
    anchors.append(total)
    anchors.sort()
    monotonic = [anchors[0]]
    for a in anchors[1:]:
        if a[0] > monotonic[-1][0] + 1e-6 and a[1] > monotonic[-1][1] + 1e-6:
            monotonic.append(a)
    if monotonic[-1] != total:
        monotonic[-1] = total
    pairs = []
    for (a0, b0), (a1, b1) in zip(monotonic, monotonic[1:]):
        steps = max(1, math.ceil(max(a1 - a0, b1 - b0) / spacing_px))
        start = 0 if not pairs else 1
        for i in range(start, steps + 1):
            t = i / steps
            pairs += [at(first, a0 + t * (a1 - a0)), at(second, b0 + t * (b1 - b0))]
    return pairs


def line_distance(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    span = dx * dx + dy * dy
    t = max(0., min(1., ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / span)) if span else 0.
    return math.dist(p, (a[0] + t * dx, a[1] + t * dy))


def simplify(points, tolerance):
    """Douglas-Peucker: drop points within ``tolerance`` of the simplified line."""
    if len(points) < 3:
        return points
    keep, stack = {0, len(points) - 1}, [(0, len(points) - 1)]
    while stack:
        start, end = stack.pop()
        worst, index = 0., None
        for i in range(start + 1, end):
            d = line_distance(points[i], points[start], points[end])
            if d > worst:
                worst, index = d, i
        if index is not None and worst > tolerance:
            keep.add(index)
            stack += [(start, index), (index, end)]
    return [points[i] for i in sorted(keep)]


def simplify_pairs(pairs, tolerance):
    """Drop rail stations whose left and right points both lie on their neighbours' lines."""
    left, right = pairs[::2], pairs[1::2]
    keep = [0]
    for i in range(1, len(left) - 1):
        a = keep[-1]
        if line_distance(left[i], left[a], left[i + 1]) > tolerance or line_distance(right[i], right[a], right[i + 1]) > tolerance:
            keep.append(i)
    keep.append(len(left) - 1)
    return [p for i in keep for p in (left[i], right[i])]


def transform_of(element):
    value = element.get("transform")
    return Matrix(value) if value else Matrix()


def glyph_pieces(layer, matrix, baseline, left, scale):
    """Stitch pieces of one glyph layer in millimetres from the glyph origin."""
    pieces = []

    def to_mm(points):
        return [[round((x - left) * scale, 3), round((y - baseline) * scale, 3)] for x, y in points]
    tolerance = .03 / scale

    def walk(element, current):
        for child in element:
            tag = child.tag.split("}")[-1]
            local = transform_of(child) * current
            if tag == "g":
                walk(child, local)
            elif tag == "path" and child.get("d"):
                style = child.get("style", "")
                attrs = {k.split("}")[-1]: v for k, v in child.attrib.items() if k.startswith("{%s}" % NS["inkstitch"])}
                paths = subpaths(child.get("d"), local)
                if not paths:
                    continue
                if attrs.get("satin_column") == "True":
                    pairs = satin_pairs(paths, .5 / scale)
                    if pairs:
                        pieces.append({"rails": to_mm(simplify_pairs(pairs, tolerance))})
                elif re.search(r"fill:\s*(?!none)", style) and not attrs.get("stroke_method"):
                    rings = [to_mm(simplify(p, tolerance)) for p in paths if len(p) >= 3]
                    if rings:
                        pieces.append({"fill": rings})
                else:
                    for p in paths:
                        pieces.append({"run": to_mm(simplify(p, tolerance))})
    walk(layer, matrix)
    return pieces


def convert(font_dir, output_root):
    meta = json.loads((font_dir / "font.json").read_text(encoding="utf-8"))
    if not usable_license(meta.get("font_license")) or not (font_dir / "LICENSE").exists():
        return None, f"skipped: license {meta.get('font_license')!r}"
    # Most fonts keep every glyph in ltr.svg; a few split scripts into ltr/*.svg.
    files = [font_dir / "ltr.svg"] if (font_dir / "ltr.svg").exists() else sorted((font_dir / "ltr").glob("*.svg"))
    if not files:
        return None, "skipped: no left-to-right variant"
    glyphs = {}
    metrics = [glyphs_from(svg, meta, glyphs) for svg in files][0]
    if len(glyphs) < 10:
        return None, f"skipped: only {len(glyphs)} glyphs"
    return finish(font_dir, meta, glyphs, output_root, metrics)


def glyphs_from(svg, meta, glyphs):
    """Add one SVG's glyphs to ``glyphs``; return its scale and cap height (mm)."""
    root = ET.parse(svg).getroot()
    units = {"px": MM_PER_PX, None: MM_PER_PX, "mm": 1., "cm": 10., "in": 25.4, "pt": 25.4 / 72}

    def length_mm(value):
        match = re.fullmatch(r"\s*([0-9.]+)\s*(px|mm|cm|in|pt)?\s*", value)
        return float(match.group(1)) * units[match.group(2)]
    if root.get("viewBox"):
        view = [float(v) for v in root.get("viewBox").replace(",", " ").split()]
        # Millimetres per document unit, from the height and its unit (px when unitless).
        scale = length_mm(root.get("height") or f"{view[3]}") / view[3]
    else:
        # Without a viewBox, one document unit is one CSS pixel.
        scale = MM_PER_PX
        view = [0., 0., length_mm(root.get("width")) / MM_PER_PX, length_mm(root.get("height")) / MM_PER_PX]
    guides = {(g.get(LABEL) or "").lower(): float(g.get("position").split(",")[1]) for g in root.iter("{%s}guide" % NS["sodipodi"])}
    baseline_guide = guides.get("baseline", 0.)
    baseline = view[1] + view[3] - baseline_guide
    advance = meta.get("horiz_adv_x", {})
    default_advance = meta.get("horiz_adv_x_default")
    parents = {child: parent for parent in root.iter() for child in parent}

    def placement(layer):
        """The layer's own transform combined with every enclosing group's."""
        matrix, node = transform_of(layer), parents.get(layer)
        while node is not None:
            matrix = matrix * transform_of(node)
            node = parents.get(node)
        return matrix
    for layer in root.iter("{%s}g" % NS["svg"]):
        label = layer.get(LABEL) or ""
        if not label.startswith("GlyphLayer-"):
            continue
        char = label[len("GlyphLayer-"):]
        if len(char) != 1 or char not in CHARACTERS or char in glyphs:
            continue
        # Glyph x is measured from the document origin, as Ink/Stitch does.
        pieces = glyph_pieces(layer, placement(layer), baseline, 0., scale)
        if pieces:
            if char in advance or default_advance is not None:
                # Ink/Stitch lays glyphs out in pixels whatever the document unit.
                width = round(float(advance.get(char, default_advance)) * MM_PER_PX, 3)
            else:
                # Without widths Ink/Stitch advances to the glyph's right edge.
                width = max(x for piece in pieces for kind, value in piece.items()
                            for x, _ in (sum(value, []) if kind == "fill" else value))
            glyphs[char] = {"advance": width, "pieces": pieces}
    return {"scale": scale}


def glyph_top(glyph):
    return -min(y for piece in glyph["pieces"] for kind, value in piece.items()
                for _, y in (sum(value, []) if kind == "fill" else value))


def cap_height(glyphs):
    """Height above the baseline of a flat-topped capital, measured from the stitches.

    Guide lines in the source files are not always placed on the letters.
    """
    for char in "HEITLNMXZ":
        if char in glyphs:
            return round(glyph_top(glyphs[char]), 3)
    return round(max(glyph_top(g) for g in glyphs.values()), 3)


def rebaseline(glyphs):
    """Put flat-bottomed capitals on y = 0 when the source baseline guide is misplaced."""
    reference = next((glyphs[c] for c in "HEILTNMXZ" if c in glyphs), None)
    if reference is None:
        return
    bottom = max(y for piece in reference["pieces"] for kind, value in piece.items()
                 for _, y in (sum(value, []) if kind == "fill" else value))
    if abs(bottom) < .5:
        return
    for glyph in glyphs.values():
        for piece in glyph["pieces"]:
            for kind, value in piece.items():
                for point in (sum(value, []) if kind == "fill" else value):
                    point[1] = round(point[1] - bottom, 3)


def finish(font_dir, meta, glyphs, output_root, metrics):
    rebaseline(glyphs)
    kerning = {}
    for pair, value in (meta.get("kerning_pairs") or {}).items():
        parts = pair.split(" ")
        if len(parts) == 2 and parts[0] in glyphs and parts[1] in glyphs and value:
            kerning[pair] = round(float(value) * MM_PER_PX, 3)
    # Ids become folder names and project data: keep them to letters, digits, _ and -.
    font_id = re.sub(r"[^A-Za-z0-9_-]+", "_", font_dir.name).strip("_")
    default_advance = meta.get("horiz_adv_x_default") or 0
    result = {
        "format": "morale-embroidery-font", "version": 1, "id": font_id, "name": meta.get("name", font_id),
        "description": meta.get("description", ""), "keywords": meta.get("keywords", []),
        "license": meta.get("font_license"), "original_font": meta.get("original_font", ""),
        "source": "https://github.com/inkstitch/embroidery-fonts/tree/main/src/" + font_dir.name,
        "cap_height_mm": cap_height(glyphs),
        "size_mm": meta.get("size"), "min_scale": meta.get("min_scale", 1), "max_scale": meta.get("max_scale", 1),
        "space_mm": round(float(meta.get("horiz_adv_x_space") or default_advance or 20) * MM_PER_PX, 3),
        "letter_case": meta.get("letter_case", ""), "glyphs": glyphs, "kerning": kerning,
    }
    target = output_root / font_id
    target.mkdir(parents=True, exist_ok=True)
    # Gzip keeps the shipped library small; the JSON compresses about sixfold.
    with gzip.open(target / "font.json.gz", "wt", encoding="utf-8", compresslevel=9) as stream:
        json.dump(result, stream, ensure_ascii=False, separators=(",", ":"))
    shutil.copy(font_dir / "LICENSE", target / "LICENSE")
    return result, f"{len(glyphs)} glyphs, {sum(len(g['pieces']) for g in glyphs.values())} pieces"


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    source, output = Path(sys.argv[1]), Path(sys.argv[2])
    names = sys.argv[3:] or sorted(p.name for p in source.iterdir() if (p / "font.json").exists())
    for name in names:
        try:
            _, message = convert(source / name, output)
        except Exception as exc:  # A broken source font must not stop the batch.
            message = f"failed: {type(exc).__name__}: {exc}"
        print(f"{name}: {message}")


if __name__ == "__main__":
    main()
