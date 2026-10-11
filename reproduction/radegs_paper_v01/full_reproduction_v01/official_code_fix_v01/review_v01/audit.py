"""Post-training CPU audit and scientific visualizations; no fitting to GT."""
import json, sys, time, os
from pathlib import Path
os.environ['MPLCONFIGDIR']='/mnt/hdd1/u00134/radegs_paper_reproduction_v01/official_code_fix_v01/cache/matplotlib'
import numpy as np
import open3d as o3d
from scipy.io import loadmat
from scipy.spatial import cKDTree
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
W=Path(__file__).resolve().parents[5]
sys.path.insert(0,str(W/'reproduction/radegs_paper_v01/stage2'))
from safety import atomic_json,sha256
H=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');O=H/'official_code_fix_v01';R=O/'review_v01'
M=O/'models/scan24_official_half30k';GT=H/'data/eval_gt/dtu_eval_scan24'
def cloud(p):return np.asarray(o3d.io.read_point_cloud(str(p)).points)
def stats(d):
    assert len(d) and np.isfinite(d).all()
    return {'count':len(d),'below20mm_count':int((d<20).sum()),'excluded_fraction':float((d>=20).mean()),'official_mean_mm':float(d[d<20].mean()),'diagnostic_untruncated_mean_mm':float(d.mean()),'quantiles_mm':np.quantile(d,[0,.5,.9,.99,1]).tolist()}
data=cloud(M/'vis/vis_024_d2s.ply');stl=cloud(GT/'Points/stl/stl024_total.ply')
m=loadmat(GT/'ObsMask/ObsMask24_10.mat');obs,bb,res=[m[k] for k in ('ObsMask','BB','Res')];bb=bb.astype(np.float32)
inbound=((data>=bb[:1]-60)&(data<bb[1:]+120)).sum(-1)==3;data_in=data[inbound]
grid=np.around((data_in-bb[:1])/res).astype(np.int32);gin=((grid>=0)&(grid<np.expand_dims(obs.shape,0))).sum(-1)==3
gi=grid[gin];data_obs=data_in[gin][obs[gi[:,0],gi[:,1],gi[:,2]].astype(bool)]
plane=loadmat(GT/'ObsMask/Plane24.mat')['P'];target=stl[(np.c_[stl,np.ones(len(stl))]*plane.reshape(1,4)).sum(-1)>0]
print('Query exact saved official samples',len(data),len(target),flush=True)
d2s=cKDTree(stl).query(data_obs,workers=2)[0];s2d=cKDTree(data_in).query(target,workers=2)[0]
metric=json.loads((M/'vis/results.json').read_text())
for key,dist in [('mean_d2s',d2s),('mean_s2d',s2d)]:assert abs(float(dist[dist<20].mean())-metric[key])<1e-7
r={'d2s':stats(d2s),'s2d':stats(s2d),'official_metric_mm':metric,'sample_counts':{'downsampled':len(data),'inbound':len(data_in),'in_obs':len(data_obs),'stl':len(stl),'stl_above':len(target)},'method_variant':'official_code_fix_v01','units':'aligned DTU mm; native normalization reversed by unchanged C24 evaluator','GT_role':'post-training evaluation/display only','saved_samples_sha256':sha256(M/'vis/vis_024_d2s.ply'),'diagnostic_only':'untruncated statistics do not replace official CD; no thresholds changed'}
atomic_json(R/'DISTANCE_AUDIT.json',r);print(r,flush=True)
meshes=[o3d.io.read_triangle_mesh(str(M/n)) for n in ('recon.ply','recon_culled.ply','recon_aligned.ply')]
mesh_meta=[]
for name,mesh in zip(('raw','culled','aligned'),meshes):
    v=np.asarray(mesh.vertices);assert np.isfinite(v).all();mesh_meta.append({'kind':name,'vertices':len(v),'triangles':len(mesh.triangles),'bounds':[v.min(0).tolist(),v.max(0).tolist()]})
fig=plt.figure(figsize=(16,10));previews=[]
for row,mesh in enumerate([meshes[0],meshes[2]]):
    preview=mesh.simplify_quadric_decimation(100000);preview.compute_triangle_normals()
    v=np.asarray(preview.vertices);t=np.asarray(preview.triangles);n=np.asarray(preview.triangle_normals)
    previews.append({'row':row,'display_triangles':len(t),'operation':'quadric decimation to100000 for CPU display ONLY; no preview mesh saved or evaluated'})
    light=np.array([.4,-.3,.85]);light/=np.linalg.norm(light);shade=.30+.70*np.abs(n@light);colors=shade[:,None]*np.array([.65,.76,.88])[None,:]
    for j,(az,el) in enumerate([(20,20),(110,20),(200,60)]):
        ax=fig.add_subplot(2,3,row*3+j+1,projection='3d');ax.add_collection3d(Poly3DCollection(v[t],facecolors=colors,linewidth=0))
        bounds=v
        if row:
            show=target[::max(1,len(target)//18000)];ax.scatter(*show.T,s=.2,c='tomato',alpha=.25,rasterized=True);bounds=np.r_[v,target]
        center=(bounds.min(0)+bounds.max(0))/2;span=max(np.ptp(bounds,axis=0))*.53
        ax.set_xlim(center[0]-span,center[0]+span);ax.set_ylim(center[1]-span,center[1]+span);ax.set_zlim(center[2]-span,center[2]+span);ax.set_box_aspect([1,1,1]);ax.view_init(elev=el,azim=az)
        ax.set_title('Raw TSDF (scene units)' if row==0 else 'Official culled/aligned mesh + GT points (mm)',fontsize=9);ax.set_xlabel('x');ax.set_ylabel('y');ax.set_zlabel('z')
fig.suptitle('Actual scan24 reconstruction / official_code_fix_v01\nCPU preview simplified to100k triangles only for display. Official CD=%.6f mm; GT distances excluded>=20mm: %.4f%%'%(metric['overall'],100*r['s2d']['excluded_fraction']))
fig.tight_layout();fig.savefig(R/'MESH_VIEWS.png',dpi=145);plt.close(fig)
atomic_json(R/'MESH_AUDIT.json',{'meshes':mesh_meta,'preview':previews})
records=[json.loads(x) for x in (M/'iteration_loss.jsonl').read_text().splitlines()];exports=json.loads((M/'export_summary.json').read_text())
fig,axs=plt.subplots(2,3,figsize=(16,8));it=np.array([x['iteration'] for x in records])
for key in ('photo','distortion','normal','total'):
    y=np.array([x[key] for x in records]);assert np.isfinite(y).all();axs[0,0].semilogy(it[::50],np.maximum(y[::50],1e-12),label=key)
axs[0,0].legend();axs[0,0].set_title('Actual losses (every50th recorded value)')
axs[0,1].plot(it,[x['points'] for x in records]);axs[0,1].set_title('Gaussian count')
axs[0,2].plot(it,[x['opacity_logit_posinf'] for x in records],label='+Inf raw logits');axs[0,2].set_title('Sigmoid opacity=1 endpoints; not NaN')
axs[1,0].plot(it[::50],[x['alpha_ge_half']/x['pixels'] for x in records[::50]]);axs[1,0].set_title('Alpha>=.5 fraction; RANDOM training views')
coverage={}
for iteration in (15000,30000):
    rows=sorted((x for x in exports if x['iteration']==iteration),key=lambda x:x['view']);assert len(rows)==49
    vals=np.array([x['alpha_ge_half']/x['pixels'] for x in rows]);coverage[str(iteration)]={'min':float(vals.min()),'mean':float(vals.mean()),'max':float(vals.max())}
    axs[1,1].plot(range(49),vals,label=str(iteration));axs[1,2].plot(range(49),[x['positive_depth']/x['pixels'] for x in rows],label=str(iteration))
axs[1,1].set_title('SAME 49 views: alpha>=.5 coverage');axs[1,2].set_title('SAME49 views: positive median depth');axs[1,1].legend();axs[1,2].legend()
for ax in [*axs[0],axs[1,0]]:
    ax.axvline(15000,color='red',ls='--',lw=.8)
    for x in records:
        if x['opacity_reset_after_forward']:ax.axvline(x['iteration'],color='gray',ls=':',lw=.5)
for ax in axs.flat:ax.grid(alpha=.2)
fig.suptitle('Official C24 scan24: fixed15k/30k diagnostics, no held-out NVS claim');fig.tight_layout();fig.savefig(R/'TRAIN_AND_COVERAGE.png',dpi=145);plt.close(fig)
atomic_json(R/'TRAJECTORY_AUDIT.json',{'records':len(records),'fixed_view_alpha_coverage':coverage,'reset_iterations':[x['iteration'] for x in records if x['opacity_reset_after_forward']],'raw_opacity_posinf_max':max(x['opacity_logit_posinf'] for x in records),'raw_opacity_posinf_final':records[-1]['opacity_logit_posinf'],'losses_finite':True})
print('CPU plots and exact sample audit complete',flush=True)
