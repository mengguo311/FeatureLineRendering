"""Small exact audit and visibility semantics; production uses native traversal."""
import numpy as np

def composite(alpha, colors, background):
    alpha=np.asarray(alpha,dtype=float)
    if np.any((alpha<0)|(alpha>1)):
        raise ValueError('alpha includes footprint and opacity, must lie in [0,1]')
    weights=alpha*np.r_[1.,np.cumprod(1-alpha)[:-1]]
    return weights@np.asarray(colors)+(1-weights.sum())*np.asarray(background), weights, float(weights.sum())

def visibility_state(spatial_association, band_mass, reliable=True):
    if not spatial_association or not reliable:
        return 'unknown'
    return 'hidden' if band_mass<=1e-8 else 'visible'
