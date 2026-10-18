from env import *
def run(replay=False):
 for fn in ['CODE_PREEXEC.json','EVALUATION_CODE_FREEZE.json']:
  for n,h in json.loads((R/fn).read_text())['files'].items():assert sha(CODE/n)==h,(fn,n)
 f=json.loads((R/'METHOD_FREEZE.json').read_text());assert sha(R/'CONFIG.json')==f['config_sha256'] and sha(R/'METHOD_FREEZE_ZH.md')==f['method_sha256']
 sources=json.loads((R/'SOURCE_MANIFEST.json').read_text())['files']
 for p,h in sources.items():assert sha(p)==h,p
 units=list(R.rglob('SEAL.json'))
 for p in units:checkseal(p.parent)
 out=dict(readonly=True,source_files=len(sources),sealed_units=len(units),old=rollback(),resources=guard(),model_replays=0,prediction_replays=0,match_replays=0,raw_exact_models=0,raw_exact_predictions=0,new_GS_models=0,new_source_renders=0)
 from experiment import seed_data,infer_arrays,result,old,ARMS
 from density import fit_density
 from audit_metrics import compare,overlap
 actual_counts=[];actual_models=[]
 for s in SCENES:
  for arm in ARMS:
   data,seeds=seed_data(s,arm);m=npz(R/'models'/s/arm/'MODEL.npz');row=json.loads((R/'models'/s/arm/'COUNT.json').read_text());assert row['fit_views']==[DEV[s],AUX[s]]
   for v,ar in seeds.items():
    b=npz(R/'models'/s/arm/(v+'_SEEDS.npz'))
    for k,x in ar.items():np.testing.assert_array_equal(b[k],x)
   if arm=='raw_rgb':
    b=npz(R3/'models'/s/'pooled_rgb'/'MODEL.npz')
    for k in m:np.testing.assert_array_equal(m[k],b[k])
    out['raw_exact_models']+=1
   if replay:
    b=fit_density(data,3 if s=='ficus' else 2)
    for k,x in b.items():np.testing.assert_array_equal(m[k],x)
    out['model_replays']+=1
   actual_models.append(dict(scene=s,arm=arm,overlap=overlap(m['hist']).tolist(),threshold=m['threshold'].tolist()))
   for v in views(s):
    a=result(s,v,arm);b=old(s,v,3);mask=b['inference_mask'];np.testing.assert_array_equal(a['inference_mask'],mask);np.testing.assert_array_equal(a['unknown'],(mask&(a['labels']==0))|(b['unknown']&~mask));assert not a['labels'][~mask].any();assert not a['labels'][mask&~a['feature_eligible']].any()
    if arm=='raw_rgb':
     for k in ['labels','unknown','probability','density','inference_mask','source_uv']:np.testing.assert_array_equal(a[k],b[k])
     out['raw_exact_predictions']+=1
    if replay:
     q=infer_arrays(s,v,arm)
     for k,x in q.items():np.testing.assert_array_equal(a[k],x)
     out['prediction_replays']+=1
    floor=result(s,v,'rgb_floor');cnt=json.loads((R/'inference'/s/arm/v/'COUNT.json').read_text());assert cnt['unknown']==int((mask&(a['labels']==0)).sum());cnt.update(relative_to_raw=compare(b['labels'],a['labels'],mask),relative_to_same_floor=compare(floor['labels'],a['labels'],mask));actual_counts.append(cnt)
 count=json.loads((R/'COUNTS.json').read_text());assert sorted(actual_counts,key=lambda x:(x['scene'],x['view'],x['arm']))==sorted(count['predictions'],key=lambda x:(x['scene'],x['view'],x['arm']));assert actual_models==count['models']
 if replay:
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
