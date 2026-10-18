from env import *
def run(replay=False):
 for freeze in ['CODE_PREEXEC.json','EVALUATION_CODE_FREEZE.json']:
  for name,h in json.loads((R/freeze).read_text())['files'].items():assert sha(CODE/name)==h,name
 f=json.loads((R/'METHOD_FREEZE.json').read_text());assert sha(R/'CONFIG.json')==f['config_sha256'] and sha(R/'METHOD_FREEZE_ZH.md')==f['method_sha256']
 sources=json.loads((R/'SOURCE_MANIFEST.json').read_text())['files']
 for p,h in sources.items():assert sha(p)==h,p
 units=list(R.rglob('SEAL.json'))
 for p in units:checkseal(p.parent)
 out=dict(readonly=True,source_files=len(sources),sealed_units=len(units),old=rollback(),resources=guard(),shape_replays=0,model_replays=0,prediction_replays=0,match_replays=0,native_arrays_checked=0,baseline_rgb_exact=True,new_GS_models=0)
 from experiment import SCENES,views,shape,shape_arrays,ARMS,seed_data,infer_arrays,result,old
 from likelihood import fit
 for s in SCENES:
  for v in views(s):
   a=shape(s,v);assert np.isfinite(a['feature']).all() and ((a['feature']>=0)&(a['feature']<=1+1e-12)).all();assert not (a['candidate']&a['subject_unknown']).any()
   if replay:
    b=shape_arrays(s,v)
    for k,x in b.items():np.testing.assert_array_equal(a[k],x,err_msg=s+'/'+v+'/'+k)
    out['shape_replays']+=1
 for arm in ARMS:
  data,seeds=seed_data(arm);m=npz(R/'models'/arm/'MODEL.npz')
  for v,ar in seeds.items():
   b=npz(R/'models'/arm/(v+'_SEEDS.npz'))
   for k,x in ar.items():np.testing.assert_array_equal(b[k],x)
  if replay:
   b=fit(data,3)
   for k,x in b.items():np.testing.assert_array_equal(m[k],x)
   out['model_replays']+=1
  for v in views('ficus'):
   a=result('ficus',v,arm);d=shape('ficus',v);np.testing.assert_array_equal(a['inference_mask'],d['candidate']);np.testing.assert_array_equal(a['unknown'],(d['candidate']&(a['labels']==0))|d['subject_unknown']);assert not a['labels'][~d['candidate']].any();assert not a['probability'][~d['candidate']].any();assert np.isfinite(a['probability']).all()
   if arm=='rgb':
    b=old('ficus',v,3)
    for k in ['labels','unknown','probability','inference_mask','source_uv']:np.testing.assert_array_equal(a[k],b[k])
   if replay:
    b=infer_arrays(v,arm)
    for k,x in b.items():np.testing.assert_array_equal(a[k],x)
    out['prediction_replays']+=1
   out['native_arrays_checked']+=1
 assert not (R/'inference/scan24').exists() and not (R/'inference/scan65').exists()
 if replay:
  from audit import calculate
  assert calculate()==json.loads((R/'mechanism_audit/COUNTS.json').read_text())
  from evaluation import match
  for arm in [*ARMS,'r05']:
   for tv in [AUX['ficus'],*RES['ficus']]:
    p=R/'evaluation'/(arm+'_'+tv);ab,aa,ad=match(DEV['ficus'],tv,arm);ba,bb,bd=match(tv,DEV['ficus'],arm);row=json.loads((p/'COUNTS.json').read_text());assert aa==row['forward'] and bb==row['reverse'];assert [[i,j] for i,(j,f) in ab.items() if f>=.75 and j in ba and ba[j][0]==i and ba[j][1]>=.75]==row['mutual']
    for n,b in [('FORWARD',ad),('REVERSE',bd)]:
     a=npz(p/(n+'.npz'))
     for k,x in b.items():np.testing.assert_array_equal(a[k],x)
    out['match_replays']+=1
 if (R/'RESULTS_MANIFEST.json').exists():
  for n,d in json.loads((R/'RESULTS_MANIFEST.json').read_text())['members'].items():assert not Path(n).is_absolute() and '..' not in Path(n).parts and not (R/n).is_symlink() and sha(R/n)==d['sha256'],n
  out['manifest_verified']=True
 if (R/'PACKAGES.json').exists():
  import tarfile
  for row in json.loads((R/'PACKAGES.json').read_text()):
   p=R/row['path'];assert sha(p)==row['sha256'];members=json.loads((R/p.name.replace('.tar.gz','.MEMBERS.json')).read_text())['members']
   with tarfile.open(p,'r:gz') as tf:
    assert set(tf.getnames())==set(members)
    for x in tf:assert x.isfile() and not x.issym() and not x.islnk() and not Path(x.name).is_absolute() and '..' not in Path(x.name).parts and hashlib.sha256(tf.extractfile(x).read()).hexdigest()==members[x.name]['sha256']
  out['packages_verified']=True
 return out
if __name__=='__main__':
 import argparse;p=argparse.ArgumentParser();p.add_argument('--readonly',action='store_true',required=True);p.add_argument('--replay',action='store_true');a=p.parse_args();print(json.dumps(run(a.replay),indent=2))
