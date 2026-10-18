from env import *
def run(replay=False):
 for fn in ['CODE_PREEXEC.json','EVALUATION_CODE_FREEZE.json']:
  for n,h in json.loads((R/fn).read_text())['files'].items():assert sha(CODE/n)==h,(fn,n)
 f=json.loads((R/'METHOD_FREEZE.json').read_text());assert sha(R/'CONFIG.json')==f['config_sha256'] and sha(R/'METHOD_FREEZE_ZH.md')==f['method_sha256']
 for r in json.loads((R/'GATES.json').read_text())['reviews']:
  assert sha(R/r['path'])==r['sha256'],r['path']
 src=json.loads((R/'SOURCE_MANIFEST.json').read_text())['files']
 for p,h in src.items():assert sha(p)==h,p
 units=list(R.rglob('SEAL.json'))
 for p in units:checkseal(p.parent)
 out=dict(readonly=True,source_files=len(src),sealed_units=len(units),old=rollback(),resources=guard(),feature_views_replayed=0,model_replays=0,prediction_replays=0,match_replays=0,RGB_hist_exact_models=0,support_multisets_checked=0,new_GS_models=0,new_source_renders=0)
 from experiment import feature_arrays,seed_data,infer_arrays,result,old,ARMS
 from protocol import fit_supported
 from audit_metrics import compare,overlap
 actual_counts=[];actual_models=[];actual_features=[]
 from analytic import run as analytic_run
 a,c=analytic_run();saved=npz(R/'analytic/COUNTERFACTUAL.npz')
 for k,x in a.items():np.testing.assert_array_equal(saved[k],x)
 assert c==json.loads((R/'analytic/COUNTS.json').read_text());out['analytic_replayed']=True
 for s in SCENES:
  for v in views(s):
   a=npz(R/'features'/s/v/'FEATURES.npz');rgb,_,alpha=raw(s,v);w=np.where(np.isfinite(alpha),np.clip(alpha,0,1),0);np.testing.assert_array_equal(a['weight'],w);np.testing.assert_array_equal(np.sort(a['weight'].ravel()),np.sort(a['shifted_weight'].ravel()));out['support_multisets_checked']+=1
   for k in ['texture','shifted_texture']:assert a[k].shape==rgb.shape and np.isfinite(a[k]).all() and a[k].min()>=0 and a[k].max()<=1
   if replay:
    b=feature_arrays(s,v)
    for k,x in b.items():np.testing.assert_array_equal(a[k],x)
    out['feature_views_replayed']+=1
   actual_features.append(json.loads((R/'features'/s/v/'COUNT.json').read_text()))
  for arm in ARMS:
   data,valid,seeds=seed_data(s,arm);m=npz(R/'models'/s/arm/'MODEL.npz');row=json.loads((R/'models'/s/arm/'COUNT.json').read_text());assert row['fit_views']==[DEV[s],AUX[s]] and row['all_original_seeds_available']
   for v,a in seeds.items():
    b=npz(R/'models'/s/arm/(v+'_SEEDS.npz'));orig=npz(R3/'models'/s/'pooled_rgb'/(v+'_SEEDS.npz'))
    for k,x in a.items():np.testing.assert_array_equal(b[k],x)
    for k in ['uv','labels']:np.testing.assert_array_equal(b[k],orig[k])
    assert b['eligible'].all()
   b=npz(R9/'models'/s/'rgb_texture'/'MODEL.npz');np.testing.assert_array_equal(m['rgb_hist'],b['rgb_hist']);out['RGB_hist_exact_models']+=1
   if replay:
    b=fit_supported(s,[DEV[s],AUX[s]],data,3 if s=='ficus' else 2,valid)
    for k,x in b.items():np.testing.assert_array_equal(m[k],x)
    out['model_replays']+=1
   actual_models.append(dict(scene=s,arm=arm,texture_overlap=overlap(m['texture_hist']).tolist(),threshold=m['threshold'].tolist()))
   for v in views(s):
    a=result(s,v,arm);b=old(s,v,3);mask=b['inference_mask'];np.testing.assert_array_equal(a['inference_mask'],mask);np.testing.assert_array_equal(a['source_uv'],b['source_uv']);np.testing.assert_array_equal(a['unknown'],(mask&(a['labels']==0))|(b['unknown']&~mask));assert not a['labels'][~mask].any();invalid=mask&~a['feature_eligible'];assert not a['labels'][invalid].any() and not a['probability'][invalid].any() and not a['density'][invalid].any()
    if replay:
     q=infer_arrays(s,v,arm)
     for k,x in q.items():np.testing.assert_array_equal(a[k],x)
     out['prediction_replays']+=1
    u=result(s,v,'rgb_texture');n=result(s,v,'shifted_alpha_texture');cnt=json.loads((R/'inference'/s/arm/v/'COUNT.json').read_text());assert cnt['unknown']==int((mask&(a['labels']==0)).sum()) and cnt['feature_unavailable']==int(invalid.sum());cnt.update(relative_to_raw=compare(b['labels'],a['labels'],mask),relative_to_unconditional=compare(u['labels'],a['labels'],mask),relative_to_null=compare(n['labels'],a['labels'],mask));actual_counts.append(cnt)
 count=json.loads((R/'COUNTS.json').read_text());key=lambda x:(x['scene'],x['view'],x['arm']);assert sorted(actual_counts,key=key)==sorted(count['predictions'],key=key);assert actual_models==count['models'];assert actual_features==count['features'];assert len(actual_counts)==24 and len(actual_models)==6 and len(actual_features)==12
 matches=json.loads((R/'MATCH_COUNTS.json').read_text());assert len(matches['new'])==6 and len(matches['readonly_controls'])==9
 for row in matches['readonly_controls']:
  b=json.loads(Path(row['source_path']).read_text());assert {k:row[k] for k in b}==b and row['readonly_control']
 out['readonly_match_controls']=9
 if replay:
  from evaluation import match
  for arm in ARMS:
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
