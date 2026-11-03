"""Real restricted input adapter; complete current identities, no old validity gate."""
from runtime_io import *
from paired_loader import load as raw_load
from geometry_base import clean

def load(c,guard):
 d=raw_load(c,guard);guard('readiness');root=Path(c['initial_stage']);cp=verify_checkpoint(root,c['prior_config_sha256']);m=dict(np.load(root/'MEMBERSHIP.npz',allow_pickle=False));state=json.loads((root/'GROWTH_STATE.json').read_text())
 assert len(m['edge_id'])==c['kernel_count'] and int(np.sum(m['edge_id']>=0))==c['initial_assigned'];np.testing.assert_array_equal(m['line_kernel_id'],np.arange(c['kernel_count']));assert state['next_version']==c['initial_next_version']
 models=np.load(root/'CARRIERS.npz',allow_pickle=False)
 for j,gid in enumerate(models['carrier_id']):
  key=str(int(gid));assert int(models['version'][j])==state['versions'][key];np.testing.assert_array_equal(np.asarray(state['curves'][key])*d['p'],models['knots'][models['knot_offsets'][j]:models['knot_offsets'][j+1]])
 objects={};unavailable=[]
 for j,(cid,leaf) in enumerate(sorted(d['leaves'].items())):
  if j%512==0:guard('readiness')
  labels=m['edge_id'][leaf.rows]
  for label in np.unique(labels):
   gid=int(label) if label>=0 else -int(cid)-1;rows=leaf.rows[labels==label]
   if gid not in objects:
    q=np.asarray(state['curves'][str(gid)]) if str(gid) in state['curves'] else leaf.q.copy()
    if gid>=0 and str(gid) not in state['curves']:assert gid==cid,('UNKNOWN_CURRENT_GROUP_GEOMETRY',gid,cid)
    q=clean(q);available=len(q)>=2 and np.isfinite(q).all();version=state['versions'].get(str(gid),leaf.version)
    objects[gid]=dict(id=gid,origin_objects=[gid],q=q,version=int(version),rows=[],leaves=[],available=bool(available),seed_origins=[gid] if gid in c['seed_ids'] else [],original_valid_flag=bool(leaf.valid))
    if not available:unavailable.append(dict(id=gid,reason='nonfinite_or_degenerate_saved_q'))
   objects[gid]['rows'].extend(map(int,rows));objects[gid]['leaves'].append(cid)
 for o in objects.values():o['rows']=np.asarray(sorted(o['rows']),np.int64);o['leaves']=sorted(set(o['leaves']))
 partition=np.concatenate([o['rows'] for o in objects.values()]);np.testing.assert_array_equal(np.sort(partition),np.arange(c['kernel_count']))
 for gid in c['seed_ids']:assert gid in objects and objects[gid]['available'],('SEED_NOT_READY',gid)
 d.update(initial_membership=m,objects=objects,next_version=state['next_version'],historical_events=state['events'],starting_state=state,unavailable=unavailable,initial_checkpoint=cp)
 return d
