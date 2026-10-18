"""Read-only verification: no saving masks, models, metadata or rendered arrays."""
from env import *
from io_checks import *
from anchor import *
from regions import *
from run_b import load_model as load_regions
def run(replay=False):
 verify_frozen();files={}
 for f in ['SOURCE_MANIFEST.json','REPLAY_DEPENDENCIES.json']:
  if (ROOT/f).exists():files.update(json.loads((ROOT/f).read_text())['files'])
 for name,h in files.items():assert sha(name)==h,name
 units=[]
 for top in ['stageA','stageB']:
  for p in (ROOT/top).rglob('SEAL.json'):checkseal(p.parent);units.append(str(p.parent.relative_to(ROOT)))
 for s in SCENES:
  for v in views(s):
   ar=npz(ROOT/'stageA'/s/v/'SUBJECT.npz');assert ar['candidate'].shape==raw(s,v)[1].shape
 for v in views('ficus'):
  mask=npz(ROOT/'stageA/ficus'/v/'SUBJECT.npz')['candidate']
  for arm in B['arms']:
   for k in [3,5]:r=npz(ROOT/'stageB/ficus'/v/f'{arm}_k{k}.npz');validate_partition(mask,r['labels'],r['unknown'])
 result=dict(readonly=True,source_files=len(files),sealed_units=len(units),frozen_configuration=True,scientific_models_changed=0,stageA_replays=0,stageB_replays=0,shared_model_replays=0,match_replays=0,source_joint_replays=[])
 if replay:
  for s in SCENES:
   model=json.loads((ROOT/'stageA'/s/'model/MODEL.json').read_text());ss=samples(s,[DEV[s],AUX[s]]);saved=npz(ROOT/'stageA'/s/'model/FIT_SAMPLES.npz')
   for k in ss:np.testing.assert_array_equal(ss[k],saved[k])
   if model['plane']:
    m=fit_support_plane(ss['world'],ss['pixel_scale'],ss['view_id'],ss['peripheral'],ss['central']);assert m==model['plane'],s
   for v in views(s):
    rgb,z,a=raw(s,v);c=cam(s,v);m,u=coverage_mask(z,a) if model['mode']=='isolated_coverage_proxy' else plane_mask(z,a,c,model['plane']) if model['plane'] else (np.zeros_like(z,bool),a>=.1);sav=npz(ROOT/'stageA'/s/v/'SUBJECT.npz');np.testing.assert_array_equal(m,sav['candidate']);np.testing.assert_array_equal(u,sav['unknown']);result['stageA_replays']+=1
   for v,tv in [(DEV[s],AUX[s]),(AUX[s],DEV[s]),(DEV[s],RES[s][0]),(DEV[s],RES[s][1])]:
    m=npz(ROOT/'stageA'/s/v/'SUBJECT.npz')['candidate'];tm=npz(ROOT/'stageA'/s/tv/'SUBJECT.npz')['candidate'];row,ar=directed_overlap(s,v,tv,m,tm);sav=npz(ROOT/'stageA'/s/'transfer'/(v+'__'+tv+'.npz'))
    for key in ar:np.testing.assert_array_equal(ar[key],sav[key])
  q=ROOT/'stageB/ficus/models';data=npz(q/'TRAIN_OBSERVATIONS.npz')
  for arm in B['arms']:
   for k in [3,5]:
    m=load_regions(q/f'{arm}_k{k}.npz');again=fit_model(data['world'],data['rgb'],data['width'],k,arm,data['pixel_scale']);np.testing.assert_allclose(again['centers'],m['centers'],rtol=0,atol=1e-12);result['shared_model_replays']+=1
    for v in views('ficus'):
     ar=predict_view('ficus',v,m);sav=npz(ROOT/'stageB/ficus'/v/f'{arm}_k{k}.npz')
     for key in ar:np.testing.assert_array_equal(ar[key],sav[key])
     result['stageB_replays']+=1
    for tv in [AUX['ficus'],*RES['ficus']]:
     p=ROOT/'stageB/ficus/matches'/f'{arm}_k{k}_{tv}';sav=json.loads((p/'COUNTS.json').read_text());lab=npz(ROOT/'stageB/ficus'/DEV['ficus']/f'{arm}_k{k}.npz')['labels'];tlab=npz(ROOT/'stageB/ficus'/tv/f'{arm}_k{k}.npz')['labels'];ab,rr,ar=match('ficus',DEV['ficus'],tv,lab,tlab);ba,tt,br=match('ficus',tv,DEV['ficus'],tlab,lab);assert rr==sav['forward'] and tt==sav['reverse'];assert [list(t) for t in mutual_pairs(ab,ba)]==sav['mutual_pairs'];result['match_replays']+=1
     for name,r in [('FORWARD',ar),('REVERSE',br)]:
      sr=npz(p/(name+'.npz'))
      for key in r:np.testing.assert_array_equal(r[key],sr[key])
  from produce import load_model
  from format import read_ply
  from renderer import render
  for s in SCENES:
   r=json.loads((JOINT/'scenes'/s/'model/RANGES.json').read_text());n=r['source']['stop'];source=read_ply(registry()[s]['model']);merged=read_ply(JOINT/'scenes'/s/'model/merged_native.ply');line=read_ply(BASE/'arms/C/scenes'/s/'full/gaussians.ply')
   for key in source.dtype.names:assert source[key].tobytes()==merged[key][:n].tobytes(),(s,key)
   for key in line.dtype.names:assert line[key].tobytes()==merged[key][n:].tobytes(),(s,key)
   del source,merged,line
   aa,src,ink,floor=load_model(s);c=cam(s,DEV[s]);bg=[1,1,1] if s=='ficus' else [0,0,0];ref=npz(V1/'stageA'/s/DEV[s]/'REFERENCE.npz')
   for asset,back,fl,key in [(src,bg,floor[:n],'source_rgb'),(ink,[1,1,1],floor[n:],'line_rgb'),(aa,bg,floor,'joint_rgb')]:out=render(asset,c,back,fl);np.testing.assert_array_equal(out['rgb'],ref[key])
   result['source_joint_replays'].append(dict(scene=s,view=DEV[s],source_count=n,line_count=len(ink['means']),source_prefix_and_line_exact=True,full_SH_preserved=True,three_rgb_arrays_bitexact=True));del aa,src,ink,floor
 result['rollback']=rollback();result['resources']=guard()
 if (ROOT/'RESULTS_MANIFEST.json').exists():check_members(ROOT,json.loads((ROOT/'RESULTS_MANIFEST.json').read_text()));result['final_manifest_checked']=True
 return result
if __name__=='__main__':
 import argparse;p=argparse.ArgumentParser();p.add_argument('--readonly',action='store_true',required=True);p.add_argument('--replay',action='store_true');a=p.parse_args();print(json.dumps(run(a.replay),ensure_ascii=False,indent=2))
