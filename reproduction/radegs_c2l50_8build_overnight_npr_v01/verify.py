from env import *
def run(replay=False):
 f=json.loads((R/'METHOD_FREEZE.json').read_text());assert sha(R/'CONFIG.json')==f['config_sha256'];assert sha(R/'METHOD_FREEZE_ZH.md')==f['method_sha256'];files=json.loads((R/'SOURCE_MANIFEST.json').read_text())['files']
 for p,h in files.items():assert sha(p)==h,p
 units=list((R/'A').rglob('SEAL.json'))+list((R/'B').rglob('SEAL.json'))
 for p in units:checkseal(p.parent)
 result=dict(readonly=True,sources=len(files),sealed_units=len(units),A_replays=0,B_replays=0,match_replays=0,old=rollback(),resources=guard())
 if replay:
  import run_a,run_b,matching
  for s in SCENES:
   m=run_a.infer_scene(s);assert m==json.loads((R/'A'/s/'model/MODEL.json').read_text())
   for v in views(s):
    a=run_a.predict(s,v,m);saved=npz(R/'A'/s/v/'SUBJECT.npz')
    for k in a:np.testing.assert_array_equal(a[k],saved[k])
    result['A_replays']+=1
  data=run_b.collect();saved=npz(R/'B/ficus/model/OBSERVATIONS.npz')
  for k in data:np.testing.assert_array_equal(data[k],saved[k])
  from section import fit_sections
  up=json.loads((R/'A/ficus/model/MODEL.json').read_text())['axis']['up'];m,ar=fit_sections(data['world'],data['view_id'],up);assert m==json.loads((R/'B/ficus/model/MODEL.json').read_text());sr=npz(R/'B/ficus/model/PROFILE.npz')
  for k in ar:np.testing.assert_array_equal(ar[k],sr[k])
  for v in views('ficus'):
   arms=run_b.predict(v,m)
   for arm,a in arms.items():
    saved=npz(R/'B/ficus'/v/(arm+'.npz'))
    for k in a:np.testing.assert_array_equal(a[k],saved[k])
    result['B_replays']+=1
  for arm in ['profile','equal_thirds']:
   for tv in [AUX['ficus'],*RES['ficus']]:
    p=R/'B/ficus/matches'/(arm+'_'+tv);saved=json.loads((p/'COUNTS.json').read_text());ab,ra,aa=matching.match(DEV['ficus'],tv,arm);ba,rb,bb=matching.match(tv,DEV['ficus'],arm);assert ra==saved['forward'] and rb==saved['reverse'];assert [list(x) for x in matching.mutual(ab,ba)]==saved['mutual']
    for name,a in [('FORWARD',aa),('REVERSE',bb)]:
     sav=npz(p/(name+'.npz'))
     for k in a:np.testing.assert_array_equal(a[k],sav[k])
    result['match_replays']+=1
 if (R/'RESULTS_MANIFEST.json').exists():
  for name,d in json.loads((R/'RESULTS_MANIFEST.json').read_text())['members'].items():assert not Path(name).is_absolute() and '..' not in Path(name).parts and not (R/name).is_symlink() and sha(R/name)==d['sha256'],name
  result['manifest_verified']=True
 return result
if __name__=='__main__':
 import argparse;p=argparse.ArgumentParser();p.add_argument('--readonly',required=True,action='store_true');p.add_argument('--replay',action='store_true');a=p.parse_args();print(json.dumps(run(a.replay),ensure_ascii=False,indent=2))
