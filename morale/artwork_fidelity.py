"""Visible color-region geometry for internal artwork fidelity checks."""
from PySide6.QtGui import QPainterPath
from .auto_digitize import outline_path,area,difference_area
from .perceptual_color import distance_squared


def visible_colors(objects):
    layers={};covered=QPainterPath()
    for obj in reversed(objects):
        if not obj.visible:continue
        shape=outline_path(obj.rings())
        # Avoid Qt changing a hole on a coincident, zero-area boundary.
        visible=shape.subtracted(covered) if area(shape.intersected(covered))>1e-8 else shape
        color=obj.color.lower()
        layers[color]=layers.get(color,QPainterPath()).united(visible)
        covered=covered.united(shape)
    return layers,covered


def color_geometry(reference,actual,tolerance=2):
    expected,coverage=visible_colors(reference);observed,_=visible_colors(actual)
    matched={};unmatched=0.
    for color,shape in observed.items():
        nearest=min(expected,key=lambda candidate:distance_squared(color,candidate)) if expected else None
        if nearest is None or distance_squared(color,nearest)>tolerance*tolerance:
            unmatched+=area(shape)
        else:matched[nearest]=matched.get(nearest,QPainterPath()).united(shape)
    errors={color:difference_area(shape,matched.get(color,QPainterPath())) for color,shape in expected.items()}
    denominator=area(coverage)
    return {'symmetric_area_mm2':sum(errors.values())+unmatched,
            'reference_area_mm2':denominator,'per_color_area_mm2':errors,
            'unmatched_color_area_mm2':unmatched,'color_tolerance_oklab':tolerance,
            'error_ratio':(sum(errors.values())+unmatched)/max(denominator,1e-12)}
