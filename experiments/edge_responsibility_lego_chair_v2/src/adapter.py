"""Read only native Graphdeco binding; whole model traversal for all scoring."""
import importlib.util, sys, types, copy
import numpy as np
from types import SimpleNamespace
from runtime import NATIVE
C0 = .28209479177387814
FIELDS = ('_xyz','_features_dc','_features_rest','_opacity','_scaling','_rotation')

def install():
    import torch
    if 'diff_gaussian_rasterization' in sys.modules: return
    def binary(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
    sys.modules['diff_gaussian_rasterization._C'] = binary('onec_stock_C', NATIVE/'build/stock/onec_stock_C.so')
    p = NATIVE/'vendor/gaussian-splatting/submodules/diff-gaussian-rasterization/diff_gaussian_rasterization/__init__.py'
    spec = importlib.util.spec_from_file_location('diff_gaussian_rasterization', str(p), submodule_search_locations=[str(p.parent)])
    mod = importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod)
    k = binary('onec_knn_C', NATIVE/'build/knn/onec_knn_C.so')
    pkg = types.ModuleType('simple_knn'); pkg.__path__=[]; pkg._C=k
    sys.modules['simple_knn']=pkg; sys.modules['simple_knn._C']=k
    sys.path.insert(1, str(NATIVE/'vendor/gaussian-splatting'))

def load_model(path):
    install()
    from scene.gaussian_model import GaussianModel
    m = GaussianModel(3); m.load_ply(str(path))
    assert m.active_sh_degree == 3 and m.get_features.shape[1] == 16
    for key in FIELDS: getattr(m,key).requires_grad_(False)
    return m

def make_camera(spec):
    import torch
    install()
    from utils.graphics_utils import getProjectionMatrix
    v = torch.tensor(np.asarray(spec['w2c']).T, dtype=torch.float32, device='cuda')
    p = getProjectionMatrix(.01,100.,spec['FoVx'],spec['FoVy']).T.cuda()
    return SimpleNamespace(image_height=spec['height'], image_width=spec['width'],
                           FoVx=spec['FoVx'], FoVy=spec['FoVy'], world_view_transform=v,
                           full_proj_transform=v@p, camera_center=v.inverse()[3,:3])

def render(m, camera, colors=None, background=(1,1,1), python_sh=False):
    import torch
    install()
    from gaussian_renderer import render as native_render
    pipe = SimpleNamespace(compute_cov3D_python=False, convert_SHs_python=python_sh, debug=False)
    return native_render(camera,m,pipe,torch.tensor(background,dtype=torch.float32,device='cuda'), override_color=colors)['render']

def effective_colors(m, camera, unclamped=False):
    from utils.sh_utils import eval_sh
    dirs = m.get_xyz-camera.camera_center
    dirs = dirs/dirs.norm(dim=1,keepdim=True)
    c = eval_sh(m.active_sh_degree, m.get_features.transpose(1,2), dirs)+.5
    return c if unclamped else c.clamp_min(0)

def support(m, camera, maps):
    import torch
    assert 1 <= len(maps) <= 3
    shapes = maps[0].shape
    weights = np.stack(list(maps)+[np.zeros(shapes,np.float32)]*(3-len(maps)))
    colors = torch.zeros((len(m.get_xyz),3),device='cuda',requires_grad=True)
    image = render(m,camera,colors,(0,0,0))
    # Override colors are unclamped. Signs survive the native color adjoint.
    out = torch.autograd.grad((image*torch.as_tensor(weights,device='cuda',dtype=torch.float32)).sum(),colors)[0]
    return out[:,:len(maps)].detach().cpu().numpy()

def alpha(m,camera):
    import torch
    return render(m,camera,torch.ones((len(m.get_xyz),3),device='cuda'),(0,0,0))[0]

def contribution(m,camera,ids):
    import torch
    feat = torch.zeros((len(m.get_xyz),3),device='cuda'); feat[ids]=1
    return render(m,camera,feat,(0,0,0))[0]

def subset(m,ids):
    from scene.gaussian_model import GaussianModel
    obj = GaussianModel(3); obj.active_sh_degree = m.active_sh_degree
    for key in FIELDS: setattr(obj,key,getattr(m,key)[ids].detach())
    return obj

def perturb(m,ids,param,amount,direction):
    """Clone only changed parameter. Other parameters retain immutable storage."""
    import torch
    from scene.gaussian_model import GaussianModel
    obj = GaussianModel(3); obj.active_sh_degree=m.active_sh_degree
    for key in FIELDS: setattr(obj,key,getattr(m,key).detach())
    key = {'dc':'_features_dc','scale':'_scaling','opacity':'_opacity'}[param]
    value = getattr(m,key).detach().clone()
    d = torch.as_tensor(direction,device='cuda',dtype=torch.float32)
    if param=='dc': value[ids,0,:] += amount*d/C0
    elif param=='scale': value[ids,:] += amount*d
    else: value[ids,:] += amount*d
    setattr(obj,key,value)
    return obj

def parameter_derivative(m,camera,ids,param,direction,probe_map):
    """Native parameter derivative including activation and SH clamp chain rule."""
    import torch
    from scene.gaussian_model import GaussianModel
    obj = GaussianModel(3); obj.active_sh_degree=m.active_sh_degree
    for key in FIELDS: setattr(obj,key,getattr(m,key).detach())
    key = {'dc':'_features_dc','scale':'_scaling','opacity':'_opacity'}[param]
    value = getattr(m,key).detach().clone().requires_grad_(True); setattr(obj,key,value)
    im = render(obj,camera)
    g = torch.autograd.grad((im*torch.as_tensor(probe_map,device='cuda',dtype=torch.float32)).sum(),value)[0]
    d = torch.as_tensor(direction,device='cuda',dtype=torch.float32)
    if param=='dc': return float((g[ids,0,:]*d/C0).sum())
    return float((g[ids,:]*d).sum())

def from_npz(path):
    import torch
    install()
    from scene.gaussian_model import GaussianModel
    obj=GaussianModel(3);obj.active_sh_degree=3
    with np.load(path) as z:
        for key in FIELDS: setattr(obj,key,torch.tensor(z[key],device='cuda',dtype=torch.float32))
    return obj

def numpy_image(im):
    return im.detach().cpu().numpy().transpose(1,2,0).astype(np.float64)
