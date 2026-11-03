"""Read-only extraction of ONE bounded real M4 component; no fit or rendering."""
from runtime_io import *
from port_paths import DSU
import argparse
def prepare(unit):
 out=Path(unit)/'tests';out.mkdir(exist_ok=True);base=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_edge_growth_v05_20261031/units')
 c=json.loads((base/'unit_019/CONFIG.json').read_text());cp=Path(c['previous_carriers']);a=dict(np.load(cp,allow_pickle=False));z=dict(np.load(base/'unit_019/scenes/ficus/states/M5/controls/joint/CANDIDATE_STATUS.npz',allow_pickle=False))
 rr=np.flatnonzero((z['operation']=='overlap')&np.isin(z['reason'],['accepted','round_conflict','ambiguous']));uf=DSU()
 for i in rr:uf.union(int(z['a'][i]),int(z['b'][i]))
 groups={}
 for cid in uf.p:groups.setdefault(uf.find(cid),[]).append(cid)
 index={int(cid):i for i,cid in enumerate(a['carrier_id'])}
 part=lambda cid,key,off:a[key][a[off][index[cid]]:a[off][index[cid]+1]]
 chosen=None
 for ids in sorted((sorted(v) for v in groups.values()),key=lambda x:x[0]):
  records=[int(i) for i in rr if int(z['a'][i]) in ids];seeds=sum(len(part(i,'seedlets','seed_offsets')) for i in ids);count=sum(len(part(i,'rows','row_offsets')) for i in ids)
  if 2<=len(ids)<=5 and seeds<=128 and count<=512 and len(records)<=8:chosen=(ids,records);break
 assert chosen is not None;ids,records=chosen
 rows=np.concatenate([part(i,'rows','row_offsets') for i in ids]);reps=np.concatenate([part(i,'seedlets','seed_offsets') for i in ids]);rowmap={int(x):i for i,x in enumerate(rows)};repmap={int(x):i for i,x in enumerate(reps)}
 f=dict(original_rows=rows,original_seedlets=reps,carrier_id=np.array(ids),p=np.array(c['p']),record_ids=np.array(records),metric_names=z['metric_names'])
 for field in ['version','valid','baseline','kind']:f[field]=a[field][[index[i] for i in ids]]
 for field,offset,outfield in [('rows','row_offsets','rows'),('seedlets','seed_offsets','seedlets'),('knots','knot_offsets','knots'),('supported_intervals','interval_offsets','supported_intervals')]:
  values=[part(i,field,offset) for i in ids]
  if field=='rows':values=[np.array([rowmap[int(x)] for x in v]) for v in values]
  if field=='seedlets':values=[np.array([repmap[int(x)] for x in v]) for v in values]
  f[outfield]=np.concatenate(values);f[offset]=np.r_[0,np.cumsum([len(v) for v in values])]
 with np.load(c['gaussians'],allow_pickle=False) as asset:
  for k in asset.files:f['asset_'+k]=asset[k][rows]
 with np.load(c['representatives'],allow_pickle=False) as rep:
  for k in ['x','t','endpoints']:f['representatives_'+k]=rep[k][reps]
  f['representatives_mid']=np.array([rowmap[int(x)] for x in rep['mid'][reps]])
 with np.load(c['controls'],allow_pickle=False) as control:
  der=(control['control'][control['control_index'][rows]]*control['derivative_basis'][rows,:,None]).sum(axis=1);f['tangents']=der/np.maximum(np.linalg.norm(der,axis=1)[:,None],1e-15)
 with np.load(c['previous_membership'],allow_pickle=False) as m:
  for k in m.files:f['membership_'+k]=m[k][rows]
 f['membership_line_kernel_id']=np.arange(len(rows))
 for k in ['a','b','operation','reason','cost','metrics']:f['candidate_'+k]=z[k][records]
 nz(out/'FICUS_REAL_COMPONENT.npz',**f)
 js(out/'FICUS_REAL_COMPONENT.json',dict(scene='ficus',selection='minimum carrier-ID complete successful-overlap component with2..5 leaves,<=128seedlets,<=512kernels,<=8pairs; no fit-based selection',carriers=ids,records=records,kernels=len(rows),seedlets=len(reps),input_carriers=str(cp),input_carriers_sha256=sha(cp),original_rows=rows.tolist(),original_seedlets=reps.tolist(),fixture_sha256=sha(out/'FICUS_REAL_COMPONENT.npz'),full_asset_numerical_run=False,fit_calls=0))
 print(json.dumps(dict(carriers=ids,pairs=len(records),kernels=len(rows),seedlets=len(reps),fit_calls=0)))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--unit',required=True);a=p.parse_args();prepare(a.unit)
