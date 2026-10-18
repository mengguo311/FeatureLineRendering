from env import *
def run(replay=False):
 for freeze in ['CODE_PREEXEC.json','EVALUATION_CODE_FREEZE.json']:
  for name,h in json.loads((R/freeze).read_text())['files'].items():assert sha(CODE/name)==h,name
 f=json.loads((R/'METHOD_FREEZE.json').read_text());assert sha(R/'CONFIG.json')==f['config_sha256'] and sha(R/'METHOD_FREEZE_ZH.md')==f['method_sha256']
 sources=json.loads((R/'SOURCE_MANIFEST.json').read_text())['files']
 for p,h in sources.items():assert sha(p)==h,p
 units=list(R.rglob('SEAL.json'))
 for p in units:checkseal(p.parent)
 out=dict(readonly=True,source_files=len(sources),sealed_units=len(units),old=rollback(),resources=guard(),render_replays=0,model_replays=0,prediction_replays=0,match_replays=0,native_arrays_checked=0,new_GS_models=0)
 from experiment import source,digest,render_arrays,rendered,seed_data,infer_arrays,result,old,ARMS
 from appearance import color_mode
 from protocol import calibrate
 from density import fit_density
 for s in SCENES:
  a,info=source(s);assert info==json.loads((R/'sources'/s/'SOURCE.json').read_text());before=digest(a);cp=npz(R/'sources'/s/'COLOR_PROVENANCE.npz');np.testing.assert_array_equal(cp['source_index'],np.arange(info['count']));np.testing.assert_array_equal(cp['dc_color'],color_mode(a,cam(s,DEV[s]),'dc_only'));np.testing.assert_array_equal(cp['anchor_color'],color_mode(a,cam(s,DEV[s]),'anchor_sh',cam(s,DEV[s])))
  for v in views(s):
   full=rendered(s,v,'full_sh');rgb,z,al=raw(s,v);cal=calibrate(full,npz(V1/'stageA'/s/v/'REFERENCE.npz'),rgb,z,al);assert cal==json.loads((R/'renders'/s/v/'COUNT.json').read_text())['calibration']
   for arm in ARMS:
    rd=rendered(s,v,arm)
    for k in ['alpha','median_center_z','expected_center_z']:np.testing.assert_array_equal(rd[k],full[k])
    if replay:
     actual=render_arrays(a,s,v,arm)
     for k in actual:np.testing.assert_array_equal(rd[k],actual[k],err_msg=s+'/'+v+'/'+arm+'/'+k)
     out['render_replays']+=1
   if v==DEV[s]:np.testing.assert_array_equal(full['rgb'],rendered(s,v,'anchor_sh')['rgb'])
  assert digest(a)==before
  del a
  for arm in ARMS:
   data,seeds=seed_data(s,arm);m=npz(R/'models'/s/arm/'MODEL.npz')
   for v,ar in seeds.items():
    b=npz(R/'models'/s/arm/(v+'_SEEDS.npz'))
    for k,x in ar.items():np.testing.assert_array_equal(b[k],x)
   if replay:
    b=fit_density(data,3 if s=='ficus' else 2)
    for k,x in b.items():np.testing.assert_array_equal(m[k],x)
    out['model_replays']+=1
   for v in views(s):
    a=result(s,v,arm);b=old(s,v,3);np.testing.assert_array_equal(a['inference_mask'],b['inference_mask']);np.testing.assert_array_equal(a['unknown'],(b['inference_mask']&(a['labels']==0))|(b['unknown']&~b['inference_mask']));assert not a['labels'][~a['inference_mask']].any();assert np.isfinite(a['probability']).all()
    if replay:
     b=infer_arrays(s,v,arm)
     for k,x in b.items():np.testing.assert_array_equal(a[k],x)
     out['prediction_replays']+=1
    out['native_arrays_checked']+=1
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
