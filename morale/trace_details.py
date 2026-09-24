"""Optional physical-area filtering of filled artwork components."""
from copy import deepcopy
import math
from PySide6.QtGui import QTransform
from .model import Project
from .auto_digitize import outline_path,area
from .geometry import replace_contours


def filter_small_fills(project,minimum_area=0):
    Project.loads(project.dumps())
    if isinstance(minimum_area,bool) or not isinstance(minimum_area,(int,float)) or not math.isfinite(minimum_area) or not 0<=minimum_area<=25:
        raise ValueError('Choose a minimum filled area from 0 to 25 mm².')
    result=deepcopy(project);result.objects=[];changes=[]
    for index,source in enumerate(project.objects):
        candidate=deepcopy(source)
        eligible=(minimum_area>0 and source.visible and source.stitch_type=='fill'
                  and source.kind in {'compound','polygon','rectangle','ellipse','leaf'}
                  and not(source.stop_after or source.color_break or source.stage_note or source.group_id))
        if eligible:
            normalized=QTransform.fromScale(100,100).map(outline_path(source.rings())).simplified()
            rings=[];paths=[]
            for polygon in normalized.toSubpathPolygons():
                ring=[(p.x()/100,p.y()/100) for p in polygon]
                if len(ring)>1 and math.dist(ring[0],ring[-1])<1e-7:ring.pop()
                if len(ring)>=3:
                    rings.append(ring);paths.append(outline_path([ring]))
            if len(rings)>256:raise ValueError('Detail filtering exceeds 256 contours.')
            # Qt resolves intersections first. Nesting depth then separates each
            # filled island from its immediate holes, regardless of winding.
            parents=[[j for j,p in enumerate(paths) if j!=i and p.contains(path)] for i,path in enumerate(paths)]
            kept=[];removed=[]
            for i,path in enumerate(paths):
                depth=len(parents[i])
                if depth%2:continue
                children=[j for j in range(len(paths)) if len(parents[j])==depth+1 and i in parents[j]]
                net=area(path)-sum(area(paths[j]) for j in children)
                if net+1e-8<minimum_area:removed.append(max(0,net))
                else:kept.extend([rings[i],*[rings[j] for j in children]])
            if removed:
                if kept:
                    candidate.kind='compound';candidate.points=[];candidate.handles=[];candidate.contours=[]
                    candidate=replace_contours(candidate,kept)
                else:candidate=None
                changes.append({'source_region':index,'object_id':source.id,'name':source.name,'removed_components':len(removed),'removed_area_mm2':sum(removed),
                                'removed_region':candidate is None})
        if candidate is not None:result.objects.append(candidate)
    Project.loads(result.dumps())
    return result,{'minimum_area_mm2':minimum_area,'changes':changes,
                   'removed_components':sum(c['removed_components'] for c in changes),
                   'removed_area_mm2':sum(c['removed_area_mm2'] for c in changes)}


def fill_small_holes(project,minimum_area=0):
    """Close small voids in editable fills while preserving deeper holes."""
    Project.loads(project.dumps())
    if isinstance(minimum_area,bool) or not isinstance(minimum_area,(int,float)) or not math.isfinite(minimum_area) or not 0<=minimum_area<=25:
        raise ValueError('Choose a minimum hole area from 0 to 25 mm².')
    result=deepcopy(project);changes=[];occupied_holes=0
    protected={i:outline_path(obj.rings()) for i,obj in enumerate(project.objects)
               if minimum_area>0 and obj.visible and obj.stitch_type=='fill'}
    for index,source in enumerate(project.objects):
        if not (minimum_area>0 and source.visible and source.stitch_type=='fill' and source.kind in {'compound','polygon','rectangle','ellipse','leaf'} and not(source.stop_after or source.color_break or source.stage_note or source.group_id)):
            continue
        original=outline_path(source.rings())
        normalized=QTransform.fromScale(100,100).map(original).simplified()
        rings=[]
        for polygon in normalized.toSubpathPolygons():
            ring=[(p.x()/100,p.y()/100) for p in polygon]
            if len(ring)>1 and math.dist(ring[0],ring[-1])<1e-7:ring.pop()
            if len(ring)>=3:rings.append(ring)
        if len(rings)>256:raise ValueError('Hole filtering exceeds 256 contours.')
        paths=[outline_path([ring]) for ring in rings]
        parents=[[j for j,p in enumerate(paths) if j!=i and p.contains(path)] for i,path in enumerate(paths)]
        selected=[];void_areas={}
        for i,path in enumerate(paths):
            depth=len(parents[i])
            if depth%2!=1:continue
            children=[j for j in range(len(paths)) if len(parents[j])==depth+1 and i in parents[j]]
            void=area(path)-sum(area(paths[j]) for j in children)
            if void+1e-8<minimum_area:
                void_shape=path
                for child in children:void_shape=void_shape.subtracted(paths[child])
                bounds=void_shape.boundingRect()
                occupied=any(j!=index and bounds.intersects(other.boundingRect()) and area(void_shape.intersected(other))>1e-8
                             for j,other in protected.items())
                if occupied:
                    occupied_holes+=1;continue
                selected.append(i);void_areas[i]=void
        if not selected:continue
        # Merge each filled hole with its immediate material islands. Deeper
        # voids retain their own boundaries unless independently selected.
        discard=set(selected)
        discard.update(i for i in range(len(rings)) if any(j in parents[i] and len(parents[i])==len(parents[j])+1 for j in selected))
        kept=[ring for i,ring in enumerate(rings) if i not in discard]
        candidate=deepcopy(source);candidate.kind='compound';candidate.points=[];candidate.handles=[];candidate.contours=[]
        candidate=replace_contours(candidate,kept)
        added=area(outline_path(candidate.rings()))-area(original)
        if added< -1e-6 or abs(added-sum(void_areas.values()))>.001:
            raise ValueError('Hole filling could not preserve the expected material area.')
        result.objects[index]=candidate
        protected[index]=outline_path(candidate.rings())
        changes.append({'source_region':index,'object_id':source.id,'name':source.name,'filled_holes':len(selected),'added_area_mm2':max(0,added)})
    Project.loads(result.dumps())
    return result,{'minimum_area_mm2':minimum_area,'occupied_holes_retained':occupied_holes,'changes':changes,'filled_holes':sum(c['filled_holes'] for c in changes),'added_area_mm2':sum(c['added_area_mm2'] for c in changes)}
