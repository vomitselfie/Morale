"""Reproducible synthetic compatibility report; run with python -m morale.compatibility."""
import argparse
from datetime import datetime, timezone
from importlib.metadata import version
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from .engine import generate
from .formats import EXPORT_FORMATS, IMPORT_FORMATS, FORMAT_REGISTRY, export_machine, import_machine, export_notes
from .model import demo_project


def metrics(project):
    blocks = generate(project)
    sewn = [s for b in blocks for s in b.stitches if s.command == "stitch"]
    return {"stitches": len(sewn), "blocks": len(blocks),
            "bounds_mm": [min(s.x for s in sewn), min(s.y for s in sewn), max(s.x for s in sewn), max(s.y for s in sewn)],
            "colors": [b.color for b in blocks],
            "stops": sum(s.command == "stop" for b in blocks for s in b.stitches),
            "trims": sum(s.command == "trim" for b in blocks for s in b.stitches)}


def build_report():
    project = demo_project()
    original = metrics(project)
    expected_colors = ["#447568", "#7d9c69", "#d68b79", "#e9b75e"]
    report = {"generated_at": datetime.now(timezone.utc).isoformat(),
              "pyembroidery_version": version("pyembroidery"),
              "fixture": "Morale generated wildflower; four consecutive thread groups, negative coordinates, running and fill stitches",
              "scope": "Synthetic writer/reader checks only. No physical sew-out or external-file certification. Reader-only formats are unverified.",
              "original": original, "formats": {}, "conversion_pairs": []}
    with TemporaryDirectory(prefix="morale-compatibility-") as directory:
        projects = {}
        for extension in sorted(IMPORT_FORMATS):
            row = {"description": FORMAT_REGISTRY[extension]["description"], "reader_available": True,
                   "writer_available": extension in EXPORT_FORMATS, "external_fixture_tested": False,
                   "physical_machine_tested": False, "synthetic_roundtrip": "not_tested"}
            report["formats"][extension] = row
            if extension not in EXPORT_FORMATS:
                continue
            try:
                path = Path(directory) / ("fixture" + extension)
                export_machine(project, path)
                imported = import_machine(path)
                projects[extension] = imported.project
                measured = metrics(imported.project)
                bounds_ok = all(abs(a - b) <= .15 for a, b in zip(original["bounds_mm"], measured["bounds_mm"]))
                row.update(synthetic_roundtrip="pass" if bounds_ok and measured["blocks"] == 4 else "fail",
                           measured=measured, bounds_within_015_mm=bounds_ok,
                           rgb_retained=measured["colors"] == expected_colors and not any("Placeholder" in note for note in imported.notes),
                           import_notes=imported.notes, export_notes=export_notes(extension))
            except Exception as exc:
                row.update(synthetic_roundtrip="fail", error=str(exc))
        for source, intermediate in sorted(projects.items()):
            before = metrics(intermediate)
            for target in sorted(EXPORT_FORMATS):
                row = {"source": source, "target": target}
                try:
                    path = Path(directory) / ("converted" + target)
                    export_machine(intermediate, path)
                    after = metrics(import_machine(path).project)
                    passed = after["blocks"] == 4 and all(abs(a - b) <= .15 for a, b in zip(before["bounds_mm"], after["bounds_mm"]))
                    row["bounds_and_block_count"] = "pass" if passed else "fail"
                except Exception as exc:
                    row.update(bounds_and_block_count="fail", error=str(exc))
                report["conversion_pairs"].append(row)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("compatibility-report.json"))
    args = parser.parse_args()
    report = build_report()
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    failures = sum(row["synthetic_roundtrip"] == "fail" for row in report["formats"].values())
    failures += sum(row["bounds_and_block_count"] == "fail" for row in report["conversion_pairs"])
    print(f"{len(IMPORT_FORMATS)} readers, {len(EXPORT_FORMATS)} writers, {len(report['conversion_pairs'])} conversion pairs, {failures} failures. Report: {args.output}")
    raise SystemExit(bool(failures))


if __name__ == "__main__":
    main()
