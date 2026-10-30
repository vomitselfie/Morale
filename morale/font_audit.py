"""Reproducible bundled-font layout samples; not physical sew-out validation.

Run with ``python -m morale.font_audit --output NEW_DIRECTORY``.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path


def run(destination):
    from PySide6.QtWidgets import QApplication
    from .embroidery_fonts import FONT_DIR,load_font,height_range,make_font_lettering
    from .engine import generate
    from .model import Project
    root=Path(destination);root.mkdir(parents=True,exist_ok=False)
    os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
    application=QApplication.instance() or QApplication([])
    results=[]
    load_font.cache_clear()
    for font_path in sorted(FONT_DIR.glob('*/font.json.gz')):
        ident=font_path.parent.name
        record={'font':ident,'layouts':[]}
        try:
            record['sha256']=hashlib.sha256(font_path.read_bytes()).hexdigest()
            font=load_font(ident)
            text=''.join(c for c,g in font['glyphs'].items() if len(c)==1 and not c.isspace() and g.get('pieces'))[:3]
            height=math.ceil(height_range(font)[0]*100)/100
            record.update(text=text,height_mm=height)
        except Exception as exc:
            record['layouts']=[{'layout':layout,'passed':False,'error':f'Font loading failed: {exc}'} for layout in ('straight','curved','path')]
            results.append(record)
            continue
        for layout in ('straight','curved','path'):
            try:
                options={'layout':layout,'curve':60}
                if layout=='path':
                    straight=make_font_lettering(text,ident,height)
                    span=straight.width+2*height
                    options['baseline']=[[-span/2,0],[0,-height/2],[span/2,0]]
                obj=make_font_lettering(text,ident,height,**options)
                project=Project(objects=[obj]);blocks=generate(project)
                if blocks!=generate(Project.loads(project.dumps())):
                    raise ValueError('Generated stitches changed after save/reopen.')
                count=sum(s.command=='stitch' for block in blocks for s in block.stitches)
                if not count:raise ValueError('No sewing stitches were generated.')
                record['layouts'].append({'layout':layout,'passed':True,'stitches':count})
            except Exception as exc:
                record['layouts'].append({'layout':layout,'passed':False,'error':str(exc)})
        results.append(record)
    passed=bool(results) and all(item['passed'] for font in results for item in font['layouts'])
    report={'passed':passed,'physical_sewouts':False,'scope':'First three available glyphs per font, lower design height rounded up to 0.01 mm; straight, 60-degree arc and three-point path.', 'results':results}
    (root/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    total=sum(len(font['layouts']) for font in results)
    successes=sum(item['passed'] for font in results for item in font['layouts'])
    print(f'{len(results)} fonts; {successes}/{total} layout samples passed. Report: {root / "report.json"}')
    return 0 if passed else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True,help='New directory for the audit report')
    return run(parser.parse_args().output)


if __name__=='__main__':raise SystemExit(main())
