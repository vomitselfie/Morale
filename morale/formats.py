"""Machine-file adapters. Projects retain editable geometry; exports retain stitches."""
from pathlib import Path
from dataclasses import dataclass
import math
import os
import tempfile
import pyembroidery as emb
from .engine import generate, preflight
from .model import Project, DesignObject, PALETTE
from .threads import THREAD_FIELDS, thread_key

# Exclude thread-palette-only files, debugging formats and G-code from machine
# dialogs. A reader being present is not a claim of tested hardware support.
FORMAT_REGISTRY = {f".{f['extension']}": f for f in emb.EmbPattern.supported_formats()
                   if f.get("category") == "embroidery" and f["extension"] != "gcode"}
IMPORT_FORMATS = {ext for ext, f in FORMAT_REGISTRY.items() if f.get("reader")}
EXPORT_FORMATS = {ext for ext, f in FORMAT_REGISTRY.items() if f.get("writer")}
COMMANDS = {"stitch": emb.STITCH, "jump": emb.JUMP, "trim": emb.TRIM, "stop": emb.STOP}
MAX_IMPORT_BYTES = 20_000_000


def file_filters(export=False):
    extensions = EXPORT_FORMATS if export else IMPORT_FORMATS
    individual = [f"{FORMAT_REGISTRY[ext]['description']} (*{ext})" for ext in sorted(extensions)]
    if export:
        individual = [entry for entry in individual if not entry.endswith("(*.pes)")]
        individual = ["Brother PES v6 — RGB colors (*.pes)", "Brother PES v1 — legacy palette (*.pes)"] + individual
    if not export:
        individual.insert(0, "Embroidery files (" + " ".join(f"*{ext}" for ext in sorted(extensions)) + ")")
    return ";;".join(individual)


@dataclass
class ImportResult:
    project: Project
    notes: list[str]


def import_machine(path):
    path = Path(path)
    extension = path.suffix.lower()
    if extension not in IMPORT_FORMATS:
        raise ValueError("No embroidery reader is available for this extension.")
    if path.stat().st_size > MAX_IMPORT_BYTES:
        raise ValueError("Machine files are limited to 20 MB.")
    try:
        if extension=='.vp3':
            from .vp3_positions import read_vp3
            pattern=read_vp3(path)
        else:pattern = emb.read(str(path),settings={'trim_distance':None,'trims':False,'clipping':False}) if extension=='.jef' else emb.read(str(path))
        if extension=='.jef' and pattern is not None:decode_jef_trims(pattern)
    except Exception as exc:
        raise ValueError(f"The {extension.upper()} reader could not decode this file: {exc}") from exc
    if pattern is None:
        raise ValueError("The file could not be decoded.")
    return from_pattern(pattern, path.stem, extension)


def decode_jef_trims(pattern):
    """Recognize the writer's three stationary-jump trim convention exactly."""
    result=[];previous=(0,0);index=0
    while index<len(pattern.stitches):
        stitch=pattern.stitches[index];command=stitch[2]&emb.COMMAND_MASK
        if command==emb.JUMP and (stitch[0],stitch[1])==previous:
            end=index
            while end<len(pattern.stitches):
                row=pattern.stitches[end]
                if row[2]&emb.COMMAND_MASK!=emb.JUMP or (row[0],row[1])!=previous:break
                end+=1
            count=end-index
            result.extend([[*previous,emb.TRIM] for _ in range(count//3)])
            result.extend(pattern.stitches[end-count%3:end]);index=end;continue
        result.append(stitch)
        if command in {emb.STITCH,emb.JUMP}:previous=(stitch[0],stitch[1])
        index+=1
    pattern.stitches=result


def from_pattern(pattern, name="Imported design", source_format=""):
    if not pattern.stitches or not any(s[2] & emb.COMMAND_MASK == emb.STITCH for s in pattern.stitches):
        raise ValueError("The file contains no readable embroidery stitches.")
    if len(pattern.stitches) > 250_000:
        raise ValueError("File exceeds the 250,000-command import limit.")
    inverse = {value: key for key, value in COMMANDS.items()}
    notes = ["Imported stitches retain their stitch count when resized; density is not regenerated."]
    if source_format=='.jef':notes.append('JEF runs of three stationary jumps are interpreted as trims. Ordinary travel distance does not imply a trim.')
    project = Project(name[:200])
    thread_index = 0
    current = []
    force_break = False
    last_position = (0., 0.)
    pending_position = last_position
    missing_colors = False
    needle_events = False

    def flush():
        nonlocal current, missing_colors
        if not current:
            return
        if len(project.objects) >= 500:
            raise ValueError("File exceeds the 500-color-block limit.")
        color = PALETTE[thread_index % len(PALETTE)]
        metadata = {}
        if thread_index < len(pattern.threadlist):
            source_thread = pattern.threadlist[thread_index]
            color = source_thread.hex_color()
            metadata = {key: str(getattr(source_thread, key)) for key in THREAD_FIELDS if getattr(source_thread, key, None) is not None}
        else:
            missing_colors = True
        xs, ys = zip(*[(r[0], r[1]) for r in current])
        width, height = max(.1, max(xs) - min(xs)), max(.1, max(ys) - min(ys))
        x, y = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
        if width > 500 or height > 500 or abs(x) > 1000 or abs(y) > 1000:
            raise ValueError("Imported geometry exceeds the supported 500 mm object size or ±1,000 mm position.")
        project.objects.append(DesignObject(
            name=f"Thread {len(project.objects) + 1}", kind="stitches", x=x, y=y,
            width=width, height=height, color=color, stitch_type="manual", underlay=False,
            color_break=force_break,
            thread=metadata,
            stitch_data=[[(px - x) / width, (py - y) / height, cmd] for px, py, cmd in current]))
        current = []

    for raw_x, raw_y, encoded in pattern.stitches:
        if not math.isfinite(raw_x) or not math.isfinite(raw_y):
            raise ValueError("File contains non-finite coordinates.")
        command = encoded & emb.COMMAND_MASK
        if command == emb.END:
            break
        if command in {emb.COLOR_CHANGE, emb.NEEDLE_SET}:
            if command == emb.NEEDLE_SET and not project.objects and not any(row[2] == "stitch" for row in current):
                _, thread, needle, _ = emb.decode_embroidery_command(encoded)
                thread_index = thread if thread is not None else max(0, (needle or 1) - 1)
                needle_events = True
                continue
            if command == emb.COLOR_CHANGE and not current:
                current = [(*last_position, "jump")]
            flush()
            if command == emb.NEEDLE_SET:
                _, thread, needle, _ = emb.decode_embroidery_command(encoded)
                thread_index = thread if thread is not None else max(0, (needle or 1) - 1)
                needle_events = True
            else:
                thread_index += 1
            force_break = bool(project.objects)
            pending_position = last_position
            if command == emb.COLOR_CHANGE:
                current = [(*last_position, "jump")]
            continue
        if command not in inverse:
            raise ValueError(f"Unsupported machine command {command}; import was stopped to avoid silently losing commands.")
        # An explicit starting jump makes a block independently movable without
        # changing the original first sewn segment from the prior block/origin.
        if not current and command != emb.JUMP:
            current.append((*pending_position, "jump"))
        if command in {emb.STITCH, emb.JUMP}:
            last_position = (raw_x / 10, raw_y / 10)
        current.append((*last_position, inverse[command]))
    flush()
    if not any(row[2] == "stitch" for obj in project.objects for row in obj.stitch_data):
        raise ValueError("The file contains no readable stitches before its end command.")
    if missing_colors or source_format in {".dst", ".exp"}:
        notes.append("Some thread colors are absent from this format/file. Placeholder colors are used; confirm them with the original thread chart.")
    if needle_events:
        notes.append("Needle-selection events were converted to color-block changes. Reassign machine needles before sewing; original needle assignments are not retained.")
    positions = [p for obj in project.objects for p in obj.outline()]
    width = max(20, math.ceil(max(abs(x) for x, _ in positions) * 2))
    height = max(20, math.ceil(max(abs(y) for _, y in positions) * 2))
    project.hoop_width, project.hoop_height = min(500, max(100, width)), min(500, max(100, height))
    if width > 500 or height > 500:
        notes.append("The original coordinates extend beyond a 500 mm hoop. Reposition the design before export.")
    # Use the same schema validation as editable project files.
    project = Project.loads(project.dumps())
    return ImportResult(project, notes)


def to_pattern(project, blocks=None):
    blocks = generate(project) if blocks is None else blocks
    issues = preflight(project, blocks)
    if issues:
        raise ValueError("\n".join(issues))
    pattern = emb.EmbPattern()
    pattern.metadata("name", project.name)
    previous_color = None
    previous_thread = None
    last_position = (0, 0)
    for block in blocks:
        if not block.stitches:
            continue
        if thread_key(block) != previous_thread or block.color_break:
            if previous_color is not None:
                pattern.add_stitch_absolute(emb.COLOR_CHANGE, *last_position)
            thread = emb.EmbThread()
            thread.set(block.color)
            for key, value in block.thread.items():
                setattr(thread, key, value)
            pattern.add_thread(thread)
            previous_color = block.color
            previous_thread = thread_key(block)
        for stitch in block.stitches:
            if stitch.command not in COMMANDS:
                raise ValueError(f"Unsupported stitch command: {stitch.command}")
            pattern.add_stitch_absolute(COMMANDS[stitch.command], stitch.x * 10, stitch.y * 10)
            last_position = (stitch.x * 10, stitch.y * 10)
    pattern.add_stitch_absolute(emb.END, *last_position)
    return pattern


def export_machine(project, path, blocks=None, *, pes_version=6):
    path = Path(path)
    if path.suffix.lower() not in EXPORT_FORMATS:
        raise ValueError("Choose a supported machine file: " + ", ".join(sorted(EXPORT_FORMATS)))
    pattern = to_pattern(project, blocks)
    from .export_spans import subdivide_sewn_spans
    # Reserve one encoder unit for endpoint rounding. Subdivide sewn motion
    # before the upstream encoder can substitute jumps for oversized spans.
    maximum=FORMAT_REGISTRY[path.suffix.lower()]['writer'].MAX_STITCH_DISTANCE-1
    source_stitches=sum(row[2] & emb.COMMAND_MASK==emb.STITCH for row in pattern.stitches)
    pattern,added_stitches=subdivide_sewn_spans(pattern,maximum)
    # Several binary headers use a fixed 16-byte name field. The upstream TBF
    # and DST writers pad but do not truncate; longer UTF-8 names shift fields.
    if path.suffix.lower() in {".dst", ".tbf"}:
        pattern.metadata("name", project.name.encode("ascii", "replace").decode("ascii")[:16])
    if pes_version not in {1, 6}:
        raise ValueError("Supported PES versions are 1 and 6.")
    if path.suffix.lower() in {".dst", ".exp", ".xxx", ".vp3"}:
        # These formats represent pauses as thread changes. Normalize before
        # writing so header/thread-table counts agree with the encoded events;
        # VP3 otherwise ignores STOP entirely.
        pattern.interpolate_stop_as_duplicate_color()
    # The library chooses a writer by extension. Stage before replacing a file.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, suffix=path.suffix.lower(), delete=False) as f:
            temporary = Path(f.name)
        settings={'full_jump':False}
        if path.suffix.lower()=='.vp3':settings['round']=True
        if path.suffix.lower()=='.pes':settings['version']=pes_version
        if path.suffix.lower()=='.jef':settings.update(trims=True,trim_at=3)
        # Native blocks already contain explicit travel to their sewing start.
        # A writer's full-jump default would move again to the first stitch end,
        # silently removing that sewn span.
        if path.suffix.lower() in {'.pes','.pec','.vp3'}:
            from .writer_text import write
            write(pattern,temporary,path.suffix.lower(),settings)
        else:emb.write(pattern, str(temporary),settings)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)

    return {'format':path.suffix.lower(),'source_stitches':source_stitches,
            'prepared_stitches':source_stitches+added_stitches,'subdivision_added_stitches':added_stitches,
            'maximum_prepared_span_mm':maximum/10}


def export_summary(result):
    return (f"Stitches: {result['source_stitches']:,} in the source, {result['prepared_stitches']:,} prepared for {result['format'][1:].upper()}. "
            f"Added {result['subdivision_added_stitches']:,} needle positions along long sewn spans. "
            'The file writer may add further stitches or control commands.')


def export_notes(extension, pes_version=6):
    notes = ["Format writers may add travel, trims, or zero-length stitches. Review the exported design in the target machine's preview."]
    notes.append('Sewn spans exceeding the format limit are subdivided along their original path; this adds needle positions in the exported file.')
    if extension=='.jef':notes.append('Explicit trims are encoded as three stationary jumps. Trim execution depends on the Janome machine and its settings.')
    if extension in {".dst", ".exp", ".u01"}:
        notes.append("This file does not retain RGB thread colors; export a CSV thread chart.")
    if extension in {".pec", ".jef"} or extension == ".pes" and pes_version == 1:
        notes.append("Colors are mapped to the format's fixed thread palette; keep a CSV chart for the intended colors.")
    if extension in {".dst", ".exp", ".xxx", ".vp3"}:
        notes.append("Operator stops are represented as color changes. Reuse the current thread at those pauses.")
    if extension in {".pes", ".pec"}:
        notes.append('The PEC machine label is limited to eight ASCII characters; PES v6 extended names and thread text use byte-counted UTF-8 fields (255 bytes per field).')
        notes.append("Same-color thread changes may be decoded as operator stops by PES/PEC readers.")
        notes.append("PES/PEC encoding may add sewn points at jump landings, changing the decoded stitch count and sewn bounds.")
    if extension == ".vp3":
        notes.append("The installed VP3 writer omits explicit jump records. Its decoded travel paths can differ from Morale's preview.")
    if extension in {".tbf", ".u01"}:
        notes.append("Needle assignments are generated by the writer. Check them against the machine setup.")
    return notes
