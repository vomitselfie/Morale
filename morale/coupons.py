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
import json
import math
from pathlib import Path

from . import __version__
from .model import Project, DesignObject
from .stitch_edit import manual_object
from .engine import generate
from .formats import export_machine
from .templates import export_template
from .threads import write_chart

THREAD = {"color": "#1f2a44", "thread": {"description": "Dark thread on light fabric (any 40 wt)"}}
SCALE_CORNER = (-45., 35.)  # The 10 mm scale square occupies x -45..-35, y 35..45.


def _normalized(points, **settings):
    xs, ys = zip(*points)
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    w, h = max(.1, max(xs) - min(xs)), max(.1, max(ys) - min(ys))
    obj = DesignObject(x=cx, y=cy, width=w, height=h, color=THREAD["color"], thread=dict(THREAD["thread"]),
                       points=[[(x - cx) / w, (y - cy) / h] for x, y in points])
    for key, value in settings.items():
        setattr(obj, key, value)
    return obj


def _resample(points, step):
    out = [points[0]]
    for a, b in zip(points, points[1:]):
        count = max(1, math.ceil(math.dist(a, b) / step))
        out += [(a[0] + (b[0] - a[0]) * i / count, a[1] + (b[1] - a[1]) * i / count) for i in range(1, count + 1)]
    return out


def satin(centerline, width, name, **settings):
    """A satin column of constant width along a polyline centerline."""
    line = _resample(centerline, .5)
    pairs = []
    for i, (x, y) in enumerate(line):
        a, b = line[max(0, i - 1)], line[min(len(line) - 1, i + 1)]
        length = math.dist(a, b)
        nx, ny = -(b[1] - a[1]) / length, (b[0] - a[0]) / length
        pairs += [(x - nx * width / 2, y - ny * width / 2), (x + nx * width / 2, y + ny * width / 2)]
    return _normalized(pairs, name=name, kind="satin", stitch_type="satin", **settings)


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
    by_label = {c["cell"]: c for c in cells}
    tests = [test(obj, cell=obj.name.split()[0], shape=by_label[obj.name.split()[0]]["shape"],
                  join_overlap_mm=by_label[obj.name.split()[0]]["join_overlap_mm"]) for obj in project.objects]
    return "Branch joins", tests, "Look for gaps or ridges where branch pieces meet; compare exact, 0.3 and 0.6 mm joins."


COUPONS = {
    "satin-width": satin_width, "pull-compensation": pull_compensation, "fill-density": fill_density,
    "fill-angles": fill_angles, "underlay": underlay, "small-fills": small_fills, "stitch-length": stitch_length,
    "tiny-stitches": tiny_stitches, "layering": layering, "jumps": jumps, "lettering": lettering,
    "branch-joins": branch_joins,
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


def build_coupon(name, destination):
    root = Path(destination)
    root.mkdir(parents=True, exist_ok=False)
    project, tests, title, guidance = build_project(name)
    blocks = generate(project)
    project.save(root / f"{name}.morale")
    files = []
    for filename, options in [(f"{name}.pes", {}), (f"{name}-v1.pes", {"pes_version": 1}), (f"{name}.exp", {}), (f"{name}.dst", {})]:
        export_machine(project, root / filename, blocks, **options)
        files.append(filename)
    export_template(project, root / "placement.pdf")
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
              "files": files, "physical_sewouts": False}
    (root / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (root / "README.txt").write_text(README.format(title=title, name=name, guidance=guidance,
                                                   objects="\n".join(f"  - {obj.name}" for obj, _ in tests)), encoding="utf-8")
    return report


README = """Morale sew-out coupon: {title}
{guidance}

Test objects, in sewing order:
{objects}

The 10 mm square with a crosshair in the lower-left corner is for measuring
photos and scans.

Files
-----
{name}.pes / {name}-v1.pes   Brother (try v1 if v6 is refused)
{name}.exp                   Bernina
{name}.dst                   Most other machines (no colour information)
{name}.morale                Editable Morale project
placement.pdf                Actual-size template; print at 100% and check its ruler
metadata.json                Fill in: machine, needle, threads, fabric, stabilizer
evaluation.json              Fill in: pass / marginal / fail and measurements per object

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
    args = parser.parse_args()
    if args.list or not args.output:
        for name in COUPONS:
            print(name)
        return
    args.output.mkdir(parents=True, exist_ok=True)
    for name in args.coupon or COUPONS:
        report = build_coupon(name, args.output / name)
        print(f"{name}: {report['objects']} objects, {report['stitches']} stitches, bounds {report['sewn_bounds_mm']}")


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    application = QApplication.instance() or QApplication([])
    main()
