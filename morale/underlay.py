"""Inset support geometry; Qt path operations require no GUI application."""
import math


def inset_rings(rings, distance):
    if not math.isfinite(distance) or not 0 <= distance <= 3:
        raise ValueError("Underlay inset must be between 0 and 3 mm.")
    if distance == 0:
        return rings
    return OffsetGeometry(rings).inset(distance)


class OffsetGeometry:
    """Reuse one normalized source path for successive inward offsets."""
    def __init__(self,rings):
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QPainterPath
        path=QPainterPath()
        path.setFillRule(Qt.FillRule.OddEvenFill)
        for ring in rings:
            path.moveTo(ring[0][0]*20,ring[0][1]*20)
            for x,y in ring[1:]:
                path.lineTo(x*20,y*20)
            path.closeSubpath()
        self.path=path.simplified()
        bounds=self.path.boundingRect()
        self.maximum_depth=min(bounds.width(),bounds.height())/40

    def inset(self,distance):
        if not math.isfinite(distance) or not 0 <= distance <= 500:
            raise ValueError("Outline inset must be between 0 and 500 mm.")
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QPainterPathStroker
        stroker=QPainterPathStroker()
        stroker.setWidth(distance*40)
        stroker.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        inside=self.path.subtracted(stroker.createStroke(self.path)).simplified() if distance else self.path
        result=[]
        for polygon in inside.toSubpathPolygons():
            ring=[(p.x()/20,p.y()/20) for p in polygon]
            if len(ring)>1 and ring[0]==ring[-1]:
                ring.pop()
            if len(ring)>=3:
                result.append(ring)
        if sum(map(len,result))>30_000:
            raise ValueError("Inset geometry exceeds the 30,000-point limit.")
        return result


def inset_rails(points, distance):
    """Move satin supports inward, capping inset at each pair's center."""
    result=[]
    for left,right in zip(points[::2],points[1::2]):
        width=math.dist(left,right)
        fraction=min(.5,distance/width) if width else 0
        dx,dy=(right[0]-left[0])*fraction,(right[1]-left[1])*fraction
        result.extend([(left[0]+dx,left[1]+dy),(right[0]-dx,right[1]-dy)])
    return result
