"""Read detached runner progress without opening scientific results or review keys."""
import datetime, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
base = ROOT / 'out/direct_curve_global_fit_probe/scheduler/resume_20260929_v2'
print(datetime.datetime.now(datetime.timezone.utc).isoformat())
for run in ['run', 'rerun']:
    status = json.loads((base / run / 'STATUS.json').read_text())
    log = base / run / 'jobs' / f"{status.get('scene')}_{status.get('stage')}" / 'stdout.log'
    latest = log.read_text().splitlines()[-1] if log.exists() and log.stat().st_size else ''
    print(f"{run}: PID {status['pid']}, {status['state']}, {status.get('scene')} {status.get('stage')}; {latest}")
    if (base / run / 'COMPLETE.json').exists():
        print((base / run / 'COMPLETE.json').read_text())
