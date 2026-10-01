#!/usr/bin/env python3
"""Derive depth-time poses from sealed mocap metadata, never from depth pixels."""
import json,hashlib,datetime
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation,Slerp
ROOT=Path(__file__).resolve().parents[1]; A=ROOT/'artifacts/independent_rgbd_asset_probe'
cfg=json.loads((A/'INPUTS.json').read_text()); p=Path(cfg['raw_root'])/'groundtruth.txt'; b=p.read_bytes(); h=hashlib.sha256(b).hexdigest()
old=[json.loads(x) for x in (A/'RAW_ACCESS.jsonl').read_text().splitlines() if json.loads(x)['path']==str(p)][0]
if h!=old['sha256']:raise ValueError('mocap metadata changed')
with (A/'RAW_ACCESS.jsonl').open('a') as f:f.write(json.dumps(dict(role='metadata_depth_time_pose',split='metadata',path=str(p),bytes=len(b),sha256=h))+'\n')
gt=np.array([s.split() for s in b.decode().splitlines() if s and not s.startswith('#')],float); sl=Slerp(gt[:,0],Rotation.from_quat(gt[:,4:]))
poses={}
for f in cfg['frames']:
 t=f['depth_timestamp']; c=np.eye(4); c[:3,:3]=sl(t).as_matrix(); c[:3,3]=[np.interp(t,gt[:,0],gt[:,l]) for l in [1,2,3]]; poses[f['id']]=c.tolist()
p=A/'DEPTH_TIME_POSES.json'; p.write_text(json.dumps(dict(input_sha256=hashlib.sha256((A/'INPUTS.json').read_bytes()).hexdigest(),groundtruth_sha256=h,poses=poses),sort_keys=True)+'\n'); (A/'DEPTH_TIME_POSES.sha256').write_text(hashlib.sha256(p.read_bytes()).hexdigest()+'\n')
