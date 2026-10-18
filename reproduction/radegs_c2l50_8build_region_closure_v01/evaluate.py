from env import *
from graph import transfer_region
from closure import can_assign
from collections import Counter,defaultdict

def main():
 out=ROOT/'evaluation';out.mkdir(exist_ok=True);allcounts=[];transfer=[];source_status={};resource=guard()
 for s in SCENES:
  dev=ROOT/'dev'/s/DEV[s];checkseal(dev);raw=npz(rawpath(s,DEV[s]));c=cam(s,DEV[s]);assigned=[]
  for vp in [dev]+[ROOT/'reserved'/s/v for v in [AUX[s]]+RESERVED[s]]:
   checkseal(vp);allcounts+=json.loads((vp/'COUNTS.json').read_text())
  for case in cases(s):
   cp=dev/case['case']
   if not cp.exists():continue
   for arm in ['original','shifted','no_line']:
    rr=json.loads((cp/arm/'REGIONS.json').read_text());ms=npz(cp/arm/'REGION_MASKS.npz')['masks'];checks=[]
    for view in [AUX[s]]+RESERVED[s]:
     path=ROOT/'reserved'/s/view/case['case']/arm;qr=json.loads((path/'REGIONS.json').read_text());qm=npz(path/'REGION_MASKS.npz')['masks'];good=[i for i,r in enumerate(qr) if r['qualified']];raw2=npz(rawpath(s,view));c2=cam(s,view)
     for i,(r,m) in enumerate(zip(rr,ms)):
      t=transfer_region(m,raw,c,raw2,c2,[qm[j] for j in good]);accepted=can_assign(r['qualified'],t['comparable_fraction'],t['iou']);row=dict(scene=s,case=case['case'],arm=arm,source_view=DEV[s],target_view=view,dev_region=i,local_qualified=r['qualified'],target_qualified_region_count=len(good),target_original_region=(good[t['best']] if t['best']>=0 else -1),passed=accepted,all_historical_views=True,not_independent_GS_holdout=True,**t);transfer.append(row);checks.append(row)
    # Original-line membership requires AUX and at least one frozen reserved view; no IDs are matched across views.
    for i,r in enumerate(rr):
     if arm=='original' and r['qualified'] and any(x['dev_region']==i and x['target_view']==AUX[s] and x['passed'] for x in checks) and any(x['dev_region']==i and x['target_view'] in RESERVED[s] and x['passed'] for x in checks):assigned.append(dict(case=case['case'],region=i))
  n=json.loads((ROOT/'TOPOLOGY_AUDIT.json').read_text())[s]['source'];source_status[s]=dict(source_count=n,qualified_crossview_line_regions=len(assigned),physical_primitive_count=0,unknown_source_count=n,reason='NO_GO: no independent cross-view line-region qualifier; no forced source primitive')
  # Pilot never manufactures source labels if prerequisites fail.
  if assigned:raise RuntimeError('New qualified case requires explicit evidence review before source-region export; not automatic physical grouping')
  p=out/s;p.mkdir(exist_ok=True);np.savez_compressed(p/'SOURCE_IDS_REGION_UNKNOWN.npz',source_index=np.arange(n,dtype=np.int64),region_id=np.full(n,-1,np.int32),unknown=np.ones(n,bool));js(p/'SOURCE_REGION_STATUS.json',source_status[s])
 js(out/'TRANSFERS.json',transfer);js(out/'ALL_COUNTS.json',allcounts);js(out/'SOURCE_REGION_STATUS.json',source_status)
 agg={}
 for s in SCENES:
  agg[s]={}
  for a in ['original','shifted','no_line']:
   rr=[x for x in allcounts if x['scene']==s and x['arm']==a];tt=[x for x in transfer if x['scene']==s and x['arm']==a];agg[s][a]=dict(case_view_units=len(rr),candidates=sum(x['candidates'] for x in rr),qualified_2D=sum(x['qualified'] for x in rr),transfer_attempts=len(tt),local_qualified_transfer_attempts=sum(x['local_qualified'] for x in tt),transfer_pass=sum(x['passed'] for x in tt),median_iou=float(np.median([x['iou'] for x in tt])) if tt else None,fragment_instances=sum(x['fragments'] for x in rr))
 js(out/'COUNTS.json',agg)
 js(out/'MEASUREMENT_LIMITS.json',dict(candidate_budget_cap=16,boundary_slots_per_candidate=32,source_query_limit_per_case_arm=64,query_scope='rank0 qualified candidate only',equal_cap_not_equal_actual_budget=True,source_only_levelsets_closed_by_definition=True,cycle_basis_not_exhaustive=True,region_transfer='source-depth forward reprojection; 1px dilation both sets, depth qualified; best-of<=16 candidate IoU; not true identity',no_closed_loop_is_not_bad_open_line=True))
 print(json.dumps(agg,indent=2));state('PILOT_EVALUATED',scientific_status='NO_GO_SOURCE_REGION',children=[])
if __name__=='__main__':main()
