"""Durable CPU-only observer of existing bounded replay. No job dispatch."""
import json,os,sys,time,hashlib
from pathlib import Path
from observer_state import classify

W=Path(__file__).resolve().parents[4];H=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01')
A=W/'artifacts/radegs_paper_reproduction_v01/full_reproduction_v01';D=H/'official_code_fix_v01'
N=H/'full_reproduction_v01/suite_execution_v01/scan69_cuda_failure_v01/rgb_vjp_memcheck_v01'
sys.path.insert(0,str(W/'reproduction/radegs_paper_v01/stage2'))
from safety import verify_seal,atomic_json,sha256

def main():
    c=json.loads((N/'state/runner_config.json').read_text());assert sha256(N/'state/runner_config.json')=='c33016b83753b0d89e436a1fe3d427db15b414734c15666dd2a2e9c780c13595'
    atomic_json(D/'observer.json',{'pid':os.getpid(),'source':__file__,'source_sha256':sha256(__file__),'dispatches_jobs':False,'scientificdone':False})
    identity=None
    while True:
        s=json.loads((N/'state/runner_state.json').read_text());proc=Path('/proc',str(s['runner_pid']));live=False
        if proc.exists() and proc.stat().st_uid==os.getuid():
            start=(proc/'stat').read_text().rsplit(')',1)[1].split()[19]
            if identity is None:identity=(s['runner_pid'],start)
            live=identity==(s['runner_pid'],start)
        terminal=s['status'] in ['ENGINEERING_NOT_READY','CUDA_REPLAY_DIAGNOSTIC_COMPLETE'] or not live
        verified=verify_seal(N/'state/smoke.seal.json','smoke',c['inputs']) if terminal else False
        rows=Path(c['model'])/'iteration_loss.jsonl';last=None;count=0
        if rows.exists():
            for line in rows.read_text().splitlines():
                try:last=json.loads(line);count+=1
                except json.JSONDecodeError:break
        p={'state':classify(s['status'],live,verified),'runner_state':s['status'],'runner_pid':s['runner_pid'] if live else None,'child_pid':s.get('child_pid'),'attempt':s.get('attempt'),'last_diagnostic_iteration':last.get('iteration') if last else None,'iteration_records':count,'seal_verified':verified,'scientific_training_count_increment':0,'method_under_test':'paper_text_precision_RGB_backward_candidate; preflight only for official route','config_path':str(N/'state/runner_config.json'),'config_sha256':sha256(N/'state/runner_config.json'),'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'scientificdone':False}
        atomic_json(D/'DIAGNOSTIC_PROGRESS.json',p)
        m=json.loads((A/'MASTER_STATUS.json').read_text());assert m['method_variant']=='official_code_fix_v01'
        m.update(diagnostic_progress=p,diagnostic_runner_pid=p['runner_pid'],diagnostic_child_pid=p['child_pid'],diagnostic_attempt=p['attempt'],diagnostic_observer_pid=None if terminal else os.getpid(),runner_pid=p['runner_pid'],childPIDs=[p['child_pid']] if p['child_pid'] else [],status=p['state'],utc=p['utc'])
        if terminal:m.update(last_event='Bounded replay terminal state observed and output seal checked; official-code GPU validation/training not dispatched.',next_action='Read official_code_fix_v01/CONTINUATION_ZH.md; if replay passed, validate new official native/loss + finite checkpoints before any scan24 training; otherwise inspect failure evidence')
        atomic_json(A/'MASTER_STATUS.json',m)
        if terminal:
            atomic_json(D/'observer.json',{'pid':None,'ended_unix':time.time(),'source':__file__,'terminal_progress':p,'dispatches_jobs':False,'scientificdone':False})
            break
        time.sleep(10)

if __name__=='__main__':main()
