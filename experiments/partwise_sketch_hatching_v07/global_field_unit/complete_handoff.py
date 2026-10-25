"""Close durable command inventory and artifact manifest after local commit."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,HERE,sha,js,now
import json,subprocess,datetime

def main():
    commands={p.stem:json.loads(p.read_text()) for p in sorted((UNIT/'logs').glob('*.json'))}
    status=json.loads((UNIT/'STATUS.json').read_text())
    status['actual_commands']=commands
    status['commit']=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    status['worktree_clean']=not subprocess.check_output(['git','status','--porcelain'],text=True).strip()
    status['finished_utc']=now()
    status['elapsed_minutes_from_authorization']=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(status['execution_authorized_jst'])).total_seconds()/60
    js(UNIT/'STATUS.json',status);js(UNIT/'EXECUTION_RECORDS.json',commands)
    sources=[HERE/name for name in ('read_diagnostics.py','finish_global.py','complete_handoff.py')]
    js(UNIT/'HANDOFF_SOURCE_LOCK.json',dict(files={str(p):sha(p) for p in sources}))
    with (UNIT/'REPORT_ZH.md').open('a') as f:
        f.write(f"\n交付补记：包含目视检查、事后归因、报告与本地提交，从授权计约{status['elapsed_minutes_from_authorization']:.2f}分钟；提交`{status['commit']}`，工作树干净={status['worktree_clean']}，无push/merge。最终命令见EXECUTION_RECORDS.json；父级DECISION、协议与冻结科学源码保持。\n")
    protocol=json.loads((UNIT/'PROTOCOL.json').read_text())
    assert sha(UNIT/'DECISION.json')==protocol['decision_sha256']
    for path,h in json.loads((UNIT/'SOURCE_LOCK.json').read_text())['files'].items():assert sha(path)==h,path
    paths=sorted(p for p in UNIT.rglob('*') if p.is_file() and p.name!='ARTIFACT_MANIFEST.json')
    total=sum(p.stat().st_size for p in paths);assert total<20*2**30
    js(UNIT/'ARTIFACT_MANIFEST.json',dict(created_utc=now(),bytes=total,files={str(p.relative_to(UNIT)):sha(p) for p in paths},scope='Unit006 artifacts only; orchestration excluded; parent scientific verification pending.'))
    print(json.dumps(dict(commit=status['commit'],worktree_clean=status['worktree_clean'],files=len(paths),bytes=total,elapsed_minutes=status['elapsed_minutes_from_authorization'])),flush=True)

if __name__=='__main__':main()
