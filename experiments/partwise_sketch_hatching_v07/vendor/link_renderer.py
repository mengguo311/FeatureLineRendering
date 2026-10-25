"""Original-row-aware tracing at the delivered CPU renderer acceptance site.

All accepted contributors at requested integer pixels are retained. No top-K.
The native CUDA implementation is neither called nor per-ID validated here.
"""
import runtime
from runtime import js,sha
from pathlib import Path
import ctypes
import subprocess
import numpy as np
import base_model as base

def prepare(a,c):
    uv,z,S=base.project_cov(a['means'],a['covariance'],c)
    E=np.asarray(c['extrinsic']);R=E[:3,:3];p=a['means']@R.T+E[:3,3]
    ok=(z>.2)&np.isfinite(S).all((1,2))
    prec=a.get('precision');prec=R@prec[ok]@R.T if prec is not None else None
    plane=base.clamped_plane(p[ok],R@a['covariance'][ok]@R.T,c,prec)
    col=base.source_colors(a,c) if 'SH' in a else a['colors']
    ar=[np.ascontiguousarray(v,np.float64) for v in [uv[ok],z[ok],S[ok],plane,a['opacity'][ok],col[ok]]]
    ids=np.asarray(a.get('source_index',np.arange(len(z))),np.int64)
    if ids.shape!=z.shape or len(np.unique(ids))!=len(ids) or (ids<0).any():
        raise ValueError('source_index must be unique nonnegative original-row IDs')
    return ar,np.ascontiguousarray(ids[ok]),ok

class Renderer:
    def __init__(self,build):
        build=Path(build);build.mkdir(parents=True,exist_ok=True)
        src=Path(__file__).parent
        receipts=[]
        for name in ('baseline','link'):
            code=src/f'source_ewa_{name}.cpp';lib=build/f'libsource_{name}.so'
            stamp=lib.with_suffix('.sha256')
            if not lib.exists() or not stamp.exists() or stamp.read_text()!=sha(code):
                cmd=['g++','-O2','-shared','-fPIC','-std=c++11',str(code),'-o',str(lib)]
                r=subprocess.run(cmd,capture_output=True,text=True,timeout=120)
                receipts.append(dict(argv=cmd,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr))
                r.check_returncode();stamp.write_text(sha(code))
        if receipts:js(build/'COMPILE.json',receipts)
        base.LIB_PATH=build/'libsource_baseline.so';base._sl=None
        self.lib=ctypes.CDLL(str(build/'libsource_link.so'))
        self.lib.source_ewa_link.argtypes=[ctypes.c_int]*3+[ctypes.c_void_p]*6+[ctypes.c_double]*2+[ctypes.c_void_p]*9+[ctypes.c_int64]
        self.lib.source_ewa_link.restype=None
        self.lib.link_event_count.restype=ctypes.c_int64
        self.lib.link_overflow_count.restype=ctypes.c_int64
        self.lib.link_copy_events.argtypes=[ctypes.c_void_p]*2

    def baseline(self,a,c):return base.render_source(a,c)

    def render(self,a,c,xy=None,strength=None,max_events=3_000_000):
        ar,ids,ok=prepare(a,c);h,w=c['height'],c['width']
        sample_map=None
        if xy is not None:
            xy=np.asarray(xy,np.int32).reshape(-1,2)
            if len(np.unique(xy,axis=0))!=len(xy) or (xy<0).any() or (xy[:,0]>=w).any() or (xy[:,1]>=h).any():
                raise ValueError('unique in-bounds sample pixels required')
            sample_map=np.full((h,w),-1,np.int32)
            sample_map[xy[:,1],xy[:,0]]=np.arange(len(xy),dtype=np.int32)
        st=None if strength is None else np.ascontiguousarray(np.asarray(strength)[ok],np.float64)
        if st is not None and (not np.isfinite(st).all() or (st<0).any()):raise ValueError('bad strength')
        out={k:np.empty(shape,np.float64) for k,shape in [('rgb',(h,w,3)),('alpha',(h,w)),
             ('median_camera_z',(h,w)),('center_depth_proxy',(h,w)),('expected_camera_z',(h,w))]}
        contribution=np.empty((h,w),np.float64)
        ptr=lambda v:None if v is None else v.ctypes.data
        self.lib.source_ewa_link(len(ids),h,w,*[ptr(v) for v in ar],c['fx'],c['fy'],
            *[ptr(v) for v in out.values()],ptr(ids),ptr(sample_map),ptr(st),ptr(contribution),max_events)
        if self.lib.link_overflow_count():raise RuntimeError('trace overflow; no truncated trace may be used')
        n=self.lib.link_event_count();ii=np.empty((n,3),np.int64);vv=np.empty((n,5),np.float64)
        self.lib.link_copy_events(ptr(ii),ptr(vv))
        trace={k:ii[:,i].copy() for i,k in enumerate(('sample_index','source_index','culled_local_index'))}
        trace.update({k:vv[:,i].copy() for i,k in enumerate(('alpha','T','weight','depth','center_z'))})
        out={k:v.astype(np.float32) for k,v in out.items()}
        out['contribution']=contribution.astype(np.float32)
        return out,trace

def validate_trace(a,c,xy,frame,trace):
    n=len(xy);s=trace['sample_index'];ids=trace['source_index'];w=trace['weight']
    mass=np.bincount(s,w,minlength=n)
    colors=base.source_colors(a,c) if 'SH' in a else a['colors']
    rgb=np.ones((n,3))*(1-mass[:,None])
    for j in range(3):rgb[:,j]+=np.bincount(s,w*colors[ids,j],minlength=n)
    xx,yy=np.asarray(xy).T
    me=float(np.max(np.abs(mass-frame['alpha'][yy,xx])))
    re=float(np.max(np.abs(rgb-frame['rgb'][yy,xx])))
    assert me<=1e-6 and re<=1e-6,(me,re)
    assert np.allclose(trace['alpha']*trace['T'],w,rtol=0,atol=1e-14)
    return dict(samples=n,events=len(w),source_ids=int(len(np.unique(ids))),mass_max_error=me,
                full_SH_rgb_max_error=re,captured_mass_fraction=1.,truncation=False)
