"""Reopen an exported machine file with the real reader and compare it to the design.

Formats legitimately quantize positions and may add needle positions to split
long spans, so exact command identity is not required. The comparison reports
counts, thread changes, bounds and sampled path deviation, and flags anything
beyond small tolerances for review. It never blocks or alters the export.
"""
import math
from .comparison import compare_commands
from .engine import generate
from .formats import import_machine
from .path_fidelity import sewn_segments
from .threads import thread_key

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


def control_positions(blocks):
    """Control location is the last motion point, not unused control coordinates."""
    position=(0.,0.);result={"stop":[],"trim":[]}
    for block in blocks:
        for stitch in block.stitches:
            if stitch.command in {"stitch","jump"}:position=(stitch.x,stitch.y)
            elif stitch.command in result:result[stitch.command].append(position)
    return result


def verify_export(blocks, path):
    """Summary of how the exported file at ``path`` compares with ``blocks``."""
    imported=import_machine(path)
    decoded = generate(imported.project)
    comparison = compare_commands(blocks, decoded)
    source, reopened = comparison["source"], comparison["decoded"]
    problems = []
    source_stitches = source["counts"].get("stitch", 0)
    decoded_stitches = reopened["counts"].get("stitch", 0)
    if decoded_stitches < source_stitches:
        problems.append(f"{source_stitches - decoded_stitches:,} stitches are missing from the reopened file.")
    boundary_trims=0
    for index,block in enumerate(blocks):
        if not index:continue
        if not block.color_break and thread_key(block)==thread_key(blocks[index-1]):continue
        for stitch in block.stitches:
            if stitch.command=='stitch':break
            if stitch.command=='trim':boundary_trims+=1
    source_changes, decoded_changes = len(source["thread_rgb"]) - 1, len(reopened["thread_rgb"]) - 1
    if decoded_changes != source_changes:
        problems.append(f"Thread changes differ: {source_changes} in the design, {decoded_changes} in the file.")
    controls={}
    source_positions=control_positions(blocks);decoded_positions=control_positions(decoded)
    for command in ("stop","trim"):
        expected_count=source["counts"].get(command,0)
        actual_count=reopened["counts"].get(command,0)
        controls[command]={"source":expected_count,"decoded":actual_count}
        if actual_count < expected_count:
            problems.append(f"{command.title()} commands decreased: {expected_count} in the design, {actual_count} in the reopened file. Review format support and machine behavior.")
            if command=='trim' and boundary_trims:
                problems.append(f'{boundary_trims} source trims occur after thread changes and before sewing resumes. The encoder may omit these because it treats a thread change as already trimmed; confirm cutting behavior on the target machine.')
            if command=="stop" and decoded_changes>source_changes:
                problems.append("The reopened file also has extra thread changes. The format may represent operator pauses as thread changes; verify the pause sequence on the intended machine.")
        elif actual_count > expected_count:
            problems.append(f"{command.title()} commands increased: {expected_count} in the design, {actual_count} in the reopened file. Review added controls before sewing.")
        # Pair in command order only when counts match; do not guess an
        # alignment when a writer inserted or removed controls.
        if expected_count and expected_count==actual_count:
            displacement=max(math.dist(a,b) for a,b in zip(source_positions[command],decoded_positions[command]))
            if displacement>BOUNDS_TOLERANCE_MM:
                problems.append(f"{command.title()} locations differ by up to {displacement:.2f} mm when paired in command order. Review the control sequence before sewing.")
    control_order_matches=None
    if all(count['source']==count['decoded'] for count in controls.values()):
        def sequence(items):
            return [s.command for block in items for s in block.stitches if s.command in {'stop','trim'}]
        control_order_matches=sequence(blocks)==sequence(decoded)
        if not control_order_matches:
            problems.append('Stop/trim order differs despite matching counts. Review the operator pause and cutting sequence before sewing.')
    thread_control_order_matches=None
    if source_changes==decoded_changes and all(count['source']==count['decoded'] for count in controls.values()):
        def thread_control_sequence(items):
            sequence=[];previous=None
            for block in items:
                if not block.stitches:continue
                key=thread_key(block)
                if previous is not None and (block.color_break or key!=previous):sequence.append('thread_change')
                sequence.extend(s.command for s in block.stitches if s.command in {'stop','trim'})
                previous=key
            return sequence
        thread_control_order_matches=thread_control_sequence(blocks)==thread_control_sequence(decoded)
        if not thread_control_order_matches and control_order_matches:
            problems.append('Stop/trim placement relative to thread changes differs despite matching counts. Review cutting and thread-change order before sewing.')
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
    if not complete:
        problems.append("Sampled path comparison was incomplete; export fidelity could not be established.")
    if not extra["samples"] or not missing["samples"]:
        problems.append("No sewn-path samples were available in one comparison direction; export fidelity could not be established.")
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
        "reader_notes": list(getattr(imported,"notes",[])),
        "problems": problems,
        "complete_path_comparison": complete,
        "source_stitches": source_stitches,
        "decoded_stitches": decoded_stitches,
        "thread_changes": max(0,source_changes),
        "controls": controls,
        "control_order_matches": control_order_matches,
        "thread_control_order_matches": thread_control_order_matches,
        "bounds_delta_mm": bounds_delta,
        "sewn_length_change": length_change,
    }


def verification_text(result, name):
    if result["verified"]:
        lines = [f"Export verified: {name} was reopened and passed the sampled geometry and count checks.",
                 f"{result['decoded_stitches']:,} stitches · {result['thread_changes']} thread change"
                 f"{'s' if result['thread_changes'] != 1 else ''}"
                 + (f" · edge difference {result['bounds_delta_mm']:.2f} mm" if result["bounds_delta_mm"] is not None else "")]
        if result.get("thread_control_order_matches") is True:
            lines.append("Stop/trim sequence relative to thread changes: unchanged.")
        lines.append("These checks do not verify stitch order, thread identity or physical machine behavior.")
        lines.extend(result.get("reader_notes",[]))
        return "\n".join(lines)
    return "\n".join([f"Export check found differences or incomplete checks: {name}. Review required.",
                      *("• " + problem for problem in result["problems"]),
                      *result.get("reader_notes",[]),
                      "Review the file with File → Compare machine file with design before sewing."])
