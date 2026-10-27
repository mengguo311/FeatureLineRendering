"""Saved view-contour display; independent of fixed surface hatch geometry."""
import math
from numbers import Real

DEFAULT_DISPLAY = {'contours_visible': True, 'contour_strength': 1.0}

def validate_display(values=None):
    if values is None:
        return dict(DEFAULT_DISPLAY)
    if not isinstance(values,dict) or set(values)-set(DEFAULT_DISPLAY):
        raise ValueError('unknown contour display setting')
    result=dict(DEFAULT_DISPLAY,**values)
    strength=result['contour_strength']
    if isinstance(strength,bool) or not isinstance(strength,Real) or not math.isfinite(strength) or not 0<=strength<=1:
        raise ValueError('contour strength must be a finite number from 0 to 1')
    if not isinstance(result['contours_visible'],bool):
        raise ValueError('contours_visible must be true or false')
    result['contour_strength']=float(strength)
    return result
