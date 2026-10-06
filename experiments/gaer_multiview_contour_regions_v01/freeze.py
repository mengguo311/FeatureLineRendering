import runtime as rt
import numpy as np,json,math,subprocess
from pathlib import Path
OLD=Path('/home/u00134/3dgs_line/gaer_object_contours_v01/artifacts/gaer_object_contours_v01/INPUT_FREEZE.json')
def main():
 if (rt.ART/'INPUT_FREEZE.json').exists():return
 old=json.loads(OLD.read_text()); scenes={}; protected={str(OLD):rt.sha(OLD)}
 for name,record in old['scenes'].items():
  assert rt.sha(record['model'])==record['model_sha256'];protected[record['model']]=record['model_sha256']
  meta_path=Path(record['cameras'][0]['metadata_path']);meta=json.loads(meta_path.read_text());protected[str(meta_path)]=rt.sha(meta_path)
  assert len(meta['frames'])==86
  cameras=[]
  for idx,frame in enumerate(meta['frames']):
   key=Path(frame['file_path']).stem;c2w=np.asarray(frame['transform_matrix'],float).copy();c2w[:3,1:3]*=-1;w2c=np.linalg.inv(c2w)
   direction=c2w[:3,3]/np.linalg.norm(c2w[:3,3]);fov=float(meta['camera_angle_x']);f=800/(2*math.tan(fov/2))
   c=dict(key=key,metadata_index=idx,frame_file=frame['file_path'],width=800,height=800,FoVx=fov,FoVy=fov,w2c=w2c.tolist(),K=[[f,0,399.5],[0,f,399.5],[0,0,1]],direction=direction.tolist(),metadata_path=str(meta_path),metadata_sha256=rt.sha(meta_path),prior_exposure='GS training / possible historical research; construction holdout only')
   c['camera_sha256']=rt.digest(c);cameras.append(c)
  bykey={c['key']:c for c in cameras};assert len(bykey)==86
  for c in record['cameras']:assert np.max(np.abs(np.array(c['w2c'])-np.array(bykey[c['key']]['w2c'])))<1e-9
  chosen=['r_7','r_33']; forbidden={'r_1','r_14'}
  # Spherical farthest point coverage determined solely from metadata. Reserve forced prior views.
  while len(chosen)<34:
   candidates=[c for c in cameras if c['key'] not in chosen and c['key'] not in forbidden]
   cs=np.array([bykey[k]['direction'] for k in chosen]);best=max(candidates,key=lambda c:(float(np.min(1-cs@np.array(c['direction']))),c['key']))
   chosen.append(best['key'])
  construct=chosen[:2]+[k for j,k in enumerate(chosen[2:]) if j%4!=3][:22]
  remaining=[k for k in chosen if k not in construct];dev=remaining[:4];reserved=['r_1','r_14']+remaining[4:10]
  assert (len(construct),len(dev),len(reserved))==(24,4,8)
  dirs=np.array([c['direction'] for c in cameras]);cd=np.array([bykey[k]['direction'] for k in construct])
  coverage=np.degrees(np.arccos(np.clip(np.max(dirs@cd.T,axis=1),-1,1)))
  scenes[name]=dict(model=record['model'],model_sha256=record['model_sha256'],count=record['count'],sh_degree=3,cameras={c['key']:c for c in cameras},roles=dict(construction=construct,dev=dev,reserved=reserved),arc=record['arc'],coverage=dict(max_nearest_construct_deg=float(coverage.max()),median_nearest_construct_deg=float(np.median(coverage)),camera_z_range=[float(dirs[:,2].min()),float(dirs[:,2].max())]))
 for stage in ['gaer_kernel_space_lines_v01','gaer_view_selection_v01','gaer_object_contours_v01','gaer_attribution_capacity_v02']:
  root=Path('/home/u00134/3dgs_line')/stage
  for q in list((root/'experiments'/stage).rglob('*'))+list((root/'artifacts'/stage).rglob('*')):
   if q.is_file() and q.suffix in ('.py','.json','.md','.npz') and 'downloads' not in q.parts:protected[str(q)]=rt.sha(q)
 heads=dict(line.split(' ',1) for line in subprocess.check_output(['git','for-each-ref','--format=%(refname) %(objectname)','refs/heads'],text=True).splitlines())
 rt.atomic_json(rt.ART/'INPUT_FREEZE.json',dict(source=str(OLD),source_sha256=rt.sha(OLD),scenes=scenes,protected_before=protected,heads_before=heads,partition_rule='metadata-only spherical FPS seeded r7/r33; r1/r14 forced reserved; deterministic interleave',images_opened_before_partition=False,model_config=dict(model='gpt-6-astra',reasoning_effort='ultra'),utc=__import__('time').strftime('%Y-%m-%dT%H:%M:%SZ',__import__('time').gmtime())))
 rt.guard('camera_freeze');print({n:{'roles':r['roles'],'coverage':r['coverage']} for n,r in scenes.items()},flush=True)
if __name__=='__main__':main()
