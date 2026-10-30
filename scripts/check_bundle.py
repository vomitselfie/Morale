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
import importlib.util
source_root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('morale_check_notices',source_root/'packaging/check_notices.py')
notices=importlib.util.module_from_spec(spec);spec.loader.exec_module(notices)
data_root=executable.parent.parent/'Resources' if sys.platform=='darwin' else executable.parent/'_internal'
notice_report=notices.verify(data_root,source_root)
source_spec=importlib.util.spec_from_file_location('morale_source_manifest',source_root/'packaging/source_manifest.py')
source_module=importlib.util.module_from_spec(source_spec);source_spec.loader.exec_module(source_module)
source_report=json.loads((data_root/'source-manifest.json').read_text(encoding='utf-8'))
if source_report!=source_module.manifest(source_root):
    raise SystemExit('Bundle source fingerprint differs from current build inputs; rebuild before validation.')

result=subprocess.run([str(executable),'--self-test',str(args.output.resolve())],timeout=240)
report_path=args.output/'report.json'
if not report_path.is_file():raise SystemExit(f'Bundle did not produce a self-test report (exit {result.returncode}).')
report=json.loads(report_path.read_text(encoding='utf-8'))
(args.output/'source-manifest.json').write_text(json.dumps(source_report,indent=2)+'\n',encoding='utf-8')
(args.output/'notice-integrity.json').write_text(json.dumps(notice_report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2))
if result.returncode or not report.get('passed') or not report.get('frozen'):
    raise SystemExit('Packaged self-test failed; inspect its report and worker logs.')
