"""Restore every checkpoint composite, independently of raw and active cohorts."""
from runtime_io import *
import branch_loader

def load(c,guard):
 cfg=dict(c,seed_ids=c['raw_seed_ids'],seed_versions=c['restore_seed_versions'])
 d=branch_loader.load(cfg,guard);guard('readiness')
 tracked=sorted(sid for o in d['objects'].values() for sid in o['seed_origins'])
 assert tracked==sorted(c['tracked_origin_ids']),'RESTORED_ORIGIN_COVERAGE'
 statuses={}
 for sid in c['seed_ids']:
  o=d['objects'].get(sid)
  statuses[sid]='READY' if o is not None and o['version']==c['seed_versions'][str(sid)] and len(o['rows'])==c['seed_expected_rows'][str(sid)] and o['available'] else 'NOT_RUN_SEED_BINDING'
 d['seed_status']=statuses
 d['cohort_receipt']=dict(raw_origins=c['raw_seed_ids'],active_origins=c['seed_ids'],tracked_origins=tracked,all_checkpoint_composites_restored=True,cohort_reselection=False,no_initial_version_allocation=True,next_version=d['next_version'])
 d['seed_ledger']=dict(kind='restore_existing_checkpoint_origins_only',active=c['seed_ids'],readiness=statuses,not_a_new_selection=True,no_replacement=True)
 return d
