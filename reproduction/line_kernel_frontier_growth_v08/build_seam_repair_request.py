"""Unit011 metadata-only freeze: no science, asset arrays, or renderer execution."""
from pathlib import Path
import json,copy,hashlib,datetime
S=Path(__file__).resolve().parent
O=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_frontier_growth_v08_20261102');P=O/'units/unit_010';U=O/'units/unit_011'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,obj):
 with Path(p).open('x') as f:json.dump(obj,f,ensure_ascii=False,indent=2,allow_nan=False)
prior='f4f8cabd201ccf58c6b4c8ef0545ef23b6b2d269e341b811c6d994e5cb68e88f'
assert sha(P/'CONFIG.json')==prior
c=copy.deepcopy(read(P/'CONFIG.json'));frozen=read(P/'PARENT_RUN_FROZEN.json');assert frozen['config_sha256']==prior
window=read(O/'orchestration/WINDOW.json');inputs=dict(c['input_files']);snapshots={}
for original,path in frozen['immutable_source_snapshot'].items():
 h=frozen['source_files'][original];assert sha(path)==h;assert sha(S/Path(path).name)==h,'Inherited source changed'
 inputs[path]=h;snapshots[Path(path).name]=dict(path=path,sha256=h)
for name in ['CONFIG.json','DECISION.json','PARENT_RUN_FROZEN.json','FAILURE_ANALYSIS.json','NEXT.json']:
 path=P/name;inputs[str(path)]=sha(path)
def bind(root,binding):
 cp=read(root/'CHECKPOINT.json');assert cp['complete'] and cp['config_sha256']==binding;inputs[str(root/'CHECKPOINT.json')]=sha(root/'CHECKPOINT.json')
 for name,h in cp['files'].items():assert sha(root/name)==h;inputs[str(root/name)]=h
 return cp
initial=P/'scenes/ficus/stages/PAIRED_HISTORY_FINAL';cp=bind(initial,prior)
assert cp['files']['MEMBERSHIP.npz']=='2db5ef645c13d6d39dd0e6001552de2c7d6b69e6fd65c545d184b89ca6a2f5ca'
assert cp['files']['GROWTH_STATE.json']=='f690181aa95d31922e67ba784d601277c1b6e3546fbc5bc855e3418cce49ab25'
st=read(initial/'GROWTH_STATE.json');assert len(st['chains'])==24 and len(st['events'])==4 and st['next_version']==20584
assert sorted(map(int,st['chains']))==sorted(x[0] for x in c['seeds'])
bind(P/'scenes/ficus/observation_bank',prior)
replays=[]
for v in ('0048','0049'):
 path=P/'scenes/ficus/visits/PAIRED_HISTORY'/f'{v}.json';z=read(path);assert z['version']==st['versions'][str(z['seed'])];inputs[str(path)]=sha(path);replays.append(str(path))
for arm in c['arms']:
 path=P/'scenes/ficus/stages'/(arm+'_FINAL')/'MEMBERSHIP.npz';inputs[str(path)]=sha(path);c['external_memberships']['unit010_'+arm]=str(path)
focus=sorted(set(c['focus_carriers'])|{79841,79855,177351,79865})
c.update(unit_root=str(U),runtime_root=str(O),unit=str(U),runtime=str(O),decision_path=str(U/'DECISION.json'),decision_sha256=sha(U/'DECISION.json'),scientific_contract=read(U/'DECISION.json'),initial_stage=str(initial),initial_assigned=122019,initial_next_version=20584,prior_config_sha256=prior,prior_observation_config_sha256=prior,source_predecessor_config_sha256=prior,prior_observation_bank=str(P/'scenes/ficus/observation_bank'),observation_bank=str(U/'scenes/ficus/observation_bank'),absolute_deadline_jst=window['science_wrap_jst'],max_seconds=1800,replay_libraries=replays,arms=['FIXED_BASE','FIXED_PAIRED','REPAIR_BASE','REPAIR_PAIRED'],focus_carriers=focus)
c.pop('control_reproductions',None)
c['cohort_policy']['selection']='exact24 saved unit010 PAIRED_HISTORY_FINAL chains; no reselection'
c['switch']['initial_state']='exact unit010 PAIRED_HISTORY_FINAL; no initial relabel or version allocation'
c['settings']['initialization_membership_invariant']='all fields exact against unit010 PAIRED_HISTORY_FINAL'
c['settings']['model_fitting']=True
c['settings']['model_fitting_scope']='REPAIR only: one bounded two-handle call after fixed whole_member_residual_tangent failure; all other geometry unchanged'
c['settings']['whole_path_geometry']='unchanged ARC/Hermite guards; only eligible residual/tangent-failing seams gain bounded two-handle repair'
c['seam'].update(representations=['FIXED','REPAIR'],representation_shadows='both representation libraries with BASE/PAIRED choices at each state',initial_catalog='all96 FIXED/REPAIR frontier libraries frozen before any promotion; incomplete catalog blocks promotion')
c['seam']['model_fitting']=True
c['seam']['bezier_controls']='FIXED uses D/3; eligible REPAIR uses alpha*D and beta*D within [1/6,1/2]; see seam_repair'
c['history_evidence']['policies']=['BASE','PAIRED_HISTORY'];c['contact']['policies']=['ARC']
c['seam_repair']=dict(eligible_relation='overlap',registration_required='ok',first_failure_required='whole_member_residual_tangent',unchanged=['already-valid seams','all other first-failure reasons','endpoint relays','original prefix/tail'],a='LA-min(2,LA)',b='s+min(2,LB-s)',handles=['P0+alpha*D*t0','P3-beta*D*t1'],bounds=[1/6,1/2],initial=[1/3,1/3],segments='max(1,ceil(12*max control-edge length))',max_segments=128,solver='scipy.optimize.least_squares',method='trf',jac='2-point',diff_step=1e-4,ftol=1e-8,xtol=1e-8,gtol=1e-8,max_nfev=64,max_actual_residual_evaluations=256,max_seconds_per_call=5.,max_optimizer_seconds=200.,objective='mean(distance_p^2+0.25*(unsigned_angle_deg/30)^2)+1e-4*sum((handles-1/3)^2)',all_distinct_members=True,max_members=8192,restarts=0,alternate_offsets=False,failed_convergence='reject',final_q_all_original_guards=True,identical_proposal_fit_cache='exact bytes of A,B,s,all member means/tangents/row IDs; one solver call per identical proposal',diagnostics=['original rejection','per-row distance/angle/segment/arc/region witnesses','solver actual evaluations/time/status','final guard reason'],total_timeout='incomplete frontier cannot promote')
c['control_replay_policy']=dict(saved_visits=replays,from_state='PAIRED_HISTORY_FINAL',expected_old_shadow_policies=['BASE','OBS_HISTORY','PAIRED_HISTORY'],reexecute_full_controls=False,mismatch='block comparison')
c['visual_policy'].update(focus_carriers=focus,all_four_arms=True,all_three_arms=False,preserve_later_deadends=[50407,83549,79865],inherited_seeds_and_negatives=True)
c['budgets'].update(total_seconds=1800,growth_stop_seconds=1200,delivery_reserved_seconds=600,readiness_seconds=120,optimizer_seconds=200,max_new_attempts_per_arm=64,max_new_accepts_per_seed=8)
c['source_provenance']['unit010_snapshot']=snapshots;c['input_files']=inputs
assert c['absolute_deadline_jst']=='2026-11-02T07:38:00+09:00'
for k,v in dict(legacy_groups_locked=False,kernel_geometry_frozen=True,final_ink_carrier='original_gaussians',uses_gpu=False,uses_training=False,accepted_merge_is_ground_truth=False).items():assert c[k]==v
for path,h in c['helper_files'].items():assert sha(path)==h
for path,h in inputs.items():assert sha(path)==h,('INPUT_BINDING',path)
t=U/'tests';red=read(t/'RED_EXIT.json');green=read(t/'FINAL_TEST_EXIT.json');cli=read(t/'CLI_HELP_EXIT.json')
assert red['returncode']==1 and green['returncode']==0 and cli['returncode']==0
assert 'AssertionError: 0 not greater than 0' in (t/'RED.log').read_text()
assert (t/'GREEN_FINAL.log').read_text().rstrip().endswith('OK')
receipt=dict(returncode=0,tdd_status='GENUINE_FUNCTIONAL_RED_GREEN: fixed handles fail the member-informed optimization fixture; bounded all-member least-squares passes. Explicit isolated regression suite tests real loader/phase propagation, four-arm checkpoints before rendering, repair scope, bounds, all members, convergence/evaluation limits, unchanged outer geometry and rollback.',red=dict(red,log=str(t/'RED.log'),sha256=sha(t/'RED.log'),baseline_source=str(t/'RED_seam_repair_core.py'),baseline_source_sha256=sha(t/'RED_seam_repair_core.py')),green=dict(green,log=str(t/'GREEN_FINAL.log'),sha256=sha(t/'GREEN_FINAL.log')),cli_help=dict(cli,log=str(t/'CLI_HELP.log'),sha256=sha(t/'CLI_HELP.log')),earlier_logs=[dict(path=str(p),sha256=sha(p)) for p in sorted(t.glob('*.log')) if p.name not in ['GREEN_FINAL.log','RED.log','CLI_HELP.log']],real_loader_callback_test=True,real_runner_fixture_kernels=48,full_asset_science_run=False,render_run=False,test_scope='explicit classes; all outputs unit011; no historical discovery',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
write(U/'TESTS_RECEIPT.json',receipt)
c['source_files']={str(p):sha(p) for p in sorted(S.rglob('*')) if p.is_file() and '__pycache__' not in p.parts};write(U/'CONFIG.json',c)
py=window['python'];script=str(S/'seam_repair_runner.py');request=dict(script=script,config_path=str(U/'CONFIG.json'),config_sha256=sha(U/'CONFIG.json'),source_files=c['source_files'],helper_files=c['helper_files'],max_seconds=1800,tests_receipt=str(U/'TESTS_RECEIPT.json'),python=py,command=[py,'-B',script,'--config',str(U/'CONFIG.json')]);write(U/'RUN_REQUEST.json',request)
print(json.dumps(dict(status='FROZEN',request=str(U/'RUN_REQUEST.json'),config_sha256=request['config_sha256'],decision_sha256=c['decision_sha256'],source_files=len(c['source_files']),input_files=len(inputs),helper_files=len(c['helper_files']))))
