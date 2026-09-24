"""Publish pytest results as GitHub annotations and a job summary.

Annotations are visible on public runs without downloading logs. When the run
was killed (for example by a timeout) and no JUnit report exists, the progress
file names the last test that started.
"""
import argparse
import os
from pathlib import Path
import xml.etree.ElementTree as ET


def escape(text):
    # Workflow commands need %, CR and LF escaped in their message data.
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def escape_property(text):
    # Property values (the title) also end at ':' or ','.
    return escape(text).replace(":", "%3A").replace(",", "%2C")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--junit", type=Path, required=True)
    parser.add_argument("--progress", type=Path)
    parser.add_argument("--label", default="tests")
    args = parser.parse_args()
    problems = []
    summary = [f"### {args.label}"]
    if args.junit.is_file():
        root = ET.parse(args.junit).getroot()
        suites = [root] if root.tag == "testsuite" else list(root)
        totals = {key: sum(int(s.get(key, 0)) for s in suites) for key in ("tests", "failures", "errors", "skipped")}
        summary.append(f"{totals['tests']} tests · {totals['failures']} failures · {totals['errors']} errors · {totals['skipped']} skipped")
        for case in root.iter("testcase"):
            for outcome in ("failure", "error"):
                node = case.find(outcome)
                if node is None:
                    continue
                name = f"{case.get('classname', '')}::{case.get('name', '')}"
                detail = (node.get("message") or "") + "\n" + (node.text or "")
                problems.append((name, outcome, detail.strip()[-3000:]))
    else:
        summary.append("No JUnit report: the test process did not finish.")
        started = args.progress.read_text(encoding="utf-8").splitlines() if args.progress and args.progress.is_file() else []
        if started:
            problems.append((started[-1], "error", f"Last test started before the run ended ({len(started)} started). It probably hung or crashed the interpreter."))
        else:
            problems.append(("pytest", "error", "No tests started: collection or start-up failed. Check the Run tests step."))
    # GitHub shows at most ten error annotations per step; put the rest in one.
    for name, outcome, detail in problems[:9]:
        print(f"::error title={escape_property(args.label + ' ' + outcome + ' ' + name)}::{escape(detail)}")
    if len(problems) > 9:
        rest = "\n".join(name for name, _, _ in problems[9:60])
        print(f"::error title={escape_property(f'{args.label} {len(problems) - 9} more')}::{escape(rest)}")
    summary.extend(f"- `{name}` ({outcome})" for name, outcome, _ in problems[:60])
    target = os.environ.get("GITHUB_STEP_SUMMARY")
    if target:
        with open(target, "a", encoding="utf-8") as stream:
            stream.write("\n".join(summary) + "\n")
    print("\n".join(summary))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
