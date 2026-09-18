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


def load_asset(path):
    """Full SH3 vanilla asset, without opacity/density/center pruning."""
    from plyfile import PlyData
    p=PlyData.read(str(path))['vertex']
    mu=np.stack([p[k] for k in ['x','y','z']],axis=1).astype('f4')
    scale=np.exp(np.stack([p[f'scale_{k}'] for k in range(3)],axis=1)).astype('f4')
    quat=np.stack([p[f'rot_{k}'] for k in range(4)],axis=1).astype('f4')
    quat/=np.linalg.norm(quat,axis=1,keepdims=True)
    opacity=(1/(1+np.exp(-np.asarray(p['opacity'],np.float64)))).astype('f4')[:,None]
    dc=np.stack([p[f'f_dc_{k}'] for k in range(3)],axis=1)[:,None,:]
    rest=np.stack([p[f'f_rest_{k}'] for k in range(45)],axis=1).reshape(-1,3,15).transpose(0,2,1)
    asset=dict(mu=mu,scale=scale,quat=quat,opacity=opacity,sh=np.concatenate([dc,rest],axis=1).astype('f4'))
    if not all(np.isfinite(a).all() for a in asset.values()): raise ValueError('nonfinite GS')
    return asset


def perturb_asset(asset,mode):
    """Fixed, non-tuned clone/split intervention; parent IDs are provenance only."""
    if mode not in ('clone','split'): raise ValueError('unknown intervention')
    n=len(asset['mu'])
    hashes=[hashlib.sha256(f'20260918:parent:{i}'.encode()).digest() for i in range(n)]
    chosen=sorted(range(n),key=lambda i:hashes[i])[:n//2]
    selected=np.zeros(n,bool); selected[chosen]=True
    parents=np.repeat(np.arange(n),1+selected.astype(int))
    child={k:v[parents].copy() for k,v in asset.items()}
    changed=selected[parents]
    child['opacity'][changed]=1-np.sqrt(1-child['opacity'][changed].astype(np.float64))
    if mode=='split':
        q=child['quat'][changed].astype(np.float64); q/=np.linalg.norm(q,axis=1,keepdims=True)
        w,x,y,z=q.T
        R=np.stack([1-2*(y*y+z*z),2*(x*y-w*z),2*(x*z+w*y),
                    2*(x*y+w*z),1-2*(x*x+z*z),2*(y*z-w*x),
                    2*(x*z-w*y),2*(y*z+w*x),1-2*(x*x+y*y)],axis=1).reshape(-1,3,3)
        s=child['scale'][changed]; axis=s.argmax(1); rows=np.arange(len(s))
        offset=.2*s[rows,axis,None]*R[rows,:,axis]
        sign=np.tile([-1.,1.],len(chosen))
        child['mu'][changed]+=offset*sign[:,None]
        s[rows,axis]*=np.sqrt(.96); child['scale'][changed]=s
    return child,parents,selected


def qualification_metrics(base,changed,roi):
    """Conjunctive stock RGB qualification, on the unchanged baseline ROI."""
    import cv2
    roi=np.asarray(roi,bool); n=int(roi.sum())
    if not n: return dict(valid=False,passed=False,roi_pixels=0,reason='empty foreground')
    a=np.asarray(base,np.float64); b=np.asarray(changed,np.float64)
    error=np.abs(a-b); mse=float(np.mean((a[roi]-b[roi])**2))
    psnr=None if mse==0 else float(-10*np.log10(mse))
    means=[]
    for c in range(3):
        x,y=a[:,:,c],b[:,:,c]
        ux=cv2.GaussianBlur(x,(11,11),1.5,borderType=cv2.BORDER_REFLECT)
        uy=cv2.GaussianBlur(y,(11,11),1.5,borderType=cv2.BORDER_REFLECT)
        vx=cv2.GaussianBlur(x*x,(11,11),1.5,borderType=cv2.BORDER_REFLECT)-ux*ux
        vy=cv2.GaussianBlur(y*y,(11,11),1.5,borderType=cv2.BORDER_REFLECT)-uy*uy
        vxy=cv2.GaussianBlur(x*y,(11,11),1.5,borderType=cv2.BORDER_REFLECT)-ux*uy
        s=((2*ux*uy+.01**2)*(2*vxy+.03**2))/((ux*ux+uy*uy+.01**2)*(vx+vy+.03**2))
        means.append(float(s[roi].mean()))
    ssim=min(means); p99=float(np.quantile(error.max(2)[roi],.99))
    valid=bool(np.isfinite(a).all() and np.isfinite(b).all() and np.isfinite(ssim))
    passed=valid and (psnr is None or psnr>=40) and ssim>=.995 and p99<=8/255
    return dict(valid=valid,passed=bool(passed),roi_pixels=n,mse=mse,psnr_db=psnr,
        psnr_infinite=mse==0,ssim=ssim,ssim_channels=means,p99_max_channel_abs=p99,
        max_abs=float(error[roi].max()),thresholds=dict(psnr_db=40,ssim=.995,p99_max_channel_abs=8/255))


def prerequisite_verdict(calibration,qualifications,coverage,outside,forbidden_reads,gs_unchanged):
    """Only decide prerequisite validity. Unmeasured scientific gates never pass."""
    calibrated=bool(calibration) and all(x['passed'] for x in calibration)
    nontrivial=bool(coverage) and all(np.isfinite(x) and x>=.20 for x in coverage)
    valid_interventions=[k for k,rows in qualifications.items() if rows and all(x['passed'] for x in rows) and nontrivial]
    box_ok=bool(outside) and all(np.isfinite(x) and x<=.01 for x in outside)
    reasons=[]
    if not calibrated: reasons.append('native renderer calibration not passed')
    if not valid_interventions: reasons.append('no qualifying nontrivial RGB-near-equivalent intervention')
    if not box_ok: reasons.append('outside-box contribution prerequisite not passed')
    if forbidden_reads: reasons.append('forbidden input reads')
    if not gs_unchanged: reasons.append('original GS hash changed')
    ready=not reasons
    gates={
        'G0':dict(state='PENDING' if ready else 'INVALID',reason='; '.join(reasons) if reasons else 'renderer/intervention/input prerequisites pass; search and accepted-view checks not yet measured'),
        'G1':dict(state='NOT_EVALUATED',reason='local image evidence stage not reached'),
        'G2':dict(state='UNCERTIFIED',reason='no frozen local output or independent DEV span annotations; C support not evaluated'),
        'G3':dict(state='NOT_EVALUATED',reason='no eligible local outputs for repeatability'),
        'G4':dict(state='NOT_EVALUATED',reason='local controls and independent visible-region comparison not reached'),
        'G5':dict(state='UNCERTIFIED',reason='three independent evaluators unavailable; glyph stage not reached')}
    return dict(verdict='ENGINEERING_NOT_READY' if not calibrated else 'UNDETERMINED',
        experiment_valid=False,may_run_local_probe=ready,valid_interventions=valid_interventions,
        gates=gates,reasons=reasons,scientific_failure=False)


def audit_opens(trace,allowed_files,runtime_roots,write_root):
    """Audit strace -f -yy open/openat/openat2/creat, including native calls."""
    import re
    files={str(Path(p).resolve()) for p in allowed_files}
    roots=[Path(p).resolve() for p in runtime_roots]+[Path(write_root).resolve()]
    read=set(); bad=set(); denied=set(); unparsed=[]; opened=set()
    for line in trace.splitlines():
        if not re.search(r'\b(open|openat|openat2|creat)\(',line): continue
        name=re.search(r'"([^"\n]+)"',line)
        if not name: unparsed.append(line); continue
        if '= -1' in line:
            if 'EACCES' in line: denied.add(name.group(1))
            continue
        resolved=re.search(r'= \d+<([^>]+)>',line)
        if not resolved: unparsed.append(line); continue
        p=Path(resolved.group(1)).resolve(); s=str(p); opened.add(s)
        if s in files: read.add(s)
        elif not any(p==r or r in p.parents for r in roots): bad.add(s)
    return dict(forbidden_successes=sorted(bad),denied=sorted(denied),
        approved_data_reads=sorted(read),successful_paths=sorted(opened),unparsed_open_lines=unparsed)


def save_sheet(path,panels):
    """Deterministic labeled RGB panels; never fabricate images for an unrun stage."""
    import cv2
    tiles=[]
    for title,rgb in panels:
        im=np.round(np.clip(rgb,0,1)*255).astype(np.uint8)[:,:,::-1]
        tile=np.full((im.shape[0]+28,im.shape[1],3),255,np.uint8); tile[28:]=im
        cv2.putText(tile,title,(4,19),cv2.FONT_HERSHEY_SIMPLEX,.42,(0,0,0),1,cv2.LINE_AA)
        tiles.append(tile)
    ok,data=cv2.imencode('.png',np.hstack(tiles),[cv2.IMWRITE_PNG_COMPRESSION,6])
    if not ok: raise RuntimeError('PNG encoder failed')
    with Path(path).open('xb') as f: f.write(data.tobytes())
    return hashlib.sha256(data.tobytes()).hexdigest()
