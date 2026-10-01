#!/usr/bin/env python3
"""Readback audit and supplemental observation of already frozen identities."""
import sys,json,os,subprocess,csv
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np,cv2
from src.independent_rgbd.core import *
from src.independent_rgbd.geometry import cloud_zbuffer
from src.independent_rgbd.render import render_asset,compile_asset
from independent_rgbd_probe import A,O,inputs,resources,write_json,confine

def observe():
 cfg=inputs();seal=json.loads((A/'ASSET_SEAL.json').read_text())
 for e in seal['files']:
  if sha256(e['path'])!=e['sha256']:raise ValueError('sealed asset changed')
 reader=confine(cfg,'eval');asset=json.loads((A/'ASSET.json').read_text());curve=asset['curves'][0];one={'curves':[curve]};compiled=compile_asset(one);cloud=np.load(O/'F_fused_cloud.npz')['points'];K=np.array(cfg['K']);fmap={f['id']:f for f in cfg['frames']};poses=json.loads((A/'DEPTH_TIME_POSES.json').read_text())['poses']
 events=[e for e in json.loads((A/'OCCLUSION_REVEALS.json').read_text())['events'] if e['id']==curve['id']]
 # First event is an observation choice, not an asset/camera-domain change.
 e=events[0] if events else None;observations=[];panels=[]
 if e:
  ids=[e['before'],e['occluded'][0],e['after']]
  for id in ids:
   f=fmap[id];c=np.array(f['c2w']);dc=np.array(poses[id]);rgb=reader.read(f['rgb']);d=depth_metres(reader.read(f['depth']));cloud_d=cloud_zbuffer(cloud,K,c,(480,640));mask,_=render_asset(one,K,c,cloud_d,compiled)
   p=np.array(curve['points']);uv,z=project(p,K,c);pred=visibility(uv,z,cloud_d);duv,dz=project(p,K,dc);truth=visibility(duv,dz,d);observations.append(dict(frame=id,split=f['split'],predicted={k:int((pred==k).sum()) for k in ['consistent','occluded','contradiction','unknown']},sensor={k:int((truth==k).sum()) for k in ['consistent','occluded','contradiction','unknown']}))
   view=rgb.copy();view[mask>0]=[255,25,25];finite=np.isfinite(uv).all(1)&(z>0)
   for xy in uv[finite]:cv2.circle(view,tuple(np.rint(xy).astype(int)),3,(255,180,0),1)
   title=np.full((50,640,3),245,np.uint8);cv2.putText(title,id+' '+f['split']+' fixed ID in red, controls orange',(8,20),cv2.FONT_HERSHEY_SIMPLEX,.43,(0,0,0),1);cv2.putText(title,'pred '+str(observations[-1]['predicted']),(8,40),cv2.FONT_HERSHEY_SIMPLEX,.34,(0,0,0),1);panels.append(np.concatenate([title,view]))
  cv2.imwrite(str(A/'OCCLUSION_OBSERVATION.png'),np.concatenate(panels,axis=1)[:,:,::-1])
 confirmed=bool(observations and observations[0]['sensor']['consistent']>0 and observations[1]['sensor']['occluded']>0 and observations[2]['sensor']['consistent']>0)
 write_json(A/'REVEAL_VALIDATION.json',dict(identity=curve['id'],event=e,observations=observations,sensor_confirmed_visible_hidden_visible=confirmed,selection='first event of first frozen ID; no new stroke selection or relocation',caveat='projected visibility event counts are not certified physical occlusion; depth-time sensor categories independently checked, no human review'))
 # Demonstrate the predetermined edit in two C cameras with the largest raster differences.
 rows=list(csv.DictReader((A/'FRAME_METRICS.csv').open()));rows=sorted([r for r in rows if r['split']=='C'],key=lambda r:(-int(r['edit_changed_pixels']),int(r['index'])))[:2]
 edited=json.loads((A/'EDITED_ASSET.json').read_text());ec=edited['curves'][0];eo={'curves':[ec]};ce=compile_asset(eo);panels=[];edit_obs=[]
 for r in rows:
  f=fmap[r['frame']];c=np.array(f['c2w']);rgb=reader.read(f['rgb']);occ=cloud_zbuffer(cloud,K,c,(480,640));bm,_=render_asset(one,K,c,occ,compiled);am,_=render_asset(eo,K,c,occ,ce)
  before=rgb.copy();after=rgb.copy();before[bm>0]=[255,25,25];after[am>0]=[255,25,25]
  pair=np.concatenate([before,after],axis=1);header=np.full((55,1280,3),245,np.uint8);cv2.putText(header,r['frame']+' C | original ID left; same ID +2cm world X, width x2 right',(8,22),cv2.FONT_HERSHEY_SIMPLEX,.5,(0,0,0),1);cv2.putText(header,curve['id'],(8,45),cv2.FONT_HERSHEY_SIMPLEX,.5,(0,0,0),1);panels.append(np.concatenate([header,pair]));edit_obs.append(dict(frame=r['frame'],full_asset_changed_pixels=int(r['edit_changed_pixels']),single_id_changed_pixels=int((bm!=am).sum())))
 cv2.imwrite(str(A/'EDIT_OBSERVATION.png'),np.concatenate(panels,axis=0)[:,:,::-1]);write_json(A/'EDIT_OBSERVATION.json',dict(identity=curve['id'],views=edit_obs,selection='post-evaluation inspection of largest predetermined edit effect; full 552-camera video/domain retained'))
 print(json.dumps(dict(reveal_confirmed=confirmed,observations=observations,edit=edit_obs),indent=2))

def audit():
 cfg=inputs();raw=[json.loads(s) for s in (A/'RAW_ACCESS.jsonl').read_text().splitlines()];frames=cfg['frames'];split={str(Path(cfg['raw_root'])/f[k]):(f['split'],k) for f in frames for k in ['rgb','depth']};errors=[];counts={};first_c=None
 for i,r in enumerate(raw):
  role=r['role'];key=f"{role}/{r['split']}/"+(split[r['path']][1] if r['path'] in split else 'metadata');counts[key]=counts.get(key,0)+1
  if r['path'] in split:
   sp,typ=split[r['path']]
   if r['split']!=sp:errors.append('split mismatch')
   if role=='train' and (sp!='F' or typ!='rgb'):errors.append('training raw leak')
   if role=='build' and (sp!='F' or typ!='depth'):errors.append('construction raw leak')
   if role not in ['train','build','eval']:errors.append('unknown pixel role')
   if typ=='depth' and sp=='C':
    if role!='eval':errors.append('C depth before eval')
    if first_c is None:first_c=i
  elif role not in ['metadata_preregistration','metadata_depth_time_pose']:errors.append('unknown raw path')
  if not r['path'].startswith(cfg['raw_root']+'/'):errors.append('raw outside approved root')
 # Builder's deterministic replay must precede the first C sensor access.
 prereads=raw[:first_c] if first_c is not None else raw
 build_depth=sum(r['role']=='build' and r['split']=='F' for r in prereads)
 if build_depth!=184:errors.append('builder/reproduction order')
 seals=[]
 for name in ['MODEL_SEAL.json','ASSET_SEAL.json']:
  s=json.loads((A/name).read_text());files=s.get('files',[s])
  for e in files:seals.append(dict(path=e['path'],expected=e['sha256'],actual=sha256(e['path']),passed=sha256(e['path'])==e['sha256']))
 asset=json.loads((A/'ASSET.json').read_text());edited=json.loads((A/'EDITED_ASSET.json').read_text());ar=asset_arrays(asset);npz=np.load(A/'ASSET.npz');integrity=[]
 for k in ar:integrity.append(dict(field=k,equal=bool(np.array_equal(ar[k],npz[k]))))
 ids=[c['id'] for c in asset['curves']];unique=len(ids)==len(set(ids));edit_ok=all(a['id']==b['id'] and a['edges']==b['edges'] for a,b in zip(asset['curves'],edited['curves']))
 for c in asset['curves']:
  if c['edges']!=[[j,j+1] for j in range(len(c['points'])-1)] or c['width']!=.007:errors.append('asset topology/width changed')
 import imageio_ffmpeg
 ff=imageio_ffmpeg.get_ffmpeg_exe();v=json.loads((A/'VIDEO.json').read_text());result=subprocess.run([ff,'-v','error','-i',v['path'],'-progress','pipe:1','-f','null','-'],capture_output=True,text=True);decoded=[int(l.split('=')[1]) for l in result.stdout.splitlines() if l.startswith('frame=')][-1];v.update(decoded_frames=decoded,readback_sha256=sha256(v['path']),decode_count_exit=result.returncode);write_json(A/'VIDEO.json',v)
 if decoded!=552 or result.returncode or result.stderr or v['readback_sha256']!=v['sha256']:errors.append('video readback')
 passed=not errors and all(s['passed'] for s in seals) and all(i['equal'] for i in integrity) and unique and edit_ok
 write_json(A/'FINAL_ACCESS_AUDIT.json',dict(passed=passed,errors=errors,raw_access_counts=counts,first_C_depth_access_record_zero_based=first_c,F_build_reads_before_C=build_depth,seals=seals,asset_npz_json_parity=integrity,unique_identity=unique,edit_preserves_all_ids_topology=edit_ok,access_control='Landlock native opens, real split denial tests in BOUNDARY_*; role RAW reader logs SHA256',scope='no original scene TEST or mesh opened; tier1 code only read-only; no second worktree writes',total_resources=resources(),independent_human_review=False))
 if not passed:raise RuntimeError('final integrity audit failed')
 print('final audit PASS; decoded frames',decoded)

if __name__=='__main__':
 if sys.argv[1]=='observe':observe()
 elif sys.argv[1]=='audit':audit()
 else:raise ValueError('stage')
