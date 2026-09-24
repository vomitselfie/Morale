"""Apply explicit stitch settings to converted artwork before route planning."""
from copy import deepcopy
import math


def apply_stitch_settings(project,settings):
    limits={'fill_spacing':(.2,5),'satin_spacing':(.2,5),'stitch_length':(.5,6),'pull_compensation':(0,2),'underlay_inset':(0,3),'underlay_spacing':(.5,10)}
    choices={'underlay':{'keep','off','auto'},'fill_underlay':{'keep','off','auto','edge','sparse','edge_sparse'},
             'satin_underlay':{'keep','off','auto','zigzag','center_zigzag'}}
    if not isinstance(settings,dict) or set(settings)-set(limits)-set(choices):
        raise ValueError('Invalid conversion stitch settings.')
    for key,value in settings.items():
        if key in choices:
            if not isinstance(value,str) or value not in choices[key]:
                raise ValueError(f'Invalid conversion {key.replace("_"," ")}.')
        elif isinstance(value,bool) or not isinstance(value,(int,float)) or not limits[key][0]<=value<=limits[key][1] or not math.isfinite(value):
            raise ValueError(f'Invalid conversion {key.replace("_"," ")}.')
    result=deepcopy(project);changed=[]
    for obj in result.objects:
        if obj.kind=='stitches':continue
        before=deepcopy(obj)
        spacing=settings.get(obj.stitch_type+'_spacing')
        if spacing is not None:obj.spacing=spacing
        if 'stitch_length' in settings:obj.stitch_length=settings['stitch_length']
        if obj.stitch_type in {'fill','satin'}:
            if 'pull_compensation' in settings:obj.pull_compensation=settings['pull_compensation']
            mode=settings.get(obj.stitch_type+'_underlay','keep')
            if mode=='keep':mode=settings.get('underlay','keep')
            if mode!='keep':
                obj.underlay=mode!='off'
                if obj.underlay:obj.underlay_style=mode
            for key in ('underlay_inset','underlay_spacing'):
                if key in settings:setattr(obj,key,settings[key])
        if obj!=before:changed.append(obj.id)
    return result,{'requested':dict(settings),'changed_objects':len(changed)}
