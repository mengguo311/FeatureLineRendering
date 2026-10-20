"""Serial execution with recoverable started/completed receipts and exact return code."""
import round015_common as c
import subprocess
import sys
import time
name, *args = sys.argv[1:]
receipt = c.R/(name+'.json'); log = c.R/'runtime'/(name.lower()+'.log')
assert not receipt.exists() and not log.exists()
c.resources()
log.parent.mkdir(exist_ok=True)
cmd = ['taskset','-c','0,1','timeout','600',sys.executable]+args
obj = {'argv':cmd,'execution_state':'running','returncode':None,'log':str(log),
       'cpu_affinity':[0,1],'threads_max':2,'GPU':False}
c.write(receipt,obj)
t = time.monotonic()
with log.open('w') as f:
    result = subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
obj.update(execution_state='completed',returncode=result.returncode,wall_seconds=time.monotonic()-t,log_sha256=c.sha(log))
c.write(receipt,obj)
print(__import__('json').dumps(obj),flush=True)
sys.exit(result.returncode)
