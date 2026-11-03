"""BUILD only: frozen inputs/config; never executes numerical scene code."""
from pathlib import Path
import json,hashlib,argparse
S=Path(__file__).resolve().parent
O=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_global_association_v06_20261101');PREV=O/'units/unit_002'
def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for block in iter(lambda:f.read(2**20),b''):h.update(block)
 return h.hexdigest()
def prepare(u):
 u=Path(u);assert u==O/'units/unit_003';assert not (u/'RUN_REQUEST.json').exists(),'ALREADY_FROZEN'
 expected='d32eb66790e729d8e8a3203dad8e08fc3979a7682ff6791cffcfa2d970afa6f1';assert sha(PREV/'CONFIG.json')==expected
 c=json.loads((PREV/'CONFIG.json').read_text());decision=json.loads((u/'DECISION.json').read_text());frozen=json.loads((PREV/'PARENT_RUN_FROZEN.json').read_text())
 for p,h in c['input_files'].items():assert sha(p)==h,'INPUT_HASH_MISMATCH '+p
 for p,h in c['helper_files'].items():assert sha(p)==h,'HELPER_HASH_MISMATCH '+p
 for p,snap in frozen['immutable_source_snapshot'].items():assert sha(snap)==frozen['source_files'][p],'SNAPSHOT_HASH_MISMATCH '+snap
 for name in ('port_paths.py','geometry_base.py','adapter.py','delivery.py','paired_delivery.py','runtime_io.py'):assert sha(S/name)==sha(PREV/'source_snapshot'/name),'PINNED_CORE_CHANGED '+name
 refs=[PREV/'CONFIG.json',PREV/'PARENT_RUN_FROZEN.json',PREV/'PARENT_SEAL.json']+[Path(p) for p in frozen['immutable_source_snapshot'].values()]
 for arm in ('greedy','joint'):
  out=PREV/'scenes/scan24/stages'/arm;cp=json.loads((out/'CHECKPOINT.json').read_text());assert cp['complete'] and cp['config_sha256']==expected
  refs.append(out/'CHECKPOINT.json')
  for name,h in cp['files'].items():assert sha(out/name)==h;refs.append(out/name)
 for p in refs:c['input_files'][str(p)]=sha(p)
 for k in ('prior_scope','prior_links'):c.pop(k,None)
 c.update(unit=str(u),output=str(u),decision_path=str(u/'DECISION.json'),decision_sha256=sha(u/'DECISION.json'),scientific_decision=decision['recommended_next_step'],changed_variable=decision['changed_variable'],falsification=decision['falsification'],previous_config_sha256=expected,previous_arms={a:str(PREV/'scenes/scan24/stages'/a) for a in ('greedy','joint')},expected_ambiguity_components=73,expected_scope_audit=dict(full_endpoint_components=1252,overlap_free_components=292,overlap_free_edges=459,overlap_free_masked=195),expected_successful_overlap=5452,expected_candidate_records=112414,reference_groups=[53254,201906,10975])
 c['implementation_details']=dict(selection='Full successful endpoint closure, include masked edges first; any incident successful overlap vetoes whole component; complete incident evidence halo',certificate=dict(delta='F_star-F_without_e',threshold='0.15*max(2-cost,1e-8)+1e-8',strict=True,required_status='optimal or exact empty graph',scope='full component, no physical-confidence claim'),fallback='Both arms retain exact unit002 component on any incomplete proof',outside='unit002 memberships and existing composite versions retained',new_versions='start above maximum predecessor/composite version; separate disjoint arm ranges',numerical_core='unit002 unchanged',threshold_sweeps=False)
 c['source_files']={str(p):sha(p) for p in sorted(S.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
 (u/'CONFIG.draft.json').write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n')
 (u/'INPUT_HASH_RECEIPT.json').write_text(json.dumps(dict(input_files=c['input_files'],helpers=c['helper_files'],snapshot_verified=True,original_core_byte_identical=True,full_science_run=False),indent=2)+'\n')
 print(json.dumps(dict(draft=str(u/'CONFIG.draft.json'),input_files=len(c['input_files']),source_files=len(c['source_files']),decision_sha256=c['decision_sha256'])))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--unit',required=True);args=p.parse_args();prepare(args.unit)
