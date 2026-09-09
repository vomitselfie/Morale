"""Local SVG artwork to editable fill contours and Bezier running outlines."""
from dataclasses import dataclass
import io
import math
from pathlib import Path
import xml.etree.ElementTree as ET

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainterPath, QTransform
import svgelements as svg

from .model import DesignObject, Project
from .bezier import edit_controls
from .engine import generate


@dataclass
class SVGImport:
    objects: list
    notices: list


def checked_xml(text):
    if "<!DOCTYPE" in text.upper() or "<!ENTITY" in text.upper():
        raise ValueError("SVG document types and entity declarations are not supported.")
    root = ET.fromstring(text)
    def tag(node):
        return node.tag.split("}")[-1]
    if tag(root) != "svg":
        raise ValueError("Expected an SVG document.")
    nodes = list(root.iter())
    if len(nodes) > 10_000:
        raise ValueError("SVG exceeds 10,000 XML elements.")
    ids = {n.get("id"): n for n in nodes if n.get("id")}
    allowed = {"svg", "g", "defs", "use", "path", "rect", "circle", "ellipse", "line", "polyline", "polygon", "title", "desc", "metadata"}
    visits = 0
    def visit(node, stack):
        nonlocal visits
        visits += 1
        if visits > 10_000 or len(stack) > 64:
            raise ValueError("SVG nesting or reference expansion exceeds the supported limit.")
        if id(node) in stack:
            raise ValueError("SVG contains a circular use reference.")
        if tag(node) in {"metadata", "title", "desc"}:
            return
        if tag(node) not in allowed:
            raise ValueError(f"SVG element '{tag(node)}' is not supported. Convert text and special effects to plain paths first.")
        styles = dict(item.split(":", 1) for item in node.get("style", "").split(";") if ":" in item)
        properties = {**node.attrib, **{k.strip(): v.strip() for k, v in styles.items()}}
        for key in ("clip-path", "mask", "filter", "marker-start", "marker-mid", "marker-end", "stroke-dasharray"):
            if properties.get(key, "none") != "none":
                raise ValueError(f"SVG {key} needs to be converted to plain paths before import.")
        if "slice" in properties.get("preserveAspectRatio", "") or properties.get("overflow") in {"hidden", "scroll"}:
            raise ValueError("SVG viewport clipping needs to be converted to plain paths before import.")
        for key in ("fill", "stroke"):
            if "url(" in properties.get(key, "").lower():
                raise ValueError("SVG gradient/pattern paint is not supported; use solid colors.")
        if tag(node) == "use":
            href = node.get("href", node.get("{http://www.w3.org/1999/xlink}href", ""))
            if not href.startswith("#") or href[1:] not in ids:
                raise ValueError("SVG use references must name an existing local element.")
            visit(ids[href[1:]], stack + [id(node)])
        for child in node:
            visit(child, stack + [id(node)])
    visit(root, [])
    notices = []
    viewbox = root.get("viewBox", "").replace(",", " ").split()
    for key, index, default in [("width", 2, "300"), ("height", 3, "150")]:
        if "%" in root.get(key, ""):
            raise ValueError("SVG page dimensions must be absolute, not percentages.")
        if not root.get(key):
            root.set(key, viewbox[index] if len(viewbox) == 4 else default)
            notices.append("Missing page dimensions use viewBox units (or a 300 × 150 px viewport) at 96 px/in.")
    return ET.tostring(root, encoding="unicode"), notices


def import_svg(path):
    path = Path(path)
    if path.stat().st_size > 2_000_000:
        raise ValueError("SVG artwork is limited to 2 MB.")
    try:
        text, notices = checked_xml(path.read_text(encoding="utf-8-sig"))
        document = svg.SVG.parse(io.StringIO(text), ppi=96, reify=True, width=300, height=150, on_error="raise")
        return convert_document(document, notices)
    except (ET.ParseError, UnicodeError, TypeError, AttributeError, IndexError, ZeroDivisionError, RecursionError, OverflowError) as exc:
        raise ValueError(f"Could not interpret SVG artwork: {exc}") from exc


def convert_document(document, notices):
    objects = []
    origin = (float(document.width) / 2, float(document.height) / 2)
    def point(p):
        result = ((p.x - origin[0]) * 25.4 / 96, (p.y - origin[1]) * 25.4 / 96)
        if not all(math.isfinite(v) and abs(v) <= 1000 for v in result):
            raise ValueError("SVG coordinates exceed ±1,000 mm from the page center.")
        return result
    for element in document.elements():
        if not isinstance(element, svg.Shape) or element.values.get("visibility") in {"hidden", "collapse"}:
            continue
        if element.values.get("display") == "none" or float(element.values.get("opacity", 1)) == 0:
            continue
        path = svg.Path(element)
        path.reify()
        if len(path) > 6000:
            raise ValueError("An SVG shape exceeds 6,000 segments.")
        outlines = []
        controls = []
        closed = False
        def finish():
            nonlocal controls, closed
            if len(controls) >= 6:
                if closed and controls[-2] == controls[1]:
                    controls[0] = controls[-3]
                    controls = controls[:-3]
                if closed and len(controls) == 3:
                    incoming, anchor, outgoing = controls
                    controls = [anchor, anchor, outgoing, incoming, anchor, anchor]
                if closed and len(controls) == 6:
                    # A two-anchor closed cubic can enclose area. Split one
                    # segment exactly to meet the project's three-anchor rule.
                    def midpoint(a, b):
                        return tuple((x+y)/2 for x,y in zip(a,b))
                    a,b,c,d = controls[1:5]
                    ab,bc,cd = midpoint(a,b),midpoint(b,c),midpoint(c,d)
                    abc,bcd = midpoint(ab,bc),midpoint(bc,cd)
                    middle = midpoint(abc,bcd)
                    controls = [controls[0],a,ab,abc,middle,bcd,cd,d,controls[5]]
                if len(controls) >= (9 if closed else 6):
                    outlines.append((controls, closed))
            controls, closed = [], False
        for segment in path:
            if isinstance(segment, svg.Move):
                finish()
                anchor = point(segment.end)
                controls = [anchor, anchor, anchor]
                continue
            if not controls:
                anchor = point(segment.start)
                controls = [anchor, anchor, anchor]
            segments = list(segment.as_cubic_curves()) if isinstance(segment, svg.Arc) else [segment]
            for part in segments:
                start, end = point(part.start), point(part.end)
                if isinstance(part, svg.CubicBezier):
                    outgoing, incoming = point(part.control1), point(part.control2)
                elif isinstance(part, svg.QuadraticBezier):
                    control = point(part.control)
                    outgoing = tuple(a + 2*(c-a)/3 for a, c in zip(start, control))
                    incoming = tuple(a + 2*(c-a)/3 for a, c in zip(end, control))
                else:
                    outgoing = tuple(a + (b-a)/3 for a, b in zip(start, end))
                    incoming = tuple(b + (a-b)/3 for a, b in zip(start, end))
                controls[-1] = outgoing
                controls.extend([incoming, end, end])
            closed = isinstance(segment, svg.Close)
        finish()
        name = str(element.values.get("id") or element.values.get("tag") or "SVG shape")[:160]
        fill_path = QPainterPath()
        rule = element.values.get("fill-rule", "nonzero")
        if rule not in {"nonzero", "evenodd"}:
            raise ValueError("Unsupported SVG fill rule.")
        fill_path.setFillRule(Qt.FillRule.OddEvenFill if rule == "evenodd" else Qt.FillRule.WindingFill)
        for controls, closed in outlines:
            fill_path.moveTo(*controls[1])
            count = len(controls)//3
            for i in range(count if closed else count-1):
                j = (i+1) % count
                fill_path.cubicTo(*controls[3*i+2], *controls[3*j], *controls[3*j+1])
            fill_path.closeSubpath()
        for paint in (element.fill, element.stroke):
            if paint.value is not None and paint.alpha != 255:
                notices.append("Partial transparency is imported as opaque thread color.")
        if float(element.values.get("opacity", 1)) != 1:
            notices.append("Partial transparency is imported as opaque thread color.")
        if element.fill.value is not None and element.fill.alpha:
            # Qt normalizes the SVG fill rule before persisting even-odd rings.
            normalized = QTransform().scale(20, 20).map(fill_path).simplified()
            bounds = normalized.boundingRect()
            if bounds.width() >= 2 and bounds.height() >= 2:
                contours = []
                for polygon in normalized.toSubpathPolygons():
                    ring = [[(p.x()-bounds.center().x())/bounds.width(), (p.y()-bounds.center().y())/bounds.height()] for p in polygon]
                    if len(ring) > 1 and ring[0] == ring[-1]:
                        ring.pop()
                    if len(ring) >= 3:
                        contours.append(ring)
                objects.append(DesignObject(name=name, kind="compound", x=bounds.center().x()/20, y=bounds.center().y()/20,
                    width=bounds.width()/20, height=bounds.height()/20, contours=contours,
                    color=element.fill.hex[:7], underlay=False, connect_fill=True))
        if element.stroke.value is not None and element.stroke.alpha and element.stroke_width > 0:
            notices.append("SVG strokes become running centerlines; stroke width, caps, and joins are not embroidery borders.")
            for controls, closed in outlines:
                source = DesignObject(name=f"{name} · outline", kind="polygon" if closed else "path",
                                      stitch_type="running", color=element.stroke.hex[:7], underlay=False)
                objects.append(edit_controls(source, controls))
        if len(objects) > 500:
            raise ValueError("SVG import exceeds the 500-object limit.")
    if not objects:
        raise ValueError("SVG contains no usable visible vector shapes.")
    # Center the artwork as a whole while preserving physical size and spacing.
    points = [p for obj in objects for ring in obj.rings() for p in ring]
    xs, ys = zip(*points)
    dx, dy = (min(xs)+max(xs))/2, (min(ys)+max(ys))/2
    for obj in objects:
        obj.x -= dx
        obj.y -= dy
    project = Project.loads(Project(objects=objects).dumps())
    generate(project)
    return SVGImport(project.objects, list(dict.fromkeys(notices)))
