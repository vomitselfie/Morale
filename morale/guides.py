"""Persistent design-space layout guides (millimeters)."""
import math


def validate_guides(guides):
    if not isinstance(guides,list) or len(guides)>100:raise ValueError('Use at most 100 layout guides.')
    for guide in guides:
        if not isinstance(guide,dict) or set(guide)!={'axis','position'} or not isinstance(guide['axis'],str) or guide['axis'] not in {'x','y'}:
            raise ValueError('Each guide needs an x/y axis and position.')
        value=guide['position']
        if type(value) not in {int,float} or not -1000<=value<=1000 or not math.isfinite(value):
            raise ValueError('Guide positions must be within ±1,000 mm.')
    return [dict(guide) for guide in guides]


def edit_guides(window):
    from PySide6.QtWidgets import QInputDialog
    current='\n'.join(f'{g["axis"]} {g["position"]}' for g in window.project.guides)
    text,accepted=QInputDialog.getMultiLineText(window,'Layout guides',
        'One guide per line: x 10 for vertical, y -20 for horizontal (mm). Clear to remove all.',current)
    if not accepted:return
    try:
        guides=[]
        for line in text.splitlines():
            if not line.strip():continue
            parts=line.split()
            if len(parts)!=2:raise ValueError('Enter an axis and millimeter position on each line, such as x 10.')
            guides.append({'axis':parts[0].lower(),'position':float(parts[1])})
        guides=validate_guides(guides)
        if guides!=window.project.guides:window.commit(lambda:setattr(window.project,'guides',guides))
    except ValueError as exc:window.error(str(exc))
