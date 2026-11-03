"""Unit007 BUILD-only metadata binding; never loads scientific arrays."""
from pathlib import Path
import json,hashlib,argparse
S=Path(__file__).resolve().parent
O=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_global_association_v06_20261101');PREV=O/'units/unit_006'
def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(2**20),b''):h.update(b)
 return h.hexdigest()
def prepare(u):
 u=Path(u);assert u==O/'units/unit_007' and not (u/'RUN_REQUEST.json').exists()
 expected='bcb3d5e7bf64493888bbf6b29ccbc27d5cdd6d87f52d4ec4258b3764b9f3fbdf';assert sha(PREV/'CONFIG.json')==expected
 c=json.loads((PREV/'CONFIG.json').read_text());decision=json.loads((u/'DECISION.json').read_text());f=json.loads((PREV/'PARENT_RUN_FROZEN.json').read_text())
 for p,h in c['input_files'].items():assert sha(p)==h,'INPUT_HASH '+p
 for p,h in c['helper_files'].items():assert sha(p)==h,'HELPER_HASH '+p
 for old,snap in f['immutable_source_snapshot'].items():
  assert sha(snap)==f['source_files'][old];assert sha(S/Path(old).name)==sha(snap),'OLD_SOURCE_CHANGED '+old
 refs=[PREV/'CONFIG.json',PREV/'PARENT_RUN_FROZEN.json']+[Path(p) for p in f['immutable_source_snapshot'].values()]
 for sub in ['readiness','models','banks','stages/greedy','stages/joint']:
  for cp in sorted((PREV/'scenes/scan24'/sub).rglob('CHECKPOINT.json')):
   rec=json.loads(cp.read_text());assert rec['complete'] and rec['config_sha256']==expected;refs.append(cp)
   for name,h in rec['files'].items():assert sha(cp.parent/name)==h;refs.append(cp.parent/name)
 refs.append(PREV/'scenes/scan24/diagnostics/SELECTION.json')
 for p in refs:c['input_files'][str(p)]=sha(p)
 c.update(unit=str(u),output=str(u),decision_path=str(u/'DECISION.json'),decision_sha256=sha(u/'DECISION.json'),scientific_decision=decision['recommended_next_step'],changed_variable=decision['changed_variable'],falsification=decision['falsification'],prior_unit=str(PREV),previous_config_sha256=expected,previous_arms={a:str(PREV/'scenes/scan24/stages'/a) for a in ('greedy','joint')},prior_selection=str(PREV/'scenes/scan24/readiness/SELECTION.json'),prior_diagnostics=str(PREV/'scenes/scan24/diagnostics/SELECTION.json'),control_contexts=8,expected_control_hypotheses=32,expected_all_components=1917,max_components=1917,expected_contexts=1917,expected_old_hypotheses=11,expected_selected_pairs=38,fixed_member_ids=[51111,51166,113545],max_seconds=1800,absolute_deadline_jst='2026-11-01T09:38:00+09:00')
 c['fit_source']=str(S/'pinned_v05_fit_core.py');assert sha(c['fit_source'])=='c1565d2c33ee1f75e1a58469f14d8e153a138eb5f3c0dc73fbbcc5a9ab20e512'
 c['model_fit']=dict(enabled=True,maximum_attempts=5414,reuse_models=38,source=c['fit_source'],metric_rtol=0,metric_atol=1e-10,no_retry=True,new_spatial_candidates=False)
 c['implementation_details'].update(scope='all1917 successful overlap components; same ranking; cap128 whole component, no trimming',old_bank='unit00632 hypotheses/selectors/full membership/version replay; unit004 original11 unchanged',new_model_library='original leaf anchors plus one recovered model per saved successful pair; any metric mismatch blocks entire component',fallback='unprocessed/oversized/new blocked components retain M4; old8 control identities/versions remain exact',diagnostics='member-set changes take precedence over model key; fixed51111/51166/113545 and four negatives; identical rows M4/unit006/greedy/joint',resume='only complete config-hash checkpoints; interrupted attempts saved and never silently retried')
 c['new_candidate_generation']=False;c['source_files']={str(p):sha(p) for p in sorted(S.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
 (u/'CONFIG.draft.json').write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n')
 (u/'INPUT_HASH_RECEIPT.json').write_text(json.dumps(dict(input_files_verified=len(c['input_files']),helper_files=c['helper_files'],snapshot_files_verified=len(f['source_files']),prior_source_unchanged=True,full_asset_science_run=False),indent=2)+'\n')
 print(json.dumps(dict(config_draft=str(u/'CONFIG.draft.json'),decision_sha256=c['decision_sha256'],source_files=len(c['source_files']),input_files=len(c['input_files']))))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--unit',required=True);a=p.parse_args();prepare(a.unit)
