"""Independent CPU replica of stock 3DGS forward and fixed-full-T feature operators.

This is NOT execution of the native CUDA renderer. The acceptance rules are read
from the pinned historical CUDA source, and numerical agreement is measured
against its stored outputs in test_cpu_native.py. All original PLY IDs survive.
No K truncation or H*W*N allocation occurs. Only this stage's C++ is compiled.
"""
import os
os.environ.setdefault('OMP_NUM_THREADS','2')
os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
import ctypes
import hashlib
import json
import math
from pathlib import Path
import subprocess
import numpy as np
from plyfile import PlyData

ROOT=Path(__file__).resolve().parents[2]
BUILD=ROOT/'out/gaer_multiview_contour_regions_v01/cpu_native'
SOURCE=Path('/home/u00134/3dgs_line/gaer_attribution_capacity_v02/out/gaer_attribution_capacity_v02/native_shape/cuda_rasterizer')

CPP=r'''
#include <algorithm>
#include <cmath>
#include <numeric>
#include <vector>
#include <omp.h>
extern "C" int raster(int n,int w,int h,int c,int f,const float* xy,
 const float* conic,const float* opacity,const float* colors,const float* depth,
 const int* rect,const float* maps,const float* features,const float* bg,
 float* rgb,float* alpha,float* mass,float* adj,float* fout,float* ez,float* front){
 const int gx=(w+15)/16,gy=(h+15)/16,nt=gx*gy;
 std::vector<int> order(n);std::iota(order.begin(),order.end(),0);
 std::stable_sort(order.begin(),order.end(),[&](int a,int b){return depth[a]<depth[b];});
 std::vector<std::vector<int>> bins(nt);
 for(int i:order) for(int ty=rect[4*i+1];ty<rect[4*i+3];++ty)
  for(int tx=rect[4*i];tx<rect[4*i+2];++tx) bins[ty*gx+tx].push_back(i);
 const int threads=2;
 std::vector<float> mm(size_t(threads)*n,0.f), aa(size_t(threads)*n*c,0.f);
 #pragma omp parallel num_threads(2)
 {
  int th=omp_get_thread_num();float* m=mm.data()+size_t(th)*n;
  float* ad=aa.data()+size_t(th)*n*c;
  #pragma omp for schedule(static)
  for(int t=0;t<nt;++t){
   const int x0=(t%gx)*16,y0=(t/gx)*16;
   float tr[256];bool done[256];std::fill(tr,tr+256,1.f);std::fill(done,done+256,false);
   for(int id:bins[t]){
    const float cx=xy[2*id],cy=xy[2*id+1],a=conic[3*id],b=conic[3*id+1],d=conic[3*id+2],op=opacity[id];
    if(op<1.f/255.f)continue;
    for(int yy=0;yy<16 && yy+y0<h;++yy)for(int xx=0;xx<16 && xx+x0<w;++xx){
     int q=yy*16+xx;if(done[q])continue;int p=(y0+yy)*w+x0+xx;
     float dx=cx-(x0+xx),dy=cy-(y0+yy);
     float power=-.5f*(a*dx*dx+d*dy*dy)-b*dx*dy;
     if(power>0.f)continue;
     float al=std::min(.99f,op*std::exp(power));if(al<1.f/255.f)continue;
     float test=tr[q]*(1.f-al);if(test<.0001f){done[q]=true;continue;}
     float weight=al*tr[q];
     for(int k=0;k<3;++k)rgb[3*p+k]+=colors[3*id+k]*weight;
     m[id]+=weight;for(int k=0;k<c;++k)ad[size_t(id)*c+k]+=weight*maps[size_t(p)*c+k];
     for(int k=0;k<f;++k)fout[size_t(p)*f+k]+=weight*features[size_t(id)*f+k];
     ez[p]+=weight*depth[id];
     if(tr[q]>.5f && test<=.5f)front[p]=depth[id];
     tr[q]=test;
    }
   }
   for(int yy=0;yy<16 && yy+y0<h;++yy)for(int xx=0;xx<16 && xx+x0<w;++xx){
    int p=(y0+yy)*w+x0+xx;float T=tr[yy*16+xx];alpha[p]=1.f-T;
    for(int k=0;k<3;++k)rgb[3*p+k]+=T*bg[k];
   }
  }
 }
 for(int i=0;i<n;++i){mass[i]=mm[i]+mm[n+i];for(int k=0;k<c;++k)adj[size_t(i)*c+k]=aa[size_t(i)*c+k]+aa[size_t(n+i)*c+k];}
 return 0;
}
'''
_LIB=None

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()

def library():
    global _LIB
    if _LIB is not None:return _LIB
    BUILD.mkdir(parents=True,exist_ok=True)
    source_hash=hashlib.sha256(CPP.encode()).hexdigest()
    cpp=BUILD/('raster_'+source_hash[:16]+'.cpp');so=cpp.with_suffix('.so')
    cpp.write_text(CPP)
    flags=['g++','-O3','-std=c++17','-fPIC','-shared','-fopenmp','-ffp-contract=off',str(cpp),'-o',str(so)]
    if not so.exists():subprocess.run(flags,check=True,env=dict(os.environ,TMPDIR=str(BUILD)))
    manifest=dict(cpu_replica=True,cuda_executed=False,source_sha256=source_hash,binary_sha256=sha(so),compile_argv=flags,threads=2,read_reference_sources={str(SOURCE/n):sha(SOURCE/n) for n in ('forward.cu','auxiliary.h')})
    manifest_text=json.dumps(manifest,indent=2)+'\n'
    (BUILD/'BUILD.json').write_text(manifest_text)
    evidence=ROOT/'artifacts/gaer_multiview_contour_regions_v01/tdd'
    evidence.mkdir(parents=True,exist_ok=True)
    (evidence/'native_BUILD.json').write_text(manifest_text)
    _LIB=ctypes.CDLL(str(so));_LIB.raster.restype=ctypes.c_int
    _LIB.raster.argtypes=[ctypes.c_int]*5+[ctypes.c_void_p]*16
    return _LIB

def load_model_cpu(record):
    path=Path(record['model'])
    if sha(path)!=record['model_sha256']:raise ValueError('original PLY hash mismatch')
    v=PlyData.read(str(path))['vertex']
    def stack(names):return np.stack([v[n] for n in names],axis=1).astype(np.float32)
    xyz=stack(['x','y','z']);n=len(xyz)
    if n!=record['count']:raise ValueError('original ID count mismatch')
    dc=stack(['f_dc_'+str(i) for i in range(3)])[:,None,:]
    rest=stack(['f_rest_'+str(i) for i in range(45)]).reshape(n,3,15).transpose(0,2,1)
    q=stack(['rot_'+str(i) for i in range(4)]);q/=np.linalg.norm(q,axis=1,keepdims=True)
    return dict(xyz=xyz,scales=np.exp(stack(['scale_'+str(i) for i in range(3)])),rotations=q,opacity=(1/(1+np.exp(-stack(['opacity'])[:,0]))).astype(np.float32),shs=np.ascontiguousarray(np.concatenate([dc,rest],axis=1)),original_id=np.arange(n,dtype=np.int32),model_sha256=record['model_sha256'])

def covariance(model):
    if '_cov' in model:return model['_cov']
    r,x,y,z=model['rotations'].T
    R=np.empty((len(r),3,3),np.float32)
    R[:,0,0]=1-2*(y*y+z*z);R[:,0,1]=2*(x*y-r*z);R[:,0,2]=2*(x*z+r*y)
    R[:,1,0]=2*(x*y+r*z);R[:,1,1]=1-2*(x*x+z*z);R[:,1,2]=2*(y*z-r*x)
    R[:,2,0]=2*(x*z-r*y);R[:,2,1]=2*(y*z+r*x);R[:,2,2]=1-2*(x*x+y*y)
    L=R*model['scales'][:,None,:]
    model['_cov']=L@L.transpose(0,2,1)
    return model['_cov']

def sh_color(model,camera):
    pos=np.linalg.inv(np.asarray(camera['w2c'],np.float32))[:3,3]
    d=model['xyz']-pos;d/=np.linalg.norm(d,axis=1,keepdims=True)
    x,y,z=d.T;xx=x*x;yy=y*y;zz=z*z
    basis=np.stack([np.full_like(x,.28209479177387814),-.4886025119029199*y,.4886025119029199*z,-.4886025119029199*x,
     1.0925484305920792*x*y,-1.0925484305920792*y*z,.31539156525252005*(2*zz-xx-yy),-1.0925484305920792*x*z,.5462742152960396*(xx-yy),
     -.5900435899266435*y*(3*xx-yy),2.890611442640554*x*y*z,-.4570457994644658*y*(4*zz-xx-yy),.3731763325901154*z*(2*zz-3*xx-3*yy),-.4570457994644658*x*(4*zz-xx-yy),1.445305721320277*z*(xx-yy),-.5900435899266435*x*(xx-3*yy)],axis=1)
    return np.ascontiguousarray(np.maximum(np.einsum('ni,nic->nc',basis,model['shs'])+.5,0),dtype=np.float32)

def preprocess(model,camera):
    xyz=model['xyz'];n=len(xyz);w=int(camera['width']);h=int(camera['height'])
    V=np.asarray(camera['w2c'],np.float32);tx=np.float32(math.tan(camera['FoVx']/2));ty=np.float32(math.tan(camera['FoVy']/2))
    fx=np.float32(w/(2*tx));fy=np.float32(h/(2*ty))
    p=xyz@V[:3,:3].T+V[:3,3];z=p[:,2]
    xy=np.empty((n,2),np.float32);xy[:,0]=(p[:,0]/tx/(z+1e-7)+1)*w*.5-.5;xy[:,1]=(p[:,1]/ty/(z+1e-7)+1)*h*.5-.5
    clipped_x=np.clip(p[:,0]/z,-1.3*tx,1.3*tx)*z;clipped_y=np.clip(p[:,1]/z,-1.3*ty,1.3*ty)*z
    J=np.zeros((n,2,3),np.float32);J[:,0,0]=fx/z;J[:,1,1]=fy/z;J[:,0,2]=-fx*clipped_x/(z*z);J[:,1,2]=-fy*clipped_y/(z*z)
    T=J@V[:3,:3];cov=T@covariance(model)@T.transpose(0,2,1)
    cov[:,0,0]+=.3;cov[:,1,1]+=.3
    a=cov[:,0,0];b=cov[:,0,1];d=cov[:,1,1];det=a*d-b*b
    conic=np.stack([d/det,-b/det,a/det],axis=1).astype(np.float32)
    mid=.5*(a+d);radius=np.ceil(3*np.sqrt(mid+np.sqrt(np.maximum(.1,mid*mid-det)))).astype(np.int32)
    gx=(w+15)//16;gy=(h+15)//16
    rect=np.empty((n,4),np.int32)
    rect[:,0]=np.clip(np.trunc((xy[:,0]-radius)/16),0,gx);rect[:,1]=np.clip(np.trunc((xy[:,1]-radius)/16),0,gy)
    rect[:,2]=np.clip(np.trunc((xy[:,0]+radius+15)/16),0,gx);rect[:,3]=np.clip(np.trunc((xy[:,1]+radius+15)/16),0,gy)
    valid=(z>.2)&(det!=0)&(rect[:,2]>rect[:,0])&(rect[:,3]>rect[:,1])
    rect[~valid]=0;radius[~valid]=0
    return dict(width=w,height=h,xy=xy,conic=conic,radius=radius,depth=np.ascontiguousarray(z),rect=rect,opacity=np.ascontiguousarray(model['opacity'].reshape(-1)),colors=sh_color(model,camera),original_id=model.get('original_id',np.arange(n,dtype=np.int32)),cov2d=cov)

def rasterize(projected,maps=None,features=None,background=(1,1,1)):
    """Return full forward and A^T(maps); features computes A(features) at full T.

    maps: H,W,C. features: N,F, normally membership of selected original IDs.
    mass=sum_pixels alpha*T. Alpha is 1-final_T. depth is accepted weighted
    Gaussian-center depth (proxy, not a surface or sensor depth).
    """
    p=projected;w=p['width'];h=p['height'];n=len(p['xy'])
    maps=np.zeros((h,w,0),np.float32) if maps is None else np.ascontiguousarray(maps,np.float32)
    if maps.ndim==2:maps=maps[...,None]
    if maps.shape[:2]!=(h,w):raise ValueError('maps camera shape mismatch')
    features=np.zeros((n,0),np.float32) if features is None else np.ascontiguousarray(features,np.float32)
    if features.ndim==1:features=features[:,None]
    if len(features)!=n:raise ValueError('feature original ID shape mismatch')
    c=maps.shape[2];f=features.shape[1]
    rgb=np.zeros((h,w,3),np.float32);alpha=np.zeros((h,w),np.float32);mass=np.zeros(n,np.float32);adj=np.zeros((n,c),np.float32);feat=np.zeros((h,w,f),np.float32);ez=np.zeros((h,w),np.float32);front=np.full((h,w),np.nan,np.float32);bg=np.ascontiguousarray(background,np.float32)
    arrays=[p['xy'],p['conic'],p['opacity'],p['colors'],p['depth'],p['rect'],maps,features,bg,rgb,alpha,mass,adj,feat,ez,front]
    lib=library()
    lib.raster.argtypes=[ctypes.c_int]*5+[ctypes.c_void_p]*len(arrays)
    code=lib.raster(n,w,h,c,f,*[ctypes.c_void_p(a.ctypes.data) for a in arrays])
    if code:raise RuntimeError('CPU raster returned '+str(code))
    expected=np.divide(ez,alpha,out=np.full_like(ez,np.nan),where=alpha>0)
    return dict(rgb=rgb,alpha=alpha,mass=mass,adjoints=adj,features=feat,expected_depth=expected,median_depth=front,projected=p,cpu_replica=True)

def render(model,camera,maps=None,features=None,**kwargs):
    return rasterize(preprocess(model,camera),maps=maps,features=features,**kwargs)
