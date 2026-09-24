"""Match traced artwork colors to an explicitly selected thread chart."""
from copy import deepcopy
from pathlib import Path
import math
from .catalogs import builtin_catalog,read_catalog,distance_squared


def match_trace_threads(project,catalog,metric='oklab'):
    if not isinstance(metric,str) or metric not in {'rgb','oklab'}: raise ValueError('Choose Oklab or RGB color matching.')
    if not isinstance(catalog,str): raise ValueError('Invalid thread chart selection.')
    if not catalog: return deepcopy(project),[]
    if catalog in {'PEC fixed palette','JEF fixed palette'}:
        entries=builtin_catalog(catalog);name=catalog
    else:
        path=Path(catalog);before=path.stat();entries=read_catalog(path);after=path.stat()
        if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):
            raise ValueError('Thread chart changed while reading. Generate another preview.')
        name=path.name
    result=deepcopy(project);matches={}
    if metric=='oklab':
        from .perceptual_color import distance_squared as score
    else: score=distance_squared
    for obj in result.objects:
        source=obj.color.lower()
        if source not in matches:
            entry=min(entries,key=lambda entry:score(source,entry.color))
            matches[source]={'source_color':source,'color':entry.color.lower(),'metadata':dict(entry.metadata),
                'rgb_distance':math.sqrt(distance_squared(source,entry.color)),'catalog':name,
                'metric':metric,'distance':math.sqrt(score(source,entry.color))}
        match=matches[source];obj.color=match['color'];obj.thread=dict(match['metadata'])
    return result,list(matches.values())
