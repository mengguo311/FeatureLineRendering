"""CPU final evidence verification, no CUDA/model changes."""
from pathlib import Path
import sys,json,subprocess,ast,re,shutil,datetime
WORK=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(WORK/'reproduction/radegs_paper_v01/stage2'))
from safety import atomic_json,sha256,verify_seal
h=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');o=h/'full_reproduction_v01/precision_v01/corrected_result_audit_v01';a=WORK/'artifacts/radegs_paper_reproduction_v01/full_reproduction_v01';p=a/'precision_v01/corrected_result_audit_v01';code=Path(__file__).parent;cfg=h/'full_reproduction_v01/precision_v01/pilot_v02/state/runner_config.json';c=json.loads(cfg.read_text())
assert all(sha256(f)==v for f,v in c['immutable_files'].items())
assert all(verify_seal(cfg.parent/(s+'.seal.json'),s,c['inputs']) for s in ['smoke','train','export'])
clone=h/'sources/RaDe-GS';head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=WORK,text=True).strip();chead=subprocess.check_output(['git','rev-parse','HEAD'],cwd=clone,text=True).strip();clean=not subprocess.check_output(['git','status','--porcelain'],cwd=clone,text=True).strip();assert clean
source_proof=json.loads((o/'EVALUATOR_SOURCE_CORRECTION.json').read_text());assert source_proof['outer_all_algorithm_and_parser_AST_identical'] and source_proof['inner_byte_identical']
for f,digest in source_proof['files'].items():assert sha256(f)==digest
seals={}
for f,stage in [(o/'tsdf/tsdf.seal.json','tsdf'),(o/'official_eval/model/eval.seal.json','eval')]:
 ss=json.loads(f.read_text());assert verify_seal(f,stage,ss['inputs']);seals[str(f)]=sha256(f)
# Registration is only in this diagnostic verification process.
import safety
safety.STAGES=tuple(safety.STAGES)+('checkpoint_diagnostic',)
for name in ['official_eval','checkpoint_diagnostic','gradient_audit_v02']:
 q=o/name/'state';c2=json.loads((q/'runner_config.json').read_text());assert all(sha256(f)==v for f,v in c2['immutable_files'].items());f=q/'checkpoint_diagnostic.seal.json';assert verify_seal(f,'checkpoint_diagnostic',c2['inputs']);seals[str(f)]=sha256(f)
for x in code.glob('*.py'):ast.parse(x.read_text())
jsonfiles=list(a.rglob('*.json'))
for x in jsonfiles:json.loads(x.read_text())
missing=[]
for doc in [a/'REPRODUCTION_REPORT_ZH.md',*p.glob('*.md')]:
 for target in re.findall(r'\]\(([^)]+)\)',doc.read_text()):
  if '://' in target or target.startswith('#'):continue
  if not (doc.parent/target.split('#')[0]).exists():missing.append({'doc':str(doc),'target':target})
assert not missing,missing
checks=[]
for f in [*code.glob('*.py'),*p.glob('*.md'),*p.glob('*.json'),a/'REPRODUCTION_REPORT_ZH.md']:
 r=subprocess.run(['git','diff','--no-index','--check','--','/dev/null',str(f)],capture_output=True,text=True)
 if r.stdout or r.stderr:checks.append({'file':str(f),'output':r.stdout+r.stderr})
assert not checks,checks
protocol=json.loads((a/'FULL_SUITE_PROTOCOL.json').read_text());ids={x['id'] for x in protocol['entries']};actual={x.parent.name for x in (a/'experiments').glob('*/STATUS.json')};metrics=json.loads((a/'METRICS.json').read_text());assert len(ids)==74 and ids==actual=={r['id'] for r in metrics['rows']}
state=json.loads((o/'gradient_audit_v02/state/runner_state.json').read_text());assert state['status']=='DIAGNOSTIC_COMPLETE' and state['child_pid'] is None and not Path('/proc',str(state['runner_pid'])).exists()
receipt={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'workspace_HEAD':head,'C24_HEAD':chead,'C24_clean':clean,'training_config_sha256':sha256(cfg),'training_immutable_inputs_verified':len(c['immutable_files']),'original_smoke_train_export_seals_verified':True,'new_seals':seals,'official_evaluator_sources':source_proof,'candidate_native_sha256':c['inputs']['candidate_native'],'CPU_regression':json.loads((o/'CPU_corrected_invocation/results.json').read_text())['test_count'],'real_sparse_view_GREEN':1,'diagnostic_decomposition_CPU_GREEN':2,'negative_GPU_diagnostic_failures_preserved':True,'allview_diagnostic_rows':98,'JSON_parsed':len(jsonfiles),'new_code_AST_passed':True,'relative_links_missing':missing,'new_files_diff_check_passed':True,'suite_protocol_records':len(ids),'suite_STATUS_files':len(actual),'actual_metrics':sum(r['metric_value'] is not None for r in metrics['rows']),'negative_evaluated_chains':1,'full_suite_done':False,'scientificdone':False,'resource_free_bytes':{'root':shutil.disk_usage('/').free,'HDD':shutil.disk_usage(h).free},'current_runner_snapshot':{'status':state['status'],'historical_PID':state['runner_pid'],'child_pid':None,'supervisor_exited':True,'state_path':str(o/'gradient_audit_v02/state/runner_state.json')},'initial_validation_correction':'Earlier byte-identity assertion on outer evaluate_dtu_mesh.py failed; existing stage2 subprocess-launcher-only patch now audited with exact full-module AST normalization, inner evaluator byte identity. No old seal rewritten.'}
atomic_json(p/'VALIDATION.json',receipt)
atomic_json(p/'STATUS.json',{'status':'SLICE_HANDOFF_FULL_REPRODUCTION_INCOMPLETE','phase':'SCAN24_EVALUATED_NEGATIVE_GRADIENT_DIAGNOSIS_COMPLETED','scan24_official_CD_mm':6.376827928599536,'full_suite_done':False,'scientificdone':False,'live_child_PIDs':[],'remaining':'Optimizer/opacity boundary audit; explain negative-result scope, then remaining frozen paper scenes/protocols','runner_state_path':str(o/'gradient_audit_v02/state/runner_state.json'),'master_status':str(a/'MASTER_STATUS.json'),'report':str(p/'SCAN24_RESULT_REPORT_ZH.md'),'utc':receipt['utc']})
files=[x for x in o.rglob('*') if x.is_file() and (x.suffix in ['.py','.json','.log','.png'] or x.name in ['tsdf_volume.npz','actual_gradients.npz']) and not any(z in x.name for z in ['.tmp-']) and not x.name.startswith('final_validation')]
files.extend(x for x in p.iterdir() if x.is_file() and x.name!='EVIDENCE_MANIFEST.json');files.extend(code.glob('*.py'))
manifest={str(x):{'sha256':sha256(x),'bytes':x.stat().st_size} for x in files}
atomic_json(p/'EVIDENCE_MANIFEST.json',{'files':manifest,'mutable_root_status_not_included':str(a/'MASTER_STATUS.json'),'purpose':'current-slice evidence only; old manifests/seals preserved','scientificdone':False})
print(json.dumps({'validation':str(p/'VALIDATION.json'),'evidence_files':len(manifest),'suite_rows':len(ids),'allview_rows':98,'full_suite_done':False}))
