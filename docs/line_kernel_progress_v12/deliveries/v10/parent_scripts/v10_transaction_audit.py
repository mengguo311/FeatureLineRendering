from pathlib import Path
import json,hashlib,os,subprocess
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='2'
os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2])
import numpy as np
O=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_relaxed_guards_v10_20261103');R=O/'orchestration';A=R/'parent_acceptance/final_0542';out={'scope':'independent saved-byte transaction/selection/refit evidence audit, no science rerun','arms':[],'issues':[],'freeze_checks':[]}
def L(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
D=L(O/'DELIVERY_STATUS.json')
for uu in D['units']:
 u=O/'units'/uu['unit'];c=L(u/'CONFIG.json');f=L(u/'PARENT_RUN_FROZEN.json');req=L(u/'RUN_REQUEST.json');errors=[]
 for n,k in [('CONFIG.json','config_sha256'),('DECISION.json','decision_sha256')]:
  if sha(u/n)!=f[k]:errors.append(n)
 for p,h in req['source_files'].items():
  target=u/'source_snapshot'/Path(p).name
  if not target.exists() or sha(target)!=h:errors.append('source '+str(target))
 for p,h in req['helper_files'].items():
  if sha(p)!=h:errors.append('helper '+p)
 g=L(u/'GEOMETRY_AUDIT.json');scene='scan24' if (u/'scenes/scan24').exists() else 'scan65';gp=Path(uu['original_inputs']['gaussians']);ga=np.load(gp,allow_pickle=False)
 for k,v in g['fields_before'].items():
  if hashlib.sha256(ga[k].tobytes()).hexdigest()!=v['sha256'] or list(ga[k].shape)!=v['shape']:errors.append('original_array '+k)
 out['freeze_checks'].append({'unit':u.name,'snapshot_files':len(req['source_files']),'seven_arrays_match':not any('original_array' in s for s in errors),'errors':errors})
 for arm in uu['outputs']:
  st=u/'scenes'/scene/'stages';final=st/(arm+'_FINAL')
  if not final.exists():out['issues'].append('missing_arm '+str(final));continue
  lin=L(final/'LINEAGE.json');m0=np.load(st/'START/MEMBERSHIP.npz',allow_pickle=False);expected=m0['edge_id'].copy();n=len(expected);events=lin['events'];info={'unit':u.name,'arm':arm,'events':len(events),'exact_unions':0,'full_map_replays':0,'complete_minimum_with_tie_break':0,'committed_q_equals_selected':0,'fit_all_rows':0,'witnesses':{'rule2_distance':0,'rule2_angle':0,'parallel':0,'self_contact':0,'gap':0,'pure_pooling':0},'errors':[]}
  for ev in events:
   seq=ev['sequence'];gid=ev['group'];fid=ev['donor'];added=np.asarray(ev['added_rows'],np.int64);oldrows=np.flatnonzero(expected==gid)
   if fid>=0 and not np.array_equal(np.sort(added),np.flatnonzero(expected==fid)):info['errors'].append(f'donor_union {seq}')
   elif fid<0 and np.any(expected[added]>=0):info['errors'].append(f'unknown_donor {seq}')
   target=np.union1d(oldrows,added);expected[added]=gid
   cp=st/f'{arm}_{seq:04d}';actual=np.load(cp/'MEMBERSHIP.npz',allow_pickle=False)
   if np.array_equal(actual['edge_id'],expected):info['full_map_replays']+=1
   else:info['errors'].append(f'full_map {seq}')
   mods=np.load(cp/'MODELS.npz',allow_pickle=False);jj=np.flatnonzero(mods['group_id']==gid)[0];r=mods['rows'][mods['row_offsets'][jj]:mods['row_offsets'][jj+1]]
   if np.array_equal(np.sort(r),target):info['exact_unions']+=1
   else:info['errors'].append(f'model_rows {seq}')
   libdir=u/'scenes'/scene/'libraries'/arm/f"{ev['library_visit']:04d}_{gid}"
   lib=L(libdir/'LIBRARY.json');recs=lib['records'];best=min((r['metrics']['score'],r['donor'],r['relation'],r['direction'],i) for i,r in enumerate(recs) if r.get('connectable'))[-1]
   if lib['complete'] and best==lib['selected'] and recs[best]['donor']==fid:info['complete_minimum_with_tie_break']+=1
   else:info['errors'].append(f'best {seq}')
   rec=recs[best];geom=np.load(libdir/'GEOMETRY.npz',allow_pickle=False);q=mods['knots_p'][mods['knot_offsets'][jj]:mods['knot_offsets'][jj+1]]
   if np.array_equal(geom[rec['q_array']],q):info['committed_q_equals_selected']+=1
   else:info['errors'].append(f'q {seq}')
   if 'fit_evidence_arrays' in rec:
    fit=np.load(libdir/rec['fit_evidence_file'],allow_pickle=False)
    if np.array_equal(np.sort(fit[rec['fit_evidence_arrays']['rows']]),target):info['fit_all_rows']+=1
    else:info['errors'].append(f'fit_rows {seq}')
   mm=ev['metrics'];rr=ev['relaxed_rule_groups'];w=info['witnesses'];w['rule2_distance']+=int(mm['max_distance_p']>1.5+1e-9);w['rule2_angle']+=int(mm['max_angle_deg']>75+1e-9);w['parallel']+=int(bool(mm.get('parallel_conflicts')));w['self_contact']+=int(mm.get('contact',{}).get('reject',False));w['gap']+=int(mm.get('max_gap_p',0)>1.5+1e-9);w['pure_pooling']+=int(mm.get('unique_donor_support_p',1)<1e-9)
   if 2 in rr and mm['rule2']['hard_enabled']:info['errors'].append('rule2_hidden')
   if 6 in rr and mm['rule6']['hard_enabled']:info['errors'].append('rule6_hidden')
  mf=np.load(final/'MEMBERSHIP.npz',allow_pickle=False)
  if not np.array_equal(expected,mf['edge_id']):info['errors'].append('final_map')
  info['gain_vs_start']=int(np.sum((m0['edge_id']<0)&(expected>=0)));info['loss_vs_start']=int(np.sum((m0['edge_id']>=0)&(expected<0)));info['inherited_events']=len(lin['historical']);out['arms'].append(info);out['issues']+=info['errors'];print(u.name,arm,len(events),len(info['errors']),flush=True)
 out['issues']+=errors
# exact own process identities only; no foreign commandlines or envs.
pids={3420947}
for p in R.glob('unit_*/COMPUTE_START.json'):
 d=L(p)
 for k in ['pid','child_pid','pgid']:
  if isinstance(d.get(k),int):pids.add(d[k])
for p in R.glob('unit_*/*/LAUNCH.json'):
 d=L(p)
 for k in ['pid','child_pid']:
  if isinstance(d.get(k),int):pids.add(d[k])
out['owned_pid_comm_readback']=subprocess.run(['ps','-p',','.join(map(str,sorted(pids))),'-o','pid=,comm='],capture_output=True,text=True).stdout
out['own_science_processes_absent']=not out['owned_pid_comm_readback'].strip();out['total_transactions']=sum(x['events'] for x in out['arms']);out['total_inherited_not_summed']=True
(A/'TRANSACTION_SOURCE_AUDIT.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print('DONE',out['total_transactions'],'issues',len(out['issues']))
