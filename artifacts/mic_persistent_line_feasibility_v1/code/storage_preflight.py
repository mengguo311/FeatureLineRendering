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
workspace = Path(__file__).resolve().parents[3]
objects = common / "objects"
structural_ok = (common == workspace / ".git" and objects.resolve() == objects and not common.is_symlink() and not objects.is_symlink() and not (objects / "info/alternates").exists() and common.stat().st_dev == Path("/mnt/hdd1").stat().st_dev)
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
    'git_write_permitted': structural_ok and free >= reserve + write_allowance,
    'standalone_hdd_objectstore_verified': structural_ok,
    'workspace': str(workspace),
    'action': 'read_only_preflight_no_git_mutation',
}
print(json.dumps(record, indent=2, sort_keys=True))
raise SystemExit(0 if record['git_write_permitted'] else 75)
