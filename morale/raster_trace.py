"""Deterministic color reduction and editable raster-region tracing."""
from collections import Counter
import base64
import json
import math
from pathlib import Path
import sys

from PySide6.QtCore import Qt,QBuffer,QByteArray,QIODevice
from PySide6.QtGui import QImageReader,QPainterPath

from .model import Project,DesignObject
from .engine import generate


def reduce_colors(histogram,count):
    boxes=[list(histogram)]
    while len(boxes)<count:
        choices=[(max(max(c[k] for c in box)-min(c[k] for c in box) for k in range(3)),sum(histogram[c] for c in box),i)
                 for i,box in enumerate(boxes) if len(box)>1]
        if not choices:
            break
        _,_,index=max(choices)
        box=boxes.pop(index)
        axis=max(range(3),key=lambda k:max(c[k] for c in box)-min(c[k] for c in box))
        box.sort(key=lambda c:(c[axis],c))
        half=sum(histogram[c] for c in box)/2
        accumulated=0
        split=1
        for i,color in enumerate(box[:-1],1):
            accumulated+=histogram[color]
            split=i
            if accumulated>=half:
                break
        boxes.extend([box[:split],box[split:]])
    return [tuple(round(sum(c[k]*histogram[c] for c in box)/sum(histogram[c] for c in box)) for k in range(3)) for box in boxes]


def trace_image(path,width=80,colors=6,resolution=128,ignore_white=True,minimum_region=4):
    if isinstance(width,bool) or not isinstance(width,(int,float)) or not math.isfinite(width) or not 1<=width<=300:
        raise ValueError('Choose a tracing width from 1 to 300 mm.')
    if type(colors) is not int or not 1<=colors<=16 or type(resolution) is not int or resolution not in {64,128,256} or type(ignore_white) is not bool or type(minimum_region) is not int or not 1<=minimum_region<=100:
        raise ValueError('Invalid raster tracing settings.')
    path=Path(path)
    if path.stat().st_size>20_000_000:
        raise ValueError('Raster files are limited to 20 MB.')
    reader=QImageReader(str(path))
    if bytes(reader.format()).lower() not in {b'png',b'jpeg',b'bmp',b'webp'}:
        raise ValueError('Choose a PNG, JPEG, BMP or WebP image.')
    size=reader.size()
    if size.width()<=0 or size.height()<=0 or size.width()*size.height()>16_777_216:
        raise ValueError('Raster images are limited to 16 megapixels.')
    reader.setAutoTransform(True)
    image=reader.read()
    if image.isNull():
        raise ValueError('Could not decode the raster image.')
    height=width*image.height()/image.width()
    if height>500 or height<.1:
        raise ValueError('Resulting height must be between 0.1 and 500 mm. Change width or crop the image.')
    scale=min(1,resolution/max(image.width(),image.height()))
    if scale<1:
        image=image.scaled(max(1,round(image.width()*scale)),max(1,round(image.height()*scale)),Qt.AspectRatioMode.IgnoreAspectRatio,Qt.TransformationMode.SmoothTransformation)
    w,h=image.width(),image.height()
    pixels=[]
    for y in range(h):
        for x in range(w):
            color=image.pixelColor(x,y)
            if color.alpha()<128:
                pixels.append(None)
                continue
            alpha=color.alpha()/255
            rgb=tuple(round(channel*alpha+255*(1-alpha)) for channel in (color.red(),color.green(),color.blue()))
            pixels.append(None if ignore_white and min(rgb)>=245 else rgb)
    histogram=Counter(p for p in pixels if p is not None)
    if not histogram:
        raise ValueError('No visible colored pixels remain. Include white or choose another image.')
    palette=reduce_colors(histogram,colors)
    mapping={color:min(range(len(palette)),key=lambda i:sum((a-b)**2 for a,b in zip(color,palette[i]))) for color in histogram}
    labels=[mapping[p] if p is not None else None for p in pixels]
    visited=set()
    removed=0
    for seed,label in enumerate(labels):
        if label is None or seed in visited:
            continue
        stack=[seed]
        region=[]
        visited.add(seed)
        while stack:
            index=stack.pop()
            region.append(index)
            x,y=index%w,index//w
            neighbors=[]
            if x: neighbors.append(index-1)
            if x+1<w: neighbors.append(index+1)
            if y: neighbors.append(index-w)
            if y+1<h: neighbors.append(index+w)
            for other in neighbors:
                if other not in visited and labels[other]==label:
                    visited.add(other)
                    stack.append(other)
        if len(region)<minimum_region:
            removed+=len(region)
            for index in region:
                labels[index]=None
    paths=[QPainterPath() for _ in palette]
    counts=Counter(label for label in labels if label is not None)
    for path_item in paths:
        path_item.setFillRule(Qt.FillRule.WindingFill)
    for y in range(h):
        x=0
        while x<w:
            label=labels[y*w+x]
            end=x+1
            while end<w and labels[y*w+end]==label:
                end+=1
            if label is not None:
                paths[label].addRect(x,y,end-x,1)
            x=end
    objects=[]
    for index in sorted(counts,key=lambda i:(-counts[i],i)):
        path_item=paths[index].simplified()
        bounds=path_item.boundingRect()
        contours=[]
        for polygon in path_item.toSubpathPolygons():
            ring=[[(p.x()-bounds.center().x())/bounds.width(),(p.y()-bounds.center().y())/bounds.height()] for p in polygon]
            if len(ring)>1 and ring[0]==ring[-1]: ring.pop()
            if len(ring)>=3: contours.append(ring)
        if not contours:
            continue
        rgb=palette[index]
        objects.append(DesignObject(name=f'Trace {path.stem} · color {len(objects)+1}'[:200],kind='compound',
            x=(bounds.center().x()/w-.5)*width,y=(bounds.center().y()/h-.5)*height,
            width=bounds.width()/w*width,height=bounds.height()/h*height,
            contours=contours,color='#%02x%02x%02x'%rgb,underlay=False,connect_fill=True))
    if not objects:
        raise ValueError('No regions remain. Reduce the minimum region size.')
    project=Project(name=path.stem[:200],objects=objects)
    try:
        project=Project.loads(project.dumps())
        generate(project)
    except ValueError as exc:
        raise ValueError(f'Trace exceeds supported geometry or stitch limits. Reduce resolution/colors or simplify the artwork. {exc}') from exc
    return project,image,{'resolution':[w,h],'palette':len(objects),'omitted_pixels':removed}


def worker_main(args):
    if len(args)!=3: return 2
    source,output,options=args
    root=Path(output)
    try:
        before=Path(source).stat()
        project,image,stats=trace_image(source,**json.loads(options))
        project.save(root/'trace.morale')
        from .preview_worker import create_preview
        create_preview(root/'trace.morale',root)
        info=json.loads((root/'preview.json').read_text())
        data=QByteArray()
        buffer=QBuffer(data)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        image.save(buffer,'PNG')
        info.update(project=project.dumps(),raster_png=base64.b64encode(bytes(data)).decode('ascii'),trace_stats=stats)
        after=Path(source).stat()
        if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):
            raise ValueError('Image changed during tracing. Generate another preview.')
        (root/'preview.json').write_text(json.dumps(info),encoding='utf-8')
        return 0
    except Exception as exc:
        (root/'preview.error.json').write_text(json.dumps({'error':str(exc)[:8192]}),encoding='utf-8')
        return 1


if __name__=='__main__':
    sys.exit(worker_main(sys.argv[2:]) if len(sys.argv)>1 and sys.argv[1]=='--worker' else 2)
