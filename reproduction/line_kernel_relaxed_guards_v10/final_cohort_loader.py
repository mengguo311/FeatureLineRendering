"""Restore frozen composites, then activate only the two prebound intact M4 origins."""
from runtime_io import *
import branch_loader

def load(c,guard):
 d=branch_loader.load(dict(c,seed_ids=c['raw_seed_ids'],seed_versions=c['restore_seed_versions']),guard);guard('readiness')
 tracked=sorted(s for o in d['objects'].values() for s in o['seed_origins']);assert tracked==sorted(c['restored_origin_ids'])
 statuses={}
 for gid in c['seed_ids']:
  o=d['objects'].get(gid);leaf=d['leaves'].get(gid)
  intact=o is not None and leaf is not None and o['version']==leaf.version==c['seed_versions'][str(gid)] and o['leaves']==[gid] and len(o['rows'])==c['seed_expected_rows'][str(gid)] and np.array_equal(o['rows'],np.sort(leaf.rows)) and np.array_equal(o['q'],leaf.q)
  if not intact:statuses[gid]='NOT_RUN_SEED_BINDING';continue
  if not o['available']:statuses[gid]='NOT_RUN_SEED_GEOMETRY';continue
  assert not o['seed_origins'];o['seed_origins']=[gid];statuses[gid]='READY'
 tracked=sorted(s for o in d['objects'].values() for s in o['seed_origins'])
 assert tracked==sorted(c['restored_origin_ids']+[s for s,v in statuses.items() if v=='READY'])
 d['seed_status']=statuses;d['cohort_receipt']=dict(raw_origins=c['raw_seed_ids'],active_origins=c['seed_ids'],tracked_origins=tracked,old_groups_remain_whole_donors=True,membership_and_q_and_versions_unchanged=True,no_initial_version_allocation=True,next_version=d['next_version'])
 d['seed_ledger']=dict(kind='activate frozen eligible-unselected IDs; no reselection',active=c['seed_ids'],readiness=statuses,no_replacement=True)
 return d
