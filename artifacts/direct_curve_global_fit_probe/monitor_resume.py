"""Sample worker process/GPU resources until detached schedulers finish."""
import json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];base=ROOT/'out/direct_curve_global_fit_probe/scheduler'/sys.argv[1]
while True:
 rows=[];t=time.time()
 raw=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,used_memory','--format=csv,noheader,nounits'],text=True)
 memory={int(r.split(',')[0]):int(r.split(',')[1]) for r in raw.splitlines() if r.strip()}
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   cmd=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
   if not any('python scripts/'+s in cmd for s in ['run_direct_curve_probe.py','calibrate_direct_curve_replay.py']):continue
   status=(p/'status').read_text();fields={line.split(':')[0]:line.split(':')[1].strip() for line in status.splitlines() if line.startswith(('VmRSS:','VmHWM:','Threads:'))}
   stat=(p/'stat').read_text().split(') ',1)[1].split();cpu=(int(stat[11])+int(stat[12]))/os.sysconf('SC_CLK_TCK')
   rows.append(dict(pid=int(p.name),command=cmd,cpu_seconds=cpu,gpu_MiB=memory.get(int(p.name)),**fields))
  except (OSError,ValueError):pass
 with (base/'RESOURCES.jsonl').open('a') as f:f.write(json.dumps(dict(epoch=t,workers=rows))+'\n')
 if all((base/r/'COMPLETE.json').exists() for r in ['run','rerun']):break
 time.sleep(15)
