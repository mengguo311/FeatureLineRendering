"""Restore the old accepted cohort first; activate intact M4 objects without mutation."""
from runtime_io import *
import branch_loader

def select(c,d,groups,lineage):
 endpoints={tuple(e['output']) for e in lineage['events'] if e.get('operation')=='endpoint'}
 old=set(c['restore_seed_ids']);records=[];eligible={m:[] for m in ['line','polyline']}
 for g in groups['groups']:
  gid=int(g['edge_id']);version=int(g['version']);obj=d['objects'].get(gid);leaf=d['leaves'].get(gid);why=[]
  if not g['valid']:why.append('saved_invalid')
  if (gid,version) not in endpoints:why.append('not_surviving_endpoint_output')
  if gid in old:why.append('old_restore_origin')
  intact=obj is not None and leaf is not None and obj['version']==version==leaf.version and obj['leaves']==[gid] and np.array_equal(obj['rows'],np.sort(leaf.rows))
  if not intact:why.append('absorbed_changed_or_missing_membership_version')
  count=sum(x['kernels']>=12 and x['mapped_supported_length_p']>=2 for x in g['M3_contributions'])
  if count<2:why.append('fewer_than_two_substantial_M3')
  length=float(g['supported_length_p'])
  if not 10<=length<=80:why.append('outside_10_80p_saved_support')
  if g['model'] not in eligible:why.append('unsupported_saved_model')
  rec=dict(id=gid,version=version,model=g['model'],supported_length_p=length,substantial_M3=count,current_rows=len(obj['rows']) if obj else None,reasons=why,eligible=not why,selected=False)
  records.append(rec)
  if not why:eligible[g['model']].append(rec)
 chosen=[]
 for model,rr in eligible.items():
  rr.sort(key=lambda r:(-r['supported_length_p'],r['id']))
  for r in rr[:3]:r['selected']=True;chosen.append(r['id'])
 ledger=dict(records=records,selected=sorted(chosen),eligible_counts={m:len(rr) for m,rr in eligible.items()},eligible_unselected=[r['id'] for r in records if r['eligible'] and not r['selected']],selection_precedes_growth=True,cohort_only_not_donor_gate=True,no_replacement=True)
 return ledger

def load(c,guard):
 restore=dict(c,seed_ids=c['restore_seed_ids'],seed_versions=c['restore_seed_versions'])
 d=branch_loader.load(restore,guard);guard('readiness')
 ledger=select(c,d,json.loads(Path(c['groups']).read_text()),json.loads(Path(c['lineage']).read_text()))
 expected=c.get('expected_selection_counts')
 if expected:
  assert len(ledger['records'])==expected['records'],'COHORT_RECORD_COUNT'
  assert ledger['eligible_counts']==expected['eligible'],'COHORT_ELIGIBLE_COUNT'
  assert len(ledger['eligible_unselected'])==expected['unselected'],'COHORT_UNSELECTED_COUNT'
 statuses={};snapshot={k:(o['version'],o['rows'].copy(),o['q'].copy()) for k,o in d['objects'].items()}
 for gid in c['seed_ids']:
  o=d['objects'].get(gid)
  if gid not in ledger['selected'] or o is None or o['version']!=c['seed_versions'][str(gid)] or len(o['rows'])!=c['seed_expected_rows'][str(gid)]:statuses[gid]='NOT_RUN_SEED_BINDING';continue
  if not o['available']:statuses[gid]='NOT_RUN_SEED_GEOMETRY';continue
  assert not o['seed_origins'],'NEW_ORIGIN_ALREADY_TRACKED'
  o['seed_origins']=[gid];statuses[gid]='READY'
 for gid,(version,rows,q) in snapshot.items():
  o=d['objects'][gid];assert version==o['version'];np.testing.assert_array_equal(rows,o['rows']);np.testing.assert_array_equal(q,o['q'])
 ledger.update(frozen_ids=c['seed_ids'],readiness=statuses,missing_frozen_ids=sorted(set(c['seed_ids'])-set(ledger['selected'])),eligible_selected_not_substituted=sorted(set(ledger['selected'])-set(c['seed_ids'])))
 d.update(seed_status=statuses,seed_ledger=ledger)
 d['cohort_receipt']=dict(restore_origins=c['restore_seed_ids'],active_origins=c['seed_ids'],tracked_origins=sorted(s for o in d['objects'].values() for s in o['seed_origins']),membership_and_q_and_versions_unchanged=True,no_initial_version_allocation=True,next_version=d['next_version'],old_groups_remain_whole_donors=True)
 return d
