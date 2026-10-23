"""Final immutable-payload and source-commit readback; no scientific rerun."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,OUTPUT_ROOT,sha,js,now
from pathlib import Path
import json
import subprocess

assert UNIT.name=='unit_007'
repo=Path('/home/u00134/3dgs_line/partwise_sketch_hatching_gaussian_link_v06')
def git(*args):return subprocess.check_output(['git',*args],cwd=repo,text=True).strip()
assert git('branch','--show-current')=='partwise-sketch-hatching-gaussian-link-v06'
assert not git('status','--porcelain')
commit=git('rev-parse','HEAD')
manifest=json.loads((UNIT/'ARTIFACT_MANIFEST.json').read_text())['files']
for name,h in manifest.items():assert sha(UNIT/name)==h,name
inputs=json.loads((UNIT/'INPUT_LOCK.json').read_text())['files']
for name,h in inputs.items():assert sha(name)==h,name
source=json.loads((UNIT/'EXECUTION_SOURCE_LOCK.json').read_text())['files']
for name,h in source.items():assert sha(repo/'experiments/partwise_sketch_hatching_v06'/name)==h,name
for name,h in json.loads((UNIT/'HANDOFF_SOURCE_LOCK.json').read_text())['files'].items():
    assert sha(repo/'experiments/partwise_sketch_hatching_v06'/name)==h,name
receipts=[]
for f in sorted((UNIT/'logs').glob('*.receipt.json')):
    r=json.loads(f.read_text());assert r['returncode']==(1 if f.name=='tdd_red_001.receipt.json' else 0),f.name
    receipts.append(dict(name=f.name,argv=r['argv'],returncode=r['returncode'],elapsed_seconds=r['elapsed_seconds']))
status=json.loads((UNIT/'STATUS.json').read_text());assert status['execution_state']=='completed'
for name,path in status['artifacts'].items():assert Path(path).is_file(),name
assert json.loads((UNIT/'NEXT.json').read_text())['action']=='continue'
js(UNIT/'GIT_RECEIPT.json',dict(utc=now(),commit=commit,branch=git('branch','--show-current'),worktree_clean=True,
    source_snapshot_files_match=True,finalizer_sha256=sha(Path(__file__))))
js(UNIT/'FINAL_DELIVERY_READBACK.json',dict(utc=now(),artifact_hashes=len(manifest),immutable_inputs=len(inputs),
    receipts=len(receipts),all_checked=True,expected_RED_preserved=True,source_snapshot_matches_lock=True,
    scientific_seal=False,commit=commit,worktree_clean=True))
status.update(local_commit=commit,worktree_clean=True,final_readback_utc=now(),tests_and_actual_commands=receipts)
if (UNIT/'GIT_STAGE_FAILURE.json').exists():
    status['preserved_failures'].append(dict(stage='initial_explicit_git_add',returncode=1,
        reason='sparse-checkout staging restriction; recovered with explicit git add --sparse',record=str(UNIT/'GIT_STAGE_FAILURE.json')))
    report=UNIT/'REPORT_ZH.md'
    report.write_text(report.read_text()+'\n交付补记：上述rc0描述限科学/验证阶段。其后首次本地git add因稀疏checkout路径限制rc1；改用同一组授权新文件的git add --sparse完成本地提交，未改变稀疏配置。原失败记录见GIT_STAGE_FAILURE.json。\n')
for name in ('GIT_RECEIPT.json','FINAL_DELIVERY_READBACK.json'):status['artifacts'][name]=str(UNIT/name)
js(UNIT/'STATUS.json',status)
delivery=json.loads((OUTPUT_ROOT/'DELIVERY_STATUS.json').read_text());assert delivery['latest_completed_unit']=='unit_007'
delivery.update(source_commit=commit,handoff_finalized_utc=now(),worktree_clean=True)
js(OUTPUT_ROOT/'DELIVERY_STATUS.json',delivery)
print('FINAL_READBACK',len(manifest),'payloads',len(inputs),'inputs',len(receipts),'receipts',commit,flush=True)
