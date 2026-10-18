from env import *
def run(replay=False):
 pre=json.loads((R/'CODE_PREEXEC.json').read_text())
 for name,h in pre['files'].items():assert sha(CODE/name)==h,name
 f=json.loads((R/'METHOD_FREEZE.json').read_text());assert sha(R/'CONFIG.json')==f['config_sha256'] and sha(R/'METHOD_FREEZE_ZH.md')==f['method_sha256']
 sources=json.loads((R/'SOURCE_MANIFEST.json').read_text())['files']
 for p,h in sources.items():assert sha(p)==h,p
 units=list(R.rglob('SEAL.json'))
 for p in units:checkseal(p.parent)
 from experiment import ARMS,build_data,infer_arrays,target_arrays,result,old_result
 from graph import load
 from output import pack
 out=dict(readonly=True,source_files=len(sources),sealed_units=len(units),old=rollback(),resources=guard(),graph_replays=0,target_replays=0,native_arrays_checked=0,match_replays=0,crossfit_replays=0,audit_replays=0,baseline_graph_equal=True)
 # Reconstruct original other-view models and predictions, never training on target seeds.
 if replay:
  sys.path.append(str(CODE.parent/'round03'));from density import fit_density,predict
  for s in SCENES:
   for v in [DEV[s],AUX[s]]:
    other=AUX[s] if v==DEV[s] else DEV[s];tr=npz(R3/'models'/s/'pooled_rgb'/(other+'_SEEDS.npz'));ev=npz(R3/'crossfit'/s/(other+'_TO_'+v)/'RESULT.npz');rgb,_,_=raw(s,other);x=rgb[tr['uv'][:,1],tr['uv'][:,0]];m=fit_density([(x,tr['labels'])],3 if s=='ficus' else 2);target_rgb,_,_=raw(s,v);lab,q,density=predict(m,target_rgb[ev['target_uv'][:,1],ev['target_uv'][:,0]])
    for name,val in [('predicted',lab),('probability',q),('density',density)]:np.testing.assert_array_equal(ev[name],val)
    out['crossfit_replays']+=1
 for s in SCENES:
  base=npz(R4/'B'/s/'coupled/fit/GRAPH.npz');original_data=[load(s,v,True) for v in [DEV[s],AUX[s]]];policies=[]
  for arm in ARMS:
   data=[build_data(s,v,arm) for v in [DEV[s],AUX[s]]];p=R/'B'/s/arm/'fit';saved=npz(p/'GRAPH.npz')
   for name in ['i','j','weight','gamma','prior','view_offsets']:np.testing.assert_array_equal(saved[name],base[name],err_msg=s+'/'+arm+'/'+name)
   policies.append(saved['seeds']);orig=np.concatenate([d['seeds'] for d in original_data]);assert np.all((saved['seeds']==0)|(saved['seeds']==orig));assert np.all(saved['seeds'][orig==0]==0)
   if replay:
    a,meta=infer_arrays(data,arm)
    for name,val in a.items():np.testing.assert_array_equal(saved[name],val,err_msg=s+'/'+arm+'/'+name)
    out['graph_replays']+=1
   for ix,v in enumerate([DEV[s],AUX[s]]):
    a=result(s,v,arm);lo,hi=saved['view_offsets'][ix:ix+2];re=pack(saved['probability'][lo:hi],data[ix])
    for k,val in re.items():np.testing.assert_array_equal(a[k],val)
   for v in views(s):
    a=result(s,v,arm);d=load(s,v,False);mask=d['mask'];np.testing.assert_array_equal(a['inference_mask'],mask);np.testing.assert_array_equal(a['unknown'],(mask&(a['labels']==0))|d['subject_unknown']);assert (a['labels'][~mask]==0).all();assert np.isfinite(a['probability']).all() and a['probability'].min()>=0 and a['probability'].max()<=1
    if v in RES[s]:
     assert not a['seeds'].any()
     if replay:
      q,dd,meta,extra=target_arrays(s,v,arm);re=pack(q,dd);re.update(extra)
      for k,val in re.items():np.testing.assert_array_equal(a[k],val,err_msg=s+'/'+v+'/'+arm+'/'+k)
      out['target_replays']+=1
    out['native_arrays_checked']+=1
  for ix in range(2):
   lo,hi=base['view_offsets'][ix:ix+2]
   for k in range(1,base['probability'].shape[1]+1):assert np.count_nonzero(policies[0][lo:hi]==k)==np.count_nonzero(policies[1][lo:hi]==k)
 if replay:
  from evaluation import match
  for arm in [*ARMS,'r04']:
   for tv in [AUX['ficus'],*RES['ficus']]:
    p=R/'evaluation'/(arm+'_'+tv);ab,aa,ad=match(DEV['ficus'],tv,arm);ba,bb,bd=match(tv,DEV['ficus'],arm);row=json.loads((p/'COUNTS.json').read_text());assert aa==row['forward'] and bb==row['reverse'];assert [[i,j] for i,(j,f) in ab.items() if f>=.75 and j in ba and ba[j][0]==i and ba[j][1]>=.75]==row['mutual']
    for nm,ar in [('FORWARD',ad),('REVERSE',bd)]:
     a=npz(p/(nm+'.npz'))
     for k,val in ar.items():np.testing.assert_array_equal(a[k],val)
    out['match_replays']+=1
  from audit import calculate
  rr=[]
  for s in SCENES:
   for arm in ARMS:
    rows,aa=calculate(s,arm);rr.extend(rows)
    for v,ar in aa.items():
     a=npz(R/'mechanism_audit'/(s+'_'+arm+'_'+v+'.npz'))
     for k,val in ar.items():np.testing.assert_array_equal(a[k],val)
    out['audit_replays']+=1
  assert rr==json.loads((R/'mechanism_audit/COUNTS.json').read_text())
 if (R/'RESULTS_MANIFEST.json').exists():
  for n,d in json.loads((R/'RESULTS_MANIFEST.json').read_text())['members'].items():assert not Path(n).is_absolute() and '..' not in Path(n).parts and not (R/n).is_symlink() and sha(R/n)==d['sha256'],n
  out['manifest_verified']=True
 if (R/'PACKAGES.json').exists():
  import tarfile
  for row in json.loads((R/'PACKAGES.json').read_text()):
   p=R/row['path'];assert sha(p)==row['sha256'];members=json.loads((R/(p.name.removesuffix('.tar.gz')+'.MEMBERS.json')).read_text())['members']
   with tarfile.open(p,'r:gz') as tf:
    assert set(tf.getnames())==set(members)
    for m in tf:assert m.isfile() and not m.issym() and not m.islnk() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts and hashlib.sha256(tf.extractfile(m).read()).hexdigest()==members[m.name]['sha256']
  out['packages_verified']=True
 return out
if __name__=='__main__':
 import argparse;p=argparse.ArgumentParser();p.add_argument('--readonly',required=True,action='store_true');p.add_argument('--replay',action='store_true');a=p.parse_args();print(json.dumps(run(a.replay),ensure_ascii=False,indent=2))
