"""RGB-only sensitivity adapter. Never reads depth, alpha, cameras or geometry."""
import numpy as np
from skimage.morphology import skeletonize
import boundary
SCALES={'native':[.7,1.4,2.8],'medium':[1.,2.,4.],'coarse':[1.4,2.8,5.6]}
def rgb_from_npz(z):
    rgb=z['rgb']
    if rgb.dtype!=np.float32 or rgb.ndim!=3 or rgb.shape[-1]!=3 or not np.isfinite(rgb).all():
        raise ValueError('Require finite native HWC float32 rendered RGB; no normalization')
    return rgb
def analyze_rgb(rgb,analysis):
    if rgb.dtype!=np.float32 or rgb.ndim!=3 or rgb.shape[-1]!=3 or not np.isfinite(rgb).all():raise ValueError('Invalid RGB')
    return boundary.analyze(rgb,dict(scales=SCALES[analysis]))
def mix_fields(fields,detail_lambda):
    if not 0<=detail_lambda<=1:raise ValueError('lambda outside frozen range')
    return np.maximum(fields['structural'],np.float32(detail_lambda)*fields['detail']).astype(np.float32)
def candidate(soft,threshold,gain=1.,sigma=.5):
    if gain!=1.:raise ValueError('Fixed gain=1 in this experiment')
    darkness=1-boundary.ink(soft,gain=gain,sigma=sigma)[...,0]
    marked=darkness>threshold
    return dict(soft=soft,darkness=darkness,marked=marked,skeleton=skeletonize(marked),candidate_darkness=darkness*marked)
