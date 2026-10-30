"""Probe a supplied machine file through every writer and two-step conversion."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from datetime import datetime,timezone
from importlib.metadata import version
from .formats import EXPORT_FORMATS,MAX_IMPORT_BYTES,import_machine,export_machine
from .engine import generate
from .export_verify import verify_export


def build_report(source,destination):
    source=Path(source).resolve();root=Path(destination)
    if source.stat().st_size>MAX_IMPORT_BYTES:raise ValueError('Source exceeds the machine-file size limit.')
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    project=import_machine(source).project;original=generate(project)
    root.mkdir(parents=True,exist_ok=False)
    marker=root/'INCOMPLETE.txt';marker.write_text('Matrix probe incomplete; inspect individual errors before using results.\n')
    report={'source':str(source),'source_sha256':digest,'provenance':'User-supplied file; provenance not independently verified',
        'physical_validation':False,'generated_at':datetime.now(timezone.utc).isoformat(),
        'pyembroidery_version':version('pyembroidery'),'first_exports':{},'conversions':{}}
    for first in sorted(EXPORT_FORMATS):
        folder=root/first[1:];folder.mkdir();path=folder/('first'+first)
        try:
            export_machine(project,path,original)
            report['first_exports'][first]=verify_export(original,path)
            intermediate=import_machine(path).project;blocks=generate(intermediate)
        except Exception as exc:
            report['first_exports'][first]={'error':str(exc)}
            for second in sorted(EXPORT_FORMATS):report['conversions'][first+'->'+second]={'error':'Intermediate failed: '+str(exc)}
            continue
        for second in sorted(EXPORT_FORMATS):
            target=folder/('converted'+second);key=first+'->'+second
            try:
                export_machine(intermediate,target,blocks)
                report['conversions'][key]={'against_intermediate':verify_export(blocks,target),
                    'against_original':verify_export(original,target)}
            except Exception as exc:report['conversions'][key]={'error':str(exc)}
    if hashlib.sha256(source.read_bytes()).hexdigest()!=digest:raise ValueError('Source changed during the matrix probe.')
    report['summary']={scope:sum(row.get(scope,{}).get('verified',False) for row in report['conversions'].values())
        for scope in ('against_intermediate','against_original')}
    report['summary']['pairs']=len(report['conversions'])
    (root/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    write_review_csv(report,root/'review.csv');marker.unlink()
    return report


def write_review_csv(report,path):
    """One row per conversion; a clean intermediate does not erase earlier loss."""
    def cell(value):
        text=str(value)
        return "'"+text if text.lstrip().startswith(('=','+','-','@')) else text
    with Path(path).open('x',encoding='utf-8-sig',newline='') as stream:
        writer=csv.writer(stream)
        writer.writerow(['Intermediate format','Final format','Against intermediate','Against original',
            'Intermediate findings','Original findings','Execution error','Physical validation'])
        for key,row in sorted(report['conversions'].items()):
            first,second=key.split('->')
            def status(scope):
                if 'error' in row:return 'Not completed'
                return 'Passed software checks' if row[scope]['verified'] else 'Review required'
            writer.writerow([first,second,status('against_intermediate'),status('against_original'),
                cell(' | '.join(row.get('against_intermediate',{}).get('problems',[]))),
                cell(' | '.join(row.get('against_original',{}).get('problems',[]))),
                cell(row.get('error','')),'Not verified'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();report=build_report(args.source,args.output)
    print(json.dumps(report['summary']))
    return int(any('error' in row or not row['against_original']['verified'] for row in report['conversions'].values()))


if __name__=='__main__':raise SystemExit(main())
