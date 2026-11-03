"""Unit012 metadata-only binding/freezing. Never loads original numerical arrays."""
from pathlib import Path
import json,copy,hashlib,datetime
S=Path(__file__).resolve().parent
O=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_frontier_growth_v08_20261102');P=O/'units/unit_011';U=O/'units/unit_012'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,obj):
 with Path(p).open('x') as f:json.dump(obj,f,ensure_ascii=False,indent=2,allow_nan=False)
prior='bde0a0525512038517f69cdb7bf0773d5dca11d68a14192d7f4332fdab87dab4';startbinding='f4f8cabd201ccf58c6b4c8ef0545ef23b6b2d269e341b811c6d994e5cb68e88f'
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
initial=P/'scenes/ficus/stages/NO_FURTHER_GROWTH';cp=bind(initial,startbinding)
assert cp['files']['MEMBERSHIP.npz']=='2db5ef645c13d6d39dd0e6001552de2c7d6b69e6fd65c545d184b89ca6a2f5ca'
assert cp['files']['GROWTH_STATE.json']=='f690181aa95d31922e67ba784d601277c1b6e3546fbc5bc855e3418cce49ab25'
st=read(initial/'GROWTH_STATE.json');assert len(st['chains'])==24 and len(st['events'])==4 and st['next_version']==20584
assert sorted(map(int,st['chains']))==sorted(x[0] for x in c['seeds'])
bind(P/'scenes/ficus/observation_bank',prior)
replays=[]
for sid in sorted(map(int,st['chains'])):
 for side in (0,1):
  path=P/'scenes/ficus/initial_libraries'/f'REPAIR_{sid}_{side}.json';assert path.exists();inputs[str(path)]=sha(path);replays.append(str(path))
controls={}
for arm,old in [('BASE','REPAIR_BASE'),('PAIRED','REPAIR_PAIRED')]:
 root=P/'scenes/ficus/stages'/(old+'_FINAL');bind(root,prior);controls[arm]=dict(stage=str(root),config_sha256=prior)
for arm in c['arms']:
 path=P/'scenes/ficus/stages'/(arm+'_FINAL')/'MEMBERSHIP.npz';inputs[str(path)]=sha(path);c['external_memberships']['unit011_'+arm]=str(path)
v07=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_free_reassignment_v07_20261101/units/unit_006')
assert sha(v07/'CONFIG.json')=='6ef789ee86b78f1e339b399ce390ebaace322ac7aefa1e1a158d97bf89aa8843';inputs[str(v07/'CONFIG.json')]=sha(v07/'CONFIG.json')
image_root=Path('/home/u00134/cglib/data/full/ficus');images={'test_r_1':str(image_root/'val/r_1.png'),'test_r_79':str(image_root/'val/r_79.png')};calibration=str(image_root/'transforms_val.json')
for path,h in [(images['test_r_1'],'294de4156912ffbd4c80d3a8404eea4661f54da44a0586b453e7c8ce4ad128cf'),(images['test_r_79'],'b6dfd1eafdbb0b9eb4aa416c70bfe09c5853c8e576b6d5599762bc5d977896e9'),(calibration,'0d12d088ff4fb586740e939dff6bc77db7c4aadfacd2f75867965e6786b32990')]:
 assert sha(path)==h;assert read(v07/'CONFIG.json')['input_files'][path]==h;inputs[path]=h
helper=v07/'source_snapshot/image_path_core.py';inputs[str(helper)]=sha(helper)
c.update(unit_root=str(U),runtime_root=str(O),unit=str(U),runtime=str(O),decision_path=str(U/'DECISION.json'),decision_sha256=sha(U/'DECISION.json'),scientific_contract=read(U/'DECISION.json'),initial_stage=str(initial),initial_assigned=122019,initial_next_version=20584,prior_config_sha256=startbinding,prior_observation_config_sha256=prior,source_predecessor_config_sha256=prior,prior_observation_bank=str(P/'scenes/ficus/observation_bank'),observation_bank=str(U/'scenes/ficus/observation_bank'),absolute_deadline_jst=window['science_wrap_jst'],max_seconds=1800,replay_libraries=replays,control_reproductions=controls,arms=['BASE','PAIRED','IMAGE_CHAIN'],image_inputs=images,image_calibration=calibration)
c['cohort_policy']['selection']='exact24 saved unit011 NO_FURTHER_GROWTH chains; no reselection'
c['switch']['initial_state']='exact unit011 NO_FURTHER_GROWTH; no initial relabel or version allocation'
c['settings']['initialization_membership_invariant']='all fields exact against unit011 NO_FURTHER_GROWTH'
c['settings']['model_fitting_scope']='unchanged unit011 REPAIR geometry in all three arms; one bounded two-handle call per eligible proposal'
c['seam'].update(representations=['REPAIR'],representation_shadows='same REPAIR library with BASE/PAIRED/IMAGE_CHAIN choices',initial_catalog='all48 common frontier libraries and complete image evidence before promotion; incomplete catalog blocks promotion')
c['history_evidence']['policies']=['BASE','PAIRED_HISTORY','IMAGE_CHAIN'];c['contact']['policies']=['ARC']
c['control_replay_policy']=dict(saved_visits=replays,from_state='NO_FURTHER_GROWTH',reexecute_full_controls=True,control_reproductions=controls,comparison='all membership fields,chains,curves,versions,next_version,events,used,metrics,ports exact; only elapsed_seconds wallclock diagnostics excluded',mismatch='block comparison')
c['image_chain']=dict(images=images,calibration=calibration,camera_binding=c['cameras'],image_size=[800,800],calibration_atol=1e-8,original_c2w_gl_exact=True,white_composite=True,luminance=[.2126,.7152,.0722],gaussian_sigma=1.,boundary='reflect',gradient='Sobel/8',gradient_min=.1,source_frontier_projection='finite-Q lowest-segment tie',arc_window_p=[-2.,2.],retain_all_knots_and_anchors=True,minimum_each_projected_half_px=2.,invalid_projection='UNKNOWN',pixel_radius=2.,unsigned_tangent_deg=30.,all_pixels=True,graph='complete8-neighbor, projected arclength nondecreasing within EPS',eps=1e-8,start='anchor distance<=2px and arc<=1px',middle='middle-anchor distance<=2px',end='anchor distance<=2px and arc>=total-1px',minimum_distinct_pixels=3,search='Dijkstra Euclidean pixel-step; row-major node/predecessor ties',both_views_required=True,negative_evidence='abstain, not cannot-link',save_full_graph=True,visibility_verified=False,held_out=False,old_producer_executed=False)
c['visual_policy'].update(all_four_arms=False,all_three_arms=True,real_image_evidence_separate_from_original_kernel_ink=True)
c['budgets'].update(total_seconds=1800,growth_stop_seconds=1200,delivery_reserved_seconds=600,readiness_seconds=120,optimizer_seconds=200,max_new_attempts_per_arm=64,max_new_accepts_per_seed=8)
c['source_provenance']['unit011_snapshot']=snapshots;c['input_files']=inputs
assert c['absolute_deadline_jst']=='2026-11-02T07:38:00+09:00'
for k,v in dict(legacy_groups_locked=False,kernel_geometry_frozen=True,final_ink_carrier='original_gaussians',uses_gpu=False,uses_training=False,accepted_merge_is_ground_truth=False).items():assert c[k]==v
for path,h in c['helper_files'].items():assert sha(path)==h
for path,h in inputs.items():assert sha(path)==h,('INPUT_BINDING',path)
t=U/'tests';red=read(t/'RED_EXIT.json');green=read(t/'FINAL_TEST_EXIT.json');cli=read(t/'CLI_HELP_EXIT.json')
assert red['returncode']==1 and green['returncode']==0 and cli['returncode']==0
assert 'AssertionError: Lists differ: [0, 1, 2] != []' in (t/'RED.log').read_text()
assert (t/'GREEN_FINAL.log').read_text().rstrip().endswith('OK')
receipt=dict(returncode=0,tdd_status='GENUINE_FUNCTIONAL_RED_GREEN: disconnected anchor hits falsely passed before ordered graph search; complete ordered path implementation rejects them. Explicit small regression suite includes real calibration and real loader phase callbacks, three-arm full-row checkpoints and exact control reproduction before renderer access, actual repeated image-gated geometry transactions and rollback.',red=dict(red,log=str(t/'RED.log'),sha256=sha(t/'RED.log'),baseline_source=str(t/'RED_image_chain_core.py'),baseline_source_sha256=sha(t/'RED_image_chain_core.py')),green=dict(green,log=str(t/'GREEN_FINAL.log'),sha256=sha(t/'GREEN_FINAL.log')),cli_help=dict(cli,log=str(t/'CLI_HELP.log'),sha256=sha(t/'CLI_HELP.log')),earlier_logs=[dict(path=str(p),sha256=sha(p)) for p in sorted(t.glob('*.log')) if p.name not in ['GREEN_FINAL.log','RED.log','CLI_HELP.log']],real_loader_callback_test=True,real_runner_fixture_kernels=48,full_asset_science_run=False,render_run=False,test_scope='explicit classes; all outputs unit012; no historical discovery',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
write(U/'TESTS_RECEIPT.json',receipt)
c['source_files']={str(p):sha(p) for p in sorted(S.rglob('*')) if p.is_file() and '__pycache__' not in p.parts};write(U/'CONFIG.json',c)
py=window['python'];script=str(S/'image_chain_runner.py');request=dict(script=script,config_path=str(U/'CONFIG.json'),config_sha256=sha(U/'CONFIG.json'),source_files=c['source_files'],helper_files=c['helper_files'],max_seconds=1800,tests_receipt=str(U/'TESTS_RECEIPT.json'),python=py,command=[py,'-B',script,'--config',str(U/'CONFIG.json')]);write(U/'RUN_REQUEST.json',request)
print(json.dumps(dict(status='FROZEN',request=str(U/'RUN_REQUEST.json'),config_sha256=request['config_sha256'],decision_sha256=c['decision_sha256'],source_files=len(c['source_files']),input_files=len(inputs),helper_files=len(c['helper_files']))))
