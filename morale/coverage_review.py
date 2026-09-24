"""Stacked coverage between objects and fabric-dependent review thresholds.

Each object's sewn footprint (its outline plus a 0.4 mm band along every sewn
segment, which captures compensation and underlay) is rasterized once. Adding
the footprints gives the number of distinct objects over every point. These
are geometric measurements, not predictions of how a fabric will behave.
"""
from collections import Counter
import math
import sys

from PySide6.QtCore import QRectF, Qt, QPointF
from PySide6.QtGui import QImage, QPainter, QColor, QFont, QPen, QTransform

from .auto_digitize import outline_path, area

THREAD_WIDTH_MM = .4
MAX_PIXELS = 4_000_000
MAX_PAIRS = 2000

# Starting-point review thresholds, not calibrated sewing limits. Layers are
# distinct objects over one point; density uses the 1 mm sewn-length map, where
# one satin layer with underlay measures about 5-6 mm/mm² and a 0.45 mm fill
# about 2.3, so medium woven allows roughly two stacked satins.
FABRICS = {
    "woven": {"label": "Medium woven (cotton, twill)", "max_layers": 3, "max_density": 11.0, "min_satin_mm": 1.0, "min_fill_mm2": 4.0,
              "advice": "Tear-away or cut-away stabilizer."},
    "light": {"label": "Lightweight woven (poplin, shirting)", "max_layers": 2, "max_density": 8.5, "min_satin_mm": 1.0, "min_fill_mm2": 4.0,
              "advice": "Cut-away or no-show mesh; dense areas pucker easily."},
    "knit": {"label": "Knit or stretch (jersey, T-shirt)", "max_layers": 2, "max_density": 9.5, "min_satin_mm": 1.2, "min_fill_mm2": 6.0,
             "advice": "Cut-away stabilizer; avoid long satins across the stretch."},
    "heavy": {"label": "Heavy woven (denim, canvas)", "max_layers": 4, "max_density": 14.0, "min_satin_mm": 1.0, "min_fill_mm2": 3.0,
              "advice": "Tear-away stabilizer; use a sharp or denim needle."},
    "pile": {"label": "Pile (towel, fleece)", "max_layers": 3, "max_density": 11.0, "min_satin_mm": 2.0, "min_fill_mm2": 10.0,
             "advice": "Water-soluble topping keeps small details from sinking into the pile."},
}


def _footprint(obj, block, painter, scale):
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(1, 1, 1))
    if obj.kind != "stitches" and obj.stitch_type in {"fill", "satin"}:
        painter.drawPath(scale.map(outline_path(obj.rings())))
    pen = QPen(QColor(1, 1, 1))
    pen.setWidthF(THREAD_WIDTH_MM * scale.m11())
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    previous = None
    for stitch in block.stitches:
        point = scale.map(QPointF(stitch.x, stitch.y))
        if stitch.command == "stitch" and previous is not None:
            painter.drawLine(previous, point)
        if stitch.command in {"stitch", "jump"}:
            previous = point


def _red(image):
    """One byte per pixel: the red channel, which carries the layer count."""
    raw = bytes(image.constBits())
    width = image.width()
    stride = image.bytesPerLine()
    # 32-bit ARGB pixels are stored B, G, R, A on little-endian hosts.
    channel = 2 if sys.byteorder == "little" else 1
    return b"".join(raw[row * stride + channel:row * stride + width * 4:4] for row in range(image.height()))


def measure_layers(project, blocks):
    """Distinct-object layers per point and overlap area for each object pair."""
    objects = {obj.id: obj for obj in project.objects}
    shapes = []
    for block in blocks:
        obj = objects.get(block.object_id)
        points = [(s.x, s.y) for s in block.stitches if s.command in {"stitch", "jump"}]
        if obj is None or not any(s.command == "stitch" for s in block.stitches):
            continue
        if obj.kind != "stitches" and obj.stitch_type in {"fill", "satin"}:
            points += [p for ring in obj.rings() for p in ring]
        xs, ys = zip(*points)
        pad = THREAD_WIDTH_MM
        shapes.append((obj, block, (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)))
    report = {"objects": len(shapes), "pixel_mm": None, "area_by_layers_mm2": {}, "peak_layers": 0,
              "overlap_pairs": [], "pairs_complete": True, "stacked_locations": []}
    if not shapes:
        return report, None
    left = min(s[2][0] for s in shapes); top = min(s[2][1] for s in shapes)
    right = max(s[2][2] for s in shapes); bottom = max(s[2][3] for s in shapes)
    per_mm = max(1.0, min(10.0, math.sqrt(MAX_PIXELS / max(1e-6, (right - left) * (bottom - top)))))
    width, height = math.ceil((right - left) * per_mm) + 1, math.ceil((bottom - top) * per_mm) + 1
    report["pixel_mm"] = 1 / per_mm
    scale = QTransform().scale(per_mm, per_mm).translate(-left, -top)
    total = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    total.fill(QColor(0, 0, 0, 255))
    adder = QPainter(total)
    adder.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
    masks = []
    for obj, block, (x0, y0, x1, y1) in shapes:
        # Rasterize each object alone so its own passes count once.
        px, py = math.floor((x0 - left) * per_mm), math.floor((y0 - top) * per_mm)
        mask = QImage(math.ceil((x1 - x0) * per_mm) + 2, math.ceil((y1 - y0) * per_mm) + 2, QImage.Format.Format_ARGB32_Premultiplied)
        mask.fill(Qt.GlobalColor.transparent)
        painter = QPainter(mask)
        _footprint(obj, block, painter, scale * QTransform.fromTranslate(-px, -py))
        painter.end()
        adder.drawImage(px, py, mask)
        masks.append((obj, px, py, mask))
    adder.end()
    layers = _red(total)
    pixel_area = report["pixel_mm"] ** 2
    histogram = Counter(layers)
    report["area_by_layers_mm2"] = {str(k): round(v * pixel_area, 3) for k, v in sorted(histogram.items()) if k}
    report["peak_layers"] = max((k for k in histogram if k), default=0)
    # Report stacked (three or more layer) areas by 1 mm cell.
    stacked = Counter()
    for row in range(height):
        line = layers[row * width:(row + 1) * width]
        if max(line) < 3:
            continue
        for column, value in enumerate(line):
            if value >= 3:
                cell = (math.floor(left + column / per_mm), math.floor(top + row / per_mm))
                stacked[cell] = max(stacked[cell], value)
    report["stacked_locations"] = [{"x_mm": x, "y_mm": y, "layers": v}
                                   for (x, y), v in sorted(stacked.items(), key=lambda item: (-item[1], item[0]))[:20]]
    pairs = []
    checked = 0
    for index, (a, ax, ay, amask) in enumerate(masks):
        for b, bx, by, bmask in masks[index + 1:]:
            x0, y0 = max(ax, bx), max(ay, by)
            x1, y1 = min(ax + amask.width(), bx + bmask.width()), min(ay + amask.height(), by + bmask.height())
            if x1 <= x0 or y1 <= y0:
                continue
            checked += 1
            if checked > MAX_PAIRS:
                report["pairs_complete"] = False
                break
            both = QImage(x1 - x0, y1 - y0, QImage.Format.Format_ARGB32_Premultiplied)
            both.fill(QColor(0, 0, 0, 255))
            painter = QPainter(both)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
            painter.drawImage(ax - x0, ay - y0, amask)
            painter.drawImage(bx - x0, by - y0, bmask)
            painter.end()
            shared = _red(both).count(2) * pixel_area
            if shared >= .05:
                pairs.append({"first": a.name, "second": b.name, "first_id": a.id, "second_id": b.id, "area_mm2": round(shared, 3)})
        if not report["pairs_complete"]:
            break
    report["overlap_pairs"] = sorted(pairs, key=lambda p: -p["area_mm2"])[:50]
    report["overlap_pair_count"] = len(pairs)
    return report, (layers, width, height, left, top, per_mm)


LAYER_COLORS = [QColor("#fffdf8"), QColor("#c9d6e3"), QColor("#f2b134"), QColor("#e4572e"), QColor("#8c1c13")]


def layers_text(report):
    areas = report["area_by_layers_mm2"]
    single = areas.get("1", 0)
    stacked = sum(v for k, v in areas.items() if int(k) >= 2)
    lines = [f"Coverage layers: peak {report['peak_layers']}; {single:.1f} mm² single layer, {stacked:.1f} mm² overlapped.",
             "Footprints include a 0.4 mm band along each sewn segment, so touching objects can show a thin overlap."]
    for pair in report["overlap_pairs"][:10]:
        lines.append(f"  {pair['first']} / {pair['second']}: {pair['area_mm2']:.2f} mm² shared.")
    if report.get("overlap_pair_count", 0) > 10:
        lines.append(f"  … {report['overlap_pair_count'] - 10} more overlapping pairs.")
    if not report["pairs_complete"]:
        lines.append(f"Pair comparison stopped after {MAX_PAIRS} candidate pairs.")
    return lines


def render_layers(report, raster):
    image = QImage(640, 520, QImage.Format.Format_RGB32)
    image.fill(QColor("#fffdf8"))
    painter = QPainter(image)
    painter.setFont(QFont("Sans", 11))
    painter.setPen(QColor("#202020"))
    painter.drawText(18, 25, "Coverage layers: distinct objects sewn over each point")
    areas = report["area_by_layers_mm2"]
    stacked = sum(v for k, v in areas.items() if int(k) >= 2)
    painter.drawText(18, 47, f"Peak: {report['peak_layers']} layers · Overlapping area: {stacked:.1f} mm² · Object pairs: {report.get('overlap_pair_count', 0)}")
    if raster is not None:
        layers, width, height, left, top, per_mm = raster
        indexed = QImage(layers, width, height, width, QImage.Format.Format_Indexed8)
        indexed.setColorTable([LAYER_COLORS[min(value, 4)].rgb() for value in range(256)])
        target = QRectF(0, 0, width, height)
        target.setSize(target.size().scaled(604, 380, Qt.AspectRatioMode.KeepAspectRatio))
        target.moveCenter(QPointF(320, 255))
        painter.drawImage(target, indexed.copy())
        painter.drawText(18, 458, f"Extent: X {left:.1f} to {left + width / per_mm:.1f} mm · Y {top:.1f} to {top + height / per_mm:.1f} mm")
    else:
        painter.drawText(18, 100, "No sewn stitches to measure.")
    for index, label in enumerate(("1 layer", "2 layers", "3 layers", "4+ layers")):
        x = 18 + index * 120
        painter.fillRect(QRectF(x, 468, 14, 14), LAYER_COLORS[index + 1])
        painter.drawText(x + 20, 480, label)
    painter.drawText(18, 498, "Fixed scale. Footprints add a 0.4 mm band along each sewn segment,")
    painter.drawText(18, 514, "so touching objects show a thin seam. Not a fabric-damage prediction.")
    painter.end()
    return image


def _satin_width(obj):
    rails = obj.transform(obj.points)
    return max((math.dist(a, b) for a, b in zip(rails[::2], rails[1::2])), default=0.)


def detail_measurements(project):
    """Per-object sizes used by fabric guidance."""
    details = []
    for obj in project.objects:
        entry = {"object_id": obj.id, "name": obj.name, "stitch_type": obj.stitch_type}
        if obj.kind == "satin":
            entry["satin_width_mm"] = round(_satin_width(obj), 3)
        elif obj.kind != "stitches" and obj.stitch_type == "fill":
            entry["fill_area_mm2"] = round(area(outline_path(obj.rings())), 3)
        details.append(entry)
    return details


def fabric_guidance(quality, fabric):
    """Findings for one fabric from stored measurements; no regeneration needed."""
    if fabric not in FABRICS:
        raise ValueError("Choose a listed fabric.")
    limits = FABRICS[fabric]
    lines = [f"Fabric guidance: {limits['label']}",
             "Starting-point review thresholds, not calibrated limits. Confirm with a test sew-out.", limits["advice"]]
    findings = 0
    layers = quality.get("layers")
    if layers:
        over = sum(v for k, v in layers["area_by_layers_mm2"].items() if int(k) > limits["max_layers"])
        if over:
            findings += 1
            lines.append(f"{over:.1f} mm² has more than {limits['max_layers']} stacked layers (peak {layers['peak_layers']}).")
            lines.extend(f"  Stacked at X {s['x_mm']} mm, Y {s['y_mm']} mm: {s['layers']} layers."
                         for s in layers["stacked_locations"] if s["layers"] > limits["max_layers"])
    density = quality.get("thread_density")
    if density and density.get("histogram"):
        over = sum(count for low, count in density["histogram"] if low >= limits["max_density"])
        if over:
            findings += 1
            lines.append(f"{over} cells of 1 mm² exceed {limits['max_density']:g} mm of sewn thread per mm² (peak {density['peak_mm_per_mm2']:.2f}).")
            lines.extend(f"  Dense at X {c['x_mm']} mm, Y {c['y_mm']} mm: {c['sewn_mm']:.2f} mm/mm²."
                         for c in density.get("hottest_cells", [])[:5] if c["sewn_mm"] >= limits["max_density"])
    for detail in quality.get("details", []):
        width = detail.get("satin_width_mm")
        if width is not None and width < limits["min_satin_mm"]:
            findings += 1
            lines.append(f"{detail['name']}: satin {width:.2f} mm wide, below {limits['min_satin_mm']:g} mm for this fabric; consider a running or triple outline.")
        size = detail.get("fill_area_mm2")
        if size is not None and size < limits["min_fill_mm2"]:
            findings += 1
            lines.append(f"{detail['name']}: fill of {size:.2f} mm², below {limits['min_fill_mm2']:g} mm²; small fills can lose shape.")
    if not findings:
        lines.append("No thresholds exceeded for this fabric.")
    return findings, "\n".join(lines)
