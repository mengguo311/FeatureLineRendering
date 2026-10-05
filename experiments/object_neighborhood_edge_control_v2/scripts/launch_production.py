import sys,subprocess,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from runtime import *
pidfile=OUT/'production.pid'
if pidfile.exists():
    pid=int(pidfile.read_text())
    try:os.kill(pid,0);raise RuntimeError('production already running; do not duplicate')
    except ProcessLookupError:pass
log=(OUT/'production.log').open('ab',buffering=0)
env=os.environ.copy();env['PYTHONPATH']=str(EXP/'src');env['PYTHONDONTWRITEBYTECODE']='1'
p=subprocess.Popen([PYTHON,str(EXP/'scripts/runner.py')],cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
pidfile.write_text(str(p.pid)+'\n');print(p.pid)
