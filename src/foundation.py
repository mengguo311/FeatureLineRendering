"""Foundation prerequisites. No historical generators, caches, or disc rasterizer."""
import hashlib
import json
from pathlib import Path
import numpy as np


def freeze_json(path, value):
    """Create a canonical JSON artifact exactly once; hash the bytes actually written."""
    data=(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
    path=Path(path)
    digest=hashlib.sha256(data).hexdigest()
    with path.open('xb') as f:
        f.write(data)
    with Path(str(path)+'.sha256').open('x') as f:
        f.write(digest+'\n')
    return digest


def verified_json(path, expected_sha256):
    data=Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest()!=expected_sha256:
        raise ValueError('immutable artifact hash mismatch: '+str(path))
    return json.loads(data)


def restrict_filesystem(readonly, writable):
    """Irreversible Landlock allowlist, also covering native open calls; fail closed."""
    import ctypes
    import os
    lib=ctypes.CDLL(None,use_errno=True)
    abi=lib.syscall(444,0,0,1)
    if abi<3:
        raise RuntimeError('Landlock ABI >=3 required')
    class Ruleset(ctypes.Structure):
        _fields_=[('handled_access_fs',ctypes.c_uint64)]
    class Rule(ctypes.Structure):
        _pack_=1
        _fields_=[('allowed_access',ctypes.c_uint64),('parent_fd',ctypes.c_int32)]
    handled=(1<<15)-1
    attr=Ruleset(handled)
    ruleset=lib.syscall(444,ctypes.byref(attr),ctypes.sizeof(attr),0)
    if ruleset<0:
        raise OSError(ctypes.get_errno(),'Landlock create')
    try:
        for write,paths in [(False,readonly),(True,writable)]:
            for path in paths:
                path=Path(path).resolve(strict=True)
                rights=handled if write else (1|4|8)
                if not path.is_dir(): rights &= (1|2|4|(1<<14))
                fd=os.open(path,os.O_PATH|os.O_CLOEXEC)
                try:
                    rule=Rule(rights,fd)
                    if lib.syscall(445,ruleset,1,ctypes.byref(rule),0):
                        raise OSError(ctypes.get_errno(),'Landlock add '+str(path))
                finally:
                    os.close(fd)
        if lib.prctl(38,1,0,0,0) or lib.syscall(446,ruleset,0):
            raise OSError(ctypes.get_errno(),'Landlock restrict')
    finally:
        os.close(ruleset)


def project_jacobian(points, K, w2c):
    points=np.asarray(points,dtype=np.float64)
    K=np.asarray(K,dtype=np.float64); w2c=np.asarray(w2c,dtype=np.float64)
    q=points@w2c[:3,:3].T+w2c[:3,3]
    h=q@K.T; z=q[:,2]
    with np.errstate(divide='ignore',invalid='ignore'):
        uv=h[:,:2]/h[:,2,None]
        J=(K[None,:2,:]*h[:,2,None,None]-h[:,:2,None]*K[None,2:3,:])/h[:,2,None,None]**2
    J=J@w2c[:3,:3]
    uv[z<=0]=np.nan; J[z<=0]=np.nan
    return uv,z,J


STOCK_SITE=Path(__file__).resolve().parents[1]/'out/vrss/vendor/official_site'
STOCK_BINARY_SHA='583e896f3aaa1c2dece9c67eaaa26d919f98aae0597591bf6693b9a19530e9e9'
STOCK_WRAPPER_SHA='eafa9c3f670258b34535b7ee2832e6d8410d6a68762037216f04935ccdafba34'


def native_render(asset,K,w2c,height,width,background):
    """Unmodified stock CUDA forward + stock public wrapper; expose native state.

    Layout follows rasterizer_impl.cu @59f5f77. No projection/conic/sort proxy.
    RGB is unclipped, preserving white/black transmittance calibration semantics.
    """
    import sys
    import torch
    sys.path.insert(0,str(STOCK_SITE))
    import diff_gaussian_rasterization as dr
    if Path(dr.__file__).resolve().parent!=STOCK_SITE/'diff_gaussian_rasterization':
        raise RuntimeError('unapproved native renderer')
    for p,h in [(dr.__file__,STOCK_WRAPPER_SHA),(dr._C.__file__,STOCK_BINARY_SHA)]:
        if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h:
            raise ValueError('stock renderer hash mismatch')
    K=np.asarray(K); w2c=np.asarray(w2c)
    if not np.allclose(K[2],[0,0,1]) or K[0,1]!=0 or K[1,0]!=0:
        raise ValueError('stock camera requires pinhole K without skew')
    P=np.zeros((4,4),np.float32); near,far=.01,100.
    P[0,0],P[1,1]=2*K[0,0]/width,2*K[1,1]/height
    P[0,2],P[1,2]=(2*K[0,2]+1)/width-1,(2*K[1,2]+1)/height-1
    P[2,2],P[2,3],P[3,2]=far/(far-near),-far*near/(far-near),1
    view=torch.tensor(w2c.T.copy(),dtype=torch.float32,device='cuda')
    projection=view@torch.tensor(P.T.copy(),device='cuda')
    center=torch.tensor(np.linalg.inv(w2c)[:3,3],dtype=torch.float32,device='cuda')
    arrays={k:torch.tensor(v,dtype=torch.float32,device='cuda').contiguous() for k,v in asset.items()}
    arrays['quat']=torch.nn.functional.normalize(arrays['quat'],dim=1)
    bg=torch.full((3,),float(background),device='cuda'); empty=torch.empty(0,device='cuda')
    settings=dr.GaussianRasterizationSettings(image_height=height,image_width=width,
        tanfovx=float(width/(2*K[0,0])),tanfovy=float(height/(2*K[1,1])),bg=bg,
        scale_modifier=1.,viewmatrix=view,projmatrix=projection,sh_degree=3,
        campos=center,prefiltered=False,debug=False)
    with torch.no_grad():
        result=dr._C.rasterize_gaussians(bg,arrays['mu'],empty,arrays['opacity'],arrays['scale'],
            arrays['quat'],1.,empty,view,projection,settings.tanfovx,settings.tanfovy,
            height,width,arrays['sh'],3,center,False,False)
        wrapper,_=dr.GaussianRasterizer(settings)(means3D=arrays['mu'],means2D=torch.zeros_like(arrays['mu']),
            shs=arrays['sh'],opacities=arrays['opacity'],scales=arrays['scale'],rotations=arrays['quat'])
    rendered,rgb,radii,geom,binning,img=result
    n=len(asset['mu']); pixels=height*width
    state={'stock_rgb':rgb.permute(1,2,0).cpu().numpy(),
           'wrapper_rgb':wrapper.permute(1,2,0).cpu().numpy(),'radii':radii.cpu().numpy()}
    layouts=[(geom,[('depths','f4',(n,)),('clamped','u1',(n,3)),('internal_radii','i4',(n,)),
                    ('means2D','f4',(n,2)),('cov3D','f4',(n,6)),('conic','f4',(n,4)),('rgb','f4',(n,3))]),
             (binning,[('point_list','u4',(rendered,))]),
             (img,[('final_T','f4',(height,width)),('n_contrib','u4',(height,width)),('ranges','u4',(pixels,2))])]
    for buffer,layout in layouts:
        raw=buffer.cpu().numpy(); offset=0
        for key,dtype,shape in layout:
            offset=(offset+127)&~127
            size=int(np.prod(shape)); itemsize=np.dtype(dtype).itemsize
            if offset+size*itemsize>raw.nbytes: raise ValueError('native buffer layout overflow')
            state[key]=np.frombuffer(raw,dtype=dtype,count=size,offset=offset).reshape(shape).copy()
            offset+=size*itemsize
    tiles=((width+15)//16)*((height+15)//16)
    state['ranges']=state['ranges'][:tiles].copy()
    for key in ['depths','clamped','internal_radii','means2D','cov3D','conic','rgb']:
        state[key][state['radii']==0]=0 # inactive native memory is unspecified, not data
    return state


def replay_native(state,height,width,selected,outside,background):
    """Replay all contributing splats with stock rules, retaining depth layers."""
    import ctypes
    library=Path(__file__).resolve().parents[1]/'out/point_feature_foundation/setup/composite.so'
    lib=ctypes.CDLL(str(library)); fn=lib.foundation_composite
    fn.argtypes=[ctypes.c_int,ctypes.c_int]+[ctypes.c_void_p]*8+[ctypes.c_float,ctypes.c_void_p]
    fn.restype=None
    n=len(state['depths'])
    shapes=[(n,2),(n,4),(n,3),(n,), (len(state['point_list']),),(((width+15)//16)*((height+15)//16),2),(n,),(n,)]
    values=[state[k] for k in ['means2D','conic','rgb','depths','point_list','ranges']]+[selected,outside]
    arrays=[np.ascontiguousarray(v,dtype=d) for v,d in zip(values,['f4']*4+['u4']*2+['u1']*2)]
    if any(a.shape!=s for a,s in zip(arrays,shapes)): raise ValueError('native replay shape mismatch')
    if arrays[4].size and (arrays[4].max()>=n or arrays[5].max()>arrays[4].size):
        raise ValueError('native replay index overflow')
    result=np.zeros((height,width,9),np.float32)
    fn(height,width,*[a.ctypes.data for a in arrays],float(background),result.ctypes.data)
    return {'rgb':result[:,:,:3],'alpha':result[:,:,3],'selected':result[:,:,4],
            'outside':result[:,:,5],'depth_quantiles':result[:,:,6:9]}


def calibration_metrics(white_state,stock_black,replay_white):
    transmittance=white_state['stock_rgb']-stock_black
    alpha=1-transmittance
    errors={
        'rgb_max_abs':float(np.max(np.abs(white_state['stock_rgb']-replay_white['rgb']))),
        'black_rgb_max_abs':float(np.max(np.abs(stock_black-(replay_white['rgb']-(1-replay_white['alpha'])[:,:,None])))),
        'alpha_max_abs':float(np.max(np.abs(alpha-replay_white['alpha'][:,:,None]))),
        'native_T_max_abs':float(np.max(np.abs(white_state['final_T']-(1-replay_white['alpha'])))),
        'wrapper_max_abs':float(np.max(np.abs(white_state['stock_rgb']-white_state['wrapper_rgb'])))}
    return dict(errors,threshold=1/255,passed=all(np.isfinite(v) and v<=1/255 for v in errors.values()))
