#!/usr/bin/env python3
"""Durable pipeline: first-seed quality/perturbations overlap remaining training."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.foundation import verified_json,freeze_json
from src.multiscene_training import free_memory,utc

root=ROOT/'out/multiscene_foundation'
cfg=verified_json(root/'config.json',(root/'config.json.sha256').read_text().strip())
logdir=root/'setup/routes';logdir.mkdir(exist_ok=False)
statuses=[]
for scene in cfg['scene_order']:
    for seed in cfg['training']['seeds']:
        d=root/'training'/scene/f'seed_{seed}'
        # Six-hour resource wait plus four six-hour training slots is the existing
        # registered queue bound. Waiting does not allocate a GPU or busy-loop.
        deadline=time.monotonic()+4*2*cfg['training']['timeout_seconds']
        while not (d/'completion.json').exists():
            if time.monotonic()>deadline:raise TimeoutError('training queue never completed')
            time.sleep(60)
        completion=json.loads((d/'completion.json').read_text())
        if not completion['complete']:
            statuses.append(dict(scene=scene,seed=seed,state='NO_POSTERIOR'));continue
        for stage in (['quality','controlled'] if seed==1729 else ['quality']):
            deadline=time.monotonic()+cfg['training']['resource_wait_seconds']
            while free_memory(0)<6144:
                if time.monotonic()>deadline:raise TimeoutError('render resource wait exhausted')
                time.sleep(60)
            command=['strace','-f','-qq','-yy','-s','4096','-e','trace=open,openat,openat2,creat',
                '-o',str(logdir/f'{scene}_{seed}_{stage}.strace'),sys.executable,
                str(ROOT/'scripts/run_multiscene_qualification.py'),'--root',str(root),
                '--scene',scene,'--seed',str(seed),'--stage',stage]
            env=dict(os.environ,CUDA_VISIBLE_DEVICES='0',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',
                MKL_NUM_THREADS='2',PYTHONDONTWRITEBYTECODE='1',CUDA_CACHE_DISABLE='1',CUDA_MODULE_LOADING='EAGER')
            row=dict(scene=scene,seed=seed,stage=stage,command=command,started_utc=utc())
            print(json.dumps(row),flush=True)
            with (logdir/f'{scene}_{seed}_{stage}.log').open('x') as log:
                try:code=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,
                    timeout=cfg['budget']['prerequisite_seconds_per_scene']).returncode
                except subprocess.TimeoutExpired:code=124
            row.update(exit_code=code,finished_utc=utc());statuses.append(row)
            freeze_json(logdir/f'{scene}_{seed}_{stage}_exit.json',row)
freeze_json(logdir/'exit_status.json',dict(finished_utc=utc(),stages=statuses))
