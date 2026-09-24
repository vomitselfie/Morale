"""Bounded, population-weighted perceptual palette fitting for sampled artwork."""
from collections import defaultdict
from .perceptual_color import oklab


def lab(rgb):
    return oklab('#%02x%02x%02x'%rgb)


def squared(a,b):
    return sum((x-y)**2 for x,y in zip(a,b))


def quantize(histogram,count,metric='rgb'):
    from .raster_trace import reduce_colors
    if not isinstance(metric,str) or metric not in {'rgb','oklab'}:
        raise ValueError('Choose RGB or Oklab palette reduction.')
    if not histogram:raise ValueError('No visible colors remain.')
    if metric=='rgb':
        palette=reduce_colors(histogram,count)
        mapping={c:min(palette,key=lambda p:squared(c,p)) for c in histogram}
        return palette,mapping,{'metric':metric}
    # At most 4,096 occupied RGB bins participate in fitting. Population and
    # mean color are retained; final assignment uses every original color.
    bins=defaultdict(lambda:[0,0,0,0])
    for color,weight in histogram.items():
        bucket=bins[tuple(v//16 for v in color)]
        bucket[0]+=weight
        for k in range(3):bucket[k+1]+=color[k]*weight
    samples={}
    for _,bucket in sorted(bins.items()):
        color=tuple(round(bucket[k+1]/bucket[0]) for k in range(3))
        samples[color]=samples.get(color,0)+bucket[0]
    if len(histogram)<=4096:samples=dict(sorted(histogram.items()))
    palette=reduce_colors(samples,count)
    coordinates={c:lab(c) for c in samples}
    def objective(colors):
        centers=[lab(c) for c in colors]
        return sum(weight*min(squared(coordinates[c],p) for p in centers) for c,weight in samples.items())/sum(samples.values())
    before=objective(palette);iterations=0
    for iterations in range(1,9):
        centers=[lab(c) for c in palette];groups=[[] for _ in palette]
        for c in samples:groups[min(range(len(centers)),key=lambda i:squared(coordinates[c],centers[i]))].append(c)
        updated=list(palette)
        for i,group in enumerate(groups):
            if not group:continue
            weight=sum(samples[c] for c in group)
            mean=tuple(sum(coordinates[c][k]*samples[c] for c in group)/weight for k in range(3))
            # Choose a representable swatch; retaining the old center prevents
            # a worse fixed-cluster objective without an out-of-gamut inverse.
            updated[i]=min([palette[i],*group],key=lambda c:squared(lab(c),mean))
        if updated==palette:break
        palette=updated
    palette=list(dict.fromkeys(palette));centers=[lab(c) for c in palette]
    mapping={}
    for c in histogram:
        point=lab(c)
        mapping[c]=palette[min(range(len(palette)),key=lambda i:squared(point,centers[i]))]
    return palette,mapping,{'metric':metric,'fit_colors':len(samples),'source_colors':len(histogram),
        'iterations':iterations,'fit_error_before':before,'fit_error_after':objective(palette)}
