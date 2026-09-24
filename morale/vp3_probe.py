"""Minimal synthetic evidence for internal-jump information loss in VP3 export."""
import argparse
import hashlib
import json
from pathlib import Path
from .model import Project,DesignObject
from .stitch_edit import manual_object
from .formats import export_machine,import_machine
from .engine import generate
from .comparison import compare_commands


def build_probe(destination):
    root=Path(destination);root.mkdir(parents=True,exist_ok=False)
    report={'external_files':False,'physical_sewouts':False,'cases':[],'formats':{}}
    for landing in (4,8):
        project=Project(objects=[manual_object(DesignObject(),[[0,0,'jump'],[1,0,'stitch'],[landing,0,'jump'],[12,0,'stitch']])])
        folder=root/f'landing-{landing}';folder.mkdir();project.save(folder/'source.morale')
        case={'jump_landing_mm':landing,'exports':{}};report['cases'].append(case)
        for extension in ('.vp3','.pes','.exp'):
            path=folder/('design'+extension);export_machine(project,path)
            comparison=compare_commands(generate(project),generate(import_machine(path).project))
            case['exports'][extension]={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'comparison':comparison}
    for extension in ('.vp3','.pes','.exp'):
        report['formats'][extension]={'identical_bytes_for_different_jump_landings':
            report['cases'][0]['exports'][extension]['sha256']==report['cases'][1]['exports'][extension]['sha256']}
    report['interpretation']='Identical output for different internal jump landings proves those landings cannot be recovered uniquely from these files. This probe does not identify a valid alternative VP3 encoding.'
    (root/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    report=build_probe(parser.parse_args().output)
    print(json.dumps(report['formats'],indent=2))


if __name__=='__main__':main()
