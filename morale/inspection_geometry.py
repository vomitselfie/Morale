"""Resolution-independent inspection layers, prepared from worker geometry."""
import xml.etree.ElementTree as ET
import math
from .trace_quality import LONG_STITCH_MM
from .review_panels import frame_transform
from .stitch_rendering import needs_contrast


def inspection_layers(info,blocks,frame,marked_starts=()):
    from PySide6.QtCore import QRectF
    transform=frame_transform(frame)
    width,height=info['trace_stats']['artwork_size_mm']
    page=transform.mapRect(QRectF(-width/2,-height/2,width,height))
    def number(value):return format(value,'.9g')
    def document():
        root=ET.Element('svg',xmlns='http://www.w3.org/2000/svg',width='640',height='640',viewBox='0 0 640 640')
        ET.SubElement(root,'rect',width='640',height='640',fill='white')
        return root
    def finish(root):
        ET.SubElement(root,'rect',x=number(page.x()),y=number(page.y()),width=number(page.width()),height=number(page.height()),
                      fill='none',stroke='#a8a8a8',**{'stroke-width':'1','stroke-dasharray':'4 2'})
        return ET.tostring(root,encoding='unicode')
    result={}
    if info.get('trace_svg'):
        root=document();artwork=ET.fromstring(info['trace_svg'])
        # Qt SVG Tiny skips nested SVG documents. Flatten the prepared root
        # into groups while retaining its viewBox mapping and root styling.
        x,y,w,h=map(float,artwork.get('viewBox','').replace(',',' ').split())
        if w<=0 or h<=0:raise ValueError('Invalid prepared artwork viewBox.')
        group=ET.SubElement(root,'g',transform=f'translate({number(page.x())} {number(page.y())}) scale({number(page.width()/w)} {number(page.height()/h)}) translate({number(-x)} {number(-y)})')
        styles={key:value for key,value in artwork.attrib.items() if key not in {'x','y','width','height','viewBox','preserveAspectRatio','version'}}
        content=ET.SubElement(group,'g',styles)
        content.extend(list(artwork))
        result['vectors']=finish(root)
    root=document();previous=(0.,0.);long_commands=[]
    for block in blocks:
        commands=[]
        for stitch in block.stitches:
            point=(stitch.x,stitch.y)
            if stitch.command=='stitch':
                a=transform.map(*previous);b=transform.map(*point)
                command=f'M {number(a[0])} {number(a[1])} L {number(b[0])} {number(b[1])}'
                commands.append(command)
                if math.dist(previous,point)>LONG_STITCH_MM:long_commands.append(command)
            if stitch.command in {'stitch','jump'}:previous=point
        if needs_contrast(block.color):
            ET.SubElement(root,'path',d=' '.join(commands),fill='none',stroke='#666666',**{'stroke-width':'2.2','stroke-linecap':'square','data-preview-contrast':'true'})
        ET.SubElement(root,'path',d=' '.join(commands),fill='none',stroke=block.color,**{'stroke-width':'1','stroke-linecap':'square'})
    for block in blocks:
        if block.object_id not in marked_starts:continue
        first=next((s for s in block.stitches if s.command=='stitch'),None)
        if first is not None:
            x,y=transform.map(first.x,first.y)
            ET.SubElement(root,'circle',cx=number(x),cy=number(y),r='6',fill='none',stroke='#1765df',**{'stroke-width':'1.5'})
    result['stitches']=finish(root)
    if long_commands:
        review=ET.Element('svg',xmlns='http://www.w3.org/2000/svg',width='640',height='640',viewBox='0 0 640 640')
        ET.SubElement(review,'path',d=' '.join(long_commands),fill='none',stroke='#d65b00',**{'stroke-width':'2.5','stroke-linecap':'round'})
        result['long_spans']=ET.tostring(review,encoding='unicode')
    return result
