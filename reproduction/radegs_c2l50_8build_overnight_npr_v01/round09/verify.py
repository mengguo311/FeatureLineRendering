from env import *
def rows(a):
 a=np.ascontiguousarray(a).reshape(-1,3);return np.sort(a.view(np.dtype((np.void,a.dtype.itemsize*3))).ravel())
def run(replay=False):
 for fn in ['CODE_PREEXEC.json','EVALUATION_CODE_FREEZE.json']:
  for n,h in json.loads((R/fn).read_text())['files'].items():assert sha(CODE/n)==h,(fn,n)
 f=json.loads((R/'METHOD_FREEZE.json').read_text());assert sha(R/'CONFIG.json')==f['config_sha256'] and sha(R/'METHOD_FREEZE_ZH.md')==f['method_sha256']
 src=json.loads((R/'SOURCE_MANIFEST.json').read_text())['files']
 for p,h in src.items():assert sha(p)==h,p
 units=list(R.rglob('SEAL.json'))
 for p in units:checkseal(p.parent)
 out=dict(readonly=True,source_files=len(src),sealed_units=len(units),old=rollback(),resources=guard(),feature_views_replayed=0,model_replays=0,prediction_replays=0,match_replays=0,raw_exact_models=0,raw_exact_predictions=0,null_multisets_checked=0,new_GS_models=0,new_source_renders=0)
 from experiment import feature_arrays,seed_data,infer_arrays,result,old,ARMS
 from likelihood import fit
 from audit_metrics import compare,overlap
 actual_counts=[];actual_models=[]
 for s in SCENES:
  for v in views(s):
   a=npz(R/'features'/s/v/'FEATURES.npz');rgb,_,_=raw(s,v);block=max(1,int(round(33*min(rgb.shape[:2])/581)))
   for y in range(0,rgb.shape[0],block):
    for x in range(0,rgb.shape[1],block):np.testing.assert_array_equal(rows(rgb[y:y+block,x:x+block]),rows(a['shuffled_rgb'][y:y+block,x:x+block]));out['null_multisets_checked']+=1
   assert a['texture'].shape==rgb.shape and np.isfinite(a['texture']).all() and a['texture'].min()>=0 and a['texture'].max()<=1
   if replay:
    b=feature_arrays(s,v)
    for k in b:np.testing.assert_array_equal(a[k],b[k])
    out['feature_views_replayed']+=1
  for arm in ARMS:
   data,seeds=seed_data(s,arm);m=npz(R/'models'/s/arm/'MODEL.npz');row=json.loads((R/'models'/s/arm/'COUNT.json').read_text());assert row['fit_views']==[DEV[s],AUX[s]]
   for v,ar in seeds.items():
    b=npz(R/'models'/s/arm/(v+'_SEEDS.npz'))
    for k,x in ar.items():np.testing.assert_array_equal(b[k],x)
   if arm=='raw_rgb':
    b=npz(R3/'models'/s/'pooled_rgb'/'MODEL.npz');np.testing.assert_array_equal(m['rgb_hist'],b['hist']);np.testing.assert_array_equal(m['threshold'],b['threshold']);out['raw_exact_models']+=1
   if replay:
    b=fit(data,3 if s=='ficus' else 2,arm)
    for k,x in b.items():np.testing.assert_array_equal(m[k],x)
    out['model_replays']+=1
   actual_models.append(dict(scene=s,arm=arm,texture_overlap=overlap(m['texture_hist']).tolist(),rgb_overlap=overlap(m['rgb_hist']).tolist(),threshold=m['threshold'].tolist()))
   for v in views(s):
    a=result(s,v,arm);b=old(s,v,3);mask=b['inference_mask'];np.testing.assert_array_equal(a['inference_mask'],mask);np.testing.assert_array_equal(a['unknown'],(mask&(a['labels']==0))|(b['unknown']&~mask));assert not a['labels'][~mask].any()
    if arm=='raw_rgb':
     for k in a:np.testing.assert_array_equal(a[k],b[k])
     out['raw_exact_predictions']+=1
    if replay:
     q=infer_arrays(s,v,arm)
     for k,x in q.items():np.testing.assert_array_equal(a[k],x)
     out['prediction_replays']+=1
    null=result(s,v,'rgb_scrambled_texture');cnt=json.loads((R/'inference'/s/arm/v/'COUNT.json').read_text());assert cnt['unknown']==int((mask&(a['labels']==0)).sum());cnt.update(relative_to_raw=compare(b['labels'],a['labels'],mask),relative_to_shuffled=compare(null['labels'],a['labels'],mask));actual_counts.append(cnt)
 count=json.loads((R/'COUNTS.json').read_text());key=lambda x:(x['scene'],x['view'],x['arm']);assert sorted(actual_counts,key=key)==sorted(count['predictions'],key=key);assert actual_models==count['models']
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
