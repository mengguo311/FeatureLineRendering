"""Finalize command receipts and package hashes after the local source commit."""
import runtime
from runtime import js,sha
from pathlib import Path
import argparse,json,shutil,datetime
from run_view import verify
UNIT=runtime.ROOT/'units/unit_006';CODE=Path(__file__).parent
def main(commit):
    verify(UNIT)
    previous=json.loads((UNIT/'delivery/MANIFEST.json').read_text())['files']
    for rel,h in previous.items():assert sha(UNIT/'delivery'/rel)==h,rel
    s=json.loads((UNIT/'STATUS.json').read_text());s.update(local_commit=commit,worktree_clean=True,completed_utc=runtime.now(),
        elapsed_minutes=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat('2026-10-27T02:25:00.284855+00:00')).total_seconds()/60,
        authoring_cost=dict(new_clicks=0,new_face_edits=0,fixed_display_masks=1,fixed_parameter_tuples=2,per_DEV_cleanup=0,authoring_minutes='UNKNOWN; not timed separately from implementation'))
    js(UNIT/'STATUS.json',s)
    report=UNIT/'REPORT_ZH.md'
    report.write_text(report.read_text()+f"\n交付补记：本地提交`{commit}`，工作树干净，无push/merge。当前距授权约{s['elapsed_minutes']:.2f}分钟。作者配置没有单独计时，不能将工程时长冒称标注成本；新增点击/面修改/逐DEV清理均0，一次固定显示掩码和两组参数。\n")
    records=[]
    for start in sorted((UNIT/'logs').glob('*.start.json')):
        end=Path(str(start).replace('.start.json','.json'));r=json.loads((end if end.exists() else start).read_text())
        r['receipt_file']=str(end.relative_to(UNIT)) if end.exists() else None
        if start.name.startswith('008_'):r['tool_outer_exit_code']=143
        records.append(r)
    js(UNIT/'EXECUTION_RECORDS.json',dict(snapshot_utc=runtime.now(),commands=records,final_engine_exit_code='UNKNOWN',
        compiler_records=json.loads((UNIT/'FINAL_VERIFICATION.json').read_text())['compiler_records'],
        scope='Actual completed raw command receipts; missing final command receipt stays UNKNOWN. Final packaging command receipt remains in unit logs after this snapshot.'))
    extra={name:sha(CODE/name) for name in ('assess_saved.py','finish_checks.py','finish_unit.py','finalize_metadata.py')}
    js(UNIT/'HANDOFF_SOURCE_LOCK.json',extra)
    for name in extra:
        shutil.copy2(CODE/name,UNIT/'delivery/audit_code'/name)
    for name in ('STATUS.json','REPORT_ZH.md','EXECUTION_RECORDS.json','HANDOFF_SOURCE_LOCK.json'):
        shutil.copy2(UNIT/name,UNIT/'delivery/evidence'/name)
    for f in (UNIT/'logs').iterdir():
        if f.is_file():shutil.copy2(f,UNIT/'delivery/evidence/logs'/f.name)
    root=json.loads((runtime.ROOT/'DELIVERY_STATUS.json').read_text());root['status']=s;js(runtime.ROOT/'DELIVERY_STATUS.json',root)
    files={str(f.relative_to(UNIT/'delivery')):sha(f) for f in sorted((UNIT/'delivery').rglob('*')) if f.is_file() and f.name!='MANIFEST.json'}
    js(UNIT/'delivery/MANIFEST.json',dict(utc=runtime.now(),source_commit=commit,scope='Local content hashes; no scientific seal',files=files))
    for rel,h in files.items():assert sha(UNIT/'delivery'/rel)==h,rel
    total=sum(f.stat().st_size for f in UNIT.rglob('*') if f.is_file())
    assert total<20*2**30
    js(UNIT/'FINAL_PACKAGE_VERIFICATION.json',dict(utc=runtime.now(),previous_manifest_verified=len(previous),final_manifest_verified=len(files),
        manifest_sha256=sha(UNIT/'delivery/MANIFEST.json'),unit_bytes=total,decision_sha256=sha(UNIT/'DECISION.json'),
        frozen_source_verified=True,frozen_inputs_verified=True,local_commit=commit,root_free_bytes=shutil.disk_usage('/').free,
        hdd_free_bytes=shutil.disk_usage(runtime.ROOT).free,scope='Local content verification only; final engine exit remains parent-owned.'))
    print(json.dumps(dict(files=len(files),unit_bytes=total,commit=commit,elapsed_minutes=s['elapsed_minutes'])),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--commit',required=True);main(p.parse_args().commit)
