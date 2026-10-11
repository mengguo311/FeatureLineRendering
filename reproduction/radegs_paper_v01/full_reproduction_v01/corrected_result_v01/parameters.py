"""Read-only CPU parameter statistics for both immutable trained checkpoints."""
from pathlib import Path
import sys,json
import numpy as np
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'precision_v01'))
sys.path.insert(0,str(ROOT/'reproduction/radegs_paper_v01/stage2'))
from eigen_probe import matrix_from_ply
from safety import atomic_json,sha256
HDD=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01')
OUT=HDD/'full_reproduction_v01/precision_v01/corrected_result_audit_v01'
rows=[]
def q(a):return dict(zip(['min','p01','p10','median','p90','p99','max'],np.quantile(a,[0,.01,.1,.5,.9,.99,1]).tolist()))
for it in [15000,30000]:
    path=HDD/f'models/scan24_paper_text_precision_v01_half_30k/point_cloud/iteration_{it}/point_cloud.ply'
    p,a=matrix_from_ply(path)
    scales=np.exp(np.stack([p[f'scale_{i}'] for i in range(3)],1).astype(float))
    coef=np.sqrt(np.prod(scales**2/(scales**2+p['filter_3D'][:,None].astype(float)**2),axis=1))
    opacity=1/(1+np.exp(-p['opacity'].astype(float)));effective=opacity*coef
    eig=np.linalg.eigvalsh(a.astype(float))
    row={'iteration':it,'points':len(p),'ply_sha256':sha256(path),'opacity':q(opacity),'filter_coefficient':q(coef),'effective_opacity':q(effective),'effective_below_1_over_255_fraction':float((effective<1/255).mean()),'true_smallest_cov_eigenvalue':q(eig[:,0]),'true_fallback_branch_count':int((eig[:,0]<=1e-8).sum()),'condition_number':q(eig[:,-1]/eig[:,0]),'scales':q(scales),'filter_3D':q(p['filter_3D']),'dc_features':q(np.stack([p[f'f_dc_{i}'] for i in range(3)],1)),'finite_all_fields':bool(all(np.isfinite(p[name]).all() for name in p.dtype.names))}
    rows.append(row);print(json.dumps(row),flush=True)
atomic_json(OUT/'parameter_statistics.json',{'rows':rows,'CUDA_used':False,'model_modified':False})
