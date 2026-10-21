"""Run one bounded subprocess, preserving original exit code and logs."""
from runtime import *
import subprocess
import time

def main():
    name, *args = sys.argv[1:]
    if not name.replace('_', '').isalnum() or not args: raise ValueError('name and command required')
    path = ROOT / 'runtime' / name
    if path.with_suffix('.json').exists(): raise FileExistsError(path)
    resources()
    command = [PYTHON, '-B', *args]
    start = time.time()
    write_json(path.with_suffix('.started.json'), dict(command=command, start_unix=start))
    with path.with_suffix('.log').open('wb') as log:
        try:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=590, cwd=WORK)
            rc = result.returncode
        except subprocess.TimeoutExpired:
            rc = 124
    receipt = dict(command=command, returncode=rc, wall_seconds=time.time()-start,
                   log=str(path.with_suffix('.log')), log_sha256=sha(path.with_suffix('.log')),
                   resources=resources())
    write_json(path.with_suffix('.json'), receipt)
    print(json.dumps(native(receipt), allow_nan=False))
    return rc

if __name__ == '__main__':
    sys.exit(main())
