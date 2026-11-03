"""BUILD-only hash/config preparation. No producers or numerical scene execution."""
from pathlib import Path
import json,hashlib,argparse
S=Path(__file__).resolve().parent
O=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_global_association_v06_20261101')
PREV=O/'units/unit_001'
def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for block in iter(lambda:f.read(2**20),b''):h.update(block)
 return h.hexdigest()
def prepare(unit):
 u=Path(unit);assert u==O/'units/unit_002';assert not (u/'RUN_REQUEST.json').exists(),'ALREADY_FROZEN'
 assert sha(PREV/'CONFIG.json')=='a15b4f24fd57bbc138cdd456ac40642ea4f58afb8459763cdaf0af509d5c7be1'
 c=json.loads((PREV/'CONFIG.json').read_text());decision=json.loads((u/'DECISION.json').read_text());frozen=json.loads((PREV/'PARENT_RUN_FROZEN.json').read_text())
 for k,h in c['input_files'].items():assert sha(k)==h,'INPUT_HASH_MISMATCH '+k
 for k,h in c['helper_files'].items():assert sha(k)==h,'HELPER_HASH_MISMATCH '+k
 for k,snapshot in frozen['immutable_source_snapshot'].items():assert sha(snapshot)==frozen['source_files'][k],'SNAPSHOT_HASH_MISMATCH '+snapshot
 for name in ('port_paths.py','geometry_base.py'):assert sha(S/name)==sha(PREV/'source_snapshot'/name),'SCIENTIFIC_CORE_CHANGED'
 prior_checkpoints=[PREV/'scenes/scan24/readiness/CHECKPOINT.json']+[PREV/'scenes/scan24/stages'/a/'CHECKPOINT.json' for a in ('greedy','joint')]
 for cp_path in prior_checkpoints:
  cp=json.loads(cp_path.read_text());assert cp['complete'] and cp['config_sha256']==sha(PREV/'CONFIG.json')
  for name,h in cp['files'].items():assert sha(cp_path.parent/name)==h,'PRIOR_CHECKPOINT_MISMATCH '+name
 c.update(unit=str(u),output=str(u),decision_path=str(u/'DECISION.json'),decision_sha256=sha(u/'DECISION.json'),scientific_decision=decision['recommended_next_step'],changed_variable=decision['changed_variable'],falsification=decision['falsification'],decision_carrier_cap=128,expected_successful_endpoints=2279,expected_eligible_endpoints=839,prior_scope=str(PREV/'scenes/scan24/readiness/SELECTION.json'),prior_links={a:str(PREV/'scenes/scan24/stages'/a/'SELECTED_LINKS.npz') for a in ('greedy','joint')})
 refs=[PREV/'CONFIG.json',PREV/'PARENT_RUN_FROZEN.json',Path(c['prior_scope'])]+prior_checkpoints+[Path(x) for x in c['prior_links'].values()]+[Path(x) for x in frozen['immutable_source_snapshot'].values()]
 for f in refs:c['input_files'][str(f)]=sha(f)
 c['source_files']={str(f):sha(f) for f in sorted(S.rglob('*')) if f.is_file() and '__pycache__' not in f.parts}
 c['implementation_details']=dict(closure='All eligible carrier components; all incident rejected/overlap/masked evidence retained one hop without recursive variable closure',dependency='Frozen PathOracle only depends on one selected path; capacity uses ports on carriers; no eligible cross-component edge',contact_oracle='Unchanged unit001',unknown='Unchanged full saved ambiguity exclusion and activation',diagnostics='Symmetric union selection; identical rows/halos; native plus paired union RGB8<254 pad16 clipped 4x nearest crops',no_evidence_of_physical_identity=True)
 c['paired_progress']='Hash-complete component link/receipt checkpoints before next component; both complete full-row mappings before rendering'
 c['prior_reference_config_sha256']=sha(PREV/'CONFIG.json')
 (u/'CONFIG.draft.json').write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n')
 (u/'INPUT_HASH_RECEIPT.json').write_text(json.dumps(dict(input_files=c['input_files'],helper_files=c['helper_files'],previous_snapshot_verified=True,science_core_byte_identical=['port_paths.py','geometry_base.py'],full_science_run=False),indent=2)+'\n')
 print(json.dumps(dict(draft=str(u/'CONFIG.draft.json'),decision_sha256=c['decision_sha256'],source_files=len(c['source_files']),input_files=len(c['input_files']),helpers=len(c['helper_files']))))
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--unit',required=True);args=parser.parse_args();prepare(args.unit)
