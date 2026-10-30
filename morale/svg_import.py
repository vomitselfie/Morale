"""Local SVG artwork to editable fill contours and Bezier running outlines."""
from dataclasses import dataclass
import io
import math
import re
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


def paint_order(value='normal'):
    parts=str(value).split()
    if parts==['normal']:return ('fill','stroke','markers')
    if not parts or len(parts)!=len(set(parts)) or any(p not in {'fill','stroke','markers'} for p in parts):
        raise ValueError('Invalid SVG paint-order; use fill, stroke and/or markers once each.')
    return tuple(parts+[p for p in ('fill','stroke','markers') if p not in parts])


def checked_xml(text, *, allow_dashes=False, paint_sink=None, layer_sink=None):
    if "<!DOCTYPE" in text.upper() or "<!ENTITY" in text.upper():
        raise ValueError("SVG document types and entity declarations are not supported.")
    root = ET.fromstring(text)
    from .svg_styles import apply_styles
    from .svg_settings import annotate
    apply_styles(root)
    annotate(root)
    def tag(node):
        return node.tag.split("}")[-1]
    if tag(root) != "svg":
        raise ValueError("Expected an SVG document.")
    nodes = list(root.iter())
    if len(nodes) > 10_000:
        raise ValueError("SVG exceeds 10,000 XML elements.")
    ids = {n.get("id"): n for n in nodes if n.get("id")}
    allowed = {"svg", "g", "defs", "clipPath", "symbol", "use", "path", "rect", "circle", "ellipse", "line", "polyline", "polygon", "title", "desc", "metadata"}
    visits = 0
    viewport_clipping = False
    rendering_nodes = {}
    def visit(node, stack):
        nonlocal visits,viewport_clipping
        visits += 1
        if visits > 10_000 or len(stack) > 64:
            raise ValueError("SVG nesting or reference expansion exceeds the supported limit.")
        if id(node) in stack:
            raise ValueError("SVG contains a circular use reference.")
        if tag(node) in {"metadata", "title", "desc"}:
            # Some parsers descend into metadata and interpret nested SVG shapes.
            # These non-rendering subtrees must not become embroidery artwork.
            node.clear()
            return
        if tag(node) not in allowed:
            raise ValueError(f"SVG element '{tag(node)}' is not supported. Convert text and special effects to plain paths first.")
        rendering_nodes[id(node)] = node
        # svgelements otherwise leaks a nested viewport's x/y into child
        # rectangles and use instances whose positions default to zero.
        if tag(node) in {"rect","use","svg"}:
            for coordinate in ("x","y"):
                if coordinate not in node.attrib:node.set(coordinate,"0")
        styles = dict(item.split(":", 1) for item in node.get("style", "").split(";") if ":" in item)
        properties = {**node.attrib, **{k.strip(): v.strip() for k, v in styles.items()}}
        if tag(node)=="svg" and node is not root:
            viewport_clipping=True
            if "overflow" not in properties:
                node.set("overflow","hidden");properties["overflow"]="hidden"
        for key in ("mask", "filter", "marker-start", "marker-mid", "marker-end", "stroke-dasharray"):
            if properties.get(key, "none") != "none" and not (key == "stroke-dasharray" and allow_dashes):
                raise ValueError(f"SVG {key} needs to be converted to plain paths before import.")
        if "slice" in properties.get("preserveAspectRatio", "") or properties.get("overflow") in {"hidden", "scroll"}:
            if tag(node)!="svg":raise ValueError("SVG viewport clipping is only supported on SVG viewport elements.")
            viewport_clipping=True
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
    for node in list(root.iter()):
        if tag(node)!="svg":continue
        styles={key.strip():value.strip() for part in node.get('style','').split(';') if ':' in part for key,value in [part.split(':',1)]}
        properties={**node.attrib,**styles}
        zero=False
        for dimension in ('width','height'):
            raw=properties.get(dimension,'')
            match=re.fullmatch(r'\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*(?:px|mm|cm|in|pt|pc|em|ex|%)?\s*',raw)
            if match:
                value=float(match[1])
                if not math.isfinite(value) or value<0:raise ValueError('SVG viewport dimensions must be nonnegative and finite.')
                zero=zero or value==0
        if zero:
            if node is root:raise ValueError('SVG page dimensions must be positive.')
            ident=node.get('id');node.clear();node.tag='g';node.set('display','none')
            if ident:node.set('id',ident)
    if any(tag(node)=="symbol" for node in root.iter()):
        from .svg_symbols import expand_symbols
        expand_symbols(root)
        return checked_xml(ET.tostring(root,encoding="unicode"),allow_dashes=allow_dashes,paint_sink=paint_sink,layer_sink=layer_sink)
    # Group opacity composites the entire subtree. svgelements treats opacity
    # as inherited, allowing a child's explicit value to revive invisible paint.
    # A zero-opacity subtree is non-rendering regardless of child overrides.
    notices = []
    from copy import deepcopy
    clip_sources={}
    for clip in root.iter():
        if tag(clip)!="clipPath":continue
        for child in clip.iter():
            if tag(child)!="use":continue
            href=child.get("href",child.get("{http://www.w3.org/1999/xlink}href",""))
            target=ids.get(href[1:])
            if target is not None and tag(target) in {"path","rect","circle","ellipse","line","polyline","polygon"}:
                clip_sources[href[1:]]=deepcopy(target)
    clip_nodes={id(child) for node in root.iter() if tag(node)=="clipPath" for child in node.iter()}
    for node in rendering_nodes.values():
        if id(node) in clip_nodes:continue
        styles=dict(item.split(":",1) for item in node.get("style","").split(";") if ":" in item)
        properties={**node.attrib,**{k.strip():v.strip() for k,v in styles.items()}}
        for key in ('opacity','fill-opacity','stroke-opacity'):
            if key not in properties:continue
            raw=properties[key].strip()
            try:value=float(raw[:-1])/100 if raw.endswith('%') else float(raw)
            except ValueError as exc:raise ValueError(f'Unsupported SVG {key}: use a number or percentage.') from exc
            if not math.isfinite(value):raise ValueError(f'SVG {key} must be finite.')
            value=max(0.,min(1.,value))
            if 0<value<1 and not (paint_sink is not None and (key in {'fill-opacity','stroke-opacity'} or layer_sink is not None)):
                notices.append("Partial transparency is imported as opaque thread color.")
            node.set(key,str(value))
            node.set('style',node.get('style','')+f';{key}:{value}')
            if key=='opacity' and value==0:
                node.set('style',node.get('style','')+';display:none')
    viewbox = root.get("viewBox", "").replace(",", " ").split()
    for key, index, default in [("width", 2, "300"), ("height", 3, "150")]:
        if "%" in root.get(key, ""):
            raise ValueError("SVG page dimensions must be absolute, not percentages.")
        if not root.get(key):
            root.set(key, viewbox[index] if len(viewbox) == 4 else default)
            notices.append("Missing page dimensions use viewBox units (or a 300 × 150 px viewport) at 96 px/in.")
    if paint_sink is not None or viewport_clipping or any(n.tag.split("}")[-1]=="clipPath" or "clip-path" in n.attrib or "clip-path" in n.get("style", "") for n in root.iter()):
        from .svg_clipping import resolve_fill_clips
        root=resolve_fill_clips(root,clip_sources,paint_sink=paint_sink,layer_sink=layer_sink)
        notices.append("SVG viewport and clipping geometry was normalized before digitizing; clipped strokes become filled borders.")
    return ET.tostring(root, encoding="unicode"), notices


def import_svg(path):
    path = Path(path)
    if path.stat().st_size > 2_000_000:
        raise ValueError("SVG artwork is limited to 2 MB.")
    try:
        return import_svg_text(path.read_text(encoding="utf-8-sig"))
    except (ET.ParseError, UnicodeError, TypeError, AttributeError, IndexError, ZeroDivisionError, RecursionError, OverflowError) as exc:
        raise ValueError(f"Could not interpret SVG artwork: {exc}") from exc


def import_svg_text(text, *, center_artwork=True):
    if len(text.encode('utf-8')) > 2_000_000:
        raise ValueError("SVG artwork is limited to 2 MB.")
    try:
        text, notices = checked_xml(text)
        document = svg.SVG.parse(io.StringIO(text), ppi=96, reify=True, width=300, height=150, on_error="raise")
        return convert_document(document, notices, center_artwork=center_artwork)
    except (ET.ParseError, UnicodeError, TypeError, AttributeError, IndexError, ZeroDivisionError, RecursionError, OverflowError) as exc:
        raise ValueError(f"Could not interpret SVG artwork: {exc}") from exc


def convert_document(document, notices, *, center_artwork=True):
    from .svg_settings import ATTRIBUTE, NAME_ATTRIBUTE, parse, apply as apply_settings
    objects = []
    named_settings = {}  # object id: settings from SVG names, applied once types are final
    satin_fills = set()
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
        base, outline_settings, _, problems = parse(element.values.get(ATTRIBUTE, ""))
        notices.extend(problems)
        if base.get("type") == "skip":
            continue
        own_words = parse(element.values.get(NAME_ATTRIBUTE, ""))[2]
        outline_type = outline_settings.get("type") or (base.get("type") if base.get("type") in {"running", "satin", "skip"} else None)
        outline_settings = {**{k: v for k, v in base.items() if k != "type"}, **outline_settings}
        order=paint_order(element.values.get("paint-order","normal"))
        first_object=len(objects)
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
        name = str(" ".join(own_words) or element.values.get("id") or element.values.get("tag") or "SVG shape")[:160]
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
                fill = DesignObject(name=name, kind="compound", x=bounds.center().x()/20, y=bounds.center().y()/20,
                    width=bounds.width()/20, height=bounds.height()/20, contours=contours,
                    color=element.fill.hex[:7], underlay=False, connect_fill=True)
                fill_type = base.get("type")
                if fill_type in {"fill", "contour", "ripple", "running"}:
                    fill.stitch_type = fill_type
                elif fill_type == "satin":
                    satin_fills.add(fill.id)
                named_settings[fill.id] = {k: v for k, v in base.items() if k != "type"}
                objects.append(fill)
        first_stroke=len(objects)
        if element.stroke.value is not None and element.stroke.alpha and element.stroke_width > 0 and outline_type != "skip":
            if outline_type != "satin":
                notices.append("SVG strokes become running centerlines; stroke width, caps, and joins are not embroidery borders.")
            for controls, closed in outlines:
                source = DesignObject(name=f"{name} · outline", kind="polygon" if closed else "path",
                                      stitch_type="running", color=element.stroke.hex[:7], underlay=False)
                outline = edit_controls(source, controls)
                if outline_type == "satin":
                    width = outline_settings.get("width", element.stroke_width * 25.4 / 96)
                    outline = satin_outline(outline, width, closed, notices)
                named_settings[outline.id] = outline_settings
                objects.append(outline)
        if order.index("stroke") < order.index("fill"):
            objects[first_object:]=objects[first_stroke:]+objects[first_object:first_stroke]
        if len(objects) > 500:
            raise ValueError("SVG import exceeds the 500-object limit.")
    if not objects:
        raise ValueError("SVG contains no usable visible vector shapes.")
    # Center the artwork as a whole while preserving physical size and spacing.
    points = [p for obj in objects for ring in obj.rings() for p in ring]
    xs, ys = zip(*points)
    dx, dy = (min(xs)+max(xs))/2, (min(ys)+max(ys))/2
    if center_artwork:
        for obj in objects:
            obj.x -= dx
            obj.y -= dy
    if satin_fills:
        from .auto_digitize import choose_stitches
        overrides = {str(i): "satin" for i, obj in enumerate(objects) if obj.id in satin_fills}
        converted, decisions = choose_stitches(Project(objects=objects), "fill", overrides)
        for decision in decisions:
            if str(decision["region"]) in overrides and decision["selected"] != "satin":
                notices.append(f"{objects[decision['region']].name}: kept as fill. {decision['reason']}")
        objects = converted.objects
    for obj in objects:
        apply_settings(obj, named_settings.get(obj.id, {}), notices)
    project = Project.loads(Project(objects=objects).dumps())
    generate(project)
    return SVGImport(project.objects, list(dict.fromkeys(notices)))


def satin_outline(outline, width, closed, notices):
    """A satin column along a stroke named ``satin``, or the running outline
    when the column cannot be sewn."""
    from .model import placed_object
    from .satin_geometry import centerline_rails
    from .engine import satin
    points = outline.outline()
    if closed and len(points) > 2 and math.dist(points[0], points[-1]) < 1e-9:
        points = points[:-1]
    try:
        rails = centerline_rails(points, width, closed=closed)
        satin(rails, outline.spacing, outline.satin_max)
        column = placed_object(rails, name=outline.name, kind="satin", stitch_type="satin", color=outline.color)
        Project.loads(Project(objects=[column]).dumps())
    except ValueError as exc:
        notices.append(f"{outline.name}: kept as a running line; a {width:g} mm satin column does not fit this path. {exc}")
        return outline
    return column
