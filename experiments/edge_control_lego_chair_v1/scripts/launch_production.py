#!/usr/bin/env python
import sys,subprocess,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from runtime import OUT,ART,EXP,PYTHON,guard,source_hashes,atomic_json
guard('launch-production',False)
if (OUT/'PRODUCTION.pid').exists():
    pid=int((OUT/'PRODUCTION.pid').read_text())
    try:os.kill(pid,0)
    except ProcessLookupError:pass
    else:raise RuntimeError('production PID still live; no duplicate launch')
if (ART/'SOURCE_FREEZE.json').exists():raise RuntimeError('source seal exists; inspect and explicitly resume, do not replace seal')
atomic_json(ART/'SOURCE_FREEZE.json',{'source_hashes':source_hashes(),'configuration':'configs/pilot.json','production_independent_process':True,'start_new_session':True,'source_changed_after_launch_permitted':False})
with (OUT/'PRODUCTION.log').open('ab') as log:
    p=subprocess.Popen([PYTHON,str(EXP/'scripts/runner.py')],cwd=str(EXP.parents[1]),stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env=os.environ.copy())
(OUT/'PRODUCTION.pid').write_text(str(p.pid)+'\n');print(p.pid)
