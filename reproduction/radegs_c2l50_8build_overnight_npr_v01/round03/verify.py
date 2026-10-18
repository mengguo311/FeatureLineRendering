from env import *
def run(replay=False):
 f=json.loads((R/'METHOD_FREEZE.json').read_text());assert sha(R/'CONFIG.json')==f['config_sha256'];assert sha(R/'METHOD_FREEZE_ZH.md')==f['method_sha256']
 source=json.loads((R/'SOURCE_MANIFEST.json').read_text())['files']
 for name,h in source.items():assert sha(name)==h,name
 units=list(R.rglob('SEAL.json'))
 for u in units:checkseal(u.parent)
 result=dict(readonly=True,source_files=len(source),sealed_units=len(units),old=rollback(),resources=guard(),model_replays=0,crossfit_replays=0,inference_replays=0,match_replays=0)
 from experiment import ARMS,SCENES,saved,load,model,seed_data
 from partition import select_views,infer_image
 from density import fit_density,predict
 for s in SCENES:
  for arm in ARMS:
   m=model(s,arm);assert m['hist'].shape==(3 if s=='ficus' else 2,16,16,16);assert np.isfinite(m['hist']).all();np.testing.assert_allclose(m['hist'].sum((1,2,3)),1,atol=1e-12)
   if replay:
    data=[]
    for v in select_views([DEV[s],AUX[s]],arm):
     x,y,uv,sl=seed_data(s,v,arm=='shuffled_labels');data.append((x,y));a=npz(R/'models'/s/arm/(v+'_SEEDS.npz'));np.testing.assert_array_equal(a['uv'],uv);np.testing.assert_array_equal(a['labels'],y);np.testing.assert_array_equal(a['seed_image'],sl)
    b=fit_density(data,3 if s=='ficus' else 2)
    for k in m:np.testing.assert_array_equal(m[k],b[k],err_msg=s+'/'+arm+'/'+k)
    result['model_replays']+=1
   for v in views(s):
    a=saved(s,v,arm);data=load(s,v);mask=data['mask'];assert np.array_equal(a['inference_mask'],mask);assert (a['labels'][~mask]==0).all();assert np.array_equal(a['unknown'],(mask&(a['labels']==0))|data['subject_unknown']);assert a['probability'].min()>=0 and a['probability'].max()<=1 and np.isfinite(a['probability']).all();assert (a['probability'][~mask]==0).all()
    if replay:
     lab,u,q,d=infer_image(m,data['rgb'],mask)
     for k,val in dict(labels=lab,unknown=u|data['subject_unknown'],probability=q,density=d).items():np.testing.assert_array_equal(a[k],val,err_msg=s+'/'+arm+'/'+v+'/'+k)
     result['inference_replays']+=1
  if replay:
   for bv,tv in [(DEV[s],AUX[s]),(AUX[s],DEV[s])]:
    x,y,_,_=seed_data(s,bv);tx,ty,uv,_=seed_data(s,tv);m=fit_density([(x,y)],3 if s=='ficus' else 2);lab,q,d=predict(m,tx);a=npz(R/'crossfit'/s/(bv+'_TO_'+tv)/'RESULT.npz')
    for k,val in dict(source_seed_labels=y,target_seed_labels=ty,target_uv=uv,predicted=lab,probability=q,density=d).items():np.testing.assert_array_equal(a[k],val)
    result['crossfit_replays']+=1
 if replay:
  from evaluation import match
  for arm in [*ARMS,'r01_profile','r02_graph','v02_rgb']:
   for tv in [AUX['ficus'],*RES['ficus']]:
    p=R/'evaluation'/(arm+'_'+tv);ab,aa,ad=match(DEV['ficus'],tv,arm);ba,bb,bd=match(tv,DEV['ficus'],arm);row=json.loads((p/'COUNTS.json').read_text());assert aa==row['forward'] and bb==row['reverse'];assert [list((i,j)) for i,(j,f) in ab.items() if f>=.75 and j in ba and ba[j][0]==i and ba[j][1]>=.75]==row['mutual']
    for name,ar in [('FORWARD',ad),('REVERSE',bd)]:
     a=npz(p/(name+'.npz'))
     for k,val in ar.items():np.testing.assert_array_equal(a[k],val)
    result['match_replays']+=1
 if (R/'RESULTS_MANIFEST.json').exists():
  for name,d in json.loads((R/'RESULTS_MANIFEST.json').read_text())['members'].items():assert not Path(name).is_absolute() and '..' not in Path(name).parts and not (R/name).is_symlink() and sha(R/name)==d['sha256'],name
  result['manifest_verified']=True
 if (R/'PACKAGES.json').exists():
  import tarfile
  for row in json.loads((R/'PACKAGES.json').read_text()):
   p=R/row['path'];assert sha(p)==row['sha256'];name=p.name.removesuffix('.tar.gz');members=json.loads((R/(name+'.MEMBERS.json')).read_text())['members']
   with tarfile.open(p,'r:gz') as tf:
    assert set(tf.getnames())==set(members)
    for m in tf:
     assert m.isfile() and not m.islnk() and not m.issym() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts;assert hashlib.sha256(tf.extractfile(m).read()).hexdigest()==members[m.name]['sha256']
  result['packages_verified']=True
 return result
if __name__=='__main__':
 import argparse;p=argparse.ArgumentParser();p.add_argument('--readonly',required=True,action='store_true');p.add_argument('--replay',action='store_true');a=p.parse_args();print(json.dumps(run(a.replay),ensure_ascii=False,indent=2))
