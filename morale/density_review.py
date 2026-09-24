"""Needle-penetration counts in fixed physical cells, not a fabric verdict."""
from collections import Counter,defaultdict
import math
from PySide6.QtCore import QRectF
from PySide6.QtGui import QImage,QPainter,QColor,QFont


def measure_density(blocks):
    counts=Counter();objects=defaultdict(set)
    for block in blocks:
        for stitch in block.stitches:
            if stitch.command!='stitch':continue
            key=(math.floor(stitch.x),math.floor(stitch.y))
            counts[key]+=1;objects[key].add(block.object_id)
    hottest=sorted(counts,key=lambda k:(-counts[k],k))[:20]
    report={'cell_size_mm':1,'origin_mm':[0,0],'penetrations':sum(counts.values()),
            'occupied_cells':len(counts),'peak_per_mm2':max(counts.values(),default=0),
            'multi_object_cells':sum(len(ids)>1 for ids in objects.values()),
            'hottest_cells':[{'x_mm':x,'y_mm':y,'penetrations':counts[x,y],'objects':len(objects[x,y])} for x,y in hottest]}
    return report,counts


def measure_thread_density(blocks,budget=2_000_000):
    """Split sewn segments exactly at integer grid boundaries."""
    if type(budget) is not int or budget<1:raise ValueError('Invalid thread density budget.')
    lengths=Counter();objects=defaultdict(set);previous=(0.,0.);used=0;complete=True
    total=0.
    for block in blocks:
        for stitch in block.stitches:
            point=(stitch.x,stitch.y)
            if stitch.command=='stitch':
                distance=math.dist(previous,point);total+=distance
                if distance and complete:
                    fractions={0.,1.}
                    for a,b in zip(previous,point):
                        if a==b:continue
                        for edge in range(math.floor(min(a,b))+1,math.ceil(max(a,b))):
                            fractions.add((edge-a)/(b-a))
                    fractions=sorted(fractions)
                    if used+len(fractions)-1>budget:complete=False
                    else:
                        for low,high in zip(fractions,fractions[1:]):
                            if high-low<1e-12:continue
                            t=(low+high)/2
                            key=tuple(math.floor(a+(b-a)*t) for a,b in zip(previous,point))
                            lengths[key]+=distance*(high-low);objects[key].add(block.object_id);used+=1
            if stitch.command in {'stitch','jump'}:previous=point
    hottest=sorted(lengths,key=lambda k:(-lengths[k],k))[:20]
    # 0.5 mm/mm² bins let fabric guidance apply thresholds without the full map.
    bins=Counter(math.floor(value*2)/2 for value in lengths.values())
    return {'histogram':sorted(bins.items()),'cell_size_mm':1,'origin_mm':[0,0],'complete':complete,'total_sewn_mm':total,
            'mapped_sewn_mm':sum(lengths.values()),'peak_mm_per_mm2':max(lengths.values(),default=0.),
            'occupied_cells':len(lengths),'multi_object_cells':sum(len(ids)>1 for ids in objects.values()),
            'hottest_cells':[{'x_mm':x,'y_mm':y,'sewn_mm':lengths[x,y],'objects':len(objects[x,y])} for x,y in hottest]},lengths


def render_density(report,counts,thread_length=False):
    image=QImage(640,520,QImage.Format.Format_RGB32);image.fill(QColor('#fffdf8'))
    painter=QPainter(image);painter.setFont(QFont('Sans',11));painter.setPen(QColor('#202020'))
    peak=report['peak_mm_per_mm2'] if thread_length else report['peak_per_mm2']
    painter.drawText(18,25,'Sewn thread length per 1 × 1 mm cell' if thread_length else 'Needle penetrations per 1 × 1 mm cell')
    summary=f"Peak: {peak:.2f} mm/mm² · Mapped: {report['mapped_sewn_mm']:.1f} mm" if thread_length else f"Peak: {peak} · Total: {report['penetrations']:,}"
    painter.drawText(18,47,summary+f" · Shared cells: {report['multi_object_cells']}")
    if counts:
        left=min(x for x,y in counts);top=min(y for x,y in counts)
        right=max(x for x,y in counts)+1;bottom=max(y for x,y in counts)+1
        scale=min(604/(right-left),380/(bottom-top));ox=320-(right-left)*scale/2;oy=65+(380-(bottom-top)*scale)/2
        # At overview scale, draw high-count cells last so subpixel cells cannot
        # hide a denser neighbor. The numbers always use the original grid.
        for (x,y),count in sorted(counts.items(),key=lambda item:item[1]):
            fraction=count/peak
            color=QColor.fromRgbF(1,.94-.74*fraction,.74-.62*fraction)
            painter.fillRect(QRectF(ox+(x-left)*scale,oy+(y-top)*scale,max(1,scale),max(1,scale)),color)
        painter.drawText(18,467,f'Extent: X {left:g} to {right:g} mm · Y {top:g} to {bottom:g} mm')
    else:painter.drawText(18,100,'No sewn path length to measure.' if thread_length else 'No sewn stitches to measure.')
    painter.drawText(18,490,'Light → dark: less → more sewn thread within this design.' if thread_length else 'Light → dark: fewer → more penetrations within this design.')
    footer='Partial map: geometry budget exceeded.' if thread_length and not report['complete'] else 'Includes ties and underlay. Not a fabric-damage prediction.'
    painter.drawText(18,510,footer)
    painter.end();return image
