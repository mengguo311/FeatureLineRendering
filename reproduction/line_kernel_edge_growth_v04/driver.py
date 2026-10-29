"""Strict serial subprocess driver: actual wait returncodes per scene and level."""
from common import *
import subprocess, sys, signal

def scene_run(scene,budget):
    start=time.time();receipts=[];sd=OUT/scene;sd.mkdir(exist_ok=True);js(sd/'SCENE_START.json',dict(pid=os.getpid(),utc=now(),budget_seconds=budget))
    for lev in range(5):
        guard(120);log=sd/f'L{lev}_CHILD.log'
        with log.open('x') as f:
            child=subprocess.Popen([sys.executable,'-B',str(CODE/'runner.py'),'--scene',scene,'--level',str(lev)],stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
            js(sd/f'L{lev}_CHILD_START.json',dict(pid=child.pid,utc=now(),owned_child=True));timed=False
            while child.poll() is None:
                if time.time()>min(start+budget,DEADLINE-120):
                    timed=True;os.killpg(child.pid,signal.SIGTERM)
                    try:child.wait(timeout=5)
                    except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
                    break
                time.sleep(1)
            rc=child.wait()
        rec=dict(level=lev,pid=child.pid,returncode=rc,timed_out=timed,utc=now(),checkpoint=(sd/f'L{lev}/CHECKPOINT.json').exists());js(sd/f'L{lev}_CHILD_EXIT.json',rec);receipts.append(rec);print(scene,rec,flush=True)
        if rc!=0 or not rec['checkpoint']:break
    complete=len(receipts)==5 and all(r['returncode']==0 and r['checkpoint'] for r in receipts)
    js(sd/'SCENE_EXIT.json',dict(utc=now(),complete=complete,levels=receipts,seconds=time.time()-start));return complete

if __name__=='__main__':
    js(OUT/'RUN_START.json',dict(utc=now(),pid=os.getpid(),strict_serial=True,deadline_utc='2026-10-29T14:40:30+00:00'));results=[]
    for scene,budget in [('scan24',600),('ficus',300),('scan65',300)]:
        if results and not results[-1]['complete']:
            results.append(dict(scene=scene,complete=False,status='NOT_RUN_PREVIOUS_SCENE_INCOMPLETE'));continue
        if time.time()>DEADLINE-420:
            results.append(dict(scene=scene,complete=False,status='NOT_RUN_DEADLINE_RESERVE'));continue
        ok=scene_run(scene,budget);results.append(dict(scene=scene,complete=ok,status='COMPLETE' if ok else 'PARTIAL'))
    js(OUT/'RUN_EXIT.json',dict(utc=now(),scenes=results,all_complete=all(r['complete'] for r in results)));print('RUN_EXIT',results,flush=True)
