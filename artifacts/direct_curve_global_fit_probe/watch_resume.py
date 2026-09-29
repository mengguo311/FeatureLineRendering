"""Detached status tracking, no image/camera/checkpoint reads."""
import datetime,json,os,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];ART=Path(__file__).resolve().parent;OUT=ROOT/'out/direct_curve_global_fit_probe'
session=sys.argv[1]
def alive(pid):
 try:os.kill(pid,0);return True
 except ProcessLookupError:return False
while True:
 rows=[];done=True
 for run in ['run','rerun']:
  base=OUT/'scheduler'/session/run;path=base/'STATUS.json'
  if not path.exists():rows.append(f'- {run}: waiting for scheduler startup.');done=False;continue
  try:s=json.loads(path.read_text())
  except json.JSONDecodeError:done=False;continue
  pid=s['pid'];live=alive(pid);complete=(base/'COMPLETE.json').exists();done &= complete or not live
  rows.append(f"- {run}: PID {pid}, alive={live}, state={s.get('state')}, scene={s.get('scene','—')}, stage={s.get('stage','—')}; updated {s['time']}.")
  if s.get('child_pid'):rows.append(f"  Child strace PID {s['child_pid']}; elapsed {s.get('elapsed_seconds',0):.0f} s.")
  if complete:rows.append('  '+json.dumps(json.loads((base/'COMPLETE.json').read_text())['results'],sort_keys=True))
 timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
 text='# Direct curve probe status — '+timestamp+'\n\n'+('\n'.join(rows))+'\n\nFrozen protocol and inputs unchanged. Lego run/rerun fits preserved. CUDA replay repair is under exhaustive renderer calibration; 1/255 gate unchanged. No scientific verdict until complete evaluation, access/media/determinism checks and visual review.\n\nLogs and atomic stage seals: out/direct_curve_global_fit_probe/scheduler/'+session+'/{run,rerun}/. Prior partial evaluations are archived by the scheduler before replacement. Engineering baseline and immutable sources: RESUME_BUDGET_BASELINE.json and RESUME_IMPLEMENTATION_V2.json.\n'
 if done:text+='\nSchedulers have stopped; inspect COMPLETE.json and stage logs before interpreting results.\n'
 temp=ART/'STATUS.pending';temp.write_text(text);os.replace(temp,ART/'STATUS.md')
 if done:break
 time.sleep(30)
