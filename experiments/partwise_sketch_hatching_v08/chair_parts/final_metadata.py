"""Finalize actual receipts, local commit metadata and verified relative-input package."""
import runtime
from runtime import js,sha
from pathlib import Path
import datetime,json,shutil,subprocess
from PIL import Image
from run_view import verify

UNIT=runtime.ROOT/'units/unit_005'
CODE=Path(__file__).parent
def main():
    verify(UNIT);package=UNIT/'delivery';evidence=package/'evidence'
    git=[]
    def command(args):
        r=subprocess.run(args,capture_output=True,text=True,timeout=30)
        git.append(dict(argv=args,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr))
        r.check_returncode();return r.stdout.strip()
    branch=command(['git','branch','--show-current']);assert branch=='partwise-sketch-hatching-gaussian-link-v08'
    commit=command(['git','rev-parse','HEAD']);clean=command(['git','status','--porcelain'])==''
    assert clean,'uncommitted work remains'
    status=json.loads((UNIT/'STATUS.json').read_text())
    status.update(local_commit=commit,worktree_clean=clean,completed_utc=runtime.now(),
        elapsed_minutes=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat('2026-10-27T10:56:22.484967+09:00')).total_seconds()/60)
    js(UNIT/'STATUS.json',status)
    root=json.loads((runtime.ROOT/'DELIVERY_STATUS.json').read_text());root['status']=status;js(runtime.ROOT/'DELIVERY_STATUS.json',root)
    report=(UNIT/'REPORT_ZH.md').read_text()
    if '尤其不能把更少的墨' not in report:
        report=report.replace('## 原GS连接的范围与远区影响','尤其不能把更少的墨直接称为更干净：弱后侧上背覆盖79.24%→63.74%，高后侧58.50%→30.58%。高后侧的稀疏横段虽然仍保留窄背区形体，但覆盖下降是明确限制；本轮证明可编辑，不证明连续性修复或新风格胜出。\n\n## 原GS连接的范围与远区影响')
    status['limitations']=[x for x in status['limitations'] if not x.startswith('High-rear')]+['High-rear upper-back coverage drops58.50% to30.58%; no style winner']
    js(UNIT/'STATUS.json',status);root['status']=status;js(runtime.ROOT/'DELIVERY_STATUS.json',root)
    report+=f"\n交付补记：本地提交`{commit}`，工作树干净，无push/merge。交付时距授权约{status['elapsed_minutes']:.2f}分钟；全部原失败与冻结DECISION保持。\n"
    (UNIT/'REPORT_ZH.md').write_text(report);(package/'REPORT_ZH.md').write_text(report.replace('(delivery/README_ZH.md)','(README_ZH.md)'))
    records=[]
    for start in sorted((UNIT/'logs').glob('*.start.json')):
        final=start.with_name(start.name.replace('.start.json','.json'))
        record=json.loads((final if final.exists() else start).read_text())
        record['receipt']=str(final.relative_to(UNIT));record['final_receipt_present']=final.exists()
        records.append(record)
    compilers=[]
    for f in sorted(UNIT.rglob('COMPILE.json')):
        if package not in f.parents:
            compilers.append(dict(path=str(f.relative_to(UNIT)),commands=json.loads(f.read_text())))
    execution=dict(recorded_utc=runtime.now(),commands=records,compilers=compilers,metadata_git_commands=git,
        outer_engine_exit_code='UNKNOWN',note='Current finalizer is still running at snapshot time; its actual final receipt is written by run_logged after return. Never infer0 for an unfinished parent/child.')
    js(UNIT/'EXECUTION_RECORDS.json',execution)
    frozen=json.loads((UNIT/'SOURCE_LOCK.json').read_text());after={}
    for f in CODE.iterdir():
        if f.is_file() and f.name not in frozen:
            shutil.copy2(f,package/'handoff'/f.name);after[f.name]=sha(f)
    js(UNIT/'HANDOFF_SOURCE_LOCK.json',after)
    for name in ('STATUS.json','NEXT.json','HANDOFF_SOURCE_LOCK.json','EXECUTION_RECORDS.json','CLI_READBACK.json'):
        shutil.copy2(UNIT/name,evidence/name)
    dest=evidence/'logs';dest.mkdir(exist_ok=True)
    for f in (UNIT/'logs').iterdir():
        if f.is_file():shutil.copy2(f,dest/f.name)
    n=0
    for f in package.rglob('*.png'):
        with Image.open(f) as im:im.load();assert im.size[0]>0 and im.size[1]>0;n+=1
    manifest={str(f.relative_to(package)):sha(f) for f in sorted(package.rglob('*')) if f.is_file() and f.name!='MANIFEST.json'}
    js(package/'MANIFEST.json',dict(files=manifest,source_commit=commit,scope='Local CPU application asset and exact source/evidence package, not scientific certification'))
    for rel,digest in manifest.items():assert sha(package/rel)==digest,rel
    verify(UNIT)
    size=sum(f.stat().st_size for f in UNIT.rglob('*') if f.is_file());assert size<20*2**30
    js(UNIT/'FINAL_VERIFICATION.json',dict(package_files=len(manifest),all_package_hashes_verified=True,package_manifest_sha256=sha(package/'MANIFEST.json'),
        package_pngs_decoded=n,unit_bytes=size,source_lock_and_inputs_unchanged=True,decision_unchanged=True,
        local_commit=commit,worktree_clean=True,outer_engine_exit_code='UNKNOWN',current_finalizer_receipt='logs/023_final_metadata.json',
        scope='No new rendering/science; exact saved package readback. Final wrapper status lives in its raw receipt.'))
    print(json.dumps(dict(package_files=len(manifest),pngs_decoded=n,unit_bytes=size,commit=commit,clean=True)),flush=True)
if __name__=='__main__':main()
