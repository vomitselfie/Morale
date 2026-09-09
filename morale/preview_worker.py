"""Isolated, read-only design decoding and thumbnail rendering."""
import json
from pathlib import Path
import sys

from PySide6.QtCore import QPointF
from PySide6.QtGui import QImage,QPainter,QPainterPath,QPen,QColor

from .model import Project
from .formats import import_machine
from .engine import generate


def create_preview(source,output):
    source,output=Path(source),Path(output)
    before=source.stat()
    notes=[]
    if source.suffix.lower()=='.morale':
        if before.st_size>50_000_000:
            raise ValueError('Project exceeds 50 MB.')
        project=Project.loads(source.read_text(encoding='utf-8'))
    else:
        imported=import_machine(source)
        project,notes=imported.project,imported.notes
    blocks=generate(project)
    points=[(s.x,s.y) for b in blocks for s in b.stitches]
    first=next((s for b in blocks for s in b.stitches if s.command in {'stitch','jump'}),None)
    if first and first.command=='stitch':
        points.append((0.,0.))
    if points:
        xs,ys=zip(*points)
        left,right,top,bottom=min(xs),max(xs),min(ys),max(ys)
    else:
        left,right,top,bottom=-project.hoop_width/2,project.hoop_width/2,-project.hoop_height/2,project.hoop_height/2
    image=QImage(360,360,QImage.Format.Format_RGB32)
    image.fill(QColor('#fffdf8'))
    painter=QPainter(image)
    try:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        scale=min(330/max(1,right-left),330/max(1,bottom-top))
        painter.translate(180,180)
        painter.scale(scale,scale)
        painter.translate(-(left+right)/2,-(top+bottom)/2)
        previous=(0.,0.)
        for block in blocks:
            path=QPainterPath()
            for stitch in block.stitches:
                position=(stitch.x,stitch.y)
                if stitch.command=='stitch':
                    path.moveTo(*previous)
                    path.lineTo(*position)
                if stitch.command in {'jump','stitch'}:
                    previous=position
            color=QColor(block.color)
            painter.setPen(QPen(color.darker(160) if color.lightness()>180 else color,1/scale))
            painter.drawPath(path)
    finally:
        painter.end()
    after=source.stat()
    if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):
        raise ValueError('The file changed while its preview was being read. Select it again.')
    if not image.save(str(output/'preview.png')):
        raise OSError('Could not write the temporary preview image.')
    info={'name':project.name,'objects':len(project.objects),'stitches':sum(s.command=='stitch' for b in blocks for s in b.stitches),
          'colors':len({b.color for b in blocks}),'width':right-left,'height':bottom-top,
          'size':after.st_size,'mtime_ns':after.st_mtime_ns,'notes':notes}
    (output/'preview.json').write_text(json.dumps(info,ensure_ascii=False),encoding='utf-8')


def worker_main(args):
    if len(args)!=2:
        return 2
    try:
        create_preview(*args)
        return 0
    except Exception as exc:
        # Windowed Windows builds have no reliable stderr; keep errors in the
        # same temporary-file protocol used for successful previews.
        try:
            (Path(args[1])/'preview.error.json').write_text(json.dumps({'error':str(exc)[:8192]}),encoding='utf-8')
        except OSError:
            pass
        print(str(exc),file=sys.stderr)
        return 1


if __name__=='__main__':
    sys.exit(worker_main(sys.argv[1:]))
