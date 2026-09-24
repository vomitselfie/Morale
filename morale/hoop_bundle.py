"""Reviewable multi-hoop bundles with native tiles, coordinates and overview PDF."""
import csv
import json
from pathlib import Path
import sys
import tempfile
import zipfile
from PySide6.QtCore import Qt,QPointF,QRectF,QMarginsF
from PySide6.QtGui import QImage,QPainter,QPen,QColor,QFont,QPdfWriter,QPageLayout,QPageSize
from .multihoop import split_design
from .model import Project
from .engine import generate


NOTES=[
    'The placement map is an overview, not actual-size printing. Coordinates are millimeters in the source design; X increases right and Y increases down.',
    'Tile centers place each hoop in source coordinates. Neighboring hoop fields overlap by twice the margin; their sewn content cores do not overlap.',
    'Verify paired alignment marks with needle positioning before sewing the design. Alignment crosses are temporary stitches in a separate first block with a pause; remove them after assembly.',
    'Splitting adds needle penetrations at seams and regenerates jumps/trims. It does not add seam tie stitches. Inspect and reinforce seam starts/ends as needed; test the assembly on scrap fabric.',
    'Source thread order is retained within each tile. All explicit operator stops are retained, including stops from stages outside that tile. Some formats encode pauses as thread changes. Needle assignments and machine-specific hoop compatibility must be checked on the machine.',
    'Disconnected occupied tiles can lack shared alignment marks. Use their center coordinates and a full-size source placement template to position them.',
    'Native stitch counts include alignment marks. Prepared counts include positions added for the machine format; its writer may add further stitches or controls. Counts are listed in placements.csv.',
]


def overview(project,plan):
    image=QImage(800,700,QImage.Format.Format_ARGB32); image.fill(QColor('white'))
    painter=QPainter(image); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    left,top,right,bottom=plan.bounds
    left-=plan.margin; top-=plan.margin; right+=plan.margin; bottom+=plan.margin
    scale=min(740/(right-left),620/(bottom-top)); cx,cy=(left+right)/2,(top+bottom)/2
    def point(x,y): return QPointF(400+(x-cx)*scale,350+(y-cy)*scale)
    painter.setFont(QFont('sans-serif',10))
    for tile in plan.tiles:
        x,y=tile.center
        rect=QRectF(point(x-plan.width/2,y-plan.height/2),point(x+plan.width/2,y+plan.height/2))
        painter.setPen(QPen(QColor('#7099be'),1,Qt.PenStyle.DashLine)); painter.setBrush(QColor(100,160,210,12)); painter.drawRect(rect)
        painter.setBrush(Qt.BrushStyle.NoBrush); painter.setPen(QPen(QColor('#88988c'),1))
        painter.drawRect(QRectF(point(tile.core[0],tile.core[1]),point(tile.core[2],tile.core[3])))
    for block in generate(project):
        previous=None; painter.setPen(QPen(QColor(block.color),.8))
        for stitch in block.stitches:
            p=point(stitch.x,stitch.y)
            if stitch.command=='stitch' and previous is not None: painter.drawLine(previous,p)
            if stitch.command in {'jump','stitch'}: previous=p
    for tile in plan.tiles:
        painter.setPen(QColor('#173d64'))
        painter.drawText(point(tile.core[0]+2,tile.core[1]+4),f'{tile.row+1}-{tile.column+1}')
        painter.setPen(QPen(QColor('#c13d35'),1))
        for mark in tile.marks:
            x,y=mark['position']; p=point(x,y)
            painter.drawLine(p+QPointF(-4,0),p+QPointF(4,0)); painter.drawLine(p+QPointF(0,-4),p+QPointF(0,4))
    painter.end(); return image


def map_pdf(image,manifest,path):
    writer=QPdfWriter(str(path)); writer.setResolution(144)
    writer.setPageLayout(QPageLayout(QPageSize(QPageSize.PageSizeId.A4),QPageLayout.Orientation.Portrait,QMarginsF(0,0,0,0)))
    writer.setTitle('Morale multi-hoop placement map')
    painter=QPainter(writer)
    if not painter.isActive(): raise OSError('Could not create the hoop placement map.')
    try:
        painter.scale(144/25.4,144/25.4)
        font=QFont('sans-serif'); font.setPixelSize(5); painter.setFont(font)
        painter.drawText(QPointF(12,16),'Multi-hoop placement overview')
        font.setPixelSize(3); painter.setFont(font)
        painter.drawText(QPointF(12,23),f"{len(manifest['tiles'])} placements · {manifest['hoop_width']} × {manifest['hoop_height']} mm hoops · overview is not actual size")
        painter.drawImage(QRectF(10,30,190,166),image)
        painter.drawText(QRectF(12,205,186,78),Qt.TextFlag.TextWordWrap,'\n\n'.join(NOTES[:4]))
        for start in range(0,len(manifest['tiles']),30):
            if not writer.newPage(): raise OSError('Could not add a map page.')
            painter.drawText(QPointF(12,16),'Hoop center coordinates (mm in source design)')
            for row,tile in enumerate(manifest['tiles'][start:start+30]):
                preparation=tile.get('export_preparation')
                counts=f"{tile['stitches']:,} native"
                if preparation:counts+=f" / {preparation['prepared_stitches']:,} prepared (+{preparation['subdivision_added_stitches']:,})"
                painter.drawText(QPointF(12,27+row*7),f"{tile['id']}    X {tile['center'][0]:.3f}    Y {tile['center'][1]:.3f}    {counts}")
            painter.drawText(QRectF(12,250,186,35),Qt.TextFlag.TextWordWrap,'Paired mark coordinates are in alignment.csv. '+NOTES[4]+' '+NOTES[5]+' '+NOTES[6])
    finally: painter.end()


def build_bundle(project,root,options):
    from .formats import export_machine,export_notes,EXPORT_FORMATS
    root=Path(root); root.mkdir(exist_ok=True)
    options=dict(options); extension=options.pop('extension','')
    if extension and extension not in EXPORT_FORMATS: raise ValueError('Choose a supported machine format.')
    plan=split_design(project,**options)
    project.save(root/'source.morale')
    manifest={'format':'morale-multihoop','version':1,'hoop_width':plan.width,'hoop_height':plan.height,'margin':plan.margin,'grid_columns':plan.columns,'grid_rows':plan.rows,'bounds':plan.bounds,'tiles':[],'notes':NOTES+(export_notes(extension) if extension else [])}
    for tile in plan.tiles:
        name=f'hoop-{tile.row+1}-{tile.column+1}'; native=f'{name}.morale'
        tile.project.save(root/native)
        preparation=export_machine(tile.project,root/f'{name}{extension}') if extension else None
        manifest['tiles'].append({'id':name,'center':tile.center,'core':tile.core,'project':native,'machine':f'{name}{extension}' if extension else None,'stitches':sum(s.command=='stitch' for b in generate(tile.project) for s in b.stitches),'marks':tile.marks,'export_preparation':preparation})
    image=overview(project,plan)
    if not image.save(str(root/'placement.png')): raise OSError('Could not write the hoop overview.')
    map_pdf(image,manifest,root/'placement.pdf')
    with (root/'alignment.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.writer(stream); writer.writerow(['Mark','Hoop','Source X mm','Source Y mm','Local X mm','Local Y mm'])
        for tile in manifest['tiles']:
            for mark in tile['marks']:
                x,y=mark['position']; writer.writerow([mark['id'],tile['id'],f'{x:.6f}',f'{y:.6f}',f'{x-tile["center"][0]:.6f}',f'{y-tile["center"][1]:.6f}'])
    with (root/'placements.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(['Hoop','Source X mm','Source Y mm','Native stitches','Prepared stitches','Added needle positions','Machine file'])
        for tile in manifest['tiles']:
            preparation=tile['export_preparation']
            writer.writerow([tile['id'],f"{tile['center'][0]:.6f}",f"{tile['center'][1]:.6f}",tile['stitches'],
                             preparation['prepared_stitches'] if preparation else '',preparation['subdivision_added_stitches'] if preparation else '',tile['machine'] or ''])
    (root/'plan.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    (root/'README.txt').write_text('\n\n'.join(manifest['notes']),encoding='utf-8')
    return manifest


def save_archive(root,target):
    from .batch import publish
    target=Path(target); temporary=None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent,suffix='.zip',delete=False) as stream:
            temporary=Path(stream.name)
        with zipfile.ZipFile(temporary,'w',compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(Path(root).iterdir()):
                if path.is_file(): archive.write(path,path.name)
        publish(temporary,target)
    finally:
        if temporary: temporary.unlink(missing_ok=True)


def worker_main(args):
    if len(args)!=3: return 2
    source,output,options=args
    from PySide6.QtWidgets import QApplication
    app=QApplication.instance() or QApplication([])
    try:
        path=Path(source)
        if path.stat().st_size>50_000_000: raise ValueError('Project exceeds the 50 MB worker limit.')
        project=Project.loads(path.read_text(encoding='utf-8'))
        build_bundle(project,Path(output)/'bundle',json.loads(options)); return 0
    except Exception as exc:
        (Path(output)/'error.json').write_text(json.dumps({'error':str(exc)[:8192]}),encoding='utf-8'); return 1


if __name__=='__main__':
    sys.exit(worker_main(sys.argv[2:]) if len(sys.argv)>1 and sys.argv[1]=='--worker' else 2)
