"""Finalize post-commit records and manifest without touching scientific outputs."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,HERE,sha,js,now
from pathlib import Path
import json,subprocess,datetime

def main():
    worktree=HERE.parents[2]
    branch=subprocess.check_output(['git','branch','--show-current'],cwd=worktree,text=True).strip()
    assert branch=='partwise-sketch-hatching-gaussian-link-v07'
    dirty=subprocess.check_output(['git','status','--porcelain'],cwd=worktree,text=True)
    assert not dirty,dirty
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=worktree,text=True).strip()
    protocol=json.loads((UNIT/'PROTOCOL.json').read_text())
    assert sha(UNIT/'DECISION.json')==protocol['decision_sha256']
    for path,digest in json.loads((UNIT/'SOURCE_LOCK.json').read_text())['files'].items():assert sha(path)==digest,path
    commands={p.stem:json.loads(p.read_text()) for p in sorted((UNIT/'logs').glob('*.json'))}
    commands['git_add_initial']=json.loads((UNIT/'HANDOFF_FAILURE.json').read_text())
    failures={'red_coupling':1,'git_add_initial':1}
    for name,r in commands.items():assert r['child_returncode']==failures.get(name,0),(name,r)
    js(UNIT/'EXECUTION_RECORDS.json',commands)
    status=json.loads((UNIT/'STATUS.json').read_text());status['actual_commands']=commands
    elapsed=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(status['execution_authorized_jst'])).total_seconds()/60
    status.update(local_commit=commit,working_tree_clean=True,push_merge=False,elapsed_minutes_from_authorization=elapsed,finished_utc=now(),engineering_failures=['Expected missing-module RED preserved.','Initial git add rejected sparse-checkout path; recovered with authorized --sparse, no configuration change.'])
    status['artifacts']+=['HANDOFF_FAILURE.json','COMMIT.json']
    js(UNIT/'STATUS.json',status);js(UNIT/'COMMIT.json',dict(commit=commit,branch=branch,working_tree_clean=True,push_merge=False))
    with (UNIT/'REPORT_ZH.md').open('a') as out:out.write(f'\n最终交付：本地提交`{commit}`，工作树干净，无push/merge。含报告与提交，从授权计约{elapsed:.2f}分钟。全部原失败及父级DECISION保持。\n')
    js(UNIT/'HANDOFF_SOURCE_LOCK.json',dict(files={str(HERE/name):sha(HERE/name) for name in ('read_coupling_diagnostics.py','finish_coupling.py','complete_handoff.py')}))
    files=[p for p in UNIT.rglob('*') if p.is_file() and p.name!='ARTIFACT_MANIFEST.json']
    total=sum(p.stat().st_size for p in files);assert total<20*2**30
    js(UNIT/'ARTIFACT_MANIFEST.json',dict(scope='Completed unit007 artifacts only; not a scientific seal or mutable orchestration lock.',files={str(p.relative_to(UNIT)):dict(sha256=sha(p),bytes=p.stat().st_size) for p in sorted(files)},total_bytes=total))
    print(json.dumps(dict(execution_state=status['execution_state'],commit=commit,working_tree_clean=True,artifact_files=len(files),artifact_bytes=total,elapsed_minutes=elapsed,NEXT='continue'),ensure_ascii=False),flush=True)

if __name__=='__main__':main()
