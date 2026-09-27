"""Reopen an exported machine file with the real reader and compare it to the design.

Formats legitimately quantize positions and may add needle positions to split
long spans, so exact command identity is not required. The comparison reports
counts, thread changes, bounds and sampled path deviation, and flags anything
beyond small tolerances for review. It never blocks or alters the export.
"""
from .comparison import compare_commands
from .engine import generate
from .formats import import_machine
from .path_fidelity import sewn_segments

# Formats store positions in 0.1 mm units; the path comparison allows 0.15 mm,
# and edges may shift slightly more where formats split long spans.
BOUNDS_TOLERANCE_MM = .3
OUTSIDE_LENGTH_MM = 1.


def sewn_extent(blocks):
    """Bounds of everything sewn, including where each stitch starts.

    Landing points alone would miss the start of a stitch, so splitting one long
    stitch in two would look like the design moved.
    """
    points = [p for segment in sewn_segments(blocks) for p in segment]
    if not points:
        return None
    xs, ys = [x for x, _ in points], [y for _, y in points]
    return min(xs), min(ys), max(xs), max(ys)


def verify_export(blocks, path):
    """Summary of how the exported file at ``path`` compares with ``blocks``."""
    decoded = generate(import_machine(path).project)
    comparison = compare_commands(blocks, decoded)
    source, reopened = comparison["source"], comparison["decoded"]
    problems = []
    source_stitches = source["counts"].get("stitch", 0)
    decoded_stitches = reopened["counts"].get("stitch", 0)
    if decoded_stitches < source_stitches:
        problems.append(f"{source_stitches - decoded_stitches:,} stitches are missing from the reopened file.")
    source_changes, decoded_changes = len(source["thread_rgb"]) - 1, len(reopened["thread_rgb"]) - 1
    if decoded_changes != source_changes:
        problems.append(f"Thread changes differ: {source_changes} in the design, {decoded_changes} in the file.")
    bounds_delta = None
    expected, actual = sewn_extent(blocks), sewn_extent(decoded)
    if expected and actual:
        bounds_delta = max(abs(a - b) for a, b in zip(expected, actual))
        if bounds_delta > BOUNDS_TOLERANCE_MM:
            problems.append(f"The design's outer edge moved by up to {bounds_delta:.2f} mm.")
    geometry = comparison["sewn_geometry"]
    extra = geometry["decoded_outside_source"]
    missing = geometry["source_outside_decoded"]
    complete = extra["complete"] and missing["complete"]
    if complete:
        if extra["estimated_outside_length_mm"] > OUTSIDE_LENGTH_MM:
            problems.append(f"About {extra['estimated_outside_length_mm']:.1f} mm of stitching in the file is not in the design.")
        if missing["estimated_outside_length_mm"] > OUTSIDE_LENGTH_MM:
            problems.append(f"About {missing['estimated_outside_length_mm']:.1f} mm of the design's stitching is missing from the file.")
    length_change = None
    if source["sewn_path_m"]:
        length_change = (reopened["sewn_path_m"] - source["sewn_path_m"]) / source["sewn_path_m"]
    return {
        "verified": not problems,
        "problems": problems,
        "complete_path_comparison": complete,
        "source_stitches": source_stitches,
        "decoded_stitches": decoded_stitches,
        "thread_changes": source_changes,
        "bounds_delta_mm": bounds_delta,
        "sewn_length_change": length_change,
    }


def verification_text(result, name):
    if result["verified"]:
        lines = [f"Export verified: {name} was reopened and matches the design.",
                 f"{result['decoded_stitches']:,} stitches · {result['thread_changes']} thread change"
                 f"{'s' if result['thread_changes'] != 1 else ''}"
                 + (f" · edge difference {result['bounds_delta_mm']:.2f} mm" if result["bounds_delta_mm"] is not None else "")]
        if not result["complete_path_comparison"]:
            lines.append("The design is too large to compare every stitch; counts and edges were checked.")
        return "\n".join(lines)
    return "\n".join([f"Export check found differences: {name} was reopened and does not fully match the design.",
                      *("• " + problem for problem in result["problems"]),
                      "Review the file with File → Compare machine file with design before sewing."])
