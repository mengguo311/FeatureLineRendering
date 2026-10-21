"""Capture exact unit005 child commands, exits and wall latency, without log overwrite."""
from common import *
import subprocess
import time
from datetime import datetime,timezone

UNIT=OUT.parent/'unit_005'
name,command=sys.argv[1],sys.argv[2:]
log=UNIT/'runtime'/f'{name}.log';log.parent.mkdir(parents=True,exist_ok=True)
assert not log.exists(),log
record=dict(command=command,cwd=str(WORK),started_utc=datetime.now(timezone.utc).isoformat(),
    cpu_affinity=sorted(os.sched_getaffinity(0)),numeric_threads=1,gpu=False,timeout_s=590)
write_json(UNIT/f'EXECUTION_{name}_START.json',record)
start=time.monotonic()
with log.open('w') as handle:
    try:record['returncode']=subprocess.run(command,cwd=WORK,stdout=handle,stderr=subprocess.STDOUT,timeout=590).returncode
    except subprocess.TimeoutExpired:record.update(returncode=124,timeout=True)
record.update(wall_seconds=time.monotonic()-start,log=str(log),log_sha256=sha(log))
write_json(UNIT/f'EXECUTION_{name}.json',record)
print(json.dumps(native(record),ensure_ascii=False))
sys.exit(record['returncode'])
