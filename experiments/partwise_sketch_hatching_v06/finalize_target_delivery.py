"""Final handoff integrity/readback only; no experiment rerun or science edits."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,OUTPUT_ROOT,js,sha,now,output_guard
from pathlib import Path
import json,shutil,subprocess

assert UNIT.name=='unit_008'
HERE=Path(__file__).resolve().parent
code=subprocess.run(['git','rev-parse','HEAD'],capture_output=True,text=True,check=True).stdout.strip()
branch=subprocess.run(['git','branch','--show-current'],capture_output=True,text=True,check=True).stdout.strip()
assert branch=='partwise-sketch-hatching-gaussian-link-v06'
dirty=subprocess.run(['git','status','--porcelain'],capture_output=True,text=True,check=True).stdout
assert not dirty
p=json.loads((UNIT/'PROTOCOL.json').read_text())
assert sha(UNIT/'PROTOCOL.json')==json.loads((UNIT/'PROTOCOL_LOCK.json').read_text())['sha256']
assert sha(UNIT/'DECISION.json')==p['decision_sha256']
for name,h in p['frozen_files'].items():assert sha(UNIT/name)==h,name
for name,h in json.loads((UNIT/'INPUT_LOCK.json').read_text())['files'].items():assert sha(name)==h,name
for name,h in json.loads((UNIT/'SOURCE_LOCK.json').read_text())['files'].items():assert sha(UNIT/'source_snapshot'/name)==h,name
for name,h in json.loads((UNIT/'ASSET_LOCK.json').read_text())['files'].items():assert sha(UNIT/name)==h,name
for name,h in json.loads((UNIT/'DELIVERY_PREVIOUS_LOCK.json').read_text())['files'].items():assert sha(UNIT/'delivery_previous'/name)==h,name
out=output_guard(UNIT/'handoff_source');out.mkdir(exist_ok=False)
for name in ('finish_target_unit.py','finalize_target_delivery.py'):shutil.copyfile(HERE/name,out/name)
js(UNIT/'HANDOFF_SOURCE_LOCK.json',dict(files={f.name:sha(f) for f in out.iterdir()},role='Post-result report/readback, not frozen experimental implementation'))
status=json.loads((UNIT/'STATUS.json').read_text())
for name,path in status['artifacts'].items():assert Path(path).is_file(),name
receipts=[dict(name=f.name,**json.loads(f.read_text())) for f in sorted((UNIT/'logs').glob('*.receipt.json'))]
assert all(x['returncode']==0 for x in receipts if x['name']!='tdd_red_001.receipt.json')
status.update(local_commit=code,worktree_clean=True,final_readback_utc=now(),tests_and_actual_commands=receipts)
status['runtime_readback_note']='Post-handoff read-only check found UNIT/scratch absent. Created it before future replay. Earlier compiler temporary-file location was not recorded; all persistent science/build artifacts are under unit008. Frozen science/runtime unchanged.'
js(UNIT/'STATUS.json',status)
delivery=json.loads((OUTPUT_ROOT/'DELIVERY_STATUS.json').read_text());delivery.update(local_commit=code,worktree_clean=True,final_readback_utc=now());js(OUTPUT_ROOT/'DELIVERY_STATUS.json',delivery)
js(UNIT/'FINAL_HANDOFF_CHECK.json',dict(utc=now(),branch=branch,local_commit=code,worktree_clean=True,protocol_and_decision_exact=True,
    all_locked_inputs_and_sources_exact=True,asset_exact=True,previous_delivery_preserved=True,all_artifacts_exist=True,
    persistent_outputs_on_HDD=True,scratch_directory_exists=(UNIT/'scratch').is_dir(),
    runtime_note=status['runtime_readback_note'],scientific_seal=False,parent_monitor_verification='pending'))
print('FINAL HANDOFF verified',code,flush=True)
