"""CPU compilation of the exact private C24 GLM float eigensolver; no CUDA.

Numerical diagnostic only; source/native/model remain unchanged.
"""
import ctypes
import hashlib
import json
from pathlib import Path
import subprocess
import numpy as np

HDD=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01')
OUT=HDD/'full_reproduction_v01/precision_v01'
GLM=HDD/'sources/paper_text_variant/submodules/diff-gaussian-rasterization/third_party/glm'


def build():
    OUT.mkdir(parents=True,exist_ok=True)
    cpp=OUT/'eigen_probe.cpp';binary=OUT/'eigen_probe.so'
    source='''#define GLM_ENABLE_EXPERIMENTAL
#include <glm/glm.hpp>
#include <glm/gtx/pca.hpp>
extern "C" void eig(int n,const float* a,float* values,float* vectors) {
 for(int i=0;i<n;i++) {
  glm::mat3 m;
  for(int r=0;r<3;r++)for(int c=0;c<3;c++)m[c][r]=a[i*9+r*3+c];
  glm::vec3 v;glm::mat3 q;
  glm::findEigenvaluesSymReal(m,v,q);
  for(int r=0;r<3;r++){values[i*3+r]=v[r];for(int c=0;c<3;c++)vectors[i*9+r*3+c]=q[c][r];}
 }
}
'''
    cpp.write_text(source)
    subprocess.run(['g++','-shared','-fPIC','-O2','-I'+str(GLM),str(cpp),'-o',str(binary)],check=True)
    return binary


def legacy_eigh(matrix):
    binary=OUT/'eigen_probe.so'
    if not binary.exists():build()
    a=np.ascontiguousarray(matrix,dtype=np.float32).reshape(-1,3,3)
    val=np.empty((len(a),3),np.float32);vec=np.empty_like(a)
    p=ctypes.POINTER(ctypes.c_float);f=ctypes.CDLL(str(binary)).eig
    f.argtypes=[ctypes.c_int,p,p,p]
    f(len(a),a.ctypes.data_as(p),val.ctypes.data_as(p),vec.ctypes.data_as(p))
    return val,vec


def rotation(q):
    q=q/np.linalg.norm(q,axis=-1,keepdims=True);w,x,y,z=q.T
    return np.stack([1-2*(y*y+z*z),2*(x*y-w*z),2*(x*z+w*y),
        2*(x*y+w*z),1-2*(x*x+z*z),2*(y*z-w*x),
        2*(x*z-w*y),2*(y*z+w*x),1-2*(x*x+y*y)],axis=1).reshape(-1,3,3)


def matrix_from_ply(path):
    from plyfile import PlyData
    p=PlyData.read(path)['vertex'].data
    r=rotation(np.stack([p[f'rot_{i}'] for i in range(4)],axis=1))
    s=np.exp(np.stack([p[f'scale_{i}'] for i in range(3)],axis=1))
    matrix=(r*s[:,None,:])@(r*s[:,None,:]).transpose(0,2,1)
    matrix+=np.eye(3,dtype=np.float32)[None]*p['filter_3D'][:,None,None]**2
    return p,matrix


def main():
    build();allrows={}
    for iteration in [15000,30000]:
        path=HDD/f'models/scan24_paper_text_half_30k/point_cloud/iteration_{iteration}/point_cloud.ply'
        points,a=matrix_from_ply(path);values,vectors=legacy_eigh(a)
        true_values=np.linalg.eigvalsh(a.astype(np.float64))
        reconstructed=(vectors*values[:,None,:])@vectors.transpose(0,2,1)
        residual=np.linalg.norm(reconstructed-a,axis=(1,2))/np.linalg.norm(a,axis=(1,2))
        inv=(vectors/(values[:,None,:]))@vectors.transpose(0,2,1)
        inverse_residual=np.linalg.norm(inv@a-np.eye(3),axis=(1,2))
        finite=np.isfinite(inverse_residual)
        worst=int(np.argmax(np.where(finite,inverse_residual,np.inf)))
        row={'points':len(a),'eigen_reconstruction_relative_quantiles':np.quantile(residual,[0,.5,.9,.99,1]).tolist(),
            'inverse_residual_norm_quantiles_finite':np.quantile(inverse_residual[finite],[0,.5,.9,.99,1]).tolist(),
            'inverse_nonfinite':int((~finite).sum()),'inverse_residual_gt_0_1':int((inverse_residual>.1).sum()),
            'wrong_well_conditioned_branch':int(((values.min(1)>1e-8)!=(true_values.min(1)>1e-8)).sum()),
            'worst_index':worst,'worst_matrix':a[worst].tolist(),'worst_eigenvalues':values[worst].tolist(),
            'worst_true_eigenvalues':true_values[worst].tolist()}
        allrows[str(iteration)]=row;print(json.dumps({str(iteration):row}),flush=True)
    (OUT/'real_covariance_eigen_audit.json').write_text(json.dumps(allrows,indent=2)+'\n')


if __name__=='__main__':main()
