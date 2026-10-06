"""Full accepted mass from original RGB autograd; feature passes have separate colors."""
import numpy as np
import torch

def feature_model(model,colors): return {**{k:v.detach() for k,v in model.items() if k not in ('shs','colors_precomp')},'colors_precomp':colors}

def feature_mass(module,settings,model,pixel_objective=None):
    colors=torch.ones((len(model['means3D']),3),device='cuda',requires_grad=True)
    s=settings._replace(bg=torch.zeros(3,device='cuda'),sh_degree=0)
    rgb,_=module.GaussianRasterizer(s)(**feature_model(model,colors))
    loss=rgb[0].sum() if pixel_objective is None else (rgb[0]*torch.as_tensor(pixel_objective,device='cuda')).sum()
    grad,=torch.autograd.grad(loss,colors)
    return grad[:,0].detach().cpu().numpy(),rgb[0].detach().cpu().numpy()

def render_features(module,settings,model,selected):
    colors=torch.zeros((len(model['means3D']),3),device='cuda')
    colors[torch.as_tensor(selected.astype(np.int64),device='cuda')]=1
    s=settings._replace(bg=torch.zeros(3,device='cuda'),sh_degree=0)
    with torch.no_grad(): rgb,_=module.GaussianRasterizer(s)(**feature_model(model,colors))
    return rgb[0].cpu().numpy()

def render_subset(module,settings,model,selected):
    if len(selected)==0: return np.ones((3,settings.image_height,settings.image_width),np.float32)
    idx=torch.as_tensor(selected.astype(np.int64),device='cuda')
    subset={k:v[idx].contiguous() for k,v in model.items()}
    with torch.no_grad(): rgb,_=module.GaussianRasterizer(settings)(**subset)
    return rgb.cpu().numpy()

def deletion(module,settings,model,selected):
    isolated={k:v.detach().clone() for k,v in model.items()}
    isolated['opacities'][torch.as_tensor(selected.astype(np.int64),device='cuda')]=0
    with torch.no_grad(): out=module.GaussianRasterizer(settings)(**isolated,attribution=True,K=1)
    return out.rgb.cpu().numpy(),out.accumulated_alpha.cpu().numpy()
