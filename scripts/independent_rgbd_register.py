import json,hashlib,datetime
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation,Slerp
ROOT=Path('/home/u00134/3dgs_line/independent_rgbd_asset_probe')
RAW=Path('/home/u00134/research_inputs/tum_rgbd/rgbd_dataset_freiburg1_desk')
A=ROOT/'artifacts/independent_rgbd_asset_probe'
audit=[]
def read(name):
 p=RAW/name; b=p.read_bytes(); audit.append(dict(role='metadata_preregistration',split='metadata',path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))); return b.decode()
def rows(name): return [s.split() for s in read(name).splitlines() if s and not s.startswith('#')]
r=rows('rgb.txt'); d=rows('depth.txt'); gt=np.array(rows('groundtruth.txt'),float)
ts=gt[:,0]; rots=Rotation.from_quat(gt[:,4:]); slerp=Slerp(ts,rots)
dt=np.array([float(x[0]) for x in d]); used=set(); frames=[]; excluded=[]
for idx,(t,p) in enumerate(r):
 t=float(t); j=int(np.argmin(abs(dt-t))); gap=float(abs(dt[j]-t)); k=int(np.searchsorted(ts,t))
 if gap>.02 or j in used or k==0 or k==len(ts) or ts[k]-ts[k-1]>.05:
  excluded.append(dict(rgb_index=idx,timestamp=t,reason='missing_unique_depth_or_pose',nearest_depth_gap=gap)); continue
 used.add(j); c=np.eye(4); c[:3,:3]=slerp(t).as_matrix(); c[:3,3]=[np.interp(t,ts,gt[:,l]) for l in [1,2,3]]
 rank=len(frames); frames.append(dict(id=f'frame_{idx:04d}',rgb_index=idx,timestamp=t,rgb=p,depth=d[j][1],depth_timestamp=float(dt[j]),association_dt=gap,pose_bracket_gap=float(ts[k]-ts[k-1]),c2w=c.tolist(),split='F' if rank%6==0 else 'C'))
record=dict(schema=1,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),raw_root=str(RAW),archive_sha256='e983d6830916e66dc4a46a71368046b149b283de87769690e7aa4e0b9483530c',archive_hash_status='user supplied verified; archive not reopened',sources=['https://cvg.cit.tum.de/data/datasets/rgbd-dataset/download','https://cvg.cit.tum.de/data/datasets/rgbd-dataset/file_formats'],local_README='absent in extracted official sequence; official web file_formats audited',K=[[525.,0.,319.5],[0.,525.,239.5],[0.,0.,1.]],shape=[480,640],depth_units_per_metre=5000,depth_correction_already_applied=True,frames=frames,excluded=excluded,counts=dict(rgb=len(r),depth=len(d),poses=len(gt),F=sum(x['split']=='F' for x in frames),C=sum(x['split']=='C' for x in frames)),pose_audit=dict(max_quaternion_norm_error=float(abs(np.linalg.norm(gt[:,4:],axis=1)-1).max()),max_gap=float(np.diff(ts).max()),origin='motion capture RGB optical centre; c2w; no derived GS depth'))
b=(json.dumps(record,indent=2,sort_keys=True)+'\n').encode(); (A/'INPUTS.json').write_bytes(b); (A/'INPUTS.json.sha256').write_text(hashlib.sha256(b).hexdigest()+'\n')
(A/'RAW_ACCESS.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in audit))
print(record['counts']); print(record['pose_audit']); print('association max',max(x['association_dt'] for x in frames)); print('excluded',len(excluded))
