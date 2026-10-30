"""Physical sew-out coupons: small designs that each isolate one variable.

    python -m morale.coupons --list
    python -m morale.coupons --output DIR [--coupon NAME ...]

Every coupon is a single-colour design for a 100 x 100 mm field with a 10 mm
scale square in its lower-left corner, so photos and scans can be measured. It
is written with machine files, a placement template, a metadata template for
the machine/thread/fabric/stabilizer and an evaluation form listing each test
object with its target. See docs/SEWOUT_VALIDATION.md for the process.
"""
import argparse
import hashlib
import json
import math
import os
import tempfile
from html import escape
from pathlib import Path

from . import __version__
from .model import Project, DesignObject
from .stitch_edit import manual_object
from .engine import generate
from .formats import export_machine
from .export_verify import verify_export, verification_text
from .templates import export_template
from .threads import write_chart

THREAD = {"color": "#1f2a44", "thread": {"description": "Dark thread on light fabric (any 40 wt)"}}
SCALE_CORNER = (-45., 35.)  # The 10 mm scale square occupies x -45..-35, y 35..45.


def _normalized(points, **settings):
    from .model import placed_object
    return placed_object(points, color=THREAD["color"], thread=dict(THREAD["thread"]), **settings)


def _resample(points, step):
    out = [points[0]]
    for a, b in zip(points, points[1:]):
        count = max(1, math.ceil(math.dist(a, b) / step))
        out += [(a[0] + (b[0] - a[0]) * i / count, a[1] + (b[1] - a[1]) * i / count) for i in range(1, count + 1)]
    return out


def satin(centerline, width, name, **settings):
    """A satin column of constant width along a polyline centerline."""
    from .satin_geometry import centerline_rails
    return _normalized(centerline_rails(centerline, width), name=name, kind="satin", stitch_type="satin", **settings)


def rectangle(cx, cy, w, h, name, **settings):
    obj = DesignObject(name=name, kind="rectangle", x=cx, y=cy, width=w, height=h,
                       color=THREAD["color"], thread=dict(THREAD["thread"]))
    for key, value in settings.items():
        setattr(obj, key, value)
    return obj


def ellipse(cx, cy, d, name, **settings):
    return rectangle(cx, cy, d, d, name, kind="ellipse", **settings)


def running_line(points, name, **settings):
    return _normalized(points, name=name, kind="path", stitch_type="running", **settings)


def manual_line(start, end, span, name):
    """Straight sewn line whose stitches are exactly ``span`` mm apart.

    The line stops at the last whole span before ``end``.
    """
    length = math.dist(start, end)
    count = max(1, math.floor(length / span + 1e-9))
    ux, uy = (end[0] - start[0]) / length, (end[1] - start[1]) / length
    rows = [[start[0], start[1], "jump"]] + [[start[0] + ux * span * i, start[1] + uy * span * i, "stitch"] for i in range(count + 1)]
    return manual_object(DesignObject(name=name, color=THREAD["color"], thread=dict(THREAD["thread"])), rows)


def scale_square():
    """10 mm running square with a crosshair, for measuring photos and scans."""
    x, y = SCALE_CORNER
    square = _normalized([(x, y), (x + 10, y), (x + 10, y + 10), (x, y + 10)], name="Scale: 10 mm square",
                         kind="polygon", stitch_type="running", stitch_length=2)
    cross_a = running_line([(x + 5, y + 2), (x + 5, y + 8)], "Scale: crosshair", stitch_length=2)
    cross_b = running_line([(x + 2, y + 5), (x + 8, y + 5)], "Scale: crosshair", stitch_length=2)
    return [square, cross_a, cross_b]


def test(obj, **target):
    return obj, target


# --- Coupons ---------------------------------------------------------------

SATIN_WIDTHS = [.4, .5, .6, .8, 1., 1.5, 2., 3., 4., 5., 6.]


def satin_width():
    tests, x = [], -40.
    for width in SATIN_WIDTHS:
        cx = x + width / 2
        tests.append(test(satin([(cx, -42), (cx, -20)], width, f"Straight {width:g} mm"), shape="straight", width_mm=width))
        # Gentle S-curve: 2 mm side-to-side over 22 mm.
        wave = [(cx + 2 * math.sin(i / 20 * 2 * math.pi), -15 + i * 1.1) for i in range(21)]
        tests.append(test(satin(wave, width, f"Gentle curve {width:g} mm"), shape="gentle curve", width_mm=width))
        x += width + 4
    # Tight bends: up 8 mm, a 90° right turn on a 4 mm centerline radius, then right 6 mm.
    for index, width in enumerate([1., 2., 3., 4., 5.]):
        cx = -30 + index * 16
        arc = [(cx + 4 - 4 * math.cos(a / 20 * math.pi / 2), 22 - 4 * math.sin(a / 20 * math.pi / 2)) for a in range(21)]
        bend = [(cx, 30)] + arc + [(cx + 10, 18)]
        tests.append(test(satin(bend, width, f"Tight bend {width:g} mm"), shape="tight bend", width_mm=width))
    return "Satin width", tests, ("Narrow satins can look like a running line; wide ones can snag or pucker. "
                                  "Record the narrowest column that still looks like satin, and any that pucker.")


def pull_compensation():
    tests = []
    for index, comp in enumerate([0., .1, .2, .3, .4, .5]):
        cx = -35 + index * 14
        tests.append(test(satin([(cx, -40), (cx, -5)], 3, f"Satin 3 mm, compensation {comp:g} mm", pull_compensation=comp),
                          stitch="satin", designed_width_mm=3, compensation_mm=comp))
        tests.append(test(rectangle(cx, 12, 10, 10, f"Fill 10 mm, compensation {comp:g} mm", pull_compensation=comp),
                          stitch="fill", designed_width_mm=10, compensation_mm=comp))
    return "Pull compensation", tests, ("Fabric pulls stitches narrower than designed. Measure each finished width "
                                        "across the stitches: the best compensation gives the designed width.")


def fill_density():
    tests = []
    for index, spacing in enumerate([.3, .35, .4, .45, .5, .6]):
        row, column = divmod(index, 3)
        tests.append(test(rectangle(-25 + column * 28, -22 + row * 30, 22, 22, f"Row spacing {spacing:g} mm", spacing=spacing),
                          row_spacing_mm=spacing))
    return "Fill density", tests, "Look for fabric showing through (too sparse) and stiffness or puckering (too dense)."


def fill_angles():
    tests = []
    for index, angle in enumerate([0, 30, 45, 60, 90]):
        row, column = divmod(index, 3)
        tests.append(test(rectangle(-25 + column * 28, -22 + row * 30, 22, 22, f"Fill angle {angle}°", angle=angle), angle_deg=angle))
    return "Fill angles", tests, "Fabric pulls more along some directions. Measure each square's width and height."


def underlay():
    tests = []
    for index, (label, enabled, style) in enumerate([("none", False, "auto"), ("center run", True, "auto"),
                                                    ("zigzag", True, "zigzag"), ("center run + zigzag", True, "center_zigzag")]):
        cx = -30 + index * 18
        tests.append(test(satin([(cx, -40), (cx, -10)], 4, f"Satin, {label} underlay", underlay=enabled, underlay_style=style),
                          stitch="satin", underlay=label))
    for index, (label, enabled, style) in enumerate([("none", False, "auto"), ("edge run", True, "edge"),
                                                    ("sparse fill", True, "sparse"), ("edge + sparse", True, "edge_sparse")]):
        cx = -30 + index * 18
        tests.append(test(rectangle(cx, 15, 15, 15, f"Fill, {label} underlay", underlay=enabled, underlay_style=style),
                          stitch="fill", underlay=label))
    return "Underlay", tests, "Underlay supports the top stitches. Compare edge sharpness and how flat each piece lies."


def small_fills():
    tests = []
    for index, area in enumerate([1, 2, 4, 9, 16, 25]):
        cx = -35 + index * 14
        side = math.sqrt(area)
        tests.append(test(rectangle(cx, -20, side, side, f"Square {area} mm²"), shape="square", area_mm2=area))
        diameter = 2 * math.sqrt(area / math.pi)
        tests.append(test(ellipse(cx, 10, diameter, f"Circle {area} mm²"), shape="circle", area_mm2=area))
    return "Small fills", tests, "Record the smallest square and circle that still keep their shape."


def stitch_length():
    tests = []
    for index, span in enumerate([4, 6, 8, 10, 12]):
        y = -40 + index * 14
        tests.append(test(manual_line((-30, y), (40, y), span, f"Stitches {span} mm long"), stitch_length_mm=span))
    return "Stitch length", tests, "Long stitches can snag or lie loose. Note which lengths lie flat and tight."


def tiny_stitches():
    tests = []
    for index, span in enumerate([.1, .2, .3, .5, .8, 1.]):
        y = -40 + index * 12
        tests.append(test(manual_line((-30, y), (10, y), span, f"Stitches {span:g} mm long"), stitch_length_mm=span))
    return "Tiny stitches", tests, ("Very short stitches can break thread or pile up. "
                                    "Note thread breaks, nests and where stitches stop looking even.")


def layering():
    tests = []
    angles = [45, -45, 0, 90]
    for layers in range(1, 5):
        cx = -30 + (layers - 1) * 22
        for layer in range(layers):
            tests.append(test(rectangle(cx, -20, 16, 16, f"{layers}-layer stack, layer {layer + 1}", angle=angles[layer]),
                              layers=layers, layer=layer + 1))
        stack = [satin([(cx - 6, 10), (cx + 6, 10)], 4, f"{layers}-layer satin stack, layer {n + 1}") for n in range(layers)]
        tests += [test(obj, layers=layers, layer=n + 1, stitch="satin") for n, obj in enumerate(stack)]
    return "Layering", tests, "Record where stacked layers pucker, break thread or strike the needle plate."


def jumps():
    tests = []
    for row, (label, trim) in enumerate([("no trim", False), ("trimmed", True)]):
        y = -25 + row * 35
        for index, distance in enumerate([5, 10, 20, 30, 40]):
            x = -30 + index * 4
            start = ellipse(x, y - 5, 3, f"Jump {distance} mm, {label}: start", trim_after=trim)
            end = ellipse(x + distance, y + 5 + index * 2, 3, f"Jump {distance} mm, {label}: end")
            tests += [test(start, jump_mm=distance, trim=trim), test(end, jump_mm=distance, trim=trim)]
    return "Jumps and trims", tests, ("Untrimmed jumps leave a thread to cut by hand. Note which lengths your "
                                      "machine trims itself and whether any jump pulls or snags.")


def lettering():
    from .embroidery_fonts import available_fonts, load_font, height_range, make_font_lettering
    preferred = ["geneva_simple", "geneva_rounded", "glacial_tiny", "barstitch_regular", "caffeine_KOR"]
    fonts = [f[0] for f in available_fonts()]
    font_id = next((f for f in preferred if f in fonts), fonts[0] if fonts else None)
    if font_id is None:
        raise RuntimeError("No embroidery fonts are installed; the lettering coupon needs one.")
    font = load_font(font_id)
    low, high = height_range(font)
    tests = []
    # Heights outside the font's digitized range are clamped to it, then deduplicated.
    heights = sorted({round(min(max(target, low), high), 1) for target in (6, 8, 10, 15)})
    top = -45.
    for height in heights:
        left = -45.
        line_height = 0.
        for case, text in (("capitals", "HAMB"), ("lowercase", "aegbo")):
            obj = make_font_lettering(text, font_id, height)
            if left > -45 and left + obj.width > 45:
                # Wrap to a new line when both words do not fit side by side.
                top += line_height + 4
                left, line_height = -45., 0.
            obj.color, obj.thread = THREAD["color"], dict(THREAD["thread"])
            obj.name = f"{font['name']} {height:g} mm {case}"
            obj.x, obj.y = left + obj.width / 2, top + obj.height / 2
            left += obj.width + 5
            line_height = max(line_height, obj.height)
            tests.append(test(obj, font=font["name"], height_mm=height, case=case))
        top += line_height + 4
    if top > 33:
        raise RuntimeError(f"{font['name']} lettering does not fit the coupon field.")
    return "Lettering", tests, "Record the smallest height at which counters (the holes in a, e, g, b, o) stay open."


def branch_joins():
    from .sewout_pack import build_project
    project, cells = build_project()
    # The shared branch pack has its own thread description. Use the coupon's
    # identity so its scale marker does not introduce a same-colour change.
    for obj in project.objects:
        obj.color=THREAD['color'];obj.thread=dict(THREAD['thread'])
    by_label = {c["cell"]: c for c in cells}
    tests = [test(obj, cell=obj.name.split()[0], shape=by_label[obj.name.split()[0]]["shape"],
                  join_overlap_mm=by_label[obj.name.split()[0]]["join_overlap_mm"]) for obj in project.objects]
    return "Branch joins", tests, "Look for gaps or ridges where branch pieces meet; compare exact, 0.3 and 0.6 mm joins."


def fabric_profiles():
    from .fabric import PROFILES,apply_fabric
    tests=[]
    for index,(name,values) in enumerate(PROFILES.items()):
        spacing,pull,style,inset,support=values
        settings=dict(spacing=spacing,pull_compensation=pull,underlay_style=style,
                      underlay_inset=inset,underlay_spacing=support)
        x=-30+30*index
        fill=rectangle(x,-22,20,20,f'{name}: fill',angle=0)
        column=satin([(x,-2),(x,23)],4,f'{name}: satin')
        project,_=apply_fabric(Project(objects=[fill,column]),{fill.id,column.id},settings)
        for obj in project.objects:
            tests.append(test(obj,profile=name,stitch_type=obj.stitch_type,
                              nominal_width_mm=20 if obj.stitch_type=='fill' else 4,
                              nominal_height_mm=20 if obj.stitch_type=='fill' else 25,
                              spacing_mm=obj.spacing,pull_compensation_per_side_mm=obj.pull_compensation,
                              underlay_style=obj.underlay_style,underlay_inset_mm=obj.underlay_inset,
                              underlay_spacing_mm=obj.underlay_spacing))
    return 'Fabric profile comparison',tests,('Compare all three experimental recipes on the same fabric and stabilizer. '
        'Columns left to right: stable woven, stretch knit, textured/pile. Top: fill; bottom: 4 mm satin. '
        'Record measured width/height, coverage gaps, puckering, thread breaks and support showing. '
        'This compares bundled recipes, not isolated variables; none is physically calibrated.')


def ripple_spacing():
    tests=[]
    for row,offset in enumerate((0,-60)):
        for column,spacing in enumerate((.5,1.,2.)):
            obj=rectangle(-30+30*column,-22+32*row,20,20,
                f'Ripple {spacing:g} mm, center X {offset}%',kind='compound',stitch_type='ripple',
                spacing=spacing,underlay=False,minimum_stitch=.3,ripple_center_x=offset,
                contours=[[[-.5,-.5],[.5,-.5],[.5,.5],[-.5,.5]],
                          [[-.1,-.1],[.1,-.1],[.1,.1],[-.1,.1]]])
            tests.append(test(obj,stitch_type='ripple',nominal_width_mm=20,nominal_height_mm=20,
                cutout_width_mm=4,cutout_height_mm=4,spacing_mm=spacing,
                ripple_center_x_percent=offset,ripple_center_y_percent=0,
                minimum_stitch_mm=.3,stitch_length_mm=obj.stitch_length,underlay=False))
    return 'Ripple spacing and center',tests,('Columns left to right: 0.5, 1 and 2 mm row spacing. '
        'Top row: centered circles; bottom row: center offset -60% of width. Each sample is 20 mm square '
        'with a 4 mm square cutout. Underlay is off; short-stitch cleanup is 0.3 mm. '
        'Compare spacing within each row and center position within each column. Record row separation, '
        'cutout clearance, puckering and thread breaks. These are decorative open fills, not solid coverage targets.')


def satin_corners():
    """Sharp satin corners, which Morale sews as fans around the inner corner."""
    tests=[]
    for row,width in enumerate((2.,4.)):
        for column,angle in enumerate((120,90,60,45,30)):
            half=math.radians(angle)/2;leg=12 if angle>=60 else 14
            tip=(-32+16*column,-4+32*row)
            line=[(tip[0]-leg*math.sin(half),tip[1]-leg*math.cos(half)),tip,(tip[0]+leg*math.sin(half),tip[1]-leg*math.cos(half))]
            obj=satin(line,width,f'Corner {angle}°, {width:g} mm')
            tests.append(test(obj,shape='corner',corner_angle_degrees=angle,width_mm=width,
                              leg_length_mm=leg,underlay_style=obj.underlay_style))
    return 'Satin corners',tests,('Each V is one satin column turning a sharp corner. Morale sews the inside of the '
        'corner as a fan around one point, shortening alternate stitches there so thread does not pile up. '
        'Top row 2 mm wide, bottom row 4 mm; corners 120° to 30° left to right. Look for a lump, hole or '
        'thread break at the inner point, gaps at the outer edge, and puckering. These treatments are not yet '
        'physically validated.')


COUPONS = {
    "satin-width": satin_width, "pull-compensation": pull_compensation, "fill-density": fill_density,
    "fill-angles": fill_angles, "underlay": underlay, "small-fills": small_fills, "stitch-length": stitch_length,
    "tiny-stitches": tiny_stitches, "layering": layering, "jumps": jumps, "lettering": lettering,
    "branch-joins": branch_joins, "fabric-profiles": fabric_profiles, "ripple-spacing": ripple_spacing,
    "satin-corners": satin_corners,
}


def build_project(name):
    from .trace_finishing import finish_regions
    title, tests, guidance = COUPONS[name]()
    project = Project(name=f"Morale coupon: {title}", hoop_width=100, hoop_height=100)
    project.objects = scale_square() + [obj for obj, _ in tests]
    if name not in {"jumps", "branch-joins"}:
        # Tie each object in and off and trim between them so travel does not cross the tests.
        project, _ = finish_regions(project, threshold=5, internal=False)
    Project.loads(project.dumps())
    return project, tests, title, guidance


METADATA = {
    "id": "", "morale_version": "", "design": "", "export_format": "",
    "machine": {"manufacturer": "", "model": ""}, "hoop": "",
    "needle": {"type": "", "size": ""},
    "upper_thread": {"brand": "", "weight": "", "material": ""},
    "bobbin_thread": {"brand": "", "weight": ""},
    "fabric": {"type": "", "weight_gsm": None, "stretch": ""},
    "stabilizer": {"type": "", "layers": 1},
    "machine_speed_spm": None, "date": "", "notes": "",
}


def project_evaluation_pdf(project,path):
    """Record the current editable settings, never regenerated coupon defaults."""
    snapshot=project.dumps();project=Project.loads(snapshot)
    sewn={}
    for block in generate(project):
        sewn.setdefault(block.object_id,[]).extend((s.x,s.y) for s in block.stitches if s.command=='stitch')
    tests=[]
    for obj in project.objects:
        if not obj.visible:continue
        target=dict(object_id=obj.id,stitch_type=obj.stitch_type,width_mm=obj.width,height_mm=obj.height,
                    rotation_degrees=obj.rotation,thread_color=obj.color)
        points=sewn.get(obj.id,[])
        target['needle_penetrations']=len(points)
        if points:
            xs,ys=zip(*points)
            target.update(generated_width_mm=round(max(xs)-min(xs),4),generated_height_mm=round(max(ys)-min(ys),4))
        if obj.stitch_type!='manual':target['stitch_length_mm']=obj.stitch_length
        if obj.stitch_type=='ripple':
            target.update(ripple_center_x_percent=obj.ripple_center_x,ripple_center_y_percent=obj.ripple_center_y)
        if obj.stitch_type=='fill':
            target['fill_angle_degrees']=obj.angle
            if obj.density_gradient:
                target.update(gradient_end_spacing_mm=obj.gradient_end_spacing,gradient_reverse=obj.gradient_reverse)
        if obj.stitch_type in {'fill','satin','contour','ripple'}:
            target.update(spacing_mm=obj.spacing,underlay=obj.underlay)
            if obj.underlay:target.update(underlay_style=obj.underlay_style,underlay_inset_mm=obj.underlay_inset,
                                         underlay_spacing_mm=obj.underlay_spacing)
        if obj.stitch_type in {'fill','satin'}:target['pull_compensation_per_side_mm']=obj.pull_compensation
        tests.append((obj,target))
    if not tests:raise ValueError('The design has no included objects to evaluate.')
    digest=hashlib.sha256(snapshot.encode('utf-8')).hexdigest()
    evaluation_pdf(path,project.name,tests,
        f'Current design settings. Width/height describe source geometry before rotation and compensation. '
        f'Generated dimensions are axis-aligned bounds of needle penetrations, including underlay and ties, before machine export. '
        f'Record physical measurements after sewing. Project snapshot SHA-256: {digest}'
        +(f'\n\nDesign notes (saved with project):\n{project.notes}' if project.notes else ''))


def evaluation_pdf(path,title,tests,guidance):
    """Publish a complete PDF without damaging an existing evaluation sheet."""
    path=Path(path);temporary=None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent,suffix='.pdf',delete=False) as stream:
            temporary=Path(stream.name)
        _render_evaluation_pdf(temporary,title,tests,guidance)
        with temporary.open('rb') as stream:
            header=stream.read(5)
            stream.seek(max(0,temporary.stat().st_size-1024))
            tail=stream.read()
        if header!=b'%PDF-' or b'%%EOF' not in tail:
            raise OSError('Could not create a complete sewout evaluation PDF.')
        os.replace(temporary,path)
    finally:
        if temporary is not None:temporary.unlink(missing_ok=True)


def _render_evaluation_pdf(path,title,tests,guidance):
    """Printable blank observations, separate from actual-size placement pages."""
    from PySide6.QtGui import QTextDocument,QPdfWriter,QPageSize,QPainter
    from PySide6.QtCore import QRectF,Qt
    writer=QPdfWriter(str(path));writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setResolution(96);writer.setTitle(f'{title} — sewout evaluation')
    rows=[]
    for obj,target in tests:
        details='<br>'.join(f'{escape(key.replace("_"," "))}: {escape(str(value))}' for key,value in target.items())
        rows.append(f'<tr><td>{escape(obj.name)}<br><small>{details}</small></td>'
                    '<td>Width: __________ mm<br>Height: __________ mm<br>Status: __________<br><br>'
                    'Coverage / gaps: __________________<br>Puckering / support showing: __________<br>'
                    'Thread breaks: ______<br>Notes: __________________________</td></tr>')
    guidance_html=escape(guidance).replace('\n','<br>')
    html=('<html><head><style>body {font-size:10pt} td {padding:8px} small {font-size:8pt}</style></head><body>'
        f'<h2>{escape(title)} — sewout evaluation</h2><p>{guidance_html}</p>'
        '<p>Run/date: __________________ Machine/model: __________________<br>'
        'Export filename: __________________ Hoop: __________________<br>'
        'Fabric: __________________ Stabilizer/layers: __________________<br>'
        'Thread/needle: __________________ Speed: __________________<br>'
        'Front/back photo filenames: __________________________________</p>'
        '<p>Record observations after sewing. Blank fields are not passing results. '
        'Use the separate placement sheet for actual-size alignment.</p>'
        '<table border="1" cellspacing="0" width="100%"><thead>'
        f'<tr><th colspan="2">{escape(title)}<br>Run/date: __________________</th></tr>'
        '<tr><th width="48%">Sample and target</th>'
        '<th>Measured result / notes</th></tr></thead>'+''.join(rows)+'</table></body></html>')
    prefix,table=html.split('<table',1)
    header='<table'+table.split('</thead>',1)[0]+'</thead>'
    style=prefix.split('<body>',1)[0]+'<body>'
    def document(content):
        result=QTextDocument();result.setHtml(content)
        result.setTextWidth(writer.width())
        return result
    intro=document(prefix+'</body></html>')
    heading=document(style+header+'</table></body></html>')
    documents=[document(style+'<table border="1" cellspacing="0" width="100%">'+
                        row.replace('<td>','<td width="48%">',1)+'</table></body></html>') for row in rows]
    painter=QPainter()
    if not painter.begin(writer):raise OSError('Could not create the evaluation PDF.')
    bottom=writer.height()-24;y=0;page=1
    if heading.size().height()>=bottom:
        painter.end()
        raise ValueError('Evaluation title is too long to fit on a page.')
    def draw(doc,offset=0,height=None):
        nonlocal y
        height=doc.size().height()-offset if height is None else height
        painter.save();painter.setClipRect(QRectF(0,y,writer.width(),height))
        painter.translate(0,y-offset);doc.drawContents(painter);painter.restore();y+=height
    def new_page():
        nonlocal y,page
        painter.drawText(QRectF(0,bottom,writer.width(),24),Qt.AlignmentFlag.AlignRight,str(page))
        if not writer.newPage():raise OSError('Could not create an evaluation page.')
        page+=1;y=0;draw(heading)
    try:
        # Unusually long introductory text may span pages, too.
        offset=0
        while offset<intro.size().height():
            height=min(bottom-y,intro.size().height()-offset)
            if height<=0:new_page();continue
            draw(intro,offset,height);offset+=height
        if y+heading.size().height()>bottom:new_page()
        else:draw(heading)
        for doc in documents:
            if y+doc.size().height()>bottom:new_page()
            offset=0
            while offset<doc.size().height():
                height=min(bottom-y,doc.size().height()-offset)
                if height<=0:raise ValueError('Evaluation heading leaves no space for sample rows.')
                draw(doc,offset,height);offset+=height
                if offset<doc.size().height():new_page()
        painter.drawText(QRectF(0,bottom,writer.width(),24),Qt.AlignmentFlag.AlignRight,str(page))
    finally:painter.end()


def build_coupon(name, destination):
    root = Path(destination)
    if name not in COUPONS:raise ValueError('Unknown sewout coupon.')
    root.mkdir(parents=True, exist_ok=False)
    incomplete=root/'INCOMPLETE.txt'
    incomplete.write_text('This sewout pack did not finish exporting. Do not use its machine files for sewing. Generate a new pack in another folder.\n',encoding='utf-8')
    project, tests, title, guidance = build_project(name)
    blocks = generate(project)
    project.save(root / f"{name}.morale")
    files = []
    verification = {}
    for filename, options in [(f"{name}.pes", {}), (f"{name}-v1.pes", {"pes_version": 1}), (f"{name}.exp", {}), (f"{name}.dst", {})]:
        export_machine(project, root / filename, blocks, **options)
        files.append(filename)
        try:verification[filename]=verify_export(blocks,root/filename)
        except Exception as exc:
            verification[filename]={'verified':False,'problems':[f'Export verification could not complete: {exc}']}
    export_template(project, root / "placement.pdf")
    evaluation_pdf(root/'evaluation.pdf',title,tests,guidance)
    with (root / "thread-chart.csv").open("w", encoding="utf-8", newline="") as stream:
        write_chart(project, blocks, stream)
    stitches = [s for block in blocks for s in block.stitches if s.command == "stitch"]
    bounds = [round(min(s.x for s in stitches), 2), round(min(s.y for s in stitches), 2),
              round(max(s.x for s in stitches), 2), round(max(s.y for s in stitches), 2)]
    metadata = dict(METADATA, id=f"{name}-001", morale_version=__version__, design=f"{name}.morale")
    (root / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    evaluation = {"coupon": name, "morale_version": __version__, "statuses": ["pass", "marginal", "fail"],
                  "objects": [{"object": obj.name, "target": target, "status": None, "measured": {}, "notes": ""}
                              for obj, target in tests]}
    (root / "evaluation.json").write_text(json.dumps(evaluation, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report = {"coupon": name, "title": title, "morale_version": __version__, "field_mm": [100, 100],
              "sewn_bounds_mm": bounds, "stitches": len(stitches), "objects": len(project.objects),
              "files": files, "physical_sewouts": False,
              "export_verification": verification,
              "exports_sha256": {filename:hashlib.sha256((root/filename).read_bytes()).hexdigest() for filename in files}}
    (root / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (root / "README.txt").write_text(README.format(title=title, name=name, guidance=guidance,
                                                   verification='\n\n'.join(verification_text(result,filename) for filename,result in verification.items()),
                                                   objects="\n".join(f"  - {obj.name}" for obj, _ in tests)), encoding="utf-8")
    incomplete.unlink()
    return report


README = """Morale sew-out coupon: {title}
{guidance}

Test objects, in sewing order:
{objects}

The 10 mm square with a crosshair in the lower-left corner is for measuring
photos and scans.

Files
-----
{name}.pes / {name}-v1.pes   PES candidates for Brother testing
{name}.exp                   EXP candidate for Bernina testing
{name}.dst                   DST alternative (no colour information)
{name}.morale                Editable Morale project
placement.pdf                Actual-size template; print at 100% and check its ruler
metadata.json                Fill in: machine, needle, threads, fabric, stabilizer
evaluation.json              Fill in: pass / marginal / fail and measurements per object
evaluation.pdf               Printable blank observations and target settings
report.json                  Software export checks and machine-file SHA-256 hashes

Export checks
-------------
{verification}

Confirm format and hoop support for the exact machine model. These software
checks do not establish physical machine compatibility or sew-out quality.

How to record a result
----------------------
1. Sew the coupon without changing settings on the machine.
2. Photograph or scan the front (and back) square-on, with the scale square visible.
3. Fill in metadata.json and evaluation.json.
4. Keep the photo, both JSON files and the machine file you sewed together in one
   folder. See docs/SEWOUT_VALIDATION.md.

This design is generated by software. Watch the first run and stop the machine if
the thread nests or the needle strikes.
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, help="Folder to create; each coupon gets a subfolder")
    parser.add_argument("--coupon", action="append", choices=sorted(COUPONS), help="Coupon to build (repeatable; default all)")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--require-verification", action="store_true", help="Exit nonzero if any export needs review; retain generated files")
    args = parser.parse_args()
    if args.list or not args.output:
        for name in COUPONS:
            print(name)
        return
    args.output.mkdir(parents=True, exist_ok=True)
    review=False
    for name in args.coupon or COUPONS:
        report = build_coupon(name, args.output / name)
        print(f"{name}: {report['objects']} objects, {report['stitches']} stitches, bounds {report['sewn_bounds_mm']}")
        for filename,result in report['export_verification'].items():
            passed=result.get('verified') is True
            review=review or not passed
            print(f"  {filename}: {'CHECKS PASSED' if passed else 'REVIEW NEEDED'}")
            for problem in result.get('problems',[]):print(f'    {problem}')
    return 1 if args.require_verification and review else 0


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    application = QApplication.instance() or QApplication([])
    raise SystemExit(main())
