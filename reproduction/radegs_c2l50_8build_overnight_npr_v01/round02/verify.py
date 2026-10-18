from env import *
def run(replay=False):
 f=json.loads((R/'METHOD_FREEZE.json').read_text());assert sha(R/'CONFIG.json')==f['config_sha256'];assert sha(R/'METHOD_FREEZE_ZH.md')==f['method_sha256'];source=json.loads((R/'SOURCE_MANIFEST.json').read_text())['files']
 for name,h in source.items():assert sha(name)==h,name
 units=list((R/'B').rglob('SEAL.json'))+list((R/'A_DIAGNOSTIC').rglob('SEAL.json'))+list((R/'figures').rglob('SEAL.json'))+list((R/'evaluation').rglob('SEAL.json'))
 for u in units:checkseal(u.parent)
 result=dict(readonly=True,source_files=len(source),sealed_units=len(units),old=rollback(),resources=guard(),fit_graph_replays=0,target_replays=0,dtu_replays=0,match_replays=0)
 from experiment import ARMS,view_result
 for arm in ARMS:
  for v in views('ficus'):
   data=view_result(v,arm);sub=npz(R1/'A/ficus'/v/'SUBJECT.npz');mask=sub['candidate'];assert np.all(data['labels'][~mask]==0);assert np.array_equal(data['unknown'],(mask&(data['labels']==0))|sub['unknown']);assert data['probability'].shape==(*mask.shape,3);assert np.isfinite(data['probability']).all();assert data['probability'].min()>=0 and data['probability'].max()<=1;assert set(np.unique(data['labels'])).issubset({0,1,2,3})
   if v in RES['ficus']:assert not data['seeds'].any()
 if replay:
  from experiment import load_view,build_graph,solve,links,labels,edge_weight,combine_priors
  for arm in ARMS:
   data=[load_view(v,True) for v in [DEV['ficus'],AUX['ficus']]];i,j,w,meta=build_graph(data,arm);seeds=np.concatenate([x['seeds'] for x in data]);q,_=solve(len(seeds),i,j,w,seeds);saved=npz(R/'B'/arm/'fit/GRAPH.npz')
   for k,val in dict(i=i,j=j,weight=w,seeds=seeds,probability=q).items():np.testing.assert_array_equal(val,saved[k],err_msg=arm+':'+k)
   result['fit_graph_replays']+=1
   for v in RES['ficus']:
    t=load_view(v,False);n=len(t['world']);color=arm!='joint_no_rgb';ids=[];qs=[];ws=[]
    for bv in [DEV['ficus'],AUX['ficus']]:
     b=load_view(bv,False);q=view_result(bv,arm)['probability'][b['mask']];ii,jj,state=links(t,b);known=labels(q[jj])>0;ii=ii[known];jj=jj[known];ww=.5*edge_weight(t['color'][ii],b['color'][jj],np.ones(len(ii)),color);ids.append(ii);qs.append(q[jj]);ws.append(ww)
    ii=np.concatenate(ids);qq=np.concatenate(qs);ww=np.concatenate(ws);deg=np.bincount(ii,minlength=n);ww/=np.maximum(deg[ii],1);gamma,prior=combine_priors(n,ii,qq,ww);i,j,d=t['i'],t['j'],t['d'];w=edge_weight(t['color'][i],t['color'][j],d,color);q,_=solve(n,i,j,w,t['seeds'],gamma,prior);saved=view_result(v,arm);np.testing.assert_array_equal(q,saved['probability'][t['mask']]);np.testing.assert_array_equal(gamma,saved['prior_gamma']);np.testing.assert_array_equal(prior,saved['prior_probability']);np.testing.assert_array_equal(labels(q),saved['labels'][t['mask']]);result['target_replays']+=1
  from dtu_diagnostic import compute
  for s in ['scan24','scan65']:
   for v in views(s):
    data,row=compute(s,v);saved=npz(R/'A_DIAGNOSTIC'/s/v/'LOCAL_DEPTH.npz')
    for k,val in data.items():np.testing.assert_array_equal(val,saved[k])
    assert row==json.loads((R/'A_DIAGNOSTIC'/s/v/'COUNT.json').read_text());result['dtu_replays']+=1
  from evaluate import match
  for arm in [*ARMS,'r01_profile','v02_rgb']:
   for tv in [AUX['ficus'],*RES['ficus']]:
    p=R/'evaluation'/(arm+'_'+tv);ab,aa,da=match(DEV['ficus'],tv,arm);ba,bb,db=match(tv,DEV['ficus'],arm);row=json.loads((p/'COUNTS.json').read_text());assert aa==row['forward'] and bb==row['reverse'];assert [list((i,j)) for i,(j,f) in ab.items() if f>=.75 and j in ba and ba[j][0]==i and ba[j][1]>=.75]==row['mutual']
    for name,ar in [('FORWARD',da),('REVERSE',db)]:
     saved=npz(p/(name+'.npz'))
     for k,val in ar.items():np.testing.assert_array_equal(val,saved[k])
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
