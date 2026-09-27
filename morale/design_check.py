"""Design checks: structured, non-destructive review of a design before sewing.

Each check reports ``DesignIssue`` records tied to an object or position where
possible. Checks never change the design. Thresholds marked provisional are
starting points until sew-out results (docs/SEWOUT_VALIDATION.md) support them.
"""
from dataclasses import dataclass, field
import math
from typing import Any

# Provisional thresholds (millimetres), shared with fabric guidance where possible.
LONG_STITCH_MM = 7.
LONG_JUMP_MM = 10.
MIN_SATIN_MM = 1.
MIN_FILL_MM2 = 4.
MAX_LAYERS = 3
HIGH_COMMAND_COUNT = 100_000


@dataclass
class DesignIssue:
    severity: str  # "error" blocks export; "warning" deserves a look; "info" reports a passed check.
    code: str
    message: str
    object_id: str | None = None
    position: tuple[float, float] | None = None
    details: dict[str, Any] = field(default_factory=dict)


def _names(project):
    return {obj.id: obj.name for obj in project.objects}


def check_hoop(project, blocks):
    issues = []
    sewn = [s for b in blocks for s in b.stitches]
    if not any(s.command == "stitch" for s in sewn):
        return [DesignIssue("error", "NO_STITCHES", "The design has no stitches to export.")]
    half_w, half_h = project.hoop_width / 2 + .001, project.hoop_height / 2 + .001
    for obj in project.objects:
        if not obj.visible:
            continue
        outside = [p for ring in obj.rings() for p in ring if abs(p[0]) > half_w or abs(p[1]) > half_h]
        if outside:
            issues.append(DesignIssue("error", "OUTSIDE_HOOP",
                                      f"“{obj.name}” extends beyond the {project.hoop_width:g} × {project.hoop_height:g} mm hoop. "
                                      "Move or resize it before export.", obj.id, outside[0]))
    if not issues:
        # Stitches can reach past outlines (compensation, underlay, manual stitches).
        for block in blocks:
            stray = next((s for s in block.stitches if abs(s.x) > half_w or abs(s.y) > half_h), None)
            if stray:
                issues.append(DesignIssue("error", "OUTSIDE_HOOP", "Stitches extend beyond the selected hoop. "
                                          "Move or resize the objects before export.", block.object_id, (stray.x, stray.y)))
                break
    if not issues:
        issues.append(DesignIssue("info", "FITS_HOOP", f"Design fits the {project.hoop_width:g} × {project.hoop_height:g} mm hoop."))
    return issues


def check_spans(project, blocks):
    issues, names = [], _names(project)
    previous, trimmed = None, False  # A trim carries over to the next object's first jump.
    for block in blocks:
        longest, where = 0., None
        # Only travel into an object counts: jumps inside an object are sewn over by
        # that object's own stitches (for example underlay to top fill).
        entering = True
        for stitch in block.stitches:
            point = (stitch.x, stitch.y)
            if stitch.command == "trim":
                trimmed = True
            elif stitch.command in {"stitch", "jump"}:
                length = math.dist(previous, point) if previous is not None else 0.
                if stitch.command == "stitch":
                    if length > longest:
                        longest, where = length, point
                    trimmed = entering = False
                elif entering and length > LONG_JUMP_MM and not trimmed:
                    issues.append(DesignIssue("warning", "LONG_JUMP",
                                              f"Jump of {length:.1f} mm without a trim before “{names.get(block.object_id, 'an object')}”. "
                                              "The loose thread will need cutting by hand.", block.object_id, point,
                                              {"length_mm": round(length, 2)}))
                previous = point
        if longest > LONG_STITCH_MM:
            issues.append(DesignIssue("warning", "LONG_STITCH",
                                      f"“{names.get(block.object_id, 'An object')}” has stitches up to {longest:.1f} mm long, "
                                      f"which can snag (provisional limit {LONG_STITCH_MM:g} mm).", block.object_id, where,
                                      {"length_mm": round(longest, 2)}))
    return issues


def check_details(project, blocks):
    from .coverage_review import detail_measurements
    issues = []
    for detail in detail_measurements(project):
        width, size = detail.get("satin_width_mm"), detail.get("fill_area_mm2")
        if width is not None and width < MIN_SATIN_MM:
            issues.append(DesignIssue("warning", "SATIN_TOO_NARROW",
                                      f"Satin “{detail['name']}” is {width:.2f} mm wide and may sew like a single line "
                                      f"(provisional minimum {MIN_SATIN_MM:g} mm).", detail["object_id"], details={"width_mm": width}))
        if size is not None and size < MIN_FILL_MM2:
            issues.append(DesignIssue("warning", "FILL_TOO_SMALL",
                                      f"Fill “{detail['name']}” covers only {size:.1f} mm² and may lose its shape "
                                      f"(provisional minimum {MIN_FILL_MM2:g} mm²).", detail["object_id"], details={"area_mm2": size}))
    return issues


def check_layers(project, blocks):
    from .coverage_review import measure_layers
    report, _ = measure_layers(project, blocks)
    stacked = [s for s in report["stacked_locations"] if s["layers"] > MAX_LAYERS]
    if not stacked:
        return []
    first = stacked[0]
    return [DesignIssue("warning", "HIGH_LAYER_COVERAGE",
                        f"{first['layers']} layers of stitches overlap near x = {first['x_mm']} mm, y = {first['y_mm']} mm "
                        f"(provisional limit {MAX_LAYERS}). Dense stacks can pucker or break needles.",
                        position=(first["x_mm"] + .5, first["y_mm"] + .5), details={"locations": stacked})]


def check_commands(project, blocks):
    count = sum(len(b.stitches) for b in blocks)
    if count > HIGH_COMMAND_COUNT:
        return [DesignIssue("warning", "COMMAND_COUNT_HIGH",
                            f"{count:,} machine commands: some machines refuse very large designs.", details={"commands": count})]
    return [DesignIssue("info", "COMMAND_COUNT", f"{count:,} machine commands.", details={"commands": count})]


CHECKS = (check_hoop, check_spans, check_details, check_layers, check_commands)


def check_design(project, blocks):
    """All checks, errors first. Never modifies the project."""
    issues = []
    for check in CHECKS:
        issues += check(project, blocks)
        if any(i.code == "NO_STITCHES" for i in issues):
            break
    order = {"error": 0, "warning": 1, "info": 2}
    return sorted(issues, key=lambda issue: order[issue.severity])
