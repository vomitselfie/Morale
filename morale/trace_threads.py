"""Match traced artwork colors to an explicitly selected thread chart."""
from copy import deepcopy
from pathlib import Path
import math
from .catalogs import builtin_catalog,read_catalog,distance_squared


def match_trace_threads(project,catalog,metric='oklab',distinct=False):
    if not isinstance(metric,str) or metric not in {'rgb','oklab'}: raise ValueError('Choose Oklab or RGB color matching.')
    if not isinstance(catalog,str): raise ValueError('Invalid thread chart selection.')
    if type(distinct) is not bool: raise ValueError('Invalid distinct thread planning setting.')
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
    plan=None
    if distinct:
        from .thread_planning import plan_threads
        plan=plan_threads(project,entries,score)
    for obj in result.objects:
        source=obj.color.lower()
        if source not in matches:
            if plan is None:entry,info=min(entries,key=lambda entry:score(source,entry.color)),None
            else:entry,info=plan[source]
            matches[source]={'source_color':source,'color':entry.color.lower(),'metadata':dict(entry.metadata),
                'rgb_distance':math.sqrt(distance_squared(source,entry.color)),'catalog':name,
                'metric':metric,'distance':math.sqrt(score(source,entry.color))}
            if info is not None:
                matches[source].update(planned=True,nearest_color=info['nearest_color'],adjusted=info['adjusted'],
                    shared_with=info['shared_with'],nearest_distance=math.sqrt(score(source,info['nearest_color'])))
        match=matches[source];obj.color=match['color'];obj.thread=dict(match['metadata'])
    return result,list(matches.values())
