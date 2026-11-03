"""Unit008 BUILD metadata only; never loads an original Gaussian array."""
from pathlib import Path
import json,hashlib,argparse,datetime
S=Path(__file__).resolve().parent
O=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_global_association_v06_20261101')
OLD=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_edge_growth_v05_20261031/units')
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(2**20),b''):h.update(b)
 return h.hexdigest()
def prepare(unit):
 u=Path(unit);assert u==O/'units/unit_008';assert not (u/'RUN_REQUEST.json').exists()
 prior=O/'units/unit_007';assert sha(prior/'CONFIG.json')=='7bf5b9819a1f380d715baa4f990fe4abbf268799838287a56aaf6986242212f3'
 base=json.loads((prior/'CONFIG.json').read_text());frozen=json.loads((prior/'PARENT_RUN_FROZEN.json').read_text())
 for old,snap in frozen['immutable_source_snapshot'].items():
  assert sha(snap)==frozen['source_files'][old];assert sha(S/Path(old).name)==sha(snap),'PINNED_UNIT007_SOURCE_CHANGED'
 prev=OLD/'unit_016';producer=OLD/'unit_019';old=json.loads((producer/'CONFIG.json').read_text());pc=json.loads((prev/'CONFIG.json').read_text())
 assert sha(prev/'CONFIG.json')=='4cd1846f2b8aa17405e3e2f9270a5e723358daf538163355f941d97a8c5deeec'
 assert sha(producer/'CONFIG.json')=='9bff7e59af8c3cee6a40790a5ec1c6aea4039bfd9463815e34440b33ad01ff81'
 c={k:base[k] for k in ['runtime','solver','stage_budgets','resource_limits','implementation_details','decision_carrier_cap','helper_files','renderer','libroot']}
 decision=json.loads((u/'DECISION.json').read_text());window=json.loads((O/'orchestration/WINDOW.json').read_text())
 c.update(unit=str(u),output=str(u),scene='ficus',kernel_count=285956,p=old['p'],decision_path=str(u/'DECISION.json'),decision_sha256=sha(u/'DECISION.json'),scientific_decision=decision['recommended_next_step'],changed_variable=decision['changed_variable'],falsification=decision['falsification'],max_seconds=1800,absolute_deadline_jst=window['science_wrap_jst'],no_new_after_jst=window['no_new_after_jst'])
 assert c['p']==0.003530473547030632
 for k in ['gaussians','controls','representatives','cameras','views']:c[k]=old[k]
 c.update(state=old['previous_state'],predecessor_checkpoint=old['previous_checkpoint'],predecessor_config=str(prev/'CONFIG.json'),predecessor_config_sha256=sha(prev/'CONFIG.json'),membership=old['previous_membership'],carriers=old['previous_carriers'])
 state=producer/'scenes/ficus/states/M5';stage=producer/'scenes/ficus/stages/M5_MERGE_ONLY'
 c.update(ordered_candidates=str(state/'ORDERED_CANDIDATES.npz'),candidate_status=str(state/'controls/joint/CANDIDATE_STATUS.npz'),ambiguity=str(state/'JOINT_AMBIGUITY.npz'),candidate_metrics=str(state/'controls/joint/METRICS.json'),reference_membership=str(stage/'MEMBERSHIP.npz'),reference_groups_path=str(stage/'GROUPS.json'))
 c.update(expected_candidate_records=89486,expected_successful_overlap=1141,expected_all_components=628,expected_decision_leaves=1716,expected_max_component=9,max_components=628,overlap_priority_ids=[64355,65064,112780,116525],fixed_member_ids=[64355,65064,112780,116525],reference_leaf_sets=[[64355,65064],[112780,116525]],negative_pairs=[[11,80709],[16931,18768],[112,205435],[33117,201172]],control_contexts=0,previous_arms={},historical_same_method_control=False,new_candidate_generation=False)
 c['fit_source']=str(S/'pinned_v05_fit_core.py');assert sha(c['fit_source'])=='c1565d2c33ee1f75e1a58469f14d8e153a138eb5f3c0dc73fbbcc5a9ab20e512'
 c['model_fit']=dict(enabled=True,maximum_attempts=1141,reuse_models=0,source=c['fit_source'],metric_rtol=0,metric_atol=1e-10,no_retry=True,new_spatial_candidates=False)
 c['implementation_details'].update(old_bank='fresh ficus anchors; no scan24 hypotheses/models reused',scope='all628 complete saved-overlap components; cap128 without trimming',fallback='whole incomplete/oversized/mismatched components retain M4 in both arms',diagnostics='actual member changes and arm differences, fixed ficus references and saved negative pairs; identical rows M4/greedy/joint',control='same-bank greedy versus MILP; M4 no-new-association reference; sealed M5 and scan24 only external references')
 inputs={}
 def add(p,expected=None):
  p=Path(p);h=sha(p)
  if expected is not None:assert h==expected,'INPUT_HASH '+str(p)
  inputs[str(p)]=h
 def cp(path):
  path=Path(path);d=json.loads(path.read_text());assert d['complete'];add(path)
  for name,h in d['files'].items():add(path.parent/name,h)
 for path in [prior/'CONFIG.json',prior/'PARENT_RUN_FROZEN.json',prev/'CONFIG.json',producer/'CONFIG.json',Path(pc['decision_path']),Path(old['decision_path']),producer/'PARENT_RUN_FROZEN.json',producer/'source_snapshot/core.py']:add(path)
 for oldpath,snap in frozen['immutable_source_snapshot'].items():add(snap,frozen['source_files'][oldpath])
 for k in ['gaussians','controls','representatives','cameras','state','membership','carriers']:
  path=c[k];add(path,old['input_files'][path])
 add(c['state'],'7d1457b144b0c58b8a3fe1fd1f1620e967158c1ace8326c64e6d996671378900')
 add(c['predecessor_checkpoint'],'e88c59049615d52df0a42b6780f3e2595a0204038eb7145e7c81e5cc25466b83')
 cp(c['predecessor_checkpoint']);cp(Path(c['membership']).parent/'CHECKPOINT.json');cp(state/'CHECKPOINT.json');cp(state/'controls/joint/STATS_CHECKPOINT.json');cp(stage/'CHECKPOINT.json');cp(stage/'STATS_CHECKPOINT.json')
 add(c['candidate_status'],'960fe5f1a49c48cc79684e358246a5a9e34ea0f2ef6c33aa669ccd1d81eaa8a8')
 for k in ['ordered_candidates','ambiguity','candidate_metrics','reference_membership','reference_groups_path']:add(c[k])
 for p,h in c['helper_files'].items():assert sha(p)==h
 c['input_files']=inputs;c['source_files']={str(p):sha(p) for p in sorted(S.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
 (u/'CONFIG.draft.json').write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n')
 (u/'INPUT_HASH_RECEIPT.json').write_text(json.dumps(dict(input_files_verified=len(inputs),pinned_snapshot_files_verified=len(frozen['source_files']),prior_source_unchanged=True,helper_files=c['helper_files'],full_asset_numerical_run=False,created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()),indent=2)+'\n')
 print(json.dumps(dict(config=str(u/'CONFIG.draft.json'),source_files=len(c['source_files']),input_files=len(inputs),decision_sha256=c['decision_sha256'])))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--unit',required=True);a=p.parse_args();prepare(a.unit)
