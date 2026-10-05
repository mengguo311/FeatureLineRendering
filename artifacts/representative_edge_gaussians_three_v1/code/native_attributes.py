"""Frozen 3DGS attributes under the original native visibility traversal.

This module never removes a Gaussian. A channel is sum_i(alpha_i*T_i*f_i),
with black background. The same full model and camera also provide alpha/depth.
Checkpoint and historical native libraries are read-only; logs are local.
"""
from pathlib import Path
import datetime
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time
import numpy as np

HISTORICAL_BUILD = Path('/home/u00134/3dgs_line/hybrid_raster_evidence_v2/out/hybrid_raster_evidence_v2/native/BUILD.json')
HISTORICAL_WRAPPER = Path('/home/u00134/3dgs_line/hybrid_raster_evidence_v2/src/hybrid_raster_native.py')
EXPECTED_PATCHED_SO_SHA256 = '77ae2500aa02e7ee994ca6ad40ff4f9ebe80717d1d004df20fb352fed63a31e4'
ROOT = Path(__file__).resolve().parents[3]

def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()

def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()

def _local(path):
    path = Path(path).resolve()
    if not any(base == path or base in path.parents for base in (ROOT/'artifacts/representative_edge_gaussians_three_v1', ROOT/'out/representative_edge_gaussians_three_v1')):
        raise ValueError('New outputs must remain inside authorized workspace')
    return path

def atomic_json(path, value):
    path = _local(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix+'.partial')
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')
    os.replace(tmp, path)

def camera_record(cam):
    h = cam.get('native_height', cam.get('H'))
    w = cam.get('native_width', cam.get('W'))
    k = cam.get('native_K', cam.get('K'))
    c = dict(native_height=int(h), native_width=int(w),
             native_K=np.asarray(k,dtype=np.float64).tolist(),
             w2c=np.asarray(cam['w2c'],dtype=np.float64).tolist())
    h,w=c['native_height'],c['native_width']; k=np.asarray(c['native_K']); m=np.asarray(c['w2c'])
    if k.shape != (3,3) or m.shape != (4,4) or not np.isfinite(k).all() or not np.isfinite(m).all():
        raise ValueError('Invalid camera shape or finite state')
    if min(h,w)<=0 or min(k[0,0],k[1,1])<=0 or k[0,1]!=0 or k[1,0]!=0:
        raise ValueError('Invalid camera focal dimensions')
    if not np.allclose(k[[0,1],[2,2]],[(w-1)/2.,(h-1)/2.],atol=1e-8,rtol=0):
        raise ValueError('Native rasterizer requires (W-1)/2 principal point')
    return c

def camera_matrices(cam):
    c=camera_record(cam);h,w=c['native_height'],c['native_width'];k=np.asarray(c['native_K'])
    p=np.zeros((4,4),np.float32)
    p[0,0],p[1,1]=2*k[0,0]/w,2*k[1,1]/h
    p[2,2],p[2,3],p[3,2]=100./(100.-.01),-100.*.01/(100.-.01),1.
    view=np.asarray(c['w2c'],np.float32).T.copy()
    return view,(view @ p.T).copy()

def gpu_guard(log_dir):
    """Every launch refuses all unrelated compute PIDs, including same-user jobs."""
    log_dir=_local(log_dir);log_dir.mkdir(parents=True,exist_ok=True)
    devices=subprocess.run(['nvidia-smi','--query-gpu=index,uuid,name,memory.used,utilization.gpu','--format=csv,noheader'],check=True,capture_output=True,text=True).stdout.strip()
    rows=subprocess.run(['nvidia-smi','--query-compute-apps=pid,gpu_uuid,process_name,used_gpu_memory','--format=csv,noheader'],check=True,capture_output=True,text=True).stdout.strip()
    entries=[]
    for line in rows.splitlines():
        if line.strip():
            pid=int(line.split(',',1)[0]);owner=subprocess.run(['ps','-o','user=','-p',str(pid)],capture_output=True,text=True).stdout.strip()
            entries.append(dict(pid=pid,owner=owner,device_process=line))
    rec=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),pid=os.getpid(),uid=os.getuid(),devices=devices,processes=entries,cuda_visible_devices=os.environ.get('CUDA_VISIBLE_DEVICES','unset'))
    with (log_dir/'GPU_GUARD.jsonl').open('a') as f:f.write(json.dumps(rec)+'\n')
    foreign=[e for e in entries if e['pid']!=os.getpid()]
    if foreign:raise RuntimeError('GPU_BUSY foreign compute process: '+json.dumps(foreign))
    return rec

def load_checkpoint(path, expected_sha256):
    from plyfile import PlyData
    path=Path(path).resolve(); digest=sha256(path)
    if digest!=expected_sha256:raise ValueError('Checkpoint SHA256 mismatch')
    v=PlyData.read(str(path))['vertex'];read=lambda names:np.stack([np.asarray(v[n],np.float64) for n in names],axis=1)
    logit=np.asarray(v['opacity'],np.float64);opacity=np.empty_like(logit);p=logit>=0
    opacity[p]=1/(1+np.exp(-logit[p]));ex=np.exp(logit[~p]);opacity[~p]=ex/(1+ex)
    g=dict(mu=read(['x','y','z']),opacity=opacity,scale=np.exp(read(['scale_0','scale_1','scale_2'])),quat=read(['rot_0','rot_1','rot_2','rot_3']),albedo=np.clip(.5+.28209479177387814*read(['f_dc_0','f_dc_1','f_dc_2']),0.,1.))
    if not all(np.isfinite(x).all() for x in g.values()):raise ValueError('Nonfinite checkpoint')
    if np.any(g['scale']<=0) or np.any(np.linalg.norm(g['quat'],axis=1)<=1e-12):raise ValueError('Invalid checkpoint parameters')
    return g,dict(path=str(path),sha256=digest,gaussians=len(g['mu']),row_id_mapping='original PLY row, unchanged',ignored_full_sh_coefficients=sum(n.startswith('f_rest_') for n in v.data.dtype.names),recipe='SH0 clipped DC, white calibration / black attribute bg, kernel_size=0, no filter_3D')

class NativeAttributeRenderer:
    """Persistent full model; every field bank must have one row per original ID."""
    def __init__(self, checkpoint, expected_sha256, output_dir, library=None, library_sha256=None, topk=4):
        self.output_dir=_local(output_dir);self.output_dir.mkdir(parents=True,exist_ok=True)
        self.g,self.metadata=load_checkpoint(checkpoint,expected_sha256)
        if library is None:
            build=json.loads(HISTORICAL_BUILD.read_text());library=build['variants']['patched']['path'];library_sha256=EXPECTED_PATCHED_SO_SHA256
        self.library=Path(library).resolve();actual=sha256(self.library)
        if actual!=library_sha256:raise ValueError('Native binary SHA256 mismatch')
        self.topk=int(topk)
        if self.topk not in (4,32,64,128):raise ValueError('Only predeclared top4/top32/top64/top128 supported')
        self.metadata.update(library=str(self.library),library_sha256=actual,wrapper_sha256=sha256(__file__),all_gaussians_preserved=True)
        self._native=None;self._device=None
    def _prepare(self):
        if self._native is not None:return
        gpu_guard(self.output_dir)
        import torch
        self.torch=torch
        name='_gaussian_edge_native_'+str(self.topk)+'._C'
        spec=importlib.util.spec_from_file_location(name,str(self.library));native=importlib.util.module_from_spec(spec);sys.modules[name]=native;spec.loader.exec_module(native);self._native=native
        t=lambda x:torch.as_tensor(np.asarray(x),dtype=torch.float32,device='cuda').contiguous()
        self._t=t
        rot=t(self.g['quat']);rot=rot/rot.norm(dim=1,keepdim=True).clamp(min=1e-12)
        self._device=dict(xyz=t(self.g['mu']),sc=t(self.g['scale']),rot=rot,opacity=t(self.g['opacity']).reshape(-1,1),empty=torch.empty(0,device='cuda'))
    def _render(self, cam, colors, background, export_topk=False):
        colors=np.asarray(colors,np.float32)
        if colors.shape!=(len(self.g['mu']),3) or not np.isfinite(colors).all():raise ValueError('Attribute field bank must be finite N x 3')
        if np.any(colors<0) or np.any(colors>1):raise ValueError('Attribution fields must be in [0,1]')
        from io_utils import guard
        guard(800*800*self.topk*24+128*1024**2 if export_topk else 128*1024**2)
        self._prepare();gpu_guard(self.output_dir)
        torch=self.torch;t=self._t;d=self._device;c=camera_record(cam);view,full=camera_matrices(c);h,w=c['native_height'],c['native_width'];k=np.asarray(c['native_K'])
        args=[t(background),d['xyz'],t(colors),d['opacity'],d['sc'],d['rot'],1.,d['empty'],t(view),t(full),w/(2*k[0,0]),h/(2*k[1,1]),0.,h,w,d['empty'],0,t(np.linalg.inv(np.asarray(c['w2c']))[:3,3]),False,True,False]
        extras={}
        if export_topk:
            extras=dict(topk_id=torch.full((h,w,self.topk),-1,device='cuda',dtype=torch.int32),topk_w=torch.zeros((h,w,self.topk),device='cuda'),topk_depth=torch.zeros((h,w,self.topk),device='cuda'),topk_normal=torch.zeros((h,w,self.topk,3),device='cuda'),moment2=torch.zeros((h,w),device='cuda'),normal_len=torch.zeros((h,w),device='cuda'))
            args.extend(extras.values())
        else:args.extend([torch.empty(0,device='cuda',dtype=torch.int32)]+[d['empty']]*5)
        torch.cuda.synchronize();start=time.perf_counter()
        with torch.no_grad():_,rgb,alpha,normal,depth,median,radii,*_=self._native.rasterize_gaussians(*args)
        torch.cuda.synchronize();elapsed=time.perf_counter()-start
        conv=lambda x:x.detach().cpu().numpy()
        out=dict(rgb=np.moveaxis(conv(rgb),0,-1),alpha=conv(alpha[0]),depth=conv(depth[0]),median_depth=conv(median[0]),normal=np.moveaxis(conv(normal),0,-1),radii=conv(radii));out.update({k:conv(v) for k,v in extras.items()})
        if not all(np.isfinite(v).all() for v in out.values()):raise ValueError('Nonfinite native output')
        with (self.output_dir/'RENDER_TIMES.jsonl').open('a') as f:f.write(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),pid=os.getpid(),camera_hash=canonical_hash(c),gaussian_count=len(self.g['mu']),export_topk=export_topk,cuda_synchronized_wall_seconds=elapsed,background=list(background)))+'\n')
        return out
    def render_rgb(self, cam, export_topk=False):
        return self._render(cam,self.g['albedo'],[1.,1.,1.],export_topk)
    def render_attributes(self, cam, fields):
        """Return rgb[:,:,c] = sum_all_i raw(alpha_i*T_i)*fields[i,c]."""
        return self._render(cam,fields,[0.,0.,0.],False)
    def render_field_bank(self, cam, fields):
        fields=np.asarray(fields,np.float32)
        if fields.ndim!=2 or fields.shape[0]!=len(self.g['mu']):raise ValueError('Field bank N x D required')
        planes=[];reference=None
        for start in range(0,fields.shape[1],3):
            chunk=fields[:,start:start+3];pad=np.zeros((len(fields),3),np.float32);pad[:,:chunk.shape[1]]=chunk
            out=self.render_attributes(cam,pad)
            if reference is None:reference={k:out[k] for k in ('alpha','depth','median_depth')}
            elif any(not np.array_equal(reference[k],out[k]) for k in reference):raise ValueError('Changing fields changed native visibility/depth')
            planes.append(out['rgb'][:,:,:chunk.shape[1]])
        return dict(attributes=np.concatenate(planes,axis=-1),**reference)
