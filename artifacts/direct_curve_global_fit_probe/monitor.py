"""Administrative sampled resource accounting; never reads scene data."""
import json,time,subprocess
from pathlib import Path
out=Path('out/direct_curve_global_fit_probe/setup')
while not (out/'STOP_MONITOR').exists():
    rows=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            cmd=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
            if 'python scripts/run_direct_curve_probe.py --scene ' not in cmd:continue
            status=(p/'status').read_text();fields={line.split(':')[0]:line.split(':')[1].strip() for line in status.splitlines() if line.startswith(('VmRSS:','VmHWM:','Threads:'))}
            rows.append(dict(pid=int(p.name),command=cmd,**fields))
        except (PermissionError,FileNotFoundError,ProcessLookupError):pass
    raw=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,used_memory','--format=csv,noheader,nounits'],text=True)
    memory={int(row.split(',')[0]):row.split(',')[1].strip() for row in raw.splitlines() if row.strip()}
    for row in rows:row['gpu_MiB']=memory.get(row['pid'])
    with (out/'RESOURCES.jsonl').open('a') as f:f.write(json.dumps(dict(time=time.time(),workers=rows))+'\n')
    time.sleep(30)
