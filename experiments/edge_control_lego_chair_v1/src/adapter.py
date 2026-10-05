"""Stock Graphdeco full-SH render and full alpha*T colour Jacobian."""
import math,re,sys,importlib.util,types
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from runtime import V1
C0=.28209479177387814
def inspect_ply(path,cfg_degree):
    lines=[]
    with open(path,'rb') as f:
        while True:
            s=f.readline().decode().strip();lines.append(s)
            if s=='end_header':break
            if not s:raise ValueError('invalid PLY header')
    count=int(next(x.split()[-1] for x in lines if x.startswith('element vertex')))
    rest=sum(' f_rest_' in x for x in lines)
    d=int(round(math.sqrt(rest/3+1)-1))
    if rest!=3*((d+1)**2-1) or d!=cfg_degree:raise ValueError('PLY/cfg SH mismatch')
    return {'count':count,'degree':d,'rest_coefficients_per_gaussian':rest,'header':lines}
def stable_uids(model_sha,n):return [f'{model_sha}:{i}' for i in range(n)]
def dc_project(dc,ids):
    out=dc.clone();out[ids]=((C0*dc[ids]+.5).clamp(0,1)-.5)/C0;return out
def permission_audit(before,after,ids,cov):
    mask=np.ones(len(before['xyz']),bool);mask[np.asarray(ids,int)]=False
    allowed={'dc'}|({'scale','rotation'} if cov else set())
    checks={k:bool(np.array_equal(a[mask],after[k][mask]) and (k in allowed or np.array_equal(a,after[k]))) for k,a in before.items()}
    return {'pass':all(checks.values()),'checks':checks,'allowed':sorted(allowed),'selected_count':len(ids),'center_opacity_rest_frozen':all(checks[k] for k in ('xyz','opacity','rest'))}
def install():
    import torch
    if 'diff_gaussian_rasterization' in sys.modules:return
    def binary(name,path):
        spec=importlib.util.spec_from_file_location(name,str(path));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
    sys.modules['diff_gaussian_rasterization._C']=binary('onec_stock_C',V1/'build/stock/onec_stock_C.so')
    path=V1/'vendor/gaussian-splatting/submodules/diff-gaussian-rasterization/diff_gaussian_rasterization/__init__.py'
    spec=importlib.util.spec_from_file_location('diff_gaussian_rasterization',str(path),submodule_search_locations=[str(path.parent)])
    m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
    k=binary('onec_knn_C',V1/'build/knn/onec_knn_C.so');p=types.ModuleType('simple_knn');p.__path__=[];p._C=k
    sys.modules['simple_knn']=p;sys.modules['simple_knn._C']=k
    sys.path.insert(1,str(V1/'vendor/gaussian-splatting'))
def load_model(path,degree):
    import torch
    inspect_ply(path,degree);install()
    from scene.gaussian_model import GaussianModel
    m=GaussianModel(degree);m.load_ply(str(path))
    for key in ('_xyz','_features_dc','_features_rest','_opacity','_scaling','_rotation'):getattr(m,key).requires_grad_(False)
    return m
def make_camera(spec):
    import torch
    install()
    from utils.graphics_utils import getProjectionMatrix
    v=torch.tensor(np.asarray(spec['w2c']).T,dtype=torch.float32,device='cuda')
    p=getProjectionMatrix(.01,100.,spec['FoVx'],spec['FoVy']).T.cuda()
    return SimpleNamespace(image_height=spec['height'],image_width=spec['width'],FoVx=spec['FoVx'],FoVy=spec['FoVy'],world_view_transform=v,full_proj_transform=v@p,camera_center=v.inverse()[3,:3])
def render(m,camera,colors=None,background=(1,1,1),python_sh=False):
    import torch
    install()
    from gaussian_renderer import render as official_render
    pipe=SimpleNamespace(compute_cov3D_python=False,convert_SHs_python=python_sh,debug=False)
    return official_render(camera,m,pipe,torch.tensor(background,dtype=torch.float32,device='cuda'),override_color=colors)['render']
def alpha(m,c):
    import torch
    return render(m,c,torch.ones((len(m.get_xyz),3),device='cuda'),(0,0,0))[0]
def support(m,c,maps):
    import torch
    colors=torch.zeros((len(m.get_xyz),3),device='cuda',requires_grad=True)
    im=render(m,c,colors,(0,0,0))
    weights=torch.as_tensor(np.stack(maps),device='cuda',dtype=torch.float32)
    return torch.autograd.grad((im*weights).sum(),colors)[0].detach()
def selected_contribution(m,c,ids):
    import torch
    feat=torch.zeros((len(m.get_xyz),3),device='cuda');feat[ids]=1
    # All other primitives remain in traversal and occlusion; only feature is zero.
    return render(m,c,feat,(0,0,0))[0]
def snapshot(m):return {k:getattr(m,p).detach().cpu().numpy().copy() for k,p in {'xyz':'_xyz','dc':'_features_dc','rest':'_features_rest','scale':'_scaling','rotation':'_rotation','opacity':'_opacity'}.items()}
