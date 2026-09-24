"""Portable conversion settings, separate from artwork-specific choices."""
import json
import math
import os
from pathlib import Path
import tempfile


NUMBERS={'colors':(1,16,int),'resolution':(64,1024,int),'minimum_region':(1,100,int),
         'smoothing':(0,1,float),'overlap_allowance':(0,2,float),'branch_overlap':(0,1,float),'minimum_fill_area':(0,25,float),'minimum_hole_area':(0,25,float),
         'trim_threshold':(.5,50,float),'fill_spacing':(.2,5,float),'satin_spacing':(.2,5,float),
         'stitch_length':(.5,6,float),'pull_compensation':(0,2,float),'underlay_inset':(0,3,float),'underlay_spacing':(.5,10,float)}
CHOICES={'method':{'smooth','pixels'},'stitch_mode':{'auto','fill'},'palette_metric':{'rgb','oklab'},
         'color_metric':{'rgb','oklab'},'underlay':{'keep','off','auto'},
         'fill_underlay':{'keep','off','auto','edge','sparse','edge_sparse'},
         'satin_underlay':{'keep','off','auto','zigzag','center_zigzag'}}
FLAGS={'group_colors','distinct_threads','ignore_white','split_branches','optimize_fill_angles','route_fill','remove_overlap','reduce_travel',
       'reverse_for_travel','finish_regions','internal_trims','expand_strokes','custom_stitches','border_white'}


def validate(settings):
    # Version-one presets written before border-connected removal retain their original behavior.
    if isinstance(settings,dict):settings={'border_white':False,'minimum_hole_area':0,'fill_underlay':'keep','satin_underlay':'keep',
                                            'underlay_inset':0,'underlay_spacing':2,'branch_overlap':0,'group_colors':False,'distinct_threads':False,**settings}
    if not isinstance(settings,dict) or set(settings)!=set(NUMBERS)|set(CHOICES)|FLAGS:
        raise ValueError('Unsupported or incomplete conversion preset settings.')
    for key,(low,high,kind) in NUMBERS.items():
        value=settings[key]
        if isinstance(value,bool) or not isinstance(value,(int,float)) or (kind is int and type(value) is not int) or not low<=value<=high or not math.isfinite(value):
            raise ValueError(f'Invalid preset {key.replace("_"," ")}.')
    for key,choices in CHOICES.items():
        if not isinstance(settings[key],str) or settings[key] not in choices:raise ValueError(f'Invalid preset {key}.')
    if any(type(settings[key]) is not bool for key in FLAGS):raise ValueError('Invalid preset switch.')
    if settings['resolution'] not in {64,128,256,512,1024} or settings['method']=='pixels' and settings['resolution']>256:
        raise ValueError('Unsupported preset tracing resolution.')
    return dict(settings)


def load_preset(path):
    with Path(path).open('rb') as stream:data=stream.read(32769)
    if len(data)>32768:raise ValueError('Conversion presets are limited to 32 KB.')
    try:document=json.loads(data)
    except (ValueError,RecursionError) as exc:raise ValueError('Could not read the conversion preset.') from exc
    if not isinstance(document,dict) or set(document)!={'format','version','settings'} or document['format']!='morale-trace-preset' or type(document['version']) is not int or document['version']!=1:
        raise ValueError('Unsupported conversion preset format or version.')
    return validate(document['settings'])


def save_preset(path,settings):
    document={'format':'morale-trace-preset','version':1,'settings':validate(settings)}
    path=Path(path);temporary=None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,suffix='.tmp',delete=False) as stream:
            temporary=Path(stream.name);json.dump(document,stream,indent=2);stream.write('\n')
        os.replace(temporary,path)
    finally:
        if temporary is not None:temporary.unlink(missing_ok=True)
