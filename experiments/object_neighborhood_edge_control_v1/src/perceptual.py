"""Read-only standard LPIPS v0.1 and FLIP at declared viewing conditions."""
import sys
import numpy as np
from pathlib import Path
from runtime import OUT
sys.path.append(str(OUT/'deps'))
from edge_profiles import linear_to_srgb

_LPIPS=None
def score(image,reference,band):
    import torch
    import lpips
    import flip_evaluator as flip
    global _LPIPS
    if _LPIPS is None:
        public_cache=Path('/home/u00134/.cache/torch/hub')
        torch.hub.set_dir(str(public_cache if (public_cache/'checkpoints/alexnet-owt-7be5be79.pth').exists() else OUT/'cache/torch_hub'))
        _LPIPS=lpips.LPIPS(net='alex',version='0.1').cuda().eval()
    def tensor(x):return torch.tensor(linear_to_srgb(x).transpose(2,0,1)[None],device='cuda')*2-1
    with torch.no_grad():
        full=float(_LPIPS(tensor(image),tensor(reference)))
        ys,xs=np.nonzero(band)
        crop_score=None
        if len(xs):
            center=int(np.median(xs));x0=max(0,center-32);x1=min(image.shape[1],x0+64)
            crop_score=float(_LPIPS(tensor(image[180:330,x0:x1]),tensor(reference[180:330,x0:x1])))
    fmap,mean,parameters=flip.evaluate(np.clip(reference,0,1).astype(np.float32),np.clip(image,0,1).astype(np.float32),
        'LDR',inputsRGB=False,applyMagma=False,parameters={'ppd':67.0})
    fmap=np.asarray(fmap).squeeze()
    return {'LPIPS':full,'LPIPS_edge_crop':crop_score,'FLIP':float(mean),
            'FLIP_band':float(fmap[band].mean()) if band.any() else None,
            'LPIPS_color_space':'sRGB OETF, normalized [-1,1]',
            'FLIP_conditions':'LDR linear sRGB inputsRGB=False; 67 pixels per degree',
            'FLIP_parameters':parameters}
