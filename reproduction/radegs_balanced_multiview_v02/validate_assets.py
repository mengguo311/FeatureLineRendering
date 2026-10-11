"""Full, CPU-only validation of sealed production assets and source mappings."""
import os
os.environ['OMP_NUM_THREADS']='2';os.environ['OPENBLAS_NUM_THREADS']='2';os.environ['CUDA_VISIBLE_DEVICES']='';os.environ['PYTHONDONTWRITEBYTECODE']='1'
import json,time,fcntl
from pathlib import Path
import numpy as np
import core,demo,pipeline,multiview
T=core.TASK

def ply_check(path,a):
 props=[('x','<f4'),('y','<f4'),('z','<f4')]+[(x,'<f4') for x in ['cov_xx','cov_xy','cov_xz','cov_yy','cov_yz','cov_zz','opacity']]+[(x,'u1') for x in ['red','green','blue','view_votes']]+[('source_count','<u2'),('source_anchor','<i4')]
 with path.open('rb') as f:
  header=b''
  while not header.endswith(b'end_header\n'):
   line=f.readline();assert line;header+=line
  offset=f.tell()
 assert ('element vertex '+str(len(a['means']))+'\n').encode() in header
 assert path.stat().st_size-offset==len(a['means'])*np.dtype(props).itemsize
 p=np.memmap(path,dtype=props,offset=offset,mode='r',shape=(len(a['means']),))
 for i,k in enumerate(('x','y','z')):np.testing.assert_array_equal(p[k],a['means'][:,i].astype('f4'))
 for k,i,j in [('cov_xx',0,0),('cov_xy',0,1),('cov_xz',0,2),('cov_yy',1,1),('cov_yz',1,2),('cov_zz',2,2)]:np.testing.assert_array_equal(p[k],a['covariance'][:,i,j].astype('f4'))
 np.testing.assert_array_equal(p['opacity'],a['opacity'].astype('f4'))
 for k in ('source_count','source_anchor','view_votes'):np.testing.assert_array_equal(p[k],a[k])
 for k in ('red','green','blue'):assert not np.any(p[k])
 return {'ply_vertices':len(p),'bytes_per_vertex':np.dtype(props).itemsize,'float32_serialization_exact':True}

def validate(scene,n):
 start=time.monotonic();d=T/'models'/scene/f'views_{n:02d}';assert pipeline.checkseal(d)
 a=dict(np.load(d/'balanced.npz'));p=dict(np.load(d/'provenance.npz'));m=p['source_to_asset'];ranges=json.loads((d/'SOURCES.json').read_text())['ranges'];views=[r['view'] for r in ranges];core.assert_build_views(views);assert len(views)==n
 support,counter,weight=multiview.summarize_votes(p['votes']);np.testing.assert_array_equal(weight,p['source_weight']);np.testing.assert_array_equal(support,p['source_support_count']);np.testing.assert_array_equal(counter,p['source_counter_count'])
 assert len(m)==ranges[-1]['stop'];assert m.min()==0 and m.max()==len(a['means'])-1
 np.testing.assert_array_equal(np.bincount(m,minlength=len(a['means'])),a['source_count'])
 v=np.empty(len(m),np.int8);sources={}
 for i,r in enumerate(ranges):
  path=Path(r['cache'])/'samples.npz';assert demo.sha(path)==r['samples_sha256'];s=dict(np.load(path));sources[r['view']]=s;v[r['start']:r['stop']]=i
  assert len(s['means'])==r['stop']-r['start'];assert (s['depth']>0).all() and np.isfinite(s['depth']).all()
 assert np.unique(m.astype(np.int64)*n+v).size==len(m),'duplicate member view in a group'
 means=np.concatenate([sources[x]['means'] for x in views]);pixel=np.concatenate([sources[x]['pixel'] for x in views]);tangent=np.concatenate([sources[x]['tangent'] for x in views]);darkness=np.concatenate([sources[x]['darkness'] for x in views]);fit=np.concatenate([sources[x]['fit_valid'] for x in views]);del sources
 np.testing.assert_array_equal(p['merge_eligible'],fit&(support>=2)&(counter==0))
 cov=a['covariance'];assert np.isfinite(cov).all();diag=np.diagonal(cov,axis1=1,axis2=2);assert (diag>0).all();np.testing.assert_array_equal(diag[:,0],diag[:,1]);np.testing.assert_array_equal(diag[:,1],diag[:,2]);assert not np.any(cov[:,0,1]) and not np.any(cov[:,0,2]) and not np.any(cov[:,1,2]);np.testing.assert_array_equal(cov,cov.transpose(0,2,1));assert np.isfinite(a['opacity']).all() and (a['opacity']>0).all() and (a['opacity']<=.95).all()
 anchor=a['source_anchor'];np.testing.assert_array_equal(m[anchor],np.arange(len(anchor)));np.testing.assert_allclose(diag[:,0],(.45*pixel[anchor])**2,rtol=1e-7,atol=1e-16)
 # All groups checked; no random sample. Singleton coordinates remain exact.
 single=a['source_count']==1;np.testing.assert_allclose(a['means'][single],means[anchor[single]],rtol=0,atol=1e-12)
 order=np.argsort(m,kind='stable');starts=np.r_[0,np.cumsum(a['source_count'])];maxratio=0.;merged=0
 for gid in np.flatnonzero(~single):
  ids=order[starts[gid]:starts[gid+1]];anc=anchor[gid];assert p['merge_eligible'][ids].all()
  dist=np.linalg.norm(means[ids,None]-means[None,ids],axis=-1);lim=2*np.minimum(pixel[ids,None],pixel[None,ids]);ratio=dist/lim;maxratio=max(maxratio,float(ratio.max()));assert np.all(dist<=lim+1e-12)
  ad=np.linalg.norm(means[ids]-means[anc],axis=1);assert np.all(ad<=1.25*np.minimum(pixel[ids],pixel[anc])+1e-12)
  assert np.all(np.abs(tangent[ids]@tangent[ids].T)>=np.sqrt(.5)-1e-12)
  np.testing.assert_allclose(a['means'][gid],np.average(means[ids],weights=darkness[ids],axis=0),rtol=0,atol=1e-12);merged+=1
 ply=ply_check(d/'balanced.ply',a)
 b=dict(np.load(d/'density_compensated.npz'))
 for k in a:np.testing.assert_array_equal(b[k],multiview.density_opacity(a[k],n) if k=='opacity' else a[k])
 dp=ply_check(d/'density_compensated.ply',b)
 return {'scene':scene,'tier':n,'source_rows':len(m),'gaussians':len(a['means']),'all_sources_mapped':True,'distinct_member_view_all_groups':True,'bounded_pairwise_all_merged_groups_checked':merged,'maximum_pairwise_bound_ratio':maxratio,'sigma_opacity_and_votes_verified':True,'ply':ply,'density_ply':dp,'seconds':time.monotonic()-start}

def main():
 lock=open(T/'pipeline.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);rows=[]
 for scene in demo.SCENES:
  for n in (3,12,24,47):
   r=validate(scene,n);rows.append(r);print(json.dumps(r),flush=True);demo.writejson(T/'PRODUCTION_ASSET_VALIDATION.json',{'completed':len(rows),'expected':12,'rows':rows})
if __name__=='__main__':main()
