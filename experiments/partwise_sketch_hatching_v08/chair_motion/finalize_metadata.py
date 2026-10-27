import runtime
from runtime import js
import json,subprocess,datetime
UNIT=runtime.ROOT/'units/unit_003'
def main():
    records=[]
    def git(args):
        p=subprocess.run(['git',*args],text=True,capture_output=True,timeout=30)
        records.append(dict(argv=['git',*args],returncode=p.returncode,stdout=p.stdout,stderr=p.stderr));p.check_returncode();return p.stdout.strip()
    commit=git(['rev-parse','HEAD']);branch=git(['branch','--show-current']);clean=not git(['status','--porcelain'])
    assert branch=='partwise-sketch-hatching-gaussian-link-v08'
    status=json.loads((UNIT/'STATUS.json').read_text());status.update(local_commit=commit,worktree_clean=clean,completed_utc=runtime.now(),
        elapsed_minutes=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat('2026-10-27T09:47:41.562666+09:00')).total_seconds()/60)
    js(UNIT/'STATUS.json',status);js(UNIT/'GIT_FINAL.json',dict(commands=records))
    with (UNIT/'REPORT_ZH.md').open('a') as f:f.write(f'\n交付补记：本地提交`{commit}`，工作树干净={clean}，无push/merge；元数据完成时距执行授权约{status["elapsed_minutes"]:.2f}分钟。最终打包回执另存logs，父级DECISION及冻结输入/科学源码保持。\n')
    print(json.dumps(dict(commit=commit,clean=clean,elapsed_minutes=status['elapsed_minutes'])),flush=True)
if __name__=='__main__':main()
