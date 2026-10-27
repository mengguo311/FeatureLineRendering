"""Seal content hashes after completed science; keep missing controller exit UNKNOWN."""
import runtime
from runtime import sha,js
from pathlib import Path
import datetime,json,shutil,subprocess
from PIL import Image
from finish_unit import records,START

UNIT=runtime.ROOT/'units/unit_002'
CODE=Path(__file__).parent
def main():
    protocol=json.loads((UNIT/'PROTOCOL.json').read_text())
    assert sha(UNIT/'DECISION.json')==protocol['decision_sha256']
    assert sha(UNIT/'PROTOCOL.json')==json.loads((UNIT/'PROTOCOL_LOCK.json').read_text())['sha256']
    for f,h in json.loads((UNIT/'INPUT_LOCK.json').read_text()).items():assert sha(f)==h,f
    src=json.loads((UNIT/'SOURCE_LOCK.json').read_text())
    for n,h in src['files'].items():assert sha(CODE/n)==h,n
    for n,h in src['cli_files'].items():assert sha(UNIT/'delivery/code'/n)==h,n
    assert not (UNIT/'logs/006_view2.json').exists()
    vcs=[]
    for argv in (['git','rev-parse','HEAD'],['git','status','--porcelain'],['git','branch','--show-current']):
        r=subprocess.run(argv,capture_output=True,text=True,check=False)
        vcs.append(dict(argv=argv,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr));r.check_returncode()
    assert vcs[2]['stdout'].strip()=='partwise-sketch-hatching-gaussian-link-v08'
    status=json.loads((UNIT/'STATUS.json').read_text())
    status.update(local_commit=vcs[0]['stdout'].strip(),worktree_clean=not vcs[1]['stdout'].strip(),
        completed_utc=runtime.now(),elapsed_minutes=(datetime.datetime.now(datetime.timezone.utc)-START).total_seconds()/60)
    js(UNIT/'STATUS.json',status)
    execution=json.loads((UNIT/'EXECUTION_RECORDS.json').read_text());execution['commands']=records();execution['vcs_commands']=vcs
    execution['git_stage']=dict(first_attempt_actual_exec_exit_code=1,reason='Sparse checkout excluded the new authorized paths',recovery=json.loads((UNIT/'logs/012_stage_recovery.json').read_text()))
    execution['git_diff_check_actual_exit_code']=json.loads((UNIT/'logs/014_diff_check.json').read_text())['child_returncode']
    js(UNIT/'EXECUTION_RECORDS.json',execution)
    evidence=UNIT/'delivery/evidence'
    for f in (UNIT/'logs').iterdir():
        if f.is_file():shutil.copy2(f,evidence/'logs'/f.name)
    note='\n交付补记：首次git add因稀疏检出边界退出1，随后commit也退出1；原失败保留。显式git add --sparse限定本单元源码/文档后提交成功，未更改稀疏规则或其他工作树。最终提交与实际回执见STATUS及EXECUTION_RECORDS。\n'
    with (UNIT/'REPORT_ZH.md').open('a') as f:f.write(note)
    for name in ('STATUS.json','EXECUTION_RECORDS.json','REPORT_ZH.md'):shutil.copy2(UNIT/name,evidence/name)
    handoff={}
    for f in sorted(CODE.iterdir()):
        if f.is_file():
            dst=UNIT/'delivery/handoff_source'/f.name;dst.parent.mkdir(exist_ok=True);shutil.copy2(f,dst);handoff[f.name]=sha(f)
    js(UNIT/'HANDOFF_FINAL_SOURCE_LOCK.json',handoff)
    shutil.copy2(UNIT/'HANDOFF_FINAL_SOURCE_LOCK.json',evidence/'HANDOFF_FINAL_SOURCE_LOCK.json')
    js(runtime.ROOT/'DELIVERY_STATUS.json',dict(latest_unit='unit_002',units=['unit_001','unit_002'],status=status,old_negative_results_preserved=True))
    package=UNIT/'delivery';files={str(f.relative_to(package)):sha(f) for f in sorted(package.rglob('*')) if f.is_file() and f.name!='MANIFEST.json'}
    js(package/'MANIFEST.json',dict(files=files,scope='Content hashes, not scientific seal. Current finalizer receipt outside package completes after this snapshot. Parent orchestration excluded.'))
    for name,h in files.items():assert sha(package/name)==h,name
    decoded=0
    for f in package.rglob('*.png'):
        with Image.open(f) as im:im.load()
        decoded+=1
    js(UNIT/'PACKAGE_VERIFICATION.json',dict(files_verified=len(files),package_pngs_decoded=decoded,manifest_sha256=sha(package/'MANIFEST.json'),
        source_copy_pairs_verified=len(json.loads((UNIT/'INPUT_COPY_RECEIPT.json').read_text())['files']),
        input_lock_verified=True,science_source_lock_verified=True,decision_unchanged=True,protocol_unchanged=True,
        local_commit=status['local_commit'],worktree_clean=status['worktree_clean'],vcs=vcs,
        last_engine_exit_code='UNKNOWN',scope='Local Linux content verification. No new scene run, bootstrap, remote or cross-platform certification.'))
    print(json.dumps(dict(files_verified=len(files),package_pngs_decoded=decoded,commit=status['local_commit'],worktree_clean=status['worktree_clean'],elapsed_minutes=status['elapsed_minutes'])))
if __name__=='__main__':main()
