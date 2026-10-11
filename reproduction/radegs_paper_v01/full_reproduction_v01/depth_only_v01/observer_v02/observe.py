"""Passive depth-only observer: no GPU imports, dispatch, signals or mesh reads."""
import argparse,json,os,sys,time
from pathlib import Path
P=Path(__file__).resolve().parent;W=P.parents[4]
sys.path.insert(0,str(W/'reproduction/radegs_paper_v01/stage2'))
from safety import atomic_json,sha256,verify_seal
from progress import counts,disk_blocked
H=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');D=H/'depth_only_v01';O=H/'official_code_fix_v01';A=W/'artifacts/radegs_paper_reproduction_v01/full_reproduction_v01';DA=A/'depth_only_v01'
C=D/'scan55/state/runner_config.json';c=json.loads(C.read_text());S=Path(c['state_dir']);M=Path(c['model']);proto_path=D/'FULL_SUITE_PROTOCOL.json';proto=json.loads(proto_path.read_text());cache={}
def live(pid):
 if not pid:return None
 try:
  p=Path('/proc')/str(pid);fields=(p/'stat').read_text().rsplit(')',1)[1].split()
  return pid if p.stat().st_uid==os.getuid() and fields[0]!='Z' else None
 except (OSError,ValueError,IndexError):return None
def update():
 state=json.loads((S/'runner_state.json').read_text());verified=[]
 guard_path=D/'scan55/resource_guard_state.json';guard=json.loads(guard_path.read_text()) if guard_path.exists() else None
 low_disk=disk_blocked(guard)
 for stage in ('smoke','train','export','depth_review'):
  seal=S/(stage+'.seal.json')
  if not seal.exists():continue
  key=sha256(seal)
  if cache.get(stage)!=key:
   if not verify_seal(seal,stage,c['inputs']):raise ValueError('invalid '+stage+' seal')
   cache[stage]=key
   atomic_json(D/'scan55/observer_receipts'/(stage+'.json'),{'sha256':key,'outputs_hash_verified':True,'verified_unix':time.time()})
  verified.append(stage)
 records=[];log=M/'iteration_loss.jsonl'
 if log.exists():
  lines=log.read_text().splitlines()
  for i,line in enumerate(lines):
   try:records.append(json.loads(line))
   except json.JSONDecodeError:
    if i!=len(lines)-1:raise
  if [r['iteration'] for r in records]!=list(range(1,len(records)+1)):raise ValueError('nonsequential training records')
 quality=D/'reviews/scan55.json';review=json.loads(quality.read_text()) if quality.exists() else None
 review_pass=bool('depth_review' in verified and review and review.get('status')=='DEPTH_REVIEW_PASSED_WITH_LIMITATIONS')
 current={'id':'depth_only_v01_DTU_scan55_half30k','scene':'scan55','method_variant':'official_code_fix_v01','workflow':'depth_only_v01','status':state['status'],'train_completed':'train' in verified,'depth_export_completed':'export' in verified,'depth_review_passed':review_pass,'depth_export_npz':98 if 'export' in verified else 0,'verified_stages':verified,'iteration_records':len(records),'last_iteration':records[-1] if records else None,'quality_review':str(quality) if review else None,'scientificdone':False,'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
 for entry in proto['entries']:
  if entry['id']==current['id']:atomic_json(entry['status_path'],current)
 actual={p.parent.name for p in (DA/'experiments').glob('*/STATUS.json')};expected={e['id'] for e in proto['entries']}
 assert actual==expected and len(expected)==15
 rows=[json.loads(Path(e['status_path']).read_text()) for e in proto['entries']];n=counts(rows)
 terminal=state['status'] in ('DEPTH_DELIVERED_VISUAL_REVIEW_REQUIRED','ENGINEERING_NOT_READY')
 child=live(state.get('child_pid'));runner=live(state.get('runner_pid'))
 master={'acceptance_scope':'trusted training + original raw depth + numerical/coverage/visual review; no mesh/eval','method_variant':'official_code_fix_v01','workflow':'depth_only_v01','newbranchstage':'DTU_HALF30K_DEPTH_SEQUENTIAL','phase':'scan55_'+str(state.get('stage')),'status':state['status'],'currentdataset':'DTU','currentscene':'scan55','current_model':str(M),'verified_stages':{'scan24':['train','export','depth_review'],'scan37':['train','export','depth_review'],'scan40':['train','export','depth_review'],'scan55':verified},'runner_state_path':str(S/'runner_state.json'),'runner_config_path':str(C),'runner_config_sha256':sha256(C),'runner_pid':runner,'childPIDs':[child] if child else [],'tmux':c['tmux'],'selected_gpu_uuid':state.get('selected_gpu_uuid'),'iteration_records':len(records),'last_iteration':records[-1] if records else None,'experiment_counts':n,'actual_counts':n,'protocol_path':str(proto_path),'protocol_sha256':sha256(proto_path),'status_files_actual':len(actual),'status_files_expected':15,'status_file_ids_match':True,'delivery_index':str(D/'DELIVERY_INDEX.json'),'completed_depth_reviews':str(D/'REVIEWS_SCAN24_SCAN37_SCAN40.json'),'legacy_master_snapshot':str(D/'MASTER_BEFORE_DEPTH_ONLY.json'),'remaining':['scan55 train/export/package/visual review until verified','11 subsequent explicit DTU half30k scenes sequentially after review','other original-paper datasets only with source-backed preprocessing/training protocols'],'blocked':[{'scope':'other settings/datasets','reason':'protocol/data verification pending; not dispatched'}]+([{'scope':'scan55','reason':state.get('reason')}] if state['status']=='ENGINEERING_NOT_READY' else []),'last_event':'Read actual iteration records and verified stage seals; mesh results excluded','next_action':'Diagnose own stage failure; no automatic retry' if state['status']=='ENGINEERING_NOT_READY' else 'Inspect scan55 actual depth images and numeric report, record review before next scene' if terminal else 'Single GPU0 supervisor continues smoke/train/export/depth package; no mesh/eval','source_dir':str(O/'source'),'native_sha256':c['inputs']['native'],'environment_lock':str(O/'ENVIRONMENT_LOCK.json'),'resume_entry':str(D/'scan55/launch.sh'),'continuation_entry':str(DA/'CONTINUATION_ZH.md'),'current_reproduction_report':str(DA/'DEPTH_DELIVERY_REPORT_ZH.md'),'observer_pid':os.getpid(),'observer_tmux':'radegs-depth-observer-scan55-v01','scientificdone':False,'full_suite_completed':False,'mesh_evaluation_required':False,'handoff_kind':'LONG_EXECUTION_SLICE_NOT_TASK_COMPLETION','utc':current['utc']}
 if low_disk:
  master.update(status='PREEMPTING_OWN_STAGE_LOW_DISK' if runner or child else 'PAUSED_LOW_DISK_RESERVE',next_action='Disk reserve violated: own safe checkpoint/exit; resume only after root>=10GiB and HDD>=50GiB and fresh GPU admission')
  master['blocked'].append({'scope':'disk reserve','reason':guard.get('cause')})
  if not runner and not child:terminal=True
 master['resource_guard_state_path']=str(guard_path);master['resource_guard_state']=guard
 atomic_json(A/'MASTER_STATUS.json',master);atomic_json(D/'MASTER_STATUS.json',master);atomic_json(DA/'STATUS.json',master)
 print(json.dumps({'status':state['status'],'stage':state.get('stage'),'records':len(records),'counts':n,'utc':current['utc']}),flush=True)
 return terminal
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--once',action='store_true');args=p.parse_args()
 while True:
  try:terminal=update()
  except Exception as exc:
   atomic_json(D/'OBSERVER_FAILURE.json',{'reason':repr(exc),'unix':time.time(),'GPU_runner_not_signaled':True});raise
  if args.once or terminal:break
  time.sleep(30)
