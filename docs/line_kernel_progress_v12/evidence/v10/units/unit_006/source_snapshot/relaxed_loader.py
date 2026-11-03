"""Restore an immutable accepted composite bank after the actual M4 restricted loader."""
from runtime_io import *
import scan24_loader
from whole_delivery import mapping

def load(c,guard):
 raw=json.loads(Path(c['raw_config']).read_text());cfg=dict(c)
 for key in ['initial_stage','initial_assigned','initial_next_version','seed_versions','next_version']:cfg[key]=raw[key]
 d=scan24_loader.load(cfg,guard);guard('readiness');root=Path(c['restore_stage']);verify_checkpoint(root,c['restore_binding']);m=dict(np.load(root/'MEMBERSHIP.npz',allow_pickle=False));bank=dict(np.load(root/'MODELS.npz',allow_pickle=False));groups=json.loads((root/'GROUPS.json').read_text())['groups'];lin=json.loads((root/'LINEAGE.json').read_text());objects=d['objects'];old=d['initial_membership']
 np.testing.assert_array_equal(m['line_kernel_id'],np.arange(c['kernel_count']));assert int(np.sum(m['edge_id']>=0))==c['initial_assigned'];assert lin['next_version']==c['initial_next_version']
 seen=set();byid={int(k):i for i,k in enumerate(bank['group_id'])}
 for g in groups:
  gid=int(g['id']);j=byid[gid];rows=bank['rows'][bank['row_offsets'][j]:bank['row_offsets'][j+1]];q=bank['knots_p'][bank['knot_offsets'][j]:bank['knot_offsets'][j+1]]
  np.testing.assert_array_equal(rows,np.array(g['rows']));union=np.unique(np.concatenate([d['leaves'][cid].rows for cid in g['leaves']]));np.testing.assert_array_equal(rows,union);assert not seen.intersection(g['leaves']);seen.update(g['leaves'])
  for cid in g['leaves']:
   rr=d['leaves'][cid].rows;label=int(old['edge_id'][rr[0]]);original=label if label>=0 else -cid-1;assert original in objects;del objects[original]
  assert g['version']==int(bank['version'][j])==c['seed_versions'][str(gid)];assert np.all(m['edge_id'][rows]==gid)
  objects[gid]=dict(id=gid,origin_objects=[gid],q=q.copy(),rows=rows.copy(),version=g['version'],leaves=g['leaves'],seed_origins=g['seed_origins'],metrics=g['metrics'],available=g['geometry_available'])
 # Canonical current donor IDs are reset only for query provenance, not membership or geometry.
 for gid,o in objects.items():o['origin_objects']=[gid]
 d['objects']=objects;d['initial_membership']={k:v.copy() for k,v in m.items()};d['historical_events']=lin['historical']+lin['events'];d['next_version']=lin['next_version'];d['initial_checkpoint']=json.loads((root/'CHECKPOINT.json').read_text());d['seed_status']={s:'READY' for s in c['seed_ids']}
 np.testing.assert_array_equal(np.sort(np.concatenate([o['rows'] for o in objects.values()])),np.arange(c['kernel_count']));np.testing.assert_array_equal(mapping(d,objects)['edge_id'],m['edge_id'])
 d['restore_receipt']=dict(exact_rows=True,complete_composite_curves=True,assigned=c['initial_assigned'],next_version=d['next_version'],prior_events=len(lin['events']),source=str(root))
 return d
