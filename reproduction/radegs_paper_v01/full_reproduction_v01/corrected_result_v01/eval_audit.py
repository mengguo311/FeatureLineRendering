"""CPU validation of exact official saved samples/metric masks and visual audit.
GT is used after training solely for evaluation and display. No parameter fit.
"""
import json,sys
from pathlib import Path
import numpy as np
import open3d as o3d
from scipy.io import loadmat
from scipy.spatial import cKDTree
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'reproduction/radegs_paper_v01/stage2'))
from safety import atomic_json,sha256,verify_seal
HDD=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');OUT=HDD/'full_reproduction_v01/precision_v01/corrected_result_audit_v01';MODEL=OUT/'official_eval/model';GT=HDD/'data/eval_gt/dtu_eval_scan24'
seal=json.loads((MODEL/'eval.seal.json').read_text());assert verify_seal(MODEL/'eval.seal.json','eval',seal['inputs'])
metric=json.loads((MODEL/'vis/results.json').read_text())
def cloud(p):return np.asarray(o3d.io.read_point_cloud(str(p)).points)
data=cloud(MODEL/'vis/vis_024_d2s.ply');stl=cloud(GT/'Points/stl/stl024_total.ply')
m=loadmat(GT/'ObsMask/ObsMask24_10.mat');obs,bb,res=[m[k] for k in ['ObsMask','BB','Res']];bb=bb.astype(np.float32)
inbound=((data>=bb[:1]-60)&(data<bb[1:]+120)).sum(-1)==3;data_in=data[inbound]
grid=np.around((data_in-bb[:1])/res).astype(np.int32);gin=((grid>=0)&(grid<np.expand_dims(obs.shape,0))).sum(-1)==3
grid_in=grid[gin];in_obs=obs[grid_in[:,0],grid_in[:,1],grid_in[:,2]].astype(bool);data_obs=data_in[gin][in_obs]
plane=loadmat(GT/'ObsMask/Plane24.mat')['P'];above=(np.c_[stl,np.ones(len(stl))]*plane.reshape(1,4)).sum(-1)>0;target=stl[above]
d2s=cKDTree(stl).query(data_obs,workers=2)[0];s2d=cKDTree(data_in).query(target,workers=2)[0]
def stats(d):return {'count':len(d),'below20mm_count':int((d<20).sum()),'below20mm_fraction':float((d<20).mean()),'at_or_above20mm_fraction':float((d>=20).mean()),'official_truncated_mean_mm':float(d[d<20].mean()),'diagnostic_untruncated_mean_mm':float(d.mean()),'quantiles_mm':np.quantile(d,[0,.5,.9,.99,1]).tolist()}
r={'d2s':stats(d2s),'s2d':stats(s2d),'official_metric_mm':metric,'sample_counts':{'data_down':len(data),'data_in':len(data_in),'data_in_obs':len(data_obs),'stl':len(stl),'stl_above':len(target)},'mask_and_unit':'Unchanged C24 ObsMask/Plane, aligned mm coordinates, strict distance<20mm mean','GT_role':'posttraining evaluation/display only','not_alternative_scientific_metric':'untruncated statistics are explicitly diagnostic, not replacement paper CD'}
for key,dist in [('mean_d2s',d2s),('mean_s2d',s2d)]:assert abs(dist[dist<20].mean()-metric[key])<1e-7,(key,metric[key],dist[dist<20].mean())
atomic_json(OUT/'official_distance_audit.json',r)
raw=o3d.io.read_triangle_mesh(str(MODEL/'recon.ply'));aligned=o3d.io.read_triangle_mesh(str(MODEL/'recon_aligned.ply'))
fig=plt.figure(figsize=(18,11));angles=[(20,20),(110,20),(200,60)]
# Fixed stride display subsample, no data quality selection or mesh adjustment.
show=target[::max(1,len(target)//12000)]
for row,mesh in enumerate([raw,aligned]):
 v=np.asarray(mesh.vertices);t=np.asarray(mesh.triangles)
 for j,(az,el) in enumerate(angles):
  ax=fig.add_subplot(2,3,row*3+j+1,projection='3d');poly=Poly3DCollection(v[t],facecolor='orangered',edgecolor='maroon',linewidth=.3);ax.add_collection3d(poly)
  if row:
   ax.scatter(*show.T,s=.2,c='gray',alpha=.25,rasterized=True);bounds=target
   ax.scatter(*v.mean(0),color='red',s=28,label='only reconstructed fragment');ax.legend(loc='upper left',fontsize=8)
  else:bounds=v
  center=(bounds.min(0)+bounds.max(0))/2;span=max(np.ptp(bounds,axis=0))*.55
  ax.set_xlim(center[0]-span,center[0]+span);ax.set_ylim(center[1]-span,center[1]+span);ax.set_zlim(center[2]-span,center[2]+span);ax.set_box_aspect([1,1,1]);ax.view_init(elev=el,azim=az)
  ax.set_title(('Raw TSDF:129 vertices/122 triangles (scene units)' if not row else 'Official culled:36 vertices/37 triangles; GT gray (mm)'),fontsize=10)
  ax.set_xlabel('x');ax.set_ylabel('y');ax.set_zlabel('z')
fig.suptitle(f'Actual corrected scan24 mesh; original thresholds; all49 views fused\nOfficial CD={metric["overall"]:.5f} mm; paper=0.46 mm. GT distance>=20mm excluded by author evaluator: {r["s2d"]["at_or_above20mm_fraction"]:.2%}.',fontsize=14)
fig.tight_layout();fig.savefig(OUT/'scan24_actual_mesh_and_GT.png',dpi=150);plt.close(fig)
print(json.dumps(r,indent=2))
