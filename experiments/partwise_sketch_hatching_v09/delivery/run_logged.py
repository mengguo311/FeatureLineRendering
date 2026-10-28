import runtime
import argparse
import subprocess
import time

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--name', required=True)
    p.add_argument('argv', nargs=argparse.REMAINDER)
    a = p.parse_args()
    argv = a.argv[1:] if a.argv[:1] == ['--'] else a.argv
    receipt = runtime.guard(runtime.UNIT / 'logs' / (a.name + '.json'))
    if receipt.exists():
        raise FileExistsError(receipt)
    log = receipt.with_suffix('.log')
    record = dict(argv=argv, started_utc=runtime.now(), child_returncode='UNKNOWN')
    runtime.js(receipt.with_suffix('.start.json'), record)
    start = time.monotonic()
    with log.open('x') as f:
        try:
            result = subprocess.run(argv, stdout=f, stderr=subprocess.STDOUT, timeout=180)
            record['child_returncode'] = result.returncode
        except subprocess.TimeoutExpired:
            record['timeout'] = True
    record.update(finished_utc=runtime.now(), seconds=time.monotonic()-start, log=str(log))
    runtime.js(receipt, record)
    print(runtime.json.dumps(record), flush=True)
    raise SystemExit(record['child_returncode'] if isinstance(record['child_returncode'], int) else 124)

if __name__ == '__main__':
    main()
