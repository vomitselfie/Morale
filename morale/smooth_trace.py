"""Shared-boundary color vectorization before embroidery stitch generation."""
import xml.etree.ElementTree as ET
from collections import Counter
from .model import Project
from .svg_import import import_svg_text


def trace_regions(image,width,height,colors,ignore_white,minimum_region,smoothing,name,palette_metric='rgb'):
    import vtracer
    from .raster_palette import quantize
    pixels=[]; histogram=Counter()
    visible=0; background=False
    for y in range(image.height()):
        for x in range(image.width()):
            color=image.pixelColor(x,y)
            alpha=color.alpha()/255
            rgb=tuple(round(channel*alpha+255*(1-alpha)) for channel in (color.red(),color.green(),color.blue()))
            opaque=color.alpha()>=128
            white=opaque and min(rgb)>=245
            background=background or white
            pixels.append((255,255,255) if ignore_white and white else rgb if opaque else None)
            if opaque and not(ignore_white and white): histogram[rgb]+=1
            visible+=opaque and not(ignore_white and white)
    if not visible:
        raise ValueError('No visible colored pixels remain. Include white or choose another image.')
    palette,mapping,palette_report=quantize(histogram,colors,palette_metric)
    labels=[mapping.get(rgb,rgb) for rgb in pixels]
    # Filter connected patches explicitly: the backend treats transparent borders
    # differently from opaque backgrounds. Never let that change this control.
    seen=set(); w=image.width(); h=image.height()
    for seed,color in enumerate(labels):
        if seed in seen or color is None or (ignore_white and color==(255,255,255)): continue
        stack=[seed]; seen.add(seed); region=[]
        while stack:
            pos=stack.pop(); region.append(pos); x=pos%w; y=pos//w
            neighbors=[]
            if x: neighbors.append(pos-1)
            if x+1<w: neighbors.append(pos+1)
            if y: neighbors.append(pos-w)
            if y+1<h: neighbors.append(pos+w)
            for neighbor in neighbors:
                if neighbor not in seen and labels[neighbor]==color:
                    seen.add(neighbor); stack.append(neighbor)
        if len(region)<minimum_region**2:
            for pos in region: labels[pos]=None
    # The backend must trace the same perceptual labels used by patch filtering.
    # Keep legacy RGB backend input for reproducible comparison.
    rgba=bytes(channel for rgb,label in zip(pixels,labels) for channel in ((*(label if palette_metric=='oklab' else rgb),255) if label is not None else (0,0,0,0)))
    trace_palette=[('#%02x%02x%02x'%rgb) for rgb in palette]
    if ignore_white and background: trace_palette.append('#ffffff')
    pixel_size=min(width/image.width(),height/image.height())
    config=vtracer.Config(mode='spline',hierarchical='cutout',max_colors=colors+int(ignore_white and background),
        palette=trace_palette,filter_speckle=1,path_precision=4,optimize=1,
        simplify=smoothing/pixel_size if smoothing else None)
    vector=config.convert_pixels(bytes(rgba),image.width(),image.height())
    if len(vector.encode('utf-8'))>2_000_000:
        raise ValueError('Traced SVG exceeds 2 MB. Reduce resolution/colors or increase smoothing.')
    root=ET.fromstring(vector)
    if ignore_white:
        for element in list(root):
            color=element.get('fill','').lstrip('#')
            if len(color)==3: color=''.join(c*2 for c in color)
            if len(color)==6 and min(int(color[i:i+2],16) for i in (0,2,4))>=245:
                root.remove(element)
    root.set('viewBox',f'0 0 {image.width()} {image.height()}')
    root.set('width',f'{width:.12g}mm'); root.set('height',f'{height:.12g}mm')
    root.set('preserveAspectRatio','none')
    vector=ET.tostring(root,encoding='unicode')
    try:
        imported=import_svg_text(vector,center_artwork=False)
    except ValueError as exc:
        raise ValueError(f'Trace could not become editable embroidery. Reduce resolution/colors or simplify the artwork. {exc}') from exc
    for index,obj in enumerate(imported.objects,1):
        obj.name=f'Trace {name} · region {index}'[:200]
    project=Project(name=name[:200],objects=imported.objects)
    return project,image,{'method':'smooth','resolution':[image.width(),image.height()],
        'palette':len({o.color.lower() for o in project.objects}),'regions':len(project.objects),
        'contour_points':sum(len(ring) for o in project.objects for ring in o.contours),
        'minimum_region':minimum_region,'smoothing_mm':smoothing,'svg':vector,
        'notes':imported.notices,'palette_reduction':palette_report}
