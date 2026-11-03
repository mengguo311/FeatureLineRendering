"""Exact strong-M5 transfer; restricted original loader, no fitting or promotion."""
from runtime_io import *
from paired_loader import load as raw_load
from geometry_base import clean

def selection(groups,lineage,versions,per_model):
 endpoints={tuple(e['output']) for e in lineage['events'] if e.get('operation')=='endpoint'}
 ledger=[];eligible={'line':[],'polyline':[]}
 for g in groups['groups']:
  gid=int(g['edge_id']);version=int(g['version']);reasons=[]
  if versions.get(gid)!=version:reasons.append('not_current_version')
  if (gid,version) not in endpoints:reasons.append('not_surviving_endpoint_output')
  if not g['valid']:reasons.append('saved_invalid_seed')
  substantial=sum(x['kernels']>=12 and x['mapped_supported_length_p']>=2 for x in g['M4_contributions'])
  if substantial<2:reasons.append('fewer_than_two_substantial_M4')
  if g['model'] not in eligible:reasons.append('model_not_line_or_polyline')
  z=dict(id=gid,version=version,model=g['model'],supported_length_p=g['supported_length_p'],substantial_M4=substantial,reasons=reasons,selected=False)
  ledger.append(z)
  if not reasons:eligible[g['model']].append(z)
 chosen=[]
 for model,records in eligible.items():
  records.sort(key=lambda z:(-z['supported_length_p'],z['id']))
  for rank,z in enumerate(records):
   z['model_rank']=rank+1;z['selected']=rank<per_model
   if z['selected']:chosen.append(z['id'])
   else:z['reasons'].append('outside_frozen_top3_per_model')
 return dict(selected=sorted(chosen),records=ledger,selection_precedes_growth=True,no_readiness_replacement=True)

def cameras(c):
 cs=json.loads(Path(c['cameras']).read_text())[c['scene']];selected=[]
 for view in c['views']:
  matches=[z for z in cs if z['view']==view];assert len(matches)==1,'CAMERA_VIEW_BINDING'
  z=matches[0];assert [z['width'],z['height']]==c['camera_shape'],'CAMERA_SIZE'
  E=np.asarray(z['extrinsic']);assert E.shape==(4,4) and np.isfinite(E).all()
  np.testing.assert_allclose(E[3],[0,0,0,1],rtol=0,atol=1e-8)
  np.testing.assert_allclose(E[:3,:3]@E[:3,:3].T,np.eye(3),rtol=0,atol=1e-5)
  assert all(np.isfinite(z[k]) for k in ['fx','fy','cx','cy']) and min(z['fx'],z['fy'])>0
  selected.append(z)
 return dict(views=c['views'],shape=c['camera_shape'],convention='COLMAP_W2C_NO_GL',no_axis_conversion=True,cameras=selected)

def load(c,guard):
 d=raw_load(c,guard);guard('readiness');m=d['membership']
 assert int(np.sum(m['edge_id']>=0))==c['initial_assigned']
 assert d['next_version']==c['initial_next_version']
 groups=json.loads(Path(c['groups']).read_text());lineage=json.loads(Path(c['lineage']).read_text())
 versions={k:v.version for k,v in d['leaves'].items()}
 ledger=selection(groups,lineage,versions,c['seed_selection_per_model'])
 # The cohort is frozen; mismatches stay explicit and never select replacements.
 statuses={};objects={};unavailable=[]
 for sid in c['seed_ids']:
  leaf=d['leaves'].get(sid)
  statuses[sid]='READY' if leaf is not None and leaf.version==c['seed_versions'][str(sid)] and sid in ledger['selected'] else 'NOT_RUN_SEED_BINDING'
 for j,(cid,leaf) in enumerate(sorted(d['leaves'].items())):
  if j%512==0:guard('readiness')
  labels=np.unique(m['edge_id'][leaf.rows]);assert len(labels)==1
  gid=int(labels[0]) if labels[0]>=0 else -int(cid)-1
  assert gid not in objects,'M5_GROUP_NOT_WHOLE_CARRIER'
  q=clean(leaf.q.copy());available=len(q)>=2 and np.isfinite(q).all()
  if cid in statuses and not available:statuses[cid]='NOT_RUN_SEED_GEOMETRY'
  objects[gid]=dict(id=gid,origin_objects=[gid],q=q,version=leaf.version,rows=np.sort(leaf.rows),leaves=[cid],available=bool(available),seed_origins=[gid] if gid in statuses and statuses[gid]=='READY' else [],original_valid_flag=bool(leaf.valid))
  if not available:unavailable.append(dict(id=gid,reason='nonfinite_or_degenerate_saved_q'))
 np.testing.assert_array_equal(np.sort(np.concatenate([o['rows'] for o in objects.values()])),np.arange(c['kernel_count']))
 camera_receipt=cameras(c)
 ledger.update(frozen_ids=c['seed_ids'],readiness=statuses)
 d.update(initial_membership={k:v.copy() for k,v in m.items()},objects=objects,historical_events=lineage['events'],starting_state=dict(next_version=d['next_version']),unavailable=unavailable,initial_checkpoint=json.loads(Path(c['predecessor_checkpoint']).read_text()),seed_ledger=ledger,seed_status=statuses,camera_receipt=camera_receipt)
 return d
