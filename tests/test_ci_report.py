import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "scripts" / "ci_report.py"


def test_report_survives_legacy_console_encodings(tmp_path):
    junit = tmp_path / "results.xml"
    junit.write_text('<testsuite tests="1" failures="1" errors="0" skipped="0"><testcase classname="tests.test_x" name="test_arrow">'
                     '<failure message="Design → Design notes ≥ 1">detail ✓</failure></testcase></testsuite>', encoding="utf-8")
    env = {**os.environ, "PYTHONIOENCODING": "cp1252"}
    env.pop("GITHUB_STEP_SUMMARY", None)
    result = subprocess.run([sys.executable, str(SCRIPT), "--junit", str(junit), "--label", "Windows"],
                            capture_output=True, env=env)
    assert result.returncode == 1, result.stderr
    output = result.stdout.decode("utf-8")
    assert "::error title=" in output and "test_arrow" in output and "→" in output
