"""Capture exact commands, original return codes and logs without environment output."""
from common import *
import subprocess
import time
from datetime import datetime, timezone

name, command = sys.argv[1], sys.argv[2:]
log = OUT/'runtime'/f'{name}.log'
log.parent.mkdir(parents=True, exist_ok=True)
assert not log.exists(), f'refusing to overwrite {log}'
start = time.monotonic()
record = dict(command=command, cwd=str(WORK), started_utc=datetime.now(timezone.utc).isoformat(),
              cpu_affinity=[0,1], numeric_threads=1, timeout_s=590, GPU=False)
with log.open('w') as f:
    try:
        run = subprocess.run(command, cwd=WORK, stdout=f, stderr=subprocess.STDOUT, timeout=590)
        record['returncode'] = run.returncode
    except subprocess.TimeoutExpired:
        record['returncode'] = 124
        record['timeout'] = True
record.update(wall_seconds=time.monotonic()-start, log=str(log), log_sha256=sha(log), resources=check_resources())
write_json(OUT/f'EXECUTION_{name}.json', record)
print(json.dumps(native(record), ensure_ascii=False))
sys.exit(record['returncode'])
