"""Explicit unit002 receipt: never dispatch a producer into historical output."""
from common import *
import subprocess
import time
import shutil
from datetime import datetime, timezone
OUT=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_p1_v02/units/unit_002')
name,command=sys.argv[1],sys.argv[2:]
log=OUT/'runtime'/f'{name}.log';log.parent.mkdir(parents=True,exist_ok=True)
assert not log.exists(),log
record=dict(command=command,cwd=str(WORK),started_utc=datetime.now(timezone.utc).isoformat(),
            cpu_affinity=sorted(os.sched_getaffinity(0)),numeric_threads=1,gpu=False,timeout_s=590)
start=time.monotonic()
with log.open('w') as f:
    try:record['returncode']=subprocess.run(command,cwd=WORK,stdout=f,stderr=subprocess.STDOUT,timeout=590).returncode
    except subprocess.TimeoutExpired:record.update(returncode=124,timeout=True)
record.update(wall_seconds=time.monotonic()-start,log=str(log),log_sha256=sha(log),
              root_free_bytes=shutil.disk_usage(WORK).free,hdd_free_bytes=shutil.disk_usage(OUT).free)
write_json(OUT/f'EXECUTION_{name}.json',record)
print(json.dumps(native(record),ensure_ascii=False));sys.exit(record['returncode'])
