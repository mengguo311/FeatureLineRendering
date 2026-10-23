"""Unique receipts, serial subprocess, bounded to nine minutes."""
import runtime
from runtime import ACTIVE_UNIT, output_guard, js, now
import sys
import subprocess
import time

name, *argv = sys.argv[1:]
root = output_guard(ACTIVE_UNIT/'logs'/name)
log = root.with_suffix('.log')
receipt = root.with_suffix('.receipt.json')
if log.exists() or receipt.exists():
    raise FileExistsError(name)
start = time.monotonic()
js(root.with_suffix('.start.json'), dict(argv=argv, utc=now(), timeout_seconds=540, cpu_affinity=sorted(runtime.os.sched_getaffinity(0))))
with log.open('x') as stream:
    try:
        result = subprocess.run(argv, stdout=stream, stderr=subprocess.STDOUT, timeout=540)
        rc = result.returncode
        reason = 'completed'
    except subprocess.TimeoutExpired:
        rc = 124
        reason = 'bounded_subprocess_timeout'
js(receipt, dict(argv=argv, returncode=rc, reason=reason, elapsed_seconds=time.monotonic()-start, utc=now(), log=str(log)))
print(log.read_text()[-18000:], flush=True)
print('RECEIPT', receipt, 'rc', rc, flush=True)
sys.exit(rc)
