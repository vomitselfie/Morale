"""Generate an internal artwork corpus and exercise the complete digitizing pipeline."""
import argparse
from collections import Counter
from datetime import datetime,timezone
from importlib.metadata import version
import json
import hashlib
import math
from pathlib import Path

from PySide6.QtGui import QImage,QPainter,QColor,QTransform,QPdfWriter,QPageSize,QPageLayout,QPen,QPainterPath,QFont
from PySide6.QtCore import QRectF
from PySide6.QtWidgets import QApplication
from PySide6.QtSvg import QSvgRenderer

from .model import Project,DesignObject
from .auto_digitize import outline_path,area,difference_area
from .raster_trace import worker_main
from .svg_import import import_svg_text
from .formats import EXPORT_FORMATS,export_machine,import_machine,export_notes
from .engine import generate,segment_inside
from .comparison import compare_commands
from .stitch_rendering import draw_stitch_path
from .artwork_fidelity import visible_colors,color_geometry


def sewn_path_check(comparison):
    geometry=comparison.get('sewn_geometry',{})
    return all(geometry.get(direction,{}).get('complete') is True
               and geometry[direction].get('samples',0)>0
               and geometry[direction].get('outside_samples')==0
               for direction in ('decoded_outside_source','source_outside_decoded'))


def fixtures():
    def circle(radius):return [[radius*math.cos(i*math.tau/128)/40,radius*math.sin(i*math.tau/128)/40] for i in range(128)]
    ring=DesignObject(kind='compound',width=40,height=40,contours=[circle(10),circle(8)])
    ribbon=[]
    for radius,indices in ((11,range(97)),(9,range(96,-1,-1))):
        ribbon.extend([[radius*math.cos(math.radians(-135+270*i/96))/40,
                        radius*math.sin(math.radians(-135+270*i/96))/40] for i in indices])
    tee=DesignObject(kind='polygon',width=12,height=24,points=[[-.5,-.5],[.5,-.5],[.5,-.4],[.1,-.4],[.1,.5],[-.1,.5],[-.1,-.4],[-.5,-.4]])
    holed=DesignObject(kind='compound',width=28,height=24,rotation=12,
        contours=[[[-.5,-.5],[.5,-.5],[.5,.5],[-.5,.5]],[[-.15,-.15],[.15,-.15],[.15,.15],[-.15,.15]]])
    return [
        ('broad-fill',[DesignObject(kind='ellipse',width=20,height=20)],{'fill':1},False),
        ('closed-band',[ring],{'satin':1},False),
        ('curved-ribbon',[DesignObject(kind='compound',width=40,height=40,contours=[ribbon])],{'satin':1},False),
        ('thin-line',[DesignObject(kind='rectangle',width=.6,height=24)],{'running':1},False),
        ('offset-column',[DesignObject(kind='rectangle',x=-8,y=4,width=3,height=18)],{'satin':1},False),
        ('branching-tee',[tee],{'satin':2},True),
        ('adjacent-colors',[DesignObject(kind='rectangle',x=-5,width=10,height=20,color='#cc3355'),
                            DesignObject(kind='rectangle',x=5,width=10,height=20,color='#2266bb')],{'fill':2},False),
        ('overlapping-colors',[DesignObject(kind='rectangle',width=24,height=24,color='#2266bb'),
                               DesignObject(kind='rectangle',width=12,height=12,color='#cc3355')],{'fill':2},False),
        ('enclosed-white',[DesignObject(kind='rectangle',width=20,height=20,color='#2266bb'),
                           DesignObject(kind='rectangle',width=4,height=8,color='#ffffff')],{'fill':2},False),
        ('holed-fill-routing',[holed],{'fill':1},False),
        ('reduced-palette-fill',[DesignObject(kind='rectangle',x=-10+i*4,width=4,height=20,color='#%02x%02x%02x'%(v,v,v))
                                 for i,v in enumerate((32,64,96,128,176,224))],{'fill':3},False)]


def make_source(objects,path):
    image=QImage(400,400,QImage.Format.Format_RGB32);image.fill(QColor('white'))
    transform=QTransform();transform.translate(200,200);transform.scale(10,10)
    painter=QPainter(image);painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    for obj in objects:painter.fillPath(transform.map(outline_path(obj.rings())),QColor(obj.color))
    painter.end()
    if not image.save(str(path)):raise OSError('Could not write benchmark artwork.')


def make_stitches(blocks,path):
    image=QImage(400,400,QImage.Format.Format_RGB32);image.fill(QColor('white'))
    painter=QPainter(image);painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.translate(200,200);painter.scale(10,10);previous=(0,0)
    for block in blocks:
        drawing=QPainterPath()
        for stitch in block.stitches:
            point=(stitch.x,stitch.y)
            if stitch.command=='stitch':drawing.moveTo(*previous);drawing.lineTo(*point)
            if stitch.command in {'stitch','jump'}:previous=point
        draw_stitch_path(painter,drawing,block.color,.1)
    painter.end()
    if not image.save(str(path)):raise OSError('Could not write benchmark stitch rendering.')


def build_report(destination):
    root=Path(destination);root.mkdir(parents=True,exist_ok=False)
    report={'generated_at':datetime.now(timezone.utc).isoformat(),
        'versions':{name:version(name) for name in ('PySide6','vtracer','svgelements','pyembroidery')},
        'scope':'Generated internal artwork only. Bounds checks are not command/travel equivalence or physical sew-out certification.',
        'external_files_tested':False,'physical_sewouts_tested':False,
        'criteria':{'vector_symmetric_area_ratio_max':.08,'color_region_symmetric_area_ratio_max':.08,'color_match_tolerance_oklab_x100':2,'export_sewn_bounds_tolerance_mm':.15},'cases':[]}
    modules=Path(__file__).parent
    implementation=hashlib.sha256()
    for path in sorted(modules.glob('*.py')):
        implementation.update(path.name.encode());implementation.update(path.read_bytes())
    report['implementation_sha256']=implementation.hexdigest()
    for name,objects,expected,branching in fixtures():
        folder=root/name;folder.mkdir();source=folder/'source.png';make_source(objects,source)
        options={'width':40,'method':'smooth','resolution':512,'colors':6,'minimum_region':1,'smoothing':.15,
                 'stitch_mode':'auto','split_branches':branching,'reduce_travel':True,'reverse_for_travel':True,
                 'finish_regions':True,'internal_trims':True,'trim_threshold':5,'keep_reference':True}
        if name=='enclosed-white':options.update(stitch_mode='fill',border_white=True,colors=2)
        if name=='overlapping-colors':options.update(stitch_mode='fill')
        if name=='holed-fill-routing':options.update(stitch_mode='fill',route_fill=True,optimize_fill_angles=True)
        if name=='reduced-palette-fill':
            options.update(colors=3,palette_metric='oklab',stitch_mode='fill',route_fill=True,
                           stitch_settings={'fill_spacing':.65,'stitch_length':3.5,'pull_compensation':.15,'underlay':'off'})
        row={'name':name,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
             'settings':options,'expected_types':expected,'exports':{}};report['cases'].append(row)
        try:
            if worker_main([str(source),str(folder),json.dumps(options)]):
                raise ValueError(json.loads((folder/'preview.error.json').read_text())['error'])
            info=json.loads((folder/'preview.json').read_text());project=Project.loads(info['project'])
            (folder/'vectors.svg').write_text(info['trace_svg'],encoding='utf-8')
            traced=import_svg_text(info['trace_svg'],center_artwork=False)
            _,reference=visible_colors(objects)
            _,actual=visible_colors(traced.objects)
            ratio=difference_area(reference,actual)/area(reference)
            types=dict(Counter(o.stitch_type for o in project.objects))
            row.update(vector_area_error_ratio=ratio,stitch_types=types,type_check=types==expected,
                vector_check=ratio<=.08,quality=info['trace_stats']['quality'],routing=info['trace_stats'].get('routing'))
            if name!='reduced-palette-fill':
                row['color_geometry']=color_geometry(objects,traced.objects)
                row['color_geometry_check']=row['color_geometry']['error_ratio']<=.08
            else:row['color_geometry_skip']='Intentional palette reduction; measured separately by palette_check.'
            if name!='reduced-palette-fill' and all(o.stitch_type=='fill' for o in project.objects):
                row['planned_color_geometry']=color_geometry(objects,project.objects)
                row['planned_color_geometry_check']=row['planned_color_geometry']['error_ratio']<=.08
            else:row['planned_color_geometry_skip']='Area comparison applies to filled regions; running/satin geometry or intentional palette reduction needs separate criteria.'
            blocks=generate(project)
            if name=='reduced-palette-fill':
                palette=info['trace_stats']['palette_reduction']
                row['palette_check']=palette['metric']=='oklab' and palette['source_colors']>len({o.color for o in project.objects}) and palette['fit_error_after']<=palette['fit_error_before']+1e-12
                row['stitch_settings_check']=all(o.spacing==.65 and o.stitch_length==3.5 and o.pull_compensation==.15 and not o.underlay for o in project.objects)
                row['result_palette']=sorted({o.color for o in project.objects})
            if name=='holed-fill-routing':
                rings=project.objects[0].rings();previous=(0.,0.);contained=True
                for block in blocks:
                    for stitch in block.stitches:
                        point=(stitch.x,stitch.y)
                        if stitch.command=='stitch' and not segment_inside(previous,point,rings[0],rings[1:]):contained=False
                        if stitch.command in {'stitch','jump'}:previous=point
                row['native_sewn_containment']=contained
            make_stitches(blocks,folder/'stitches.png')
            for extension in sorted(EXPORT_FORMATS):
                path=folder/('machine'+extension)
                try:
                    export_machine(project,path);imported=import_machine(path)
                    comparison=compare_commands(blocks,generate(imported.project))
                    a=comparison['source']['sewn_bounds_mm'];b=comparison['decoded']['sewn_bounds_mm']
                    passed=a is not None and b is not None and all(abs(x-y)<=.15 for x,y in zip(a,b))
                    row['exports'][extension]={'bounds_check':passed,'sewn_path_check':sewn_path_check(comparison),'comparison':comparison,
                        'import_notes':imported.notes,'export_notes':export_notes(extension)}
                except Exception as exc:row['exports'][extension]={'bounds_check':False,'sewn_path_check':False,'error':str(exc)}
            row['artwork_checks_passed']=row['type_check'] and row['vector_check'] and row.get('planned_color_geometry_check',True) and row.get('color_geometry_check',True) and row.get('native_sewn_containment',True) and row.get('palette_check',True) and row.get('stitch_settings_check',True)
            row['checks_passed']=row['artwork_checks_passed'] and all(x['bounds_check'] and x['sewn_path_check'] for x in row['exports'].values())
        except Exception as exc:row.update(checks_passed=False,error=str(exc))
    report['artwork_checks_passed']=all(row.get('artwork_checks_passed',False) for row in report['cases'])
    report['checks_passed']=all(row['checks_passed'] for row in report['cases'])
    (root/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    write_pdf(root,report)
    return report


def write_pdf(root,report):
    writer=QPdfWriter(str(root/'review.pdf'));writer.setResolution(72)
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4));writer.setPageOrientation(QPageLayout.Orientation.Landscape)
    painter=QPainter(writer)
    try:
        for index,row in enumerate(report['cases']):
            if index:writer.newPage()
            painter.drawText(20,25,f"Morale image digitizing · {row['name']}")
            folder=root/row['name']
            for col,(title,filename) in enumerate((('Generated artwork','source.png'),('Traced vectors','vectors.svg'),('Stitches · same 40 mm canvas','stitches.png'))):
                x=20+col*260;painter.drawText(x,55,title);rect=QRectF(x,70,240,240)
                if filename.endswith('.svg') and (folder/filename).exists():QSvgRenderer(str(folder/filename)).render(painter,rect)
                elif (folder/filename).exists():painter.drawImage(rect,QImage(str(folder/filename)))
            painter.save();font=QFont(painter.font());font.setPointSize(8);painter.setFont(font)
            painter.drawText(20,325,'All panels share the same physical frame. Light stitches have gray contrast outlines for visibility; thread colors are unchanged.')
            painter.restore()
            if 'error' in row:lines=[row['error']]
            else:
                lines=[f"Stitch types: {row['stitch_types']} (expected {row['expected_types']})",
                    f"Vector symmetric area difference: {row['vector_area_error_ratio']:.2%}",
                    f"Sampled sewn-path checks: {sum(e.get('sewn_path_check',False) for e in row['exports'].values())}/{len(row['exports'])}",
                    f"Export bounds checks: {sum(e['bounds_check'] for e in row['exports'].values())}/{len(row['exports'])}",
                    f"Identical command sequences: {sum(e.get('comparison',{}).get('same_command_sequence',False) for e in row['exports'].values())}/{len(row['exports'])}",
                    f"Formats with sampled sewn-path differences: {sum(any(e.get('comparison',{}).get('sewn_geometry',{}).get(k,{}).get('outside_samples',0) for k in ('decoded_outside_source','source_outside_decoded')) for e in row['exports'].values())}/{len(row['exports'])} (see report.json)",
                    'Detailed command counts, path lengths, colors, control differences and notes are in report.json.']
                if 'color_geometry' in row:lines.append(f"Color-region area difference: {row['color_geometry']['error_ratio']:.2%}")
                if 'planned_color_geometry' in row:lines.append(f"Planned fill color-region difference: {row['planned_color_geometry']['error_ratio']:.2%}")
                if 'palette_check' in row:lines.append(f"Palette reduction / custom stitch settings: {row['palette_check']} / {row['stitch_settings_check']}")
                if 'native_sewn_containment' in row:lines.append(f"Native sewn segments inside traced material: {row['native_sewn_containment']}")
            lines+=['These are generated fixtures, not external files or physical sew-outs.',
                    'An export bounds pass does not establish command or travel equivalence.']
            for line_number,line in enumerate(lines):painter.drawText(20,340+line_number*22,line[:130])
    finally:painter.end()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();app=QApplication.instance() or QApplication([])
    report=build_report(args.output)
    print(f"{len(report['cases'])} cases; checks {'passed' if report['checks_passed'] else 'failed'}; {args.output / 'review.pdf'}")
    return 0 if report['checks_passed'] else 1


if __name__=='__main__':raise SystemExit(main())
