"""Read-only replay. Prints JSON, never repairs or writes a sealed artifact."""
from env import *
from subject import run_arrays,consensus
from hierarchy import hierarchical
from protocol import transfer
from responsibility import ProjectedSource
from produce import load_model
import argparse

def run(replay):
 out=dict(readonly=True,source_files=0,units=0,replayed_masks=[],replayed_joint=[],all_N_replay_queries=0,B_hierarchy_replays=0)
 for fn in ['SOURCE_MANIFEST.json','DEPENDENCY_MANIFEST.json','ADDITIONAL_DEPENDENCIES.json']:
  for name,h in json.loads((ROOT/fn).read_text())['files'].items():assert sha(name)==h,(fn,name);out['source_files']+=1
 for name,item in json.loads((ROOT/'PLAN_SEAL.json').read_text())['members'].items():assert sha(ROOT/name)==item['sha256'],name
 for p in [*sorted((ROOT/'stageA').glob('*/*')), *sorted((ROOT/'stageB').glob('*/*')), *sorted((ROOT/'transfer').glob('*/*'))]:
  if p.is_dir():checkseal(p);out['units']+=1
 for s in SCENES:
  with np.load(linepath(s)/'SHARED_CONTROL_AND_SAMPLING.npz') as q:
   mu=(q['control'][q['control_index']]*q['basis'][...,None]).sum(1)
  line=npz(linepath(s)/'gaussians.npz');assert np.array_equal(mu,line['means'])
  reg=registry()[s];original=read_ply(reg['model']);merged=read_ply(JOINT/'scenes'/s/'model/merged_native.ply');ranges=json.loads((JOINT/'scenes'/s/'model/RANGES.json').read_text());n=len(original);assert n==ranges['source']['stop'];assert len(merged)-n==len(line['means'])
  for k in original.dtype.names:assert original[k].tobytes()==merged[k][:n].tobytes(),(s,k)
  rawline=read_ply(linepath(s)/'gaussians.ply')
  for k in rawline.dtype.names:assert rawline[k].tobytes()==merged[k][n:].tobytes(),(s,k)
  del original,merged,rawline,line
  for v in [DEV[s],AUX[s],*RESERVED[s]]:
   p=ROOT/'stageA'/s/v;a=npz(p/'SUBJECT.npz');raw=npz(rawpath(s,v));rr=consensus(list(a['masks']),raw['alpha'].squeeze(),raw['median_camera_z'].squeeze(),a['margin'])
   for k in ['candidate','possible','certain','unknown','seed_agreement']:assert np.array_equal(a[k],rr[k]),(s,v,k)
   assert a['candidate'].shape==(cam(s,v)['height'],cam(s,v)['width'])
  if replay:
   a,src,ink,floor=load_model(s);n=len(src['means']);v=DEV[s];c=cam(s,v);ref=npz(ROOT/'stageA'/s/v/'REFERENCE.npz');rgb=render(src,c,[1,1,1] if s=='ficus' else [0,0,0],floor[:n]);li=render(ink,c,[1,1,1],floor[n:]);j=render(a,c,[1,1,1] if s=='ficus' else [0,0,0],floor)
   for key,val in [('source_rgb',rgb['rgb']),('line_rgb',li['rgb']),('joint_rgb',j['rgb']),('source_alpha',rgb['alpha'])]:assert np.array_equal(ref[key],val),(s,v,key)
   out['replayed_joint'].append(dict(scene=s,view=v,bitexact=True,source_prefix_exact=True,full_SH=True))
   proj=ProjectedSource.from_asset(src,c,s);records=json.loads((ROOT/'stageA'/s/v/'SOURCE_CONTRIBUTION_CALIBRATION.json').read_text())[:3]
   for r in records:
    x=proj.query(r['uv'],all_N=True);assert np.array_equal(x['ids'],r['source_ids']);np.testing.assert_allclose(x['weight'],r['weight'],atol=2e-12,rtol=0);out['all_N_replay_queries']+=1
   del a,src,ink,floor,proj
   for v in [DEV[s]]+([RESERVED[s][0]] if s=='ficus' else []):
    raw=npz(rawpath(s,v));arr,_=run_arrays(raw['rgb'],raw['alpha'].squeeze(),raw['median_camera_z'].squeeze(),cam(s,v));old=npz(ROOT/'stageA'/s/v/'SUBJECT.npz')
    for k in old:assert np.array_equal(arr[k],old[k]),(s,v,k)
    out['replayed_masks'].append(dict(scene=s,view=v,bitexact=True))
 if replay:
  for s in SCENES:
   for v,tv in [(DEV[s],AUX[s]),(AUX[s],DEV[s]),(DEV[s],RESERVED[s][0]),(DEV[s],RESERVED[s][1])]:
    a=npz(ROOT/'stageA'/s/v/'SUBJECT.npz');b=npz(ROOT/'stageA'/s/tv/'SUBJECT.npz');ra=npz(rawpath(s,v));rb=npz(rawpath(s,tv));p=ROOT/'transfer'/s/(v+'__'+tv)
    for arm in ['candidate','rgb_alpha_control','depth_control','alpha_control']:
     r,x=transfer(a[arm],ra['median_camera_z'].squeeze(),ra['alpha'].squeeze(),cam(s,v),b[arm],rb['median_camera_z'].squeeze(),rb['alpha'].squeeze(),cam(s,tv));old=npz(p/(arm+'.npz'))
     for k in x:assert np.array_equal(x[k],old[k]),(s,v,tv,arm,k)
  s='ficus'
  for v in [DEV[s],AUX[s],*RESERVED[s]]:
   raw=npz(rawpath(s,v));m=npz(ROOT/'stageA'/s/v/'SUBJECT.npz')['candidate']
   for arm in ['rgb_depth','rgb_only','depth_only']:
    r=hierarchical(raw['rgb'],raw['median_camera_z'].squeeze(),raw['alpha'].squeeze(),m,cam(s,v),arm);old=npz(ROOT/'stageB'/s/v/(arm+'.npz'))
    for k in r:assert np.array_equal(r[k],old[k]),(v,arm,k)
    out['B_hierarchy_replays']+=1
 out['rollback']=rollback();out['resources']=guard()
 if (ROOT/'RESULTS_MANIFEST.json').exists():
  for n,v in json.loads((ROOT/'RESULTS_MANIFEST.json').read_text())['members'].items():assert sha(ROOT/n)==v['sha256'],n
  out['final_manifest_checked']=True
 print(json.dumps(out,ensure_ascii=False,indent=2));return out
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--readonly',required=True,action='store_true');p.add_argument('--replay',action='store_true');a=p.parse_args();run(a.replay)
