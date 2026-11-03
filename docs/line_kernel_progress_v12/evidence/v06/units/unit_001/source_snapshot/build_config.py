"""BUILD metadata preparation only: hashes/config draft. Never executes scene science."""
from pathlib import Path
import json,hashlib,datetime
S=Path(__file__).resolve().parent
U=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_global_association_v06_20261101/units/unit_001')
O=U.parent.parent
OLD=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_edge_growth_v05_20261031/units')
def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(2**20),b''):h.update(b)
 return h.hexdigest()
def prepare():
 old=json.loads((OLD/'unit_018/CONFIG.json').read_text());decision=json.loads((U/'DECISION.json').read_text());p=OLD/'unit_015';r=OLD/'unit_018';state=p/'scenes/scan24/states/M4';stages=p/'scenes/scan24/stages/M4_MERGE_ONLY';ref=r/'scenes/scan24/states/M5'
 c=dict(unit=str(U),output=str(U),runtime=str(O),scene='scan24',kernel_count=458490,p=old['p'],decision_path=str(U/'DECISION.json'),decision_sha256=sha(U/'DECISION.json'),max_seconds=1800,absolute_deadline_jst='2026-11-01T09:38:00+09:00',state=str(state/'STATE.pkl'),predecessor_checkpoint=str(state/'CHECKPOINT.json'),predecessor_config=str(p/'CONFIG.json'),membership=str(stages/'MEMBERSHIP.npz'),carriers=str(stages/'CARRIERS.npz'),ordered_candidates=str(ref/'ORDERED_CANDIDATES.npz'),candidate_status=str(ref/'controls/joint/CANDIDATE_STATUS.npz'),ambiguity=str(ref/'JOINT_AMBIGUITY.npz'),reference_membership=str(r/'scenes/scan24/stages/M5_MERGE_ONLY/MEMBERSHIP.npz'),candidate_metrics=str(ref/'controls/joint/METRICS.json'),views=['0012','0036'],seed_groups=[53254,210790],negative_pairs=[[84842,362883],[153248,377058],[153427,153430],[301451,301459]],solver=dict(per_context_seconds=120,total_seconds=600,max_cut_rounds=32,mip_rel_gap=0,threads=2,parallel=False),stage_budgets=dict(readiness_seconds=300,solver_seconds=600,mapping_deadline_elapsed_seconds=1200,delivery_reserved_seconds=600,total_seconds=1800),resource_limits=dict(cpu=2,blas=2,gpu=False,unit_bytes=2*2**30,runtime_bytes=20*2**30,root_free_bytes=2**30,hdd_free_bytes=10*2**30),scientific_decision=decision['recommended_next_step'],changed_variable=decision['changed_variable'],falsification=decision['falsification'],model_fit=False,new_candidate_generation=False)
 for k in ('gaussians','representatives','controls','cameras','renderer','libroot'):c[k]=old[k]
 helpers=json.loads((r/'RUN_REQUEST.json').read_text())['helper_files']
 # AST-isolated renderer needs exactly renderer.py plus its already-built CPU library.
 c['helper_files']={k:v for k,v in helpers.items() if k.endswith('/renderer.py') or k.endswith('/libjoint.so')}
 source_ref=r/'source_snapshot/core.py'
 files=[Path(c[k]) for k in ('state','predecessor_checkpoint','predecessor_config','membership','carriers','ordered_candidates','candidate_status','ambiguity','reference_membership','candidate_metrics','gaussians','representatives','controls','cameras')]
 files.extend([p/'DECISION.json',r/'CONFIG.json',r/'DECISION.json',p/'SEAL.json',r/'SEAL.json',source_ref,r/'PARENT_RUN_FROZEN.json',O/'orchestration/INPUT_LOCK.json',O/'orchestration/WINDOW.json'])
 cp=json.loads((state/'CHECKPOINT.json').read_text());files.extend(state/k for k in cp['files'])
 seals={str(p):json.loads((p/'SEAL.json').read_text())['files'],str(r):json.loads((r/'SEAL.json').read_text())['files']}
 frozen=old['input_files'];manifest={};auth=[]
 for f in sorted(set(files)):
  actual=sha(f);expected=None;source='current readonly metadata'
  for root,seal in seals.items():
   if f.is_relative_to(root) and str(f.relative_to(root)) in seal:expected=seal[str(f.relative_to(root))];source=root+'/SEAL.json';break
  if expected is None and str(f) in frozen:expected=frozen[str(f)];source=str(r/'CONFIG.json')
  if expected is not None:assert actual==expected,'SEALED_INPUT_MISMATCH '+str(f)
  manifest[str(f)]=actual;auth.append(dict(path=str(f),sha256=actual,authority=source))
 assert manifest[c['state']]=='4f350e3a991c98d7cf011d833be4fc5aebcce1c7d328ae69b39948b5698ec31f'
 for f,h in c['helper_files'].items():assert sha(f)==h
 c['input_files']=manifest;c['source_files']={str(f):sha(f) for f in sorted(S.rglob('*')) if f.is_file() and '__pycache__' not in f.parts}
 c['implementation_details']=dict(closure='Recursive incident-record closure equals raw undirected candidate connected component; oversized closure never pruned',contact_oracle='Exact collinear redundant knots removed only from temporary contact-check curve; all exported finite q unchanged',unknown='Saved ambiguity pairs abstain identically in both arms; existing UNKNOWN eligibility retained',no_evidence_of_physical_identity=True)
 (U/'CONFIG.draft.json').write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n')
 (U/'INPUT_HASH_RECEIPT.json').write_text(json.dumps(dict(verified=auth,helpers=c['helper_files'],full_science_run=False),indent=2)+'\n')
 print(json.dumps(dict(draft=str(U/'CONFIG.draft.json'),input_files=len(manifest),source_files=len(c['source_files']),helper_files=len(c['helper_files']),decision_sha256=c['decision_sha256'])))
if __name__=='__main__':prepare()
