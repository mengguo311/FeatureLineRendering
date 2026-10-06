import argparse
import json
from pathlib import Path
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from runtime import EXP, ART, sha, atomic_json
p=argparse.ArgumentParser()
p.add_argument('phase',choices=['RED','GREEN'])
p.add_argument('module')
a=p.parse_args()
r=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(EXP/'tests'),'-p',a.module,'-v'],
                 text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                 env={**__import__('os').environ,'PYTHONPATH':str(EXP/'src')})
name=a.module.replace('.py','')+'_'+a.phase
log=ART/'tdd'/ (name+'.txt'); log.parent.mkdir(parents=True,exist_ok=True)
log.write_text(r.stdout)
atomic_json(log.with_suffix('.json'),{'phase':a.phase,'test':a.module,'returncode':r.returncode,
 'log_sha256':sha(log),'test_sha256':sha(EXP/'tests'/a.module),
 'source_sha256':{x.name:sha(x) for x in (EXP/'src').glob('*.py')}})
print(name, 'exit',r.returncode)
if (a.phase=='RED' and r.returncode==0) or (a.phase=='GREEN' and r.returncode!=0):
    print(r.stdout);sys.exit(1)
