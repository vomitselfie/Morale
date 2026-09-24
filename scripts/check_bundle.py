"""Run a built desktop application's self-test on its native build platform."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

parser=argparse.ArgumentParser()
parser.add_argument('--dist',type=Path,default=Path('dist'))
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
relative={'win32':'Morale/Morale.exe','darwin':'Morale.app/Contents/MacOS/Morale'}.get(sys.platform,'Morale/Morale')
executable=(args.dist/relative).resolve()
result=subprocess.run([str(executable),'--self-test',str(args.output.resolve())],timeout=240)
report_path=args.output/'report.json'
if not report_path.is_file():raise SystemExit(f'Bundle did not produce a self-test report (exit {result.returncode}).')
report=json.loads(report_path.read_text(encoding='utf-8'))
print(json.dumps(report,indent=2))
if result.returncode or not report.get('passed') or not report.get('frozen'):
    raise SystemExit('Packaged self-test failed; inspect its report and worker logs.')
