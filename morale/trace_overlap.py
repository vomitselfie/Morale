"""Remove covered artwork fill while retaining a chosen seam allowance."""
from copy import deepcopy
import math
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainterPath,QPainterPathStroker,QTransform
from .model import Project
from .geometry import replace_contours
from .auto_digitize import outline_path,area,difference_area


def remove_covered_fill(project,allowance=.2):
    Project.loads(project.dumps())
    if isinstance(allowance,bool) or not isinstance(allowance,(int,float)) or not math.isfinite(allowance) or not 0<=allowance<=2:
        raise ValueError('Choose an overlap allowance from 0 to 2 mm.')
    result=deepcopy(project);objects=[];coverage=QPainterPath();changes=[]
    scale=QTransform.fromScale(100,100)
    for index in range(len(project.objects)-1,-1,-1):
        source=project.objects[index]
        eligible=(source.visible and source.stitch_type=='fill' and source.kind in {'compound','polygon','rectangle','ellipse','leaf'}
                  and not(source.stop_after or source.color_break or source.stage_note or source.group_id))
        if not eligible:
            # Never remove fill across explicit sewing semantics or non-fill artwork.
            coverage=QPainterPath();objects.append(deepcopy(source));continue
        original=scale.map(outline_path(source.rings()))
        cutter=coverage
        if allowance and not coverage.isEmpty():
            stroker=QPainterPathStroker();stroker.setWidth(allowance*200)
            stroker.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            cutter=coverage.subtracted(stroker.createStroke(coverage))
        # Subtract only material actually covered. Passing coincident hole
        # boundaries directly to Qt can fill the hole and hide a real cut.
        overlap=original.intersected(cutter).simplified() if not cutter.isEmpty() else QPainterPath()
        expected_removed=area(overlap)/10000
        remaining=original.subtracted(overlap).simplified() if expected_removed>1e-8 else original
        removed=max(0,(area(original)-area(remaining))/10000)
        if abs(removed-expected_removed)>.001:
            raise ValueError('Overlap removal could not preserve the covered area. Keep the original regions or simplify their contours.')
        candidate=deepcopy(source)
        if removed>1e-6:
            rings=[]
            for polygon in remaining.toSubpathPolygons():
                ring=[(p.x()/100,p.y()/100) for p in polygon]
                if len(ring)>1 and math.dist(ring[0],ring[-1])<1e-7:ring.pop()
                if len(ring)>=3 and area(outline_path([ring]))>1e-8:rings.append(ring)
            if rings:
                candidate.kind='compound';candidate.points=[];candidate.handles=[];candidate.contours=[]
                candidate=replace_contours(candidate,rings)
                if difference_area(outline_path(candidate.rings()),QTransform.fromScale(.01,.01).map(remaining))>.001:
                    raise ValueError('Overlap removal could not preserve the remaining contours.')
            else:candidate=None
            changes.append({'source_region':index,'removed_area_mm2':removed,'removed_region':candidate is None})
        if candidate is not None:objects.append(candidate)
        # Original upper silhouettes cover lower artwork even when those upper
        # silhouettes themselves were cut by a later region.
        coverage=coverage.united(original)
        if coverage.elementCount()>40_000:raise ValueError('Overlap removal exceeds the supported geometry limit.')
    result.objects=list(reversed(objects));Project.loads(result.dumps())
    return result,{'allowance_mm':allowance,'changes':list(reversed(changes)),
                   'removed_area_mm2':sum(c['removed_area_mm2'] for c in changes),
                   'removed_regions':sum(c['removed_region'] for c in changes)}
