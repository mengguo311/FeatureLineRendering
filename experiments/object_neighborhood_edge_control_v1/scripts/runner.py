"""Resumable production units, independent of the coding-agent process.

No formal campaign. Stage completion seals carry outputs and inputs, not a
successful-process stub. Foreign GPU jobs defer the next unit without killing.
"""
import argparse
import fcntl
import json
import os
import sys
import subprocess
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from runtime import EXP,OUT,ART,PYTHON,atomic_json,resource_guard,sha

def unit(name,args,outputs):
    seal=OUT/'seals'/('unit_'+name+'.json')
    if seal.exists():
        saved=json.loads(seal.read_text())
        if all(Path(p).exists() and sha(p)==h for p,h in saved['outputs'].items()):return
        raise RuntimeError('sealed unit changed: '+name)
    while True:
        try:guard=resource_guard();break
        except RuntimeError as e:
            if 'occupied' not in str(e):raise
            atomic_json(ART/'STATUS.json',{'state':'WAITING_FOREIGN_GPU','next_unit':name,'reason':str(e)})
            time.sleep(30)
    atomic_json(ART/'STATUS.json',{'state':'RUNNING','unit':name,'guard':guard,'pid':os.getpid(),
        'milestones':{'P0':'NATIVE_TRAINING_AND_STOCK_AUDIT_EXECUTED','P1':'TESTS_EXECUTED; CANDIDATE_ENGINEERING_ACTIVE',
                      'P2':'PILOT_VALIDATION_IN_PROGRESS','P3':'BASELINES_PENDING_OR_PARTIAL',
                      'P4':None,'P5':None,'P6':None,'P7':'IN_PROGRESS'},'TEST_opened':False})
    log=OUT/'logs'/(name+'.txt');log.parent.mkdir(parents=True,exist_ok=True)
    script_sha=sha(args[0])
    source_snapshot={str(p):sha(p) for p in (EXP/'src').glob('*.py')}
    start=time.time()
    with log.open('w') as f:
        ret=subprocess.run([PYTHON,*args],cwd=EXP.parents[1],stdout=f,stderr=subprocess.STDOUT).returncode
    if ret or any(not Path(p).exists() for p in outputs):
        atomic_json(ART/'STATUS.json',{'state':'UNIT_FAILED','unit':name,'returncode':ret,'log':str(log)})
        raise RuntimeError('unit failed '+name)
    atomic_json(seal,{'unit':name,'command':[PYTHON,*args],'start_unix':start,'duration_seconds':time.time()-start,
        'guard':guard,'returncode':ret,'outputs':{str(p):sha(p) for p in outputs},'log_sha256':sha(log),
        'config_sha256':sha(EXP/'configs/pilot.json'),'data_freeze_sha256':sha(EXP/'data/manifests/data_freeze.json'),
        'script_sha256':script_sha,'source_snapshot_sha256':source_snapshot})

def run(scenes):
    scripts=EXP/'scripts';cfg=json.loads((EXP/'configs/pilot.json').read_text())
    for scene in scenes:
        initial=OUT/'models'/scene/f'chkpnt{cfg["training"]["iterations"]}.pth'
        if not (OUT/f'seals/train_{scene}.json').exists():unit('train_'+scene,[str(scripts/'train_baseline.py'),scene],[initial,EXP/f'results/manifests/train_{scene}.json'])
        directory=OUT/'controls'/scene
        if not (OUT/f'seals/selection_{scene}.json').exists():unit('select_'+scene,[str(scripts/'extract_candidates.py'),scene],[directory/'selection.json'])
        selection=json.loads((directory/'selection.json').read_text())
        # Baselines executed and validation-scored before proposed controls.
        methods=['B0','B1','B3_uniform','B6']
        if scene=='panels_high':methods+=['B4_mask_only','B4_official']
        for method in methods:
            script='run_cob.py' if method.startswith('B4') else 'run_controls.py'
            args=[str(scripts/script),scene]
            if method=='B4_mask_only':args+=['--mask-only']
            elif not method.startswith('B4'):args+=[method]
            try:
                if method.startswith('B4'):
                    unit('B4_native_calibration',[str(scripts/'calibrate_cob.py')],[ART/'environment/cob_calibration.json'])
                unit(scene+'_'+method,args,[directory/f'{method}.pth',directory/f'{method}_edit.json'])
                unit(scene+'_'+method+'_val',[str(scripts/'evaluate.py'),scene,method],[EXP/f'results/tables/{scene}_{method}_val.json'])
            except RuntimeError as e:
                if not method.startswith('B4'):raise
                atomic_json(EXP/f'results/manifests/{scene}_{method}_blocked.json',{
                    'status':'BLOCKED_OR_UNQUALIFIED','full_reproduction_claim':False,'reason':str(e),
                    'independent_work_continues':True})
        for method in ['C0_control','C1_control']:
            unit(scene+'_'+method,[str(scripts/'run_controls.py'),scene,method],[directory/f'{method}.pth'])
            unit(scene+'_'+method+'_val',[str(scripts/'evaluate.py'),scene,method],[EXP/f'results/tables/{scene}_{method}_val.json'])
    atomic_json(ART/'STATUS.json',{'state':'PILOT_VALIDATION_COMPLETE','scenes':scenes,
        'P0':'EXECUTED','P1':'EXECUTED','P2':'VALIDATION_ONLY_WAITING_FREEZE','P3':'PARTIAL',
        'P4':None,'P5':None,'P6':None,'P7':'IN_PROGRESS','TEST_opened':False})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--scenes',nargs='+',default=['panels_high'])
    a=p.parse_args()
    OUT.mkdir(exist_ok=True)
    with (OUT/'runner.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        os.environ.update(CUDA_VISIBLE_DEVICES='0',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',MKL_NUM_THREADS='2')
        run(a.scenes)
