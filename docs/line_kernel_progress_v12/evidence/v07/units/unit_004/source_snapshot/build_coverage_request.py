"""Unit002 build metadata only; reads hashes/manifests, never numerical assets."""
from pathlib import Path
import json,hashlib
S=Path(__file__).resolve().parent
O=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_free_reassignment_v07_20261101');U=O/'units/unit_002';P=O/'units/unit_001';V5=O.parent/'line_kernel_edge_growth_v05_20261031'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(2**20),b''):h.update(b)
 return h.hexdigest()
def write(p,obj):
 if p.exists():raise FileExistsError(p)
 p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def main():
 oldpath=P/'CONFIG.json';assert sha(oldpath)=='7f9151d1e010d15029ef745c78459ebc3575c1214686214db168ed5e9c107aea';c=json.loads(oldpath.read_text());frozen=json.loads((P/'PARENT_RUN_FROZEN.json').read_text());files=dict(c['input_files'])
 for src,h in frozen['source_files'].items():
  snap=frozen['immutable_source_snapshot'][src];assert sha(snap)==h;files[snap]=h
 for name in ['free_core.py','free_io.py']:
  assert sha(S/name)==frozen['source_files'][str(S/name)],'NUMERICAL_CORE_CHANGED'
 for p in [oldpath,P/'PARENT_RUN_FROZEN.json',U/'DECISION.json']:files[str(p)]=sha(p)
 seed=V5/'units/unit_016/scenes/ficus/stages/M4_MERGE_ONLY/CARRIERS.npz';cp=seed.parent/'CHECKPOINT.json';pc=V5/'units/unit_016/CONFIG.json';pd=V5/'units/unit_016/DECISION.json'
 assert sha(seed)=='813b45f98b34c8f64b21a9655ed72b0da5063f373192e55356e10c8b5e029415';checkpoint=json.loads(cp.read_text());assert checkpoint['files']['CARRIERS.npz']==sha(seed) and checkpoint['config_binding']==sha(pc)
 for p in [seed,cp,pc,pd]:files[str(p)]=sha(p)
 for name,stage in [('unit001_STATIC','FREE_STATIC'),('unit001_ADAPTIVE','FREE_ADAPTIVE_3')]:
  p=P/'scenes/ficus/stages'/stage/'MEMBERSHIP.npz';cp1=p.parent/'CHECKPOINT.json';d=json.loads(cp1.read_text());assert d['complete'] and d['config_sha256']==sha(oldpath) and d['files']['MEMBERSHIP.npz']==sha(p);c['reference_memberships'][name]=str(p);files[str(p)]=sha(p);files[str(cp1)]=sha(cp1)
 prior={name:str(P/'figures'/name/'ROWS.npz') for name in ['CURVED_144','CURVED_382','STRAIGHT_482']}
 for p in prior.values():files[p]=sha(p)
 c.update(unit='unit_002',unit_root=str(U),decision_path=str(U/'DECISION.json'),decision_sha256=sha(U/'DECISION.json'),scientific_contract=json.loads((U/'DECISION.json').read_text()),input_files=files,seed_carriers=str(seed),seed_checkpoint=str(cp),seed_predecessor_config=str(pc),seed_expected_carriers=29070,seed_expected_knots=66114,prior_case_rows=prior)
 c['settings']['initialization']='complete finite legacy-q window bank, exact greedy marginal compatible occupied-voxel coverage'
 c['settings']['seed_window_length_p']=128;c['settings']['seed_potential_cost_strict_upper']=1;c['settings']['seed_selection_cap']=512
 c['implementation_details'].update(seed_keys='carrier_id/version/window_index',seed_flags='old valid/baseline/assigned flags provenance only, never eligibility gates',seed_coverage='all original valid-tangent kernels, exact finite segment geometry; unique floor(x/p) voxels, count once',seed_selection='exact lazy greedy; gain then canonical key; all final zero-marginal candidates logged',seed_failure='any unexpected coverage/selection error blocks promotion; only explicit invalid geometry is rejected',seed_geometry='canonical nonoverlapping128p windows; unchanged unit001 arc resample and geometry guard',seed_rows='carrier row ownership verified only for provenance/negative contexts; never constrains new primary assignment',fixed_negative_context='CARRIERS row offsets including UNKNOWN; absent carrier IDs explicit',case_selection='top3 per turn-proxy class with>=3 substantial M4 fragments, even if already present in new static; fixed previous144/382/482 exact rows always retained',historical_reference='unit001 density tracing is preserved external control; no rerun',initialization_bank_complete_required=True)
 for p,h in files.items():assert sha(p)==h,p
 for p,h in c['helper_files'].items():assert sha(p)==h
 write(U/'CONFIG.json',c)
 logs=[('TEST_RED_NEW_API.log',1,'Missing new seed API before implementation; not a claimed scientific failure'),('TEST_GREEN_COVERAGE_1.log',0,'11 new small seed/coverage tests'),('TEST_RED_BANK_FAILURE.log',1,'Real failure: coverage ValueError swallowed as geometric rejection'),('TEST_GREEN_COVERAGE_2.log',0,'15 new tests, including blocked incomplete bank and actual new30-row runner'),('TEST_ALL_GREEN.log',0,'33 explicit small tests:18 unchanged regressions plus15 coverage tests'),('TEST_RED_SCOPE.log',1,'Real failure: finite-bank coverage incorrectly labeled complete model discovery'),('TEST_FINAL_GREEN.log',0,'33 tests after explicit finite-bank scope correction'),('CLI_HELP.log',0,'approved plain --config runner CLI')]
 for name,rc,note in logs:assert (U/name).is_file()
 text=(U/'TEST_FINAL_GREEN.log').read_text();assert 'Ran 33 tests' in text and text.rstrip().endswith('OK')
 write(U/'TESTS_RECEIPT.json',dict(returncode=0,tdd_status='NEW_API_TEST_FIRST_AND_REAL_RED_GREEN_BANK_FAILURE_PROPAGATION',command='approved_venv_python -B '+str(S/'run_coverage_tests.py'),full_asset_science_run=False,render_run=False,test_count=33,fixture_max_rows=96,logs=[dict(path=str(U/name),sha256=sha(U/name),returncode=rc,note=note) for name,rc,note in logs],scope='Actual original-kernel and seed loaders read temporary NPZ; actual30-row initialization/assignment/update/cold-load runner; only delivery is explicitly mocked. No protected unit writes.'))
 sources={str(p):sha(p) for p in sorted(S.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
 write(U/'RUN_REQUEST.json',dict(script=str(S/'coverage_runner.py'),config_path=str(U/'CONFIG.json'),config_sha256=sha(U/'CONFIG.json'),source_files=sources,helper_files=c['helper_files'],max_seconds=1800,tests_receipt=str(U/'TESTS_RECEIPT.json')))
 print(json.dumps(dict(status='READY_FOR_PARENT_COMPUTE',request=str(U/'RUN_REQUEST.json'),config_sha256=sha(U/'CONFIG.json'),source_files=len(sources))))
if __name__=='__main__':main()
