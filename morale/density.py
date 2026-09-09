"""Tatami scan rows with a linear spacing profile in fill coordinates."""
import math


def fill_rows(low, high, spacing, end_spacing=None, reverse=False):
    if not all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in (low,high,spacing)) or spacing<=0:
        raise ValueError('Fill bounds and positive spacing must be finite.')
    if end_spacing is not None and (isinstance(end_spacing,bool) or not isinstance(end_spacing,(int,float)) or not math.isfinite(end_spacing) or not .2<=end_spacing<=5 or not .2<=spacing<=5):
        raise ValueError('Gradient row spacing must be between 0.2 and 5 mm.')
    if type(reverse) is not bool: raise ValueError('Gradient direction must be boolean.')
    extent=high-low
    if not math.isfinite(extent): raise ValueError('Fill extent must be finite.')
    if extent<=0: return []
    if end_spacing is None or end_spacing==spacing:
        total=extent/spacing
        if not math.isfinite(total) or total>250_000: raise ValueError('Too many fill rows.')
        return [low+spacing*(i+.5) for i in range(math.ceil(total)) if low+spacing*(i+.5)<high]
    start,end=(end_spacing,spacing) if reverse else (spacing,end_spacing)
    slope=(end-start)/extent
    # Integrate 1/spacing(y), then place rows one density-unit apart.
    total=math.log1p((end-start)/start)/slope
    if not math.isfinite(total) or total>250_000: raise ValueError('Too many fill rows.')
    count=round(total)
    if count<1: return []
    offset=(total-(count-1))/2
    return [low+start*math.expm1(slope*(offset+i))/slope for i in range(count)]
