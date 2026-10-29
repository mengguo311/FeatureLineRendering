"""One bounded continuation of sealed checkpoints, with durable child wait receipts."""
from common import *
import subprocess,sys,signal

def run_scene(scene,start_level,budget):
    sd=OUT/scene;sd.mkdir(exist_ok=True);start=time.time();results=[]
    js(sd/'RECOVERY_SCENE_START.json',dict(utc=now(),pid=os.getpid(),start_level=start_level,budget_seconds=budget))
    for lev in range(start_level,5):
        if time.time()>DEADLINE-120:break
        with (sd/f'L{lev}_RECOVERY_CHILD.log').open('x') as f:
            child=subprocess.Popen([sys.executable,'-B',str(CODE/'runner.py'),'--scene',scene,'--level',str(lev)],stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
            js(sd/f'L{lev}_RECOVERY_CHILD_START.json',dict(pid=child.pid,utc=now(),owned_child=True));timed=False
            while child.poll() is None:
                if time.time()>min(start+budget,DEADLINE-120):
                    timed=True;os.killpg(child.pid,signal.SIGTERM)
                    try:child.wait(timeout=5)
                    except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
                    break
                time.sleep(1)
            rc=child.wait()
        rec=dict(level=lev,pid=child.pid,returncode=rc,timed_out=timed,utc=now(),checkpoint=(sd/f'L{lev}/CHECKPOINT.json').exists());js(sd/f'L{lev}_RECOVERY_CHILD_EXIT.json',rec);results.append(rec);print(scene,rec,flush=True)
        if rc!=0 or not rec['checkpoint']:break
    complete=all((sd/f'L{k}/CHECKPOINT.json').exists() for k in range(5))
    js(sd/'RECOVERY_SCENE_EXIT.json',dict(utc=now(),complete=complete,levels=results,seconds=time.time()-start));return complete

if __name__=='__main__':
    js(OUT/'RECOVERY_RUN_START.json',dict(pid=os.getpid(),utc=now(),strict_serial=True,previous_driver_returncode=143,L1_returncode='UNKNOWN',no_science_parameter_changes=True));results=[]
    spent=sum(json.loads((OUT/'scan24'/f'L{k}/METRICS.json').read_text())['seconds'] for k in (0,1))
    for scene,lev,budget in [('scan24',2,max(0,600-spent)),('ficus',0,300),('scan65',0,300)]:
        if results and not results[-1]['complete']:
            results.append(dict(scene=scene,complete=False,status='NOT_RUN_PREVIOUS_SCENE_INCOMPLETE'));continue
        if time.time()>DEADLINE-420:
            results.append(dict(scene=scene,complete=False,status='NOT_RUN_DEADLINE_RESERVE'));continue
        complete=run_scene(scene,lev,budget);results.append(dict(scene=scene,complete=complete,status='COMPLETE' if complete else 'PARTIAL'))
    js(OUT/'RECOVERY_RUN_EXIT.json',dict(utc=now(),scenes=results,all_complete=all(r['complete'] for r in results),L1_returncode='UNKNOWN_SUPERVISOR_EXIT'));print(results,flush=True)
