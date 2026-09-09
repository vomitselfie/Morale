"""Thread identity and measurable path lengths, independent of machine settings."""
import csv
import math

THREAD_FIELDS = ("brand", "catalog_number", "description", "weight", "chart", "details")


def thread_key(block):
    return block.color.lower(), tuple(sorted((k, v) for k, v in block.thread.items() if v))


def usage(blocks):
    result = []
    previous = (0., 0.)
    for block in blocks:
        sewn = travel = 0.
        count = trims = stops = 0
        for stitch in block.stitches:
            position = stitch.x, stitch.y
            if stitch.command == "stitch":
                sewn += math.dist(previous, position)
                count += 1
            elif stitch.command == "jump":
                travel += math.dist(previous, position)
            elif stitch.command == "trim":
                trims += 1
            elif stitch.command == "stop":
                stops += 1
            if stitch.command in {"stitch", "jump"}:
                previous = position
        result.append({"object_id": block.object_id, "color": block.color, "thread": dict(block.thread),
                       "stitches": count, "sewn_m": sewn / 1000, "travel_m": travel / 1000, "trims": trims, "stops": stops})
    return result


def csv_text(value):
    value = str(value)
    return "'" + value if value.lstrip().startswith(("=", "+", "-", "@")) else value


def write_chart(project, blocks, stream):
    writer = csv.writer(stream)
    writer.writerow(["Sequence", "Object", "Thread RGB", *THREAD_FIELDS, "Stitches", "Sewn path (m)", "Travel (m)", "Trims", "Stops", "Instruction"])
    names = {obj.id: obj.name for obj in project.objects}
    notes = {obj.id: obj.stage_note for obj in project.objects}
    for index, row in enumerate(usage(blocks), 1):
        writer.writerow([index, csv_text(names[row["object_id"]]), row["color"],
                         *[csv_text(row["thread"].get(key, "")) for key in THREAD_FIELDS],
                         row["stitches"], f"{row['sewn_m']:.6f}", f"{row['travel_m']:.6f}", row["trims"], row["stops"], csv_text(notes[row["object_id"]])])
