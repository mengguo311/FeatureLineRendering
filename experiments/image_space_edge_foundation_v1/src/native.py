"""Read-only stock Graphdeco adapter. Retains SH3 and every original Gaussian."""
import importlib.util,sys,types
from types import SimpleNamespace
import numpy as np
from runtime import NATIVE

def install():
    import torch
    if 'diff_gaussian_rasterization' in sys.modules:return
    def binary(name,path):
        spec=importlib.util.spec_from_file_location(name,str(path));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
    sys.modules['diff_gaussian_rasterization._C']=binary('onec_stock_C',NATIVE/'build/stock/onec_stock_C.so')
    path=NATIVE/'vendor/gaussian-splatting/submodules/diff-gaussian-rasterization/diff_gaussian_rasterization/__init__.py'
    spec=importlib.util.spec_from_file_location('diff_gaussian_rasterization',str(path),submodule_search_locations=[str(path.parent)])
    m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
    k=binary('onec_knn_C',NATIVE/'build/knn/onec_knn_C.so');p=types.ModuleType('simple_knn');p.__path__=[];p._C=k
    sys.modules['simple_knn']=p;sys.modules['simple_knn._C']=k
    sys.path.insert(1,str(NATIVE/'vendor/gaussian-splatting'))
def load_model(path):
    install()
    from scene.gaussian_model import GaussianModel
    m=GaussianModel(3);m.load_ply(str(path))
    assert m.active_sh_degree==3 and m.get_features.shape[1]==16
    for k in ['_xyz','_features_dc','_features_rest','_opacity','_scaling','_rotation']:getattr(m,k).requires_grad_(False)
    return m
def make_camera(spec):
    import torch
    install()
    from utils.graphics_utils import getProjectionMatrix
    v=torch.tensor(np.asarray(spec['w2c']).T,dtype=torch.float32,device='cuda')
    p=getProjectionMatrix(.01,100.,spec['FoVx'],spec['FoVy']).T.cuda()
    return SimpleNamespace(image_height=spec['height'],image_width=spec['width'],FoVx=spec['FoVx'],FoVy=spec['FoVy'],world_view_transform=v,full_proj_transform=v@p,camera_center=v.inverse()[3,:3])
def render(model,spec):
    import torch
    from gaussian_renderer import render as stock
    c=make_camera(spec);pipe=SimpleNamespace(compute_cov3D_python=False,convert_SHs_python=False,debug=False)
    with torch.no_grad():
        rgb=stock(c,model,pipe,torch.ones(3,device='cuda'))['render']
        alpha=stock(c,model,pipe,torch.zeros(3,device='cuda'),override_color=torch.ones((len(model.get_xyz),3),device='cuda'))['render'][0]
    return rgb.permute(1,2,0).cpu().numpy(),alpha.cpu().numpy()
def stock_camera_check(model,spec):
    import torch
    from scene.cameras import Camera
    from gaussian_renderer import render as stock
    w=np.asarray(spec['w2c']);c=Camera(0,w[:3,:3].T,w[:3,3],spec['FoVx'],spec['FoVy'],torch.zeros(3,spec['height'],spec['width']),None,'calibration',0,data_device='cuda')
    pipe=SimpleNamespace(compute_cov3D_python=False,convert_SHs_python=False,debug=False)
    with torch.no_grad():a=stock(c,model,pipe,torch.ones(3,device='cuda'))['render'].permute(1,2,0).cpu().numpy()
    b,_=render(model,spec);return float(np.max(abs(a-b)))
