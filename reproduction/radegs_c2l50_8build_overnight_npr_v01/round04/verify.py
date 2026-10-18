from env import *

def run(replay=False):
 f=json.loads((R/'METHOD_FREEZE.json').read_text());assert sha(R/'CONFIG.json')==f['config_sha256'];assert sha(R/'METHOD_FREEZE_ZH.md')==f['method_sha256']
 source=json.loads((R/'SOURCE_MANIFEST.json').read_text())['files']
 for name,h in source.items():assert sha(name)==h,name
 units=list(R.rglob('SEAL.json'))
 for u in units:checkseal(u.parent)
 result_report=dict(readonly=True,source_files=len(source),sealed_units=len(units),old=rollback(),resources=guard(),graph_replays=0,target_replays=0,native_arrays_checked=0,match_replays=0)
 from experiment import ARMS,infer_arrays,target_arrays,result
 from graph import load
 from output import pack
 for s in SCENES:
  data=[load(s,v,True) for v in [DEV[s],AUX[s]]]
  for arm in ARMS:
   p=R/'B'/s/arm/'fit';saved=npz(p/'GRAPH.npz');K=3 if s=='ficus' else 2;assert saved['probability'].shape[1]==K
   if replay:
    a,meta=infer_arrays(data,arm)
    for k,val in a.items():np.testing.assert_array_equal(saved[k],val,err_msg=s+'/'+arm+'/'+k)
    result_report['graph_replays']+=1
   for ix,v in enumerate([DEV[s],AUX[s]]):
    a=result(s,v,arm);lo,hi=saved['view_offsets'][ix:ix+2];re=pack(saved['probability'][lo:hi],data[ix])
    for k,val in re.items():np.testing.assert_array_equal(a[k],val,err_msg=s+'/'+v+'/'+arm+'/'+k)
   for v in views(s):
    a=result(s,v,arm);d=load(s,v,False);m=d['mask'];assert np.array_equal(a['inference_mask'],m);assert np.array_equal(a['unknown'],(m&(a['labels']==0))|d['subject_unknown']);assert (a['labels'][~m]==0).all();assert np.isfinite(a['probability']).all() and a['probability'].min()>=0 and a['probability'].max()<=1;assert (a['probability'][~m]==0).all()
    if v in RES[s]:
     assert not a['seeds'].any()
     if replay:
      q,td,meta,extra=target_arrays(s,v,arm);re=pack(q,td);re.update(extra)
      for k,val in re.items():np.testing.assert_array_equal(a[k],val,err_msg=s+'/'+v+'/'+arm+'/'+k)
      result_report['target_replays']+=1
    result_report['native_arrays_checked']+=1
 if replay:
  from evaluation import match
  for arm in [*ARMS,'r01_profile','r02_graph','r03_appearance','v02_rgb']:
   for tv in [AUX['ficus'],*RES['ficus']]:
    p=R/'evaluation'/(arm+'_'+tv);ab,aa,ad=match(DEV['ficus'],tv,arm);ba,bb,bd=match(tv,DEV['ficus'],arm);row=json.loads((p/'COUNTS.json').read_text());assert aa==row['forward'] and bb==row['reverse'];assert [[i,j] for i,(j,f) in ab.items() if f>=.75 and j in ba and ba[j][0]==i and ba[j][1]>=.75]==row['mutual']
    for name,ar in [('FORWARD',ad),('REVERSE',bd)]:
     a=npz(p/(name+'.npz'))
     for k,val in ar.items():np.testing.assert_array_equal(a[k],val)
    result_report['match_replays']+=1
 if (R/'RESULTS_MANIFEST.json').exists():
  for name,d in json.loads((R/'RESULTS_MANIFEST.json').read_text())['members'].items():assert not Path(name).is_absolute() and '..' not in Path(name).parts and not (R/name).is_symlink() and sha(R/name)==d['sha256'],name
  result_report['manifest_verified']=True
 if (R/'PACKAGES.json').exists():
  import tarfile
  for row in json.loads((R/'PACKAGES.json').read_text()):
   p=R/row['path'];assert sha(p)==row['sha256'];name=p.name.removesuffix('.tar.gz');members=json.loads((R/(name+'.MEMBERS.json')).read_text())['members']
   with tarfile.open(p,'r:gz') as tf:
    assert set(tf.getnames())==set(members)
    for m in tf:
     assert m.isfile() and not m.islnk() and not m.issym() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts;assert hashlib.sha256(tf.extractfile(m).read()).hexdigest()==members[m.name]['sha256']
  result_report['packages_verified']=True
 return result_report

if __name__=='__main__':
 import argparse;p=argparse.ArgumentParser();p.add_argument('--readonly',required=True,action='store_true');p.add_argument('--replay',action='store_true');a=p.parse_args();print(json.dumps(run(a.replay),ensure_ascii=False,indent=2))
