"""Appearance permissions from full original-row footprints; M1 stays UNKNOWN.

The C++ acceptance-site accumulator is vendored unchanged from v05 unit005.
Unlike its old path selector, this module evaluates a whole authored region
and never uses the optional proxy-depth diagnostic to promote M1 labels.
"""
import runtime
from runtime import output_guard,sha,js
from pathlib import Path
import ctypes
import subprocess
import numpy as np
from scipy import ndimage
from link_renderer import Renderer,prepare
from hybrid import region_strength

THRESHOLDS=dict(target_mass=.02,view_target_mass=.002,min_views=2,
                target_fraction=.7,far_fraction=.02,worst_far_fraction=.05,visible_view_mass=.02)


class RegionFootprintRenderer(Renderer):
    def __init__(self,build):
        build=output_guard(build);super().__init__(build)
        code=Path(__file__).with_name('source_ewa_region_footprint.cpp')
        lib=build/'libsource_region_footprint.so';stamp=lib.with_suffix('.sha256')
        if not lib.exists() or not stamp.exists() or stamp.read_text()!=sha(code):
            cmd=['g++','-O2','-shared','-fPIC','-std=c++11',str(code),'-o',str(lib)]
            r=subprocess.run(cmd,capture_output=True,text=True,timeout=120)
            js(build/'COMPILE_REGION_FOOTPRINT.json',dict(argv=cmd,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr))
            r.check_returncode();stamp.write_text(sha(code))
        old=self.lib;self.lib=ctypes.CDLL(str(lib))
        for name in ('source_ewa_link','link_event_count','link_overflow_count','link_copy_events'):
            getattr(self.lib,name).argtypes=getattr(old,name).argtypes
            getattr(self.lib,name).restype=getattr(old,name).restype
        self.lib.footprint_config.argtypes=[ctypes.c_void_p]*4
        self.lib.footprint_config.restype=None

    def footprint(self,a,c,category,proxy_depth,sample_valid,xy=None,strength=None):
        category=np.ascontiguousarray(category,np.int32);depth=np.ascontiguousarray(proxy_depth,np.float64)
        valid=np.ascontiguousarray(sample_valid,np.uint8);shape=(c['height'],c['width'])
        if category.shape!=shape or depth.shape!=shape or valid.shape!=shape or not np.isin(category,[0,1,2]).all():
            raise ValueError('same-camera full-image target/band/far inputs required')
        _,_,ok=prepare(a,c);local=np.zeros((int(ok.sum()),5),np.float64)
        self.lib.footprint_config(category.ctypes.data,depth.ctypes.data,valid.ctypes.data,local.ctypes.data)
        try:frame,trace=self.render(a,c,xy,strength)
        finally:self.lib.footprint_config(None,None,None,None)
        stats=np.zeros((len(ok),5));stats[ok]=local
        return frame,trace,stats


def categories(regions):
    target=np.asarray(regions)==4;near=ndimage.binary_dilation(target,iterations=2)
    return np.where(target,0,np.where(near,1,2)).astype(np.int32)


def completion_selection(per_view,binding):
    pv=np.asarray(per_view,float);n=len(binding['source_index'])
    if pv.ndim!=3 or pv.shape[1:]!=(n,5) or not np.isfinite(pv).all() or (pv<0).any():
        raise ValueError('view x original row x five nonnegative footprint channels required')
    if not np.allclose(pv[:,:,1:4].sum(2),pv[:,:,0],rtol=1e-12,atol=1e-10):
        raise ValueError('target/band/far must partition accepted alpha*T')
    total,inside,band,far,depth_diagnostic=pv.sum(0).T
    inside_fraction=np.divide(inside,total,out=np.zeros(n),where=total>0)
    far_fraction=np.divide(far,total,out=np.ones(n),where=total>0)
    vf=np.divide(pv[:,:,3],pv[:,:,0],out=np.zeros_like(pv[:,:,0]),where=pv[:,:,0]>0)
    worst=np.where(pv[:,:,0]>=.02,vf,0).max(0)
    views=(pv[:,:,1]>=.002).sum(0)
    eligible=np.asarray(binding['unknown'])&~np.asarray(binding['conflict'])
    gates=np.column_stack([eligible,inside>=.02,views>=2,inside_fraction>=.7,far_fraction<=.02,worst<=.05])
    added=gates.all(1);original=region_strength(binding)
    assert (original[added]==0).all()
    strength=added.astype(float);completed=original+strength
    return dict(source_index=binding['source_index'].copy(),original_strength=original,
                appearance_completion_strength=strength,completed_strength=completed,
                unknown_unchanged=binding['unknown'].copy(),region_id_unchanged=binding['region_id'].copy(),
                conflict_unchanged=binding['conflict'].copy(),total_mass=total,target_mass=inside,
                boundary_mass=band,far_mass=far,depth_accepted_diagnostic=depth_diagnostic,
                target_fraction=inside_fraction,far_fraction=far_fraction,worst_far_fraction=worst,
                target_views=views,eligibility_gates=gates)


def apply_fixed_ink(paper,alpha,ink_color=.03):
    paper=np.asarray(paper);alpha=np.asarray(alpha)
    if paper.shape!=alpha.shape+(3,) or not np.isfinite(paper).all() or not np.isfinite(alpha).all() or (alpha<0).any() or (alpha>1).any():
        raise ValueError('valid same-camera paper and frozen ink alpha required')
    return paper*(1-alpha[:,:,None])+ink_color*alpha[:,:,None]


def paper_residual(paper,regions,color=(.95,.95,.95)):
    d=np.abs(np.asarray(paper)-np.asarray(color)).sum(2)
    dc=np.abs(np.clip(paper,0,1)-np.asarray(color)).sum(2)
    target=regions==4;interior=ndimage.binary_erosion(target,iterations=2)
    out={}
    for name,mask in [('target_full',target),('target_interior',interior)]:
        out[name]=dict(pixels=int(mask.sum()),raw_L1_sum=float(d[mask].sum(dtype=float)),
                       raw_L1_mean=float(d[mask].mean()) if mask.any() else None,
                       clipped_L1_sum=float(dc[mask].sum(dtype=float)),
                       clipped_L1_mean=float(dc[mask].mean()) if mask.any() else None,
                       near_paper_fraction_0_15=float((dc[mask]<=.15).mean()) if mask.any() else None)
    return out
