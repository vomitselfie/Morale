"""Physical test pack for branch splitting and join overlap on real machines."""
import argparse
import json
import math
from pathlib import Path

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QPainterPath, QPainterPathStroker

from .model import Project, DesignObject
from .branch_regions import split_branches
from .auto_digitize import choose_stitches
from .trace_finishing import finish_regions
from .engine import generate
from .formats import export_machine
from .templates import export_template
from .threads import write_chart

CELL = 30
THREAD = {"color": "#1f2a44", "thread": {"description": "Dark navy (any 40 wt)"}}


def _polygon(path, name):
    ring = [(p.x(), p.y()) for p in path.simplified().toFillPolygons()[0]]
    if ring[0] == ring[-1]:
        ring.pop()
    xs, ys = zip(*ring)
    cx, cy, w, h = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, max(xs) - min(xs), max(ys) - min(ys)
    return DesignObject(name=name, kind="polygon", width=w, height=h, color=THREAD["color"], thread=dict(THREAD["thread"]),
                        points=[[(x - cx) / w, (y - cy) / h] for x, y in ring])


def _strokes(segments, width, rotation=0):
    path = QPainterPath()
    c, s = math.cos(math.radians(rotation)), math.sin(math.radians(rotation))
    for segment in segments:
        line = QPainterPath()
        points = [(x * c - y * s, x * s + y * c) for x, y in segment]
        line.moveTo(*points[0])
        for point in points[1:]:
            line.lineTo(*point)
        stroker = QPainterPathStroker()
        stroker.setWidth(width)
        stroker.setCapStyle(Qt.PenCapStyle.FlatCap)
        stroker.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
        path = path.united(stroker.createStroke(line))
    return path


def _radial(count, length, offset):
    return [[(0, 0), (length * math.cos(2 * math.pi * k / count + offset), length * math.sin(2 * math.pi * k / count + offset))]
            for k in range(count)]


def _leaf():
    leaf = QPainterPath()
    leaf.addEllipse(QPointF(0, -5), 5, 7.5)
    stroker = QPainterPathStroker()
    stroker.setWidth(1.6)
    stem = QPainterPath()
    stem.moveTo(0, 1.5)
    stem.lineTo(0, 11)
    return leaf.united(stroker.createStroke(stem))


def _tee():
    return _strokes([[(-10, -8), (10, -8)], [(0, -8), (0, 11)]], 2.6)


# Each shape fits a 30 mm cell. Rotations keep arms off the machine axes, where
# straight cuts would already work, so the crotch-chord planner is exercised.
SHAPES = {
    "Y": lambda: _strokes(_radial(3, 11, math.pi / 2), 3, 17),
    "K": lambda: _strokes([[(0, -11), (0, 11)], [(0, 1), (7, -10)], [(2, -1), (7, 10)]], 2.4, 8),
    "Star": lambda: _strokes(_radial(5, 11, 0), 2.6, 17),
    "T": _tee,
    "Leaf": _leaf,
}

# (shape, join overlap mm) in sewing order, left to right, top to bottom.
LAYOUT = [
    ("Y", 0), ("Y", .3), ("Y", .6),
    ("K", 0), ("K", .3), ("Star", .3),
    ("T", .3), ("Leaf", .3), ("Star", 0),
]

CHECKS = {
    "Y": "One arm meets a satin that bends through the junction. Look for a gap or a hump at the cut.",
    "K": "Two arms join the upright. Check the crotches for gaps and the bend in the upright for fanning.",
    "Star": "Arms join a central piece. Check the hub for bunching where several columns meet.",
    "T": "Stem meets the bar along part of its edge (T-junction). Check for a gap under the bar.",
    "Leaf": "Satin stem joins a fill body. Check the stem does not pull away from the fill edge.",
}


def build_project():
    project = Project(name="Branch join sew-out", hoop_width=100, hoop_height=100)
    cells = []
    for index, (shape, overlap) in enumerate(LAYOUT):
        row, column = divmod(index, 3)
        label = f"{chr(65 + row)}{column + 1}"
        source = _polygon(SHAPES[shape](), f"{label} {shape}")
        source.x, source.y = (column - 1) * CELL, (row - 1) * CELL
        split, notes = split_branches(Project(objects=[source]), overlap)
        planned, decisions = choose_stitches(split)
        if not notes:
            raise RuntimeError(f"{label} {shape} did not split; the pack would not test branch joins.")
        for piece_number, obj in enumerate(planned.objects, 1):
            obj.name = f"{label} {shape} · piece {piece_number}"
        project.objects.extend(planned.objects)
        cells.append({"cell": label, "shape": shape, "join_overlap_mm": overlap, "pieces": notes[0]["pieces"],
                      "joins": notes[0]["joins"], "overlapped_joins": notes[0]["overlapped_joins"],
                      "stitch_types": [d["selected"] for d in decisions], "check": CHECKS[shape]})
    # Tie in/off each piece and trim between cells so travel does not cross the test.
    project, _ = finish_regions(project, threshold=5, internal=False)
    Project.loads(project.dumps())
    return project, cells


README = """Morale branch-join sew-out
==========================

One thread colour, 100 x 100 mm field. Nine 30 mm cells, sewn left to right,
top to bottom:

{table}

Files
-----
branch-sewout.pes      Brother, PES v6 (most machines since about 2008)
branch-sewout-v1.pes   Brother, PES v1 (try this if the v6 file is refused)
branch-sewout.exp      Bernina EXP
branch-sewout.dst      Tajima DST (read by most machines; no colour information)
branch-sewout.morale   Editable Morale project
placement.pdf          Actual-size template. Print at 100% and measure its 50 mm ruler.
thread-chart.csv       Colour sequence and stitch counts
report.json            What was generated for each cell

How to sew
----------
1. Medium-weight woven cotton, one layer of tear-away or cut-away stabilizer,
   hooped firmly. Contrasting thread (e.g. dark on light fabric) shows gaps best.
2. Use the machine's 100 x 100 mm (4 x 4 in) hoop or larger.
3. Sew the whole design without adjusting settings on the machine.

What to record
--------------
For each cell: any gap at the cuts (fabric showing), any ridge where pieces
overlap, and bunching at junctions. Compare A1 (exact joins), A2 (0.3 mm) and
A3 (0.6 mm); B1/B2 and C3/B3 repeat the comparison for K and the star.
Note the machine model, hoop, fabric, stabilizer and thread. A photo of the
back and front, taken square-on with a ruler, is the most useful result.

This design is generated by software and has not been sewn before. Watch the
first run and stop the machine if the thread nests or the needle strikes.
"""


def build_pack(destination):
    root = Path(destination)
    root.mkdir(parents=True, exist_ok=False)
    project, cells = build_project()
    blocks = generate(project)
    project.save(root / "branch-sewout.morale")
    exports = {}
    for name, options in [("branch-sewout.pes", {}), ("branch-sewout-v1.pes", {"pes_version": 1}),
                          ("branch-sewout.exp", {}), ("branch-sewout.dst", {})]:
        export_machine(project, root / name, blocks, **options)
        exports[name] = (root / name).stat().st_size
    export_template(project, root / "placement.pdf")
    with (root / "thread-chart.csv").open("w", encoding="utf-8", newline="") as stream:
        write_chart(project, blocks, stream)
    stitches = [s for block in blocks for s in block.stitches if s.command == "stitch"]
    xs, ys = [s.x for s in stitches], [s.y for s in stitches]
    report = {"design": project.name, "field_mm": [project.hoop_width, project.hoop_height],
              "sewn_bounds_mm": [round(min(xs), 2), round(min(ys), 2), round(max(xs), 2), round(max(ys), 2)],
              "stitches": len(stitches), "cells": cells, "exports_bytes": exports,
              "physical_sewouts": False, "machine_validated": False}
    (root / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    table = "\n".join(f"  {c['cell']}  {c['shape']:<5} overlap {c['join_overlap_mm']:.1f} mm  "
                      f"{c['pieces']} pieces, {c['overlapped_joins']}/{c['joins']} joins overlapped" for c in cells)
    (root / "README.txt").write_text(README.format(table=table), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New folder to create for the pack")
    report = build_pack(parser.parse_args().output)
    print(json.dumps({k: report[k] for k in ("stitches", "sewn_bounds_mm")}, indent=2))
    for cell in report["cells"]:
        print(f"{cell['cell']} {cell['shape']:<5} {cell['join_overlap_mm']} mm  {cell['pieces']} pieces  "
              f"{cell['overlapped_joins']}/{cell['joins']} joins  {','.join(cell['stitch_types'])}")


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    application = QApplication.instance() or QApplication([])
    main()
