"""Finalize receipts and immutable unit artifact manifest after local commit."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,HERE,sha,js,now
import json,datetime,subprocess,shutil

def main():
    status=json.loads((UNIT/'STATUS.json').read_text())
    protocol=json.loads((UNIT/'PROTOCOL.json').read_text())
    assert sha(UNIT/'DECISION.json')==protocol['decision_sha256']
    for name,h in protocol['frozen'].items():assert sha(UNIT/name)==h,name
    for path,h in json.loads((UNIT/'SOURCE_LOCK.json').read_text())['files'].items():assert sha(path)==h,path
    for path,h in json.loads((UNIT/'HANDOFF_SOURCE_LOCK.json').read_text())['files'].items():assert sha(path)==h,path
    commands={p.stem:json.loads(p.read_text()) for p in sorted((UNIT/'logs').glob('*.json'))}
    assert commands['red_crossover']['child_returncode']==1
    assert all(x['child_returncode']==0 for n,x in commands.items() if n!='red_crossover')
    head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip()
    assert branch=='partwise-sketch-hatching-gaussian-link-v07'
    dirty=subprocess.check_output(['git','status','--porcelain'],text=True).strip()
    assert not dirty,dirty
    elapsed=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(status['execution_authorized_jst'])).total_seconds()/60
    status.update(actual_commands=commands,local_commit=head,working_tree_clean=True,finished_utc=now(),elapsed_minutes_from_authorization=elapsed)
    js(UNIT/'STATUS.json',status);js(UNIT/'EXECUTION_RECORDS.json',commands)
    with (UNIT/'REPORT_ZH.md').open('a') as out:out.write(f'\n最终交付：本地提交`{head}`，工作树干净，无push/merge。从执行授权至交付约{elapsed:.2f}分钟；父级DECISION和冻结科学源码再次核对不变。\n')
    folder=UNIT/'handoff_source';folder.mkdir(exist_ok=False)
    for name in ('finish_crossover.py','complete_handoff.py'):
        shutil.copyfile(HERE/name,folder/name)
    js(UNIT/'HANDOFF_FINAL_SOURCE_LOCK.json',dict(files={str(HERE/name):sha(HERE/name) for name in ('finish_crossover.py','complete_handoff.py')}))
    files={str(p.relative_to(UNIT)):sha(p) for p in sorted(UNIT.rglob('*')) if p.is_file() and p.name!='ARTIFACT_MANIFEST.json'}
    js(UNIT/'ARTIFACT_MANIFEST.json',dict(created_utc=now(),scientific_seal=False,parent_verification='pending',files=files))
    print(json.dumps(dict(execution_state=status['execution_state'],local_commit=head,files=len(files),elapsed_minutes=elapsed,next='continue',decision_unchanged=True)),flush=True)

if __name__=='__main__':main()
