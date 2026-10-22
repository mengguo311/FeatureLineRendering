"""Exact full-image accepted alpha*T footprint, not semantic ownership."""
import runtime
from runtime import sha, js
from pathlib import Path
import ctypes
import subprocess
import numpy as np
from scipy import ndimage
from link_renderer import Renderer, prepare


class FootprintRenderer(Renderer):
    def __init__(self, build):
        super().__init__(build)
        build=Path(build);code=Path(__file__).with_name('source_ewa_footprint.cpp')
        lib=build/'libsource_footprint.so';stamp=lib.with_suffix('.sha256')
        if not lib.exists() or not stamp.exists() or stamp.read_text()!=sha(code):
            cmd=['g++','-O2','-shared','-fPIC','-std=c++11',str(code),'-o',str(lib)]
            r=subprocess.run(cmd,capture_output=True,text=True,timeout=120)
            js(build/'COMPILE_FOOTPRINT.json',dict(argv=cmd,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr))
            r.check_returncode();stamp.write_text(sha(code))
        old=self.lib;self.lib=ctypes.CDLL(str(lib))
        for name in ('source_ewa_link','link_event_count','link_overflow_count','link_copy_events'):
            getattr(self.lib,name).argtypes=getattr(old,name).argtypes
            getattr(self.lib,name).restype=getattr(old,name).restype
        self.lib.footprint_config.argtypes=[ctypes.c_void_p]*4
        self.lib.footprint_config.restype=None

    def footprint(self,a,c,category,proxy_depth,sample_valid,xy=None,strength=None):
        category=np.ascontiguousarray(category,np.int32)
        depth=np.ascontiguousarray(proxy_depth,np.float64)
        valid=np.ascontiguousarray(sample_valid,np.uint8)
        shape=(c['height'],c['width'])
        if category.shape!=shape or depth.shape!=shape or valid.shape!=shape or not np.isin(category,[0,1,2]).all():
            raise ValueError('full image target/band/far category, depth and validity required')
        _,_,ok=prepare(a,c)
        local=np.zeros((int(ok.sum()),5),np.float64)
        self.lib.footprint_config(category.ctypes.data,depth.ctypes.data,valid.ctypes.data,local.ctypes.data)
        try:
            frame,trace=self.render(a,c,xy,strength)
        finally:
            self.lib.footprint_config(None,None,None,None)
        stats=np.zeros((len(ok),5));stats[ok]=local
        return frame,trace,stats


def footprint_inputs(frame):
    target=frame['path_mask']
    near=ndimage.binary_dilation(target,iterations=2)
    category=np.where(target,0,np.where(near,1,2)).astype(np.int32)
    depth=frame['proxy_depth']
    valid=np.isfinite(depth)&(frame['alpha']>=.5)&(np.abs(depth-frame['median_camera_z'])<=.08)
    return category,depth,valid


def resolve_footprint(per_view, prior):
    """Freeze a strict exclusion rule; never fill prior UNKNOWN from proximity.

    A visible full-kernel responsibility is inside the 3px capsule, its fixed
    2px dilation band, or the remaining image. This is BUILD self-consistency.
    """
    pv=np.asarray(per_view,float)
    if pv.ndim!=3 or pv.shape[2]!=5 or not np.isfinite(pv).all() or (pv<0).any():
        raise ValueError('expected finite nonnegative view x original row x 5')
    if not np.allclose(pv[:,:,1:4].sum(2),pv[:,:,0],rtol=1e-12,atol=1e-10):
        raise ValueError('inside/band/far mass must partition total')
    total,inside,band,far,accepted=pv.sum(0).T
    fraction=np.divide(far,total,out=np.ones_like(total),where=total>0)
    view_fraction=np.divide(pv[:,:,3],pv[:,:,0],out=np.zeros_like(pv[:,:,0]),where=pv[:,:,0]>0)
    # Ignore only views with less than .02 raw pixel-mass, preserving them in pv.
    worst=np.max(np.where(pv[:,:,0]>=.02,view_fraction,0),axis=0)
    depth_fraction=np.divide(accepted,inside,out=np.zeros_like(total),where=inside>0)
    views=(pv[:,:,4]>=.002).sum(0)
    prior_good=(prior['strength']>0)&~prior['unknown']
    good=prior_good&(accepted>=.02)&(views>=2)&(depth_fraction>=.7)&(fraction<=.02)&(worst<=.05)
    reason=np.full(len(total),'supported',dtype='<U28')
    reason[(fraction>.02)|(worst>.05)]='far_footprint'
    reason[depth_fraction<.7]='footprint_depth_mixed'
    reason[(accepted<.02)|(views<2)]='footprint_low_exposure'
    reason[~prior_good]='prior_path_unknown'
    reason[total==0]='footprint_unobserved'
    return dict(source_index=np.arange(len(total)),per_view_mass=pv,total=total,inside=inside,
                boundary_band=band,far=far,accepted_inside=accepted,far_fraction=fraction,
                worst_view_far_fraction=worst,depth_fraction=depth_fraction,distinct_views=views,
                unknown=~good,reason=reason,strength=np.where(good,prior['strength'],0.))
