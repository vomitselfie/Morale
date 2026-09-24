"""Deterministic color reduction and editable raster-region tracing."""
from collections import Counter
import base64
import json
import math
from pathlib import Path
import sys

from PySide6.QtCore import Qt,QBuffer,QByteArray,QIODevice
from PySide6.QtGui import QImageReader,QPainterPath,QColorSpace,QImage

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


def srgb_image(image):
    source=image.colorSpace();target=QColorSpace(QColorSpace.NamedColorSpace.SRgb)
    assumed=not source.isValid()
    if assumed:
        result=image.convertToFormat(QImage.Format.Format_RGBA8888)
        result.setColorSpace(target)
    else:
        result=image.convertedToColorSpace(target,QImage.Format.Format_RGBA8888)
        if result.isNull(): raise ValueError('Could not convert the embedded image profile to sRGB.')
    return result,{'source':source.description()[:200] if not assumed else 'No usable embedded profile',
                   'target':'sRGB','assumed':assumed,'converted':not assumed and source!=target}


def trace_image(path,width=80,colors=6,resolution=128,ignore_white=True,minimum_region=4,method='pixels',smoothing=.15,palette_metric='rgb',border_white=False):
    if isinstance(width,bool) or not isinstance(width,(int,float)) or not math.isfinite(width) or not 1<=width<=300:
        raise ValueError('Choose a tracing width from 1 to 300 mm.')
    if not isinstance(method,str) or method not in {'pixels','smooth'}:
        raise ValueError('Choose pixel or smooth tracing.')
    if isinstance(smoothing,bool) or not isinstance(smoothing,(int,float)) or not math.isfinite(smoothing) or not 0<=smoothing<=1:
        raise ValueError('Smoothing must be between 0 and 1 mm.')
    resolutions={64,128,256} if method=='pixels' else {64,128,256,512,1024}
    if type(colors) is not int or not 1<=colors<=16 or type(resolution) is not int or resolution not in resolutions or type(ignore_white) is not bool or type(minimum_region) is not int or not 1<=minimum_region<=100:
        raise ValueError('Invalid raster tracing settings.')
    if type(border_white) is not bool:raise ValueError('Invalid border background setting.')
    if not isinstance(palette_metric,str) or palette_metric not in {'rgb','oklab'}:
        raise ValueError('Choose RGB or Oklab palette reduction.')
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
    image,color_profile=srgb_image(image)
    height=width*image.height()/image.width()
    if height>500 or height<.1:
        raise ValueError('Resulting height must be between 0.1 and 500 mm. Change width or crop the image.')
    scale=min(1,resolution/max(image.width(),image.height()))
    if scale<1:
        image=image.scaled(max(1,round(image.width()*scale)),max(1,round(image.height()*scale)),Qt.AspectRatioMode.IgnoreAspectRatio,Qt.TransformationMode.SmoothTransformation)
    source_image=image
    background={'mode':'all_white' if ignore_white else 'none'}
    if ignore_white and border_white:
        from .background_removal import remove_border_white
        image,background=remove_border_white(image);ignore_white=False
    if method=='smooth':
        from .smooth_trace import trace_regions
        project,image,stats=trace_regions(image,width,height,colors,ignore_white,minimum_region,smoothing,path.stem,palette_metric)
        stats['color_profile']=color_profile
        stats['background_removal']=background
        stats['artwork_size_mm']=[width,height]
        return project,source_image,stats
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
    from .raster_palette import quantize
    palette,color_mapping,palette_report=quantize(histogram,colors,palette_metric)
    indices={color:i for i,color in enumerate(palette)}
    mapping={color:indices[target] for color,target in color_mapping.items()}
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
    return project,source_image,{'background_removal':background,'resolution':[w,h],'palette':len(objects),'omitted_pixels':removed,'palette_reduction':palette_report,'color_profile':color_profile,'artwork_size_mm':[width,height]}


def worker_main(args):
    # Density labels require Qt's font database even in a windowless worker.
    import os
    from PySide6.QtGui import QGuiApplication
    os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
    application=QGuiApplication.instance() or QGuiApplication([])
    if len(args)!=3: return 2
    source,output,options=args
    root=Path(output)
    try:
        before=Path(source).stat()
        settings=json.loads(options)
        stitch_mode=settings.pop('stitch_mode','fill')
        stitch_settings=settings.pop('stitch_settings',{})
        overrides=settings.pop('stitch_overrides',{})
        seams=settings.pop('band_seams',{})
        branching=settings.pop('split_branches',False)
        branch_overlap=settings.pop('branch_overlap',0)
        finishing=settings.pop('finish_regions',False)
        trim_threshold=settings.pop('trim_threshold',5)
        internal_trims=settings.pop('internal_trims',False)
        keep_reference=settings.pop('keep_reference',False)
        expand_strokes=settings.pop('expand_strokes',False)
        remove_overlap=settings.pop('remove_overlap',False)
        overlap_allowance=settings.pop('overlap_allowance',.2)
        minimum_fill_area=settings.pop('minimum_fill_area',0)
        minimum_hole_area=settings.pop('minimum_hole_area',0)
        if type(remove_overlap) is not bool:raise ValueError('Invalid overlap removal setting.')
        if type(expand_strokes) is not bool:raise ValueError('Invalid SVG stroke expansion setting.')
        if type(keep_reference) is not bool:raise ValueError('Invalid artwork reference setting.')
        if type(finishing) is not bool: raise ValueError('Invalid automatic finishing setting.')
        if type(branching) is not bool: raise ValueError('Invalid branch splitting setting.')
        route=settings.pop('reduce_travel',False)
        optimize_angles=settings.pop('optimize_fill_angles',False)
        route_fill=settings.pop('route_fill',False)
        if type(route_fill) is not bool:raise ValueError('Invalid fill-run routing setting.')
        if type(optimize_angles) is not bool:raise ValueError('Invalid fill-angle optimization setting.')
        reverse=settings.pop('reverse_for_travel',False)
        thread_catalog=settings.pop('thread_catalog','')
        color_metric=settings.pop('color_metric','oklab')
        if type(route) is not bool: raise ValueError('Invalid travel ordering setting.')
        if Path(source).suffix.lower()=='.svg':
            from .vector_artwork import vector_artwork
            project,image,stats=vector_artwork(source,expand_strokes=expand_strokes,**settings)
        else:project,image,stats=trace_image(source,**settings)
        if remove_overlap:
            from .trace_overlap import remove_covered_fill
            project,stats['overlap']=remove_covered_fill(project,overlap_allowance)
        from .trace_details import filter_small_fills,fill_small_holes
        project,stats['hole_filter']=fill_small_holes(project,minimum_hole_area)
        project,stats['detail_filter']=filter_small_fills(project,minimum_fill_area)
        if branching:
            from .branch_regions import split_branches
            project,stats['branch_splits']=split_branches(project,branch_overlap)
        from .auto_digitize import choose_stitches
        project,stats['stitch_decisions']=choose_stitches(project,stitch_mode,overrides,seams)
        from .trace_stitch_settings import apply_stitch_settings
        project,stats['stitch_settings']=apply_stitch_settings(project,stitch_settings)
        if route_fill:
            for obj in project.objects:
                if obj.stitch_type=='fill':obj.route_fill=True
        if optimize_angles:
            from .trace_angles import choose_fill_angles
            project,stats['fill_angles']=choose_fill_angles(project)
        from .trace_threads import match_trace_threads
        project,stats['thread_matches']=match_trace_threads(project,thread_catalog,color_metric)
        stats['thread_colors']=len({obj.color.lower() for obj in project.objects})
        if route:
            from .trace_routing import reduce_travel
            project,stats['routing']=reduce_travel(project,reverse)
        if finishing:
            from .trace_finishing import finish_regions
            project,stats['finishing']=finish_regions(project,trim_threshold,internal_trims)
        from .trace_quality import conversion_quality
        blocks=generate(project)
        stats['quality']=conversion_quality(project,blocks)
        from .density_review import measure_density,measure_thread_density,render_density
        stats['quality']['density'],density_cells=measure_density(blocks)
        density_image=render_density(stats['quality']['density'],density_cells)
        density_data=QByteArray();density_buffer=QBuffer(density_data)
        density_buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        if not density_image.save(density_buffer,'PNG'):raise ValueError('Could not render the density review.')
        density_png=base64.b64encode(bytes(density_data)).decode('ascii')
        stats['quality']['thread_density'],thread_cells=measure_thread_density(blocks)
        thread_image=render_density(stats['quality']['thread_density'],thread_cells,thread_length=True)
        thread_data=QByteArray();thread_buffer=QBuffer(thread_data);thread_buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        if not thread_image.save(thread_buffer,'PNG'):raise ValueError('Could not render the thread density review.')
        thread_density_png=base64.b64encode(bytes(thread_data)).decode('ascii')
        stats['quality']['thread_matches']=stats['thread_matches']
        stats['quality']['background_removal']=stats.get('background_removal')
        stats['quality']['color_profile']=stats['color_profile']
        stats['quality']['palette_reduction']=stats.get('palette_reduction')
        stats['quality']['stitch_settings']=stats['stitch_settings']
        stats['quality']['finishing']=stats.get('finishing')
        stats['quality']['fill_angles']=stats.get('fill_angles')
        stats['quality']['routing']=stats.get('routing')
        stats['quality']['overlap']=stats.get('overlap')
        stats['quality']['detail_filter']=stats['detail_filter']
        stats['quality']['hole_filter']=stats['hole_filter']
        stats['quality']['artwork_notes']=stats.get('notes',[])
        data=QByteArray();buffer=QBuffer(data)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        if not image.save(buffer,'PNG'):raise ValueError('Could not encode the sampled artwork.')
        raster_png=base64.b64encode(bytes(data)).decode('ascii')
        if keep_reference:
            project.reference={'png':raster_png,'name':(Path(source).name+' (sampled)')[:200],
                'x':0.,'y':0.,'width':stats['artwork_size_mm'][0],'height':stats['artwork_size_mm'][1],
                'rotation':0.,'opacity':.4,'visible':True}
            from .reference import validate_reference
            validate_reference(project.reference)
        project.save(root/'trace.morale')
        from .preview_worker import create_preview
        marked_starts={obj.id for obj in project.objects if
            (obj.kind=='satin' and obj.points[:2]==obj.points[-2:]) or
            (obj.kind=='path' and obj.points[0]==obj.points[-1])}
        create_preview(root/'trace.morale',root,marked_starts)
        info=json.loads((root/'preview.json').read_text())
        info.update(project=project.dumps(),raster_png=raster_png,density_png=density_png,thread_density_png=thread_density_png,trace_svg=stats.pop('svg',''),trace_stats=stats)
        from .review_panels import aligned_panels
        from PySide6.QtSvg import QSvgRenderer
        renderer=QSvgRenderer(info['trace_svg'].encode('utf-8')) if info['trace_svg'] else None
        panels,frame=aligned_panels(info,image,renderer,blocks=blocks,marked_starts=marked_starts)
        info['aligned_previews']={}
        for name,panel in zip(('source','vectors','stitches'),panels):
            data=QByteArray();buffer=QBuffer(data);buffer.open(QIODevice.OpenModeFlag.WriteOnly)
            if not panel.save(buffer,'PNG'):raise ValueError('Could not encode the aligned conversion preview.')
            info['aligned_previews'][name]=base64.b64encode(bytes(data)).decode('ascii')
        from .inspection_geometry import inspection_layers
        info['inspection_svg']=inspection_layers(info,blocks,frame,marked_starts)
        info['preview_frame_mm']=[frame.x(),frame.y(),frame.width(),frame.height()]
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
