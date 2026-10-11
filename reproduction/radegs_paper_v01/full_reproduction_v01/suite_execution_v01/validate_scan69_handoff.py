"""CPU provenance/style/count audit plus real running/checkpoint handoff receipt."""
import ast,datetime,json,os,re,shutil,subprocess,sys
from pathlib import Path
P=Path(__file__).resolve().parent;W=P.parents[3];H=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');S=H/'full_reproduction_v01/suite_execution_v01';A=W/'artifacts/radegs_paper_reproduction_v01/full_reproduction_v01';R=A/'suite_execution_v01/scan69_v01';O=S/'scan69_v01'
sys.path.insert(0,str(P/'runtime'));sys.path.append(str(W/'reproduction/radegs_paper_v01/stage2'));from safety import atomic_json,sha256,verify_seal
from runner import process_identity
cp=O/'state/runner_config.json';c=json.loads(cp.read_text());assert sha256(cp)=='1f98695bdc8fa2f726141dbc6278e1e83b2ad31788b4f3e956b7224a9fafda9c'
for p,h in c['immutable_files'].items():assert sha256(p)==h,p
assert verify_seal(O/'state/smoke.seal.json','smoke',c['inputs'])
manifest=json.loads((A/'suite_execution_v01/scan65_result_v01/EVIDENCE_MANIFEST.json').read_text())
for block in ['files','code']:
 for p,h in manifest[block].items():assert sha256(p)==h,p
protocol=json.loads((A/'FULL_SUITE_PROTOCOL.json').read_text());ids={e['id'] for e in protocol['entries']};files=list((A/'experiments').glob('*/STATUS.json'));metrics=json.loads((A/'METRICS.json').read_text());assert ids=={p.parent.name for p in files}=={r['id'] for r in metrics['rows']} and len(files)==len(ids)==74
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True,cwd=W).strip();assert head=='00bb67c4ae39157906bcda6abc8760cc37679414'
assert not subprocess.check_output(['git','status','--porcelain'],text=True,cwd=H/'sources/RaDe-GS').strip()
allowed=('reproduction/radegs_paper_v01/','artifacts/radegs_paper_reproduction_v01/');rows=subprocess.check_output(['git','status','--porcelain','-z','--untracked-files=all'],cwd=W).decode().split('\0');assert all(r[3:].startswith(allowed) for r in rows if r)
subprocess.run(['git','diff','--check','--',*allowed],cwd=W,check=True)
newpaths=[*P.joinpath('scan65_result_v01').glob('*.py'),P/'assemble_dtu_entry_v02.py',P/'result_review_v02.py',P/'test_result_review_v02.py',Path(__file__),*A.joinpath('suite_execution_v01/scan65_result_v01').glob('*'),*R.glob('*'),A/'MASTER_STATUS.json',A/'METRICS.json',A/'METRICS.csv',A/'REPRODUCTION_REPORT_ZH.md']
counts={'json':0,'python':0,'links':0,'text_diff_check':0}
for p in newpaths:
 if not p.is_file():continue
 if p.suffix=='.json':json.loads(p.read_text());counts['json']+=1
 if p.suffix=='.py':ast.parse(p.read_text());counts['python']+=1
 if p.suffix=='.md':
  for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
   if target.startswith(('http:','https:','#')):continue
   t=target.strip('<>').split('#')[0];assert (p.parent/t).exists(),(p,t);counts['links']+=1
 if p.suffix in ['.py','.json','.md','.csv']:
  r=subprocess.run(['git','diff','--no-index','--check','/dev/null',str(p)],capture_output=True,text=True);assert r.returncode in [0,1] and not(r.stdout or r.stderr),(p,r.stdout,r.stderr);counts['text_diff_check']+=1
s=json.loads((O/'state/runner_state.json').read_text());assert s['status']=='RUNNING' and s['stage']=='train' and s['config_sha256']==sha256(cp)
for k in ['runner_pid','child_pid']:assert process_identity(s[k])['uid']==os.getuid()
model=Path(c['model']);records=[json.loads(x) for x in (model/'iteration_loss.jsonl').read_text().splitlines()];assert records and len({r['iteration'] for r in records})==len(records)
checkpoint=json.loads((model/'restart.json').read_text());assert checkpoint['completed_iteration']>=500 and checkpoint['provenance']==c['inputs'] and sha256(checkpoint['path'])==checkpoint['sha256']
assert s['selected_gpu_uuid']==c['allowed_gpu_uuids'][0]
# Identify only own immediate training children without revealing any cmdline.
children=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  if p.stat().st_uid!=os.getuid():continue
  fields=(p/'stat').read_text().split(') ',1)[1].split()
  if int(fields[1])==s['child_pid']:children.append({'pid':int(p.name),'comm':(p/'comm').read_text().strip()})
 except (FileNotFoundError,ProcessLookupError,PermissionError):pass
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
receipt={'status':'ACTUAL_TRAINING_IN_PROGRESS','config':str(cp),'config_sha256':sha256(cp),'immutable_files_verified':len(c['immutable_files']),'native_sha256':c['inputs']['candidate_native'],'smoke_seal_verified':True,'smoke_report':str(O/'state/smoke.report.json'),'runner_state':str(O/'state/runner_state.json'),'runner_pid':s['runner_pid'],'stage_pid':s['child_pid'],'own_worker_children':children,'GPU_UUID':s['selected_gpu_uuid'],'completed_iteration_observed':records[-1]['iteration'],'last_iteration_record':records[-1],'checkpoint_iteration':checkpoint['completed_iteration'],'checkpoint_sha256':checkpoint['sha256'],'checkpoint_generation':checkpoint['path'],'checkpoint_generation_is_rotating':True,'future_resume_pointer':str(model/'restart.json'),'checkpoint_hash_verified_at_observation':True,'checkpoint_hash_verified':True,'tmux':'radegs-suite-scan69-v01','observer_admission':str(O/'launch/OBSERVERS_ADMITTED.json'),'HEAD':head,'counts_and_links':counts,'experiment_status_files':len(files),'metric_rows':len(metrics['rows']),'root_free_bytes':shutil.disk_usage('/').free,'HDD_free_bytes':shutil.disk_usage(H).free,'scientificdone':False,'full_suite_completed':False,'handoff_kind':'LONG_EXECUTION_SLICE_NOT_TASK_COMPLETION','utc':now}
atomic_json(R/'ACTUAL_TRAINING_HANDOFF.json',receipt);atomic_json(R/'VALIDATION.json',{'passed':True,'immutable_files_verified':len(c['immutable_files']),'prior_scan65_evidence_manifest_verified':True,'source_native_unchanged':True,'counts':counts,'HEAD':head,'allowed_changes_only':True,'official_C24_clean':True,'protocol_STATUS_METRICS_ids_exact_match':True,'experiment_status_files':len(files),'scientificdone':False,'utc':now})
m=json.loads((A/'MASTER_STATUS.json').read_text());m.update(phase='DTU_SCAN65_TRAINING',status='ACTUAL_TRAINING_IN_PROGRESS',runner_pid=s['runner_pid'],childPIDs=[s['child_pid']]+[x['pid'] for x in children],completed_iteration_observed=records[-1]['iteration'],verified_stages=['smoke'],handoff_receipt=str(R/'ACTUAL_TRAINING_HANDOFF.json'),validation_path=str(R/'VALIDATION.json'),continuation_entry=str(R/'CONTINUATION_ZH.md'),last_event='scan69 actual mandatory smoke sealed; real training iterations and >=500 full restart checkpoint hash verified',next_action='single runner continues scan69 to30k/export/TSDF/eval; review actual outputs or diagnose failed stage before next scene',handoff_kind='LONG_EXECUTION_SLICE_NOT_TASK_COMPLETION',utc=now);m['experiment_counts'].update(training_attempts_started=8,corrected_training_attempts_started=7,current_explicit_scene_training_started=7);atomic_json(A/'MASTER_STATUS.json',m)
print(json.dumps(receipt,indent=2))
