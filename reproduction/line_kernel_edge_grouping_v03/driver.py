"""Durable strict-serial child supervisor; only signals its own children."""
import sys,subprocess,datetime,json,time,os,signal
from pathlib import Path
CODE=Path(__file__).resolve().parent
OUT=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_edge_grouping_v03/units/unit_001')
DEADLINE=datetime.datetime.fromisoformat('2026-10-29T09:26:08.496903+00:00').timestamp()
def js(name,value):
 with (OUT/name).open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2)
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
js('RUN_START.json',dict(pid=os.getpid(),utc=now(),deadline_utc='2026-10-29T09:26:08.496903+00:00',strict_serial=True))
receipts=[]
for scene in ('scan24','ficus','scan65'):
 if time.time()>DEADLINE-240:
  receipts.append(dict(scene=scene,status='NOT_RUN_DEADLINE'));continue
 log=OUT/(scene+'_CHILD.log')
 with log.open('x') as f:
  child=subprocess.Popen([sys.executable,'-B',str(CODE/'pilot.py'),'--scene',scene],stdout=f,stderr=subprocess.STDOUT,start_new_session=True,cwd=CODE)
  started=time.time();js(scene+'_CHILD_START.json',dict(pid=child.pid,utc=now(),owned_child=True))
  timedout=False
  while child.poll() is None:
   if time.time()>min(started+660,DEADLINE-180):
    timedout=True;os.killpg(child.pid,signal.SIGTERM)
    try:child.wait(timeout=10)
    except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
    break
   time.sleep(1)
  rc=child.wait()
 rec=dict(scene=scene,pid=child.pid,returncode=rc,timedout=timedout,utc=now(),seconds=time.time()-started,child_success_file=(OUT/scene/'CHILD_SUCCESS.json').exists())
 js(scene+'_CHILD_EXIT.json',rec);receipts.append(rec);print(json.dumps(rec),flush=True)
 if rc!=0:
  # Do not spend the pilot on downstream scenes after a broken implementation.
  break
js('RUN_EXIT.json',dict(utc=now(),receipts=receipts,all_complete=len(receipts)==3 and all(r.get('returncode')==0 for r in receipts)))
