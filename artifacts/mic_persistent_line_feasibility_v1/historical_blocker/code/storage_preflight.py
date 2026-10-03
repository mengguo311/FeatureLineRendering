#!/usr/bin/env python3
"""Read-only space preflight; exit 75 means no Git writes are permitted."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import time

parser = argparse.ArgumentParser()
parser.add_argument('--payload-bytes', type=int, default=0)
args = parser.parse_args()
if args.payload_bytes < 0:
    parser.error('payload size must be nonnegative')
common = Path(subprocess.check_output(['git', 'rev-parse', '--git-common-dir'], text=True).strip()).resolve()
free = shutil.disk_usage(common).free
reserve = 1 << 30
# Reserve space for loose objects, index and commit bookkeeping; no cleanup.
write_allowance = 2 * args.payload_bytes + (2 << 20)
record = {
    'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    'git_common_dir': str(common),
    'free_bytes': free,
    'required_reserve_bytes': reserve,
    'payload_bytes': args.payload_bytes,
    'estimated_write_allowance_bytes': write_allowance,
    'required_before_write_bytes': reserve + write_allowance,
    'shortfall_bytes': max(0, reserve + write_allowance - free),
    'git_write_permitted': free >= reserve + write_allowance,
    'action': 'read_only_preflight_no_git_mutation',
}
print(json.dumps(record, indent=2, sort_keys=True))
raise SystemExit(0 if record['git_write_permitted'] else 75)
