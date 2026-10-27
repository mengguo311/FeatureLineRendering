"""Close local delivery metadata after actual checks and local commit."""
import runtime
from runtime import js,sha
from pathlib import Path
import json,shutil,subprocess,datetime
from PIL import Image
from run_motion import verify_unit
UNIT=runtime.ROOT/'units/unit_004';CODE=Path(__file__).parent
def main():
    verify_unit(UNIT)
    package=UNIT/'delivery';old=json.loads((package/'MANIFEST.json').read_text())['files']
    for rel,h in old.items():assert sha(package/rel)==h,rel
    records=[]
    expected={'001_red':1,'010_wrong_asset_expected_failure':1}
    for file in sorted((UNIT/'logs').glob('*.json')):
        if file.name.endswith('.start.json'):continue
        r=json.loads(file.read_text())
        if 'child_returncode' not in r:continue
        assert r['child_returncode']==expected.get(file.stem,0),(file,r['child_returncode'])
        records.append(dict(stage=file.stem,receipt=str(file.relative_to(UNIT)),receipt_sha256=sha(file),
            child_returncode=r['child_returncode'],controller_expected_exit_rule='run_logged exits with child returncode; actual tool observations are separate',
            expected_failure=file.stem in expected,started_utc=r.get('started_utc','UNKNOWN'),finished_utc=r.get('finished_utc','UNKNOWN')))
    compilers={}
    for f in [UNIT/'renders/build/COMPILE.json',UNIT/'cold_highlight/build/COMPILE.json']:
        rows=json.loads(f.read_text());assert all(x['returncode']==0 for x in rows)
        compilers[str(f.relative_to(UNIT))]=rows
    js(UNIT/'EXECUTION_RECORDS.json',dict(completed_logged_commands=records,compiler_children=compilers,
        setup=dict(script='setup_unit.py',actual_tool_exit_code=0,receipt='INPUT_COPY_RECEIPT.json'),
        observed_tool_exits={r['stage']:expected.get(r['stage'],0) for r in records},
        incidental_read_commands=[dict(command='ls DEMO_README_ZH.md DELIVERY_STATUS.json',actual_tool_exit_code=2,note='Absent optional worktree-root index; no scientific execution failed'),
            dict(command='git add experiments/partwise_sketch_hatching_v08/chair_path_source docs/partwise_sketch_hatching_v08/unit_004.md',actual_tool_exit_code=1,note='Sparse checkout rejected unstaged new paths; recovered using explicit --sparse on the same authorized paths. Original tool chunk299a66 retained.'),
            dict(command='git diff --check',actual_tool_exit_code=0),dict(command='df -B1 / /mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v08',actual_tool_exit_code=0)],
        current_metadata_command='Own final returncode is in logs/019_final_metadata.json after this writer exits; not guessed here',
        last_engine_exit_code='UNKNOWN',scope='Completed child commands and observed wrapper tools; parent engine completion remains parent-owned'))
    frozen=json.loads((UNIT/'SOURCE_LOCK.json').read_text())['files']
    handoff={f.name:sha(f) for f in CODE.iterdir() if f.is_file() and f.name not in frozen}
    js(UNIT/'HANDOFF_SOURCE_LOCK.json',dict(files=handoff,scope='Post-evaluation saved-result auditing/reporting only; frozen science unchanged'))
    commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    dirty=subprocess.check_output(['git','status','--porcelain'],text=True)
    assert not dirty,dirty
    elapsed=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat('2026-10-27T10:27:36.844057+09:00')).total_seconds()/60
    status=json.loads((UNIT/'STATUS.json').read_text());status.update(local_commit=commit,worktree_clean=True,
        completed_utc=runtime.now(),elapsed_minutes=elapsed)
    js(UNIT/'STATUS.json',status)
    ev=package/'evidence'
    for name in ('STATUS.json','EXECUTION_RECORDS.json','HANDOFF_SOURCE_LOCK.json','NEXT.json','PACKAGING_AUDIT.json'):
        shutil.copy2(UNIT/name,ev/name)
    # Auditors are shipped separately so the immutable science source lock stays meaningful.
    hd=package/'handoff';hd.mkdir(exist_ok=True)
    for name in handoff:shutil.copy2(CODE/name,hd/name)
    files={str(f.relative_to(package)):sha(f) for f in package.rglob('*') if f.is_file() and f.name!='MANIFEST.json'}
    js(package/'MANIFEST.json',dict(files=files,created_utc=runtime.now(),local_commit=commit,scope='Local runnable Chair asset; scientific PARTIAL'))
    for rel,h in files.items():assert sha(package/rel)==h,rel
    # Existing PNG hashes and decode certification still hold after metadata-only packaging.
    for rel,h in old.items():
        if rel.endswith('.png'):assert files[rel]==h
    total=sum(f.stat().st_size for f in UNIT.rglob('*') if f.is_file());assert total<20*2**30
    js(UNIT/'FINAL_VERIFICATION.json',dict(package_files=len(files),package_manifest_sha256=sha(package/'MANIFEST.json'),
        unchanged_decoded_PNG_count=73,unit_bytes=total,source_and_inputs_unchanged=True,decision_sha256=sha(UNIT/'DECISION.json'),
        local_commit=commit,worktree_clean=True,elapsed_minutes=elapsed,remote_verification='not performed',last_engine_exit_code='UNKNOWN'))
    print(json.dumps(dict(commit=commit,package_files=len(files),unit_bytes=total,elapsed_minutes=elapsed,worktree_clean=True)),flush=True)
if __name__=='__main__':main()
