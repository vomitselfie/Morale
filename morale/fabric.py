"""Editable fabric starting points; values require physical sewout validation."""
from copy import deepcopy
import math
from .model import Project

# Morale's experimental starting points, not vendor-calibrated recipes.
PROFILES={
    'Stable woven':(.45,.15,'edge',.5,2.5),
    'Stretch knit':(.45,.25,'edge_sparse',.5,2.0),
    'Textured / pile':(.4,.25,'edge_sparse',.5,1.5),
}


def selection_settings(objects):
    """Return common settings only when the dialog can represent them exactly."""
    values=[]
    for obj in objects:
        if obj.stitch_type not in {'fill','satin'}:continue
        style=obj.underlay_style
        if obj.stitch_type=='satin':style={'auto':'edge','center_zigzag':'edge_sparse'}.get(style)
        if style not in {'edge','edge_sparse','sparse'}:return None
        values.append(dict(spacing=obj.spacing,pull_compensation=obj.pull_compensation,
                           underlay_inset=obj.underlay_inset,underlay_spacing=obj.underlay_spacing,underlay_style=style))
        if not obj.underlay:values[-1]['underlay']=False
    return values[0] if values and all(value==values[0] for value in values) else None


def validate_settings(settings):
    ranges={'spacing':(.2,5),'pull_compensation':(0,2),'underlay_inset':(0,3),'underlay_spacing':(.5,10)}
    if not isinstance(settings,dict) or set(settings)-{'underlay'}!=set(ranges)|{'underlay_style'}:
        raise ValueError('Fabric settings are incomplete.')
    if 'underlay' in settings and type(settings['underlay']) is not bool:raise ValueError('Invalid fabric underlay switch.')
    if not isinstance(settings['underlay_style'],str) or settings['underlay_style'] not in {'edge','edge_sparse','sparse'}:
        raise ValueError('Unsupported fabric underlay style.')
    for key,(low,high) in ranges.items():
        value=settings[key]
        if type(value) not in (float,int) or not low<=value<=high or not math.isfinite(value):
            raise ValueError(f'Invalid fabric {key.replace("_"," ")}.')
    return dict(settings)


def apply_fabric(project,ids,settings):
    settings=validate_settings(settings)
    result=deepcopy(project);changed=0
    for obj in result.objects:
        if obj.id not in ids or obj.kind=='stitches' or obj.stitch_type not in {'fill','satin'}:continue
        for key,value in settings.items():setattr(obj,key,value)
        if obj.stitch_type=='satin':
            obj.underlay_style='center_zigzag' if settings['underlay_style']!='edge' else 'auto'
        obj.underlay=settings.get('underlay',True)
        changed+=1
    if not changed:raise ValueError('Select at least one editable fill or satin object.')
    # Validate all fields before anything can be committed to the document.
    Project.loads(result.dumps())
    return result,changed
