"""Unit006 freeze metadata only. Never numerical science."""
from pathlib import Path
import json,hashlib
S=Path(__file__).resolve().parent;O=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_free_reassignment_v07_20261101');U=O/'units/unit_006';P=O/'units/unit_005'
PYTHON='/mnt/hdd1/u00134/radegs_paper_reproduction_v01/c2l50_8build_part_prior_feasibility_v03/venv/bin/python'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def write(p,x):
 with p.open('x') as f:json.dump(x,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def main():
 expected='10423a1d233148eeb0a106563edad79a25feedf82e666ce10f347182424aba77';pc=P/'CONFIG.json';assert sha(pc)==expected;c=json.loads(pc.read_text());files=dict(c['input_files']);frozen=json.loads((P/'PARENT_RUN_FROZEN.json').read_text())
 for src,h in frozen['source_files'].items():
  snap=frozen['immutable_source_snapshot'][src];assert sha(snap)==h;assert sha(src)==h,'OLD_SOURCE_CHANGED';files[snap]=h
 for p in [pc,P/'PARENT_RUN_FROZEN.json',U/'DECISION.json']:files[str(p)]=sha(p)
 def bind_stage(stage):
  cp=json.loads((stage/'CHECKPOINT.json').read_text());assert cp['complete'] and cp['config_sha256']==expected
  for n,h in cp['files'].items():assert sha(stage/n)==h;files[str(stage/n)]=h
  files[str(stage/'CHECKPOINT.json')]=sha(stage/'CHECKPOINT.json')
 stage=P/'scenes/ficus/stages/NO_BIRTH';bind_stage(stage);final=P/'scenes/ficus/stages/BIRTH_FINAL';bind_stage(final)
 graph=P/'graph';cp=json.loads((graph/'CHECKPOINT.json').read_text());assert cp['complete']
 for n,h in cp['files'].items():assert sha(graph/n)==h;files[str(graph/n)]=h
 files[str(graph/'CHECKPOINT.json')]=sha(graph/'CHECKPOINT.json')
 assert files[str(graph/'MODES.npz')]=='ac17a45ce5b531c64133094bff3f76ec0e9f52bbb4ed0f718e9d03da2a14258f';assert files[str(graph/'GRAPH.npz')]=='fdc3797544a9088b381a9c2c5e7363a0b2105d7ca8fcbb8d53e38cf1b5b91f18'
 root=Path('/home/u00134/cglib/data/full/ficus');imgs={'test_r_1':str(root/'val/r_1.png'),'test_r_79':str(root/'val/r_79.png')};hs=['294de4156912ffbd4c80d3a8404eea4661f54da44a0586b453e7c8ce4ad128cf','b6dfd1eafdbb0b9eb4aa416c70bfe09c5853c8e576b6d5599762bc5d977896e9']
 for p,h in zip(imgs.values(),hs):assert sha(p)==h;files[p]=h
 tf=root/'transforms_val.json';h='0d12d088ff4fb586740e939dff6bc77db7c4aadfacd2f75867965e6786b32990';assert sha(tf)==h;files[str(tf)]=h
 for mid in [717,720,722]:
  p=P/('figures/CURVED_%d/ROWS.npz'%mid);assert p.is_file();files[str(p)]=sha(p);c['prior_case_rows']['UNIT005_CURVED_'+str(mid)]=str(p)
 c['reference_memberships']['unit005_BIRTH_FINAL']=str(final/'MEMBERSHIP.npz')
 c.update(unit='unit_006',unit_root=str(U),decision_path=str(U/'DECISION.json'),decision_sha256=sha(U/'DECISION.json'),scientific_contract=json.loads((U/'DECISION.json').read_text()),input_files=files,predecessor_stage=str(stage),predecessor_config=str(pc),predecessor_config_sha256=expected,predecessor_model_count=519,predecessor_next_id=713,max_seconds=1200,latest_parent_launch_jst='2026-11-01T19:18:00+09:00',absolute_deadline_jst='2026-11-01T19:38:00+09:00',stage_budgets=dict(readiness=120,complete_evidence_and_paths_by=420,science_by=600,delivery_reserved=600),saved_graph=str(graph),expected_modes=131891,expected_edges=344798,expected_seeds=64,evidence_images=imgs,image_transforms=str(tf),legacy_groups_locked=False,kernel_geometry_frozen=True,final_ink_carrier='original_gaussians',uses_gpu=False,uses_training=False)
 c['settings'].update(initialization='exact unit005 NO_BIRTH; static original graph and seeds',image_gaussian_sigma=1.,image_boundary='reflect',image_sobel_divisor=8.,luminance=[.2126,.7152,.0722],image_gradient_min=.1,image_pixel_radius=2.,image_tangent_degrees=30.,image_edge_samples=[0.,.5,1.],positive_edge_multiplier=.5,image_missing_penalty=0.,reachable_scope='original Dijkstra <=64 per oriented seed; induced subgraph only')
 c['implementation_details'].update(control='unit005 BIRTH_FINAL historical saved control, not rerun fits; original graph search exact replay required',initialization='hash-verified unit005 NO_BIRTH; no fresh competition',graph='exact saved graph, no new edges or vertices',paths='old seed R frozen; only positive dual-view edge reward within induced R; original canonical path policy',image_evidence='RGB alpha white; two calibrated val images, positive evidence only, no visibility or held-out certification')
 for p,h in files.items():assert sha(p)==h,p
 for p,h in c['helper_files'].items():assert sha(p)==h,p
 red=U/'TEST_RED.log';green=U/'TEST_GREEN_ACCEPTED.log';assert 'ModuleNotFoundError' in red.read_text();assert green.read_text().rstrip().endswith('OK');cli=U/'CLI_HELP.log';assert '--config' in cli.read_text()
 write(U/'CONFIG.json',c)
 write(U/'TESTS_RECEIPT.json',dict(returncode=0,tdd_status='REAL_NEW_IMAGE_API_RED_GREEN_PLUS_LEGACY_REGRESSIONS',command=[PYTHON,'-B',str(S/'run_image_tests.py')],full_asset_science_run=False,render_run=False,fixture_max_rows=96,logs=[dict(path=str(red),returncode=1,sha256=sha(red)),dict(path=str(U/'TEST_GREEN_NEW.log'),returncode=0,sha256=sha(U/'TEST_GREEN_NEW.log')),dict(path=str(U/'TEST_GREEN.log'),returncode=0,sha256=sha(U/'TEST_GREEN.log')),dict(path=str(U/'TEST_GREEN_FINAL.log'),returncode=1,sha256=sha(U/'TEST_GREEN_FINAL.log'),note='New runner fixture missing evidence_images; corrected fixture, not numerical policy'),dict(path=str(U/'TEST_RUNNER_DIAG.log'),returncode=1,sha256=sha(U/'TEST_RUNNER_DIAG.log')),dict(path=str(green),returncode=0,sha256=sha(green))],cli_help=dict(path=str(cli),returncode=0,sha256=sha(cli)),scope='Explicit bounded suites, real new runner/loader and saved-graph replay, fixed-R searches, free reassign/rollback, original checkpoint; image evidence isolated only in runner fixture and directly tested separately; no real-asset science.'))
 source={str(p):sha(p) for p in sorted(S.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
 write(U/'RUN_REQUEST.json',dict(script=str(S/'image_path_runner.py'),config_path=str(U/'CONFIG.json'),config_sha256=sha(U/'CONFIG.json'),source_files=source,helper_files=c['helper_files'],max_seconds=1200,tests_receipt=str(U/'TESTS_RECEIPT.json')))
 print(json.dumps(dict(status='READY_FOR_PARENT_COMPUTE',request=str(U/'RUN_REQUEST.json'),config_sha256=sha(U/'CONFIG.json'),source_files=len(source))))
if __name__=='__main__':main()
