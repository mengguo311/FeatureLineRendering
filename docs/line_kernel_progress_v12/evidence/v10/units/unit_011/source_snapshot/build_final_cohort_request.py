"""Freeze unit011 metadata only; numerical science is parent-owned."""
from pathlib import Path
import json,hashlib,copy,subprocess,datetime
S=Path(__file__).resolve().parent
O=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_relaxed_guards_v10_20261103');U=O/'units/unit_011';P=O/'units/unit_010';F=P/'scenes/scan65/stages/BASE_J_FINAL'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def rd(p):return json.loads(Path(p).read_text())
def wr(p,d):
 with Path(p).open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2,allow_nan=False)
prior_hash='37743b427484a8af2073749e549a737a26ac26521af78d9b38ce742e76f13781'
assert sha(P/'CONFIG.json')==prior_hash
prior=rd(P/'CONFIG.json');c=copy.deepcopy(prior);freeze=rd(P/'PARENT_RUN_FROZEN.json');window=rd(O/'orchestration/WINDOW.json')
def bind(p,h=None):
 p=Path(p).resolve();v=sha(p)
 if h:assert v==h,str(p)
 c['input_files'][str(p)]=v
reused={}
for old,snap in freeze['immutable_source_snapshot'].items():
 h=freeze['source_files'][old];bind(snap,h);assert sha(S/Path(old).name)==h;reused[Path(old).name]=h
assert len(reused)==84
for n in ['CONFIG.json','PARENT_RUN_FROZEN.json','RUN_RESULT.json','FAILURE_ANALYSIS.json','NEXT.json','SAVED_OUTPUT_AUDIT.json','GEOMETRY_AUDIT.json']:bind(P/n)
cp=rd(F/'CHECKPOINT.json');assert cp['complete'] and cp['config_sha256']==prior_hash;bind(F/'CHECKPOINT.json')
for n,h in cp['files'].items():bind(F/n,h)
assert cp['files']['MEMBERSHIP.npz']=='5304129f738a33395f8b5318a1ff286876dfe508764971d7ee70452fd8ba1371'
groups=rd(F/'GROUPS.json')['groups'];versions={str(g['id']):g['version'] for g in groups};old=sorted(map(int,versions));assert len(old)==11 and versions['30579']==21779
lin=rd(F/'LINEAGE.json');assert lin['next_version']==21780 and len(lin['historical'])+len(lin['events'])==1871
folder=P/'scenes/scan65/libraries/BASE_J/0001_30579'
for p in folder.rglob('*'):
 if p.is_file():bind(p)
lib=rd(folder/'LIBRARY.json');assert lib['complete'] and lib['selected'] is None and len(lib['records'])==498 and len(lib['neighbors'])==83
ledger=O/'units/unit_009/scenes/scan65/COHORT_SELECTION.json';bind(ledger)
ex=O/'orchestration/unit_010/COMPUTE_EXIT.json';bind(ex);assert rd(ex)['actual_child_exit'] and rd(ex)['returncode']==0
active=[8765,61271];tracked=sorted(old+active)
c.update(unit_root=str(U),runtime_root=str(O/'orchestration'),unit=str(U),runtime=str(O),initial_stage=str(F),restore_stage=str(F),restore_binding=prior_hash,initial_assigned=127010,initial_unknown=152606,initial_next_version=21780,raw_seed_ids=[5558,22130,64111,156151,238627],restored_origin_ids=old,restore_seed_versions=versions,seed_ids=active,seed_versions={'8765':21440,'61271':21494},seed_expected_rows={'8765':44,'61271':71},tracked_origin_ids=tracked,arms=['BASE_J'],executed_arms=['BASE_J'],catalog_policies=['BASE_J','CONTACT_SOFT_J'],control_replay_libraries={'30579':str(folder/'LIBRARY.json')},max_seconds=780,science_deadline=window['science_wrap_jst'],absolute_deadline_jst=window['science_wrap_jst'],decision_path=str(U/'DECISION.json'),decision_sha256=sha(U/'DECISION.json'),scientific_contract=rd(U/'DECISION.json'),source_snapshot_root=str(P/'source_snapshot'),helper_files=freeze['helper_files'])
assert c['scientific_contract']['action']=='continue' and c['relaxed_rule_groups']==[2,4,6]
c['seed_policy']=dict(kind='two frozen previously eligible-unselected intact M4 objects; no reselection',ledger=str(ledger),active=active,restore_origins=old,model_labels=['line','polyline'],substantial_M3=[2,2],no_replacement=True,no_initial_version_allocation=True,old_objects_remain_whole_donors=True)
c['settings']['seed_scope']=active;c['settings']['background_reference']=str(F)
c['fixed_reference_stages']={'UNIT011_START':dict(stage=str(U/'scenes/scan65/stages/START'),binding='THIS_CONFIG_SHA256_RESOLVED_AT_RUNTIME')}
c['fixed_support_diagnostic'].update(references=c['fixed_reference_stages'],sets='thirteen START origins inherited/current/new, freeze only READY origins without replacing failed seeds')
c['budgets']=dict(readiness_seconds=60,initial_catalog_seconds=120,growth_seconds_per_arm=240,delivery_seconds=360,total_seconds=780,actual_phase_elapsed_required=True,contact_shadow_only=True,no_new_after_jst=window['no_new_after_jst'],absolute_science_deadline=window['science_wrap_jst'])
c['initial_catalog_policy']=dict(replay_old_only=str(folder/'LIBRARY.json'),expected_records=498,expected_neighbors=83,expected_selection=None,no_old_growth=True,new_complete_catalogs=active,freeze_both_scores_before_promotion=True,only_executed_policy='BASE_J',contact_and_row_fit_shadows_only=True)
c['historical_control']='NO_FURTHER_GROWTH is exact unit010 BASE_FINAL. All1871 prior events inherited. Only new8765/61271 BASE_J rollout executes. CONTACT_SOFT_J and ROW_FIT are same-state shadows, not executed matched rollouts; unit010 two bad trajectories remain archived.'
c['visual_policy'].update(seed_ids=active,arms=['BASE_J'],fixed_support='UNIT011_START all thirteen origins, not a decision gate',inherited_events=1871,matched_control=str(F),archived_bad_trajectories=str(P/'RUN_RESULT.json'))
c['external_memberships']['unit010_BASE_FINAL']=str(F/'MEMBERSHIP.npz')
c['source_provenance']=dict(latest_frozen_source=str(P/'source_snapshot'),latest_snapshot_binding=sha(P/'PARENT_RUN_FROZEN.json'),all_84_prior_files_byte_identical=True,new_modules=['final_cohort_loader.py','final_cohort_runner.py','final_cohort_delivery.py','test_final_cohort.py','build_final_cohort_request.py'],old_outputs_edited=False,numerical_core_changed=False,inherited=prior['source_provenance'])
for section in ['input_files','helper_files']:
 for p,h in c[section].items():assert sha(p)==h,(section,p)
T=U/'tests';red=rd(T/'RED_EXIT.json');green=rd(T/'GREEN_EXIT.json');assert red['returncode']==1 and green['returncode']==0
assert 'RESTORED_ORIGIN_COVERAGE' in (T/'RED.log').read_text() and 'Ran 31 tests' in (T/'GREEN.log').read_text()
cmd=[window['python'],'-B',str(S/'final_cohort_runner.py'),'--help'];r=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);(T/'CLI.log').write_text(r.stdout);assert r.returncode==0;wr(T/'CLI_EXIT.json',dict(returncode=r.returncode,command=cmd))
receipt=dict(returncode=0,test_count=31,tdd_status='GENUINE_FUNCTIONAL_RED_GREEN: actual prior loader rejected new untracked origin with RESTORED_ORIGIN_COVERAGE; new intact-origin activation passes. Thirteen-origin cold checkpoint test added after RED; 29 prior tests reused, not new TDD.',red=dict(red,log=str(T/'RED.log'),sha256=sha(T/'RED.log'),test_source=str(T/'RED_test_final_cohort.py'),test_source_sha256=sha(T/'RED_test_final_cohort.py')),green=dict(green,log=str(T/'GREEN.log'),sha256=sha(T/'GREEN.log')),cli=dict(returncode=0,command=cmd,log=str(T/'CLI.log'),sha256=sha(T/'CLI.log')),real_loader_guard_test=True,full_asset_run=False,native_render=False,scope='real36-row M4 loader, no changed rows/Q/version, 13-origin cold mapping/reference, prior strict parity/disabled guards/finite scores/>8 requery/rollback regressions')
wr(U/'SOURCE_REUSE_PROVENANCE.json',dict(parent_manifest=str(P/'PARENT_RUN_FROZEN.json'),snapshot_files_verified=84,byte_identical_existing_files=reused,old_files_edited=False));wr(U/'TESTS_RECEIPT.json',receipt)
c['source_files']={str(p):sha(p) for p in sorted(S.rglob('*')) if p.is_file() and '__pycache__' not in p.parts};assert len(c['source_files'])==89
wr(U/'CONFIG.json',c);script=str(S/'final_cohort_runner.py')
request=dict(script=script,config_path=str(U/'CONFIG.json'),config_sha256=sha(U/'CONFIG.json'),source_files=c['source_files'],helper_files=c['helper_files'],tests_receipt=str(U/'TESTS_RECEIPT.json'),max_seconds=780,python=window['python'],command=[window['python'],'-B',script,'--config',str(U/'CONFIG.json')])
wr(U/'RUN_REQUEST.json',request)
wr(U/'BUILD_INTERFACE_AUDIT.json',dict(status='READY_FOR_PARENT_COMPUTE',returncode=0,source_files=89,helpers=len(c['helper_files']),test_count=31,actual_tests_returncode=0,config_sha256=request['config_sha256'],decision_sha256=c['decision_sha256'],full_asset_run=False,science_deadline=c['science_deadline'],no_new_after_jst=window['no_new_after_jst'],checked_jst=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat()))
print(json.dumps(dict(status='READY_FOR_PARENT_COMPUTE',request=str(U/'RUN_REQUEST.json'),config_sha256=request['config_sha256'],source_files=89,tests=31)))
