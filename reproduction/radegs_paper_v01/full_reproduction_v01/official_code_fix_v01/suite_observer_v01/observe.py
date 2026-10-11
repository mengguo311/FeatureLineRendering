"""Passive CPU-only status observer. Never dispatches or signals processes."""
import argparse,csv,json,os,sys,time
from pathlib import Path
P=Path(__file__).resolve().parent;W=P.parents[4]
sys.path.insert(0,str(W/'reproduction/radegs_paper_v01/stage2'))
from safety import atomic_json,sha256,verify_seal
from progress import counts
H=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');O=H/'official_code_fix_v01'
A=W/'artifacts/radegs_paper_reproduction_v01/full_reproduction_v01';OA=A/'official_code_fix_v01'
C=O/'suite_v01/scan37/state/runner_config.json';c=json.loads(C.read_text());D=Path(c['state_dir']);M=Path(c['model'])
protocol=O/'suite_v01/FULL_SUITE_PROTOCOL.json';proto=json.loads(protocol.read_text());cache={}
legacy=json.loads((O/'review_v01/before_MASTER_STATUS.json').read_text())
def live(pid):
 try:
  p=Path('/proc')/str(pid);fields=(p/'stat').read_text().rsplit(')',1)[1].split()
  return pid if p.stat().st_uid==os.getuid() and fields[0]!='Z' else None
 except (OSError,ValueError,IndexError):return None
def update():
 s=json.loads((D/'runner_state.json').read_text());verified=[]
 for stage in ('smoke','train','export','tsdf','eval'):
  seal=D/(stage+'.seal.json')
  if not seal.exists():continue
  key=sha256(seal)
  if cache.get(stage)!=key:
   if not verify_seal(seal,stage,c['inputs']):raise ValueError('unverified '+stage)
   cache[stage]=key
   atomic_json(O/'suite_v01/scan37/observer_receipts'/(stage+'.json'),{'verified_unix':time.time(),'seal_sha256':key,'outputs_verified':True})
  verified.append(stage)
 records=[];log=M/'iteration_loss.jsonl'
 if log.exists():
  lines=log.read_text().splitlines()
  for i,line in enumerate(lines):
   try:records.append(json.loads(line))
   except json.JSONDecodeError:
    if i!=len(lines)-1:raise
  if [x['iteration'] for x in records]!=list(range(1,len(records)+1)):raise ValueError('nonsequential iteration records')
 current={'id':'official_code_fix_v01_DTU_scan37_half30k_TSDF','method_variant':'official_code_fix_v01','dataset':'DTU','scene':'scan37','status':s['status'],'verified_stages':verified,'iteration_records':len(records),'last_iteration':records[-1] if records else None,'metric':json.loads((M/'vis/results.json').read_text()) if 'eval' in verified else None,'model':str(M),'config':str(C),'scientificdone':False,'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
 for e in proto['entries']:
  if e['id']==current['id']:atomic_json(e['status_path'],current)
 rows=[json.loads(Path(e['status_path']).read_text()) for e in proto['entries']]
 actual_ids={p.parent.name for p in (OA/'suite_v01/experiments').glob('*/STATUS.json')}
 assert actual_ids=={e['id'] for e in proto['entries']} and len(actual_ids)==74
 n=counts(rows);child=live(s.get('child_pid'));runner=live(s.get('runner_pid'));terminal=s['status'] in ('OFFICIAL_SCENE_EVALUATED_REVIEW_REQUIRED','ENGINEERING_NOT_READY')
 master={'method_variant':'official_code_fix_v01','newbranchstage':'DTU_HALF30K_SEQUENTIAL','phase':'official_scan37_'+str(s.get('stage')),'status':s['status'],'currentdataset':'DTU','currentscene':'scan37','current_model':str(M),'verified_stages':verified,'runner_state_path':str(D/'runner_state.json'),'runner_config_path':str(C),'runner_config_sha256':sha256(C),'runner_pid':runner,'childPIDs':[child] if child else [],'tmux':c['tmux'],'selected_gpu_uuid':s.get('selected_gpu_uuid'),'iteration_records':len(records),'last_iteration':records[-1] if records else None,'experiment_counts':n,'actual_counts':n,'protocol_path':str(protocol),'protocol_sha256':sha256(protocol),'status_files_actual':len(actual_ids),'status_files_expected':len(proto['entries']),'status_file_ids_match':True,'legacy_method_variant':'paper_text_precision_v01','legacy_counts':legacy.get('legacy_experiment_counts'),'legacy_snapshot':str(O/'review_v01/before_MASTER_STATUS.json'),'remaining':['scan37 remaining chain and manual geometry/metric/visual review','13 further DTU half30k scenes pending sequential preparation/validation','other59 protocol rows: full-resolution runtime/data or author-setting uncertainties, including9 unconfirmed Mip candidates','remaining paper-required ablation and other datasets require documented matching protocol; no fabricated totals'],'blocked':[{'scope':'non-half30k protocols','reason':'data/settings/runtime validation unresolved; not dispatched'}]+([{'scope':'scan37','reason':s.get('reason')}] if s['status']=='ENGINEERING_NOT_READY' else []),'last_event':'Passive observer read actual iterations and newly verified stage seals','next_action':'Review scan37 stage failure before any retry' if s['status']=='ENGINEERING_NOT_READY' else 'Review completed scan37 quality before dispatching next scene' if terminal else 'Persistent single GPU0 runner continues current chain under shared policy','source_dir':str(O/'source'),'native_sha256':c['inputs']['native'],'environment_lock':str(O/'ENVIRONMENT_LOCK.json'),'scientificdone':False,'full_suite_completed':False,'observer_pid':os.getpid(),'observer_tmux':'radegs-official-suite-observer-v01','resume_entry':str(O/'suite_v01/scan37/launch.sh'),'continuation_entry':str(OA/'suite_v01/CONTINUATION_ZH.md'),'current_reproduction_report':str(OA/'review_v01/SCAN24_RESULT_ZH.md'),'handoff_kind':'LONG_EXECUTION_SLICE_NOT_TASK_COMPLETION','utc':current['utc']}
 atomic_json(A/'MASTER_STATUS.json',master);atomic_json(OA/'STATUS.json',master);atomic_json(O/'suite_v01/MASTER_STATUS.json',master)
 metrics=[]
 for e,row in zip(proto['entries'],rows):
  value=row.get('metric');actual=value['overall'] if value else None;paper=e['metric'].get('paper_value')
  metrics.append({'id':e['id'],'method_variant':'official_code_fix_v01','dataset':e['dataset'],'scene':e['scene'],'iterations':e['iterations'],'resolution_divisor':e.get('resolution_divisor'),'status':row['status'],'paper_value':paper,'unit':e['metric'].get('unit'),'actual':actual,'delta':actual-paper if actual is not None and paper is not None else None})
 atomic_json(OA/'suite_v01/METRICS.json',{'rows':metrics,'actual_finite_metrics':sum(x['actual'] is not None for x in metrics),'scientificdone':False,'not_74_confirmed_training_jobs':True})
 out=OA/'suite_v01/METRICS.csv';tmp=out.with_suffix('.csv.tmp')
 with open(tmp,'w') as f:
  writer=csv.DictWriter(f,fieldnames=list(metrics[0]));writer.writeheader();writer.writerows(metrics);f.flush();os.fsync(f.fileno())
 os.replace(tmp,out)
 print(json.dumps({'state':s['status'],'stage':s.get('stage'),'records':len(records),'counts':n,'utc':current['utc']}),flush=True)
 return terminal
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--once',action='store_true');args=p.parse_args()
 while True:
  try:terminal=update()
  except Exception as exc:
   atomic_json(O/'suite_v01/OBSERVER_FAILURE.json',{'reason':repr(exc),'utc_unix':time.time(),'does_not_signal_or_change_GPU_runner':True});raise
  if args.once or terminal:break
  time.sleep(30)
