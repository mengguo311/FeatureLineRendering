#!/usr/bin/env python
"""Durable process independent of the coding session; resume hash-sealed units."""
import os,sys,subprocess,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'out/edge_responsibility_lego_chair_v2'
OUT.mkdir(parents=True,exist_ok=True)
env=os.environ.copy()
env.update(CUDA_VISIBLE_DEVICES='0',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',MKL_NUM_THREADS='2',
           PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(OUT/'tmp'),CUDA_CACHE_PATH=str(OUT/'cache/cuda'),
           TORCH_EXTENSIONS_DIR=str(OUT/'cache/torch'),MPLCONFIGDIR=str(OUT/'cache/mpl'),XDG_CACHE_HOME=str(OUT/'cache'))
for p in ['tmp','cache','logs']:(OUT/p).mkdir(parents=True,exist_ok=True)
log=(OUT/'logs/runner.log').open('ab',buffering=0)
p=subprocess.Popen(['/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python','-u',str(Path(__file__).with_name('runner.py'))],
                   cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
(OUT/'RUNNER_PID.json').write_text(json.dumps(dict(pid=p.pid,log=str(OUT/'logs/runner.log'),start_new_session=True))+'\n')
print(json.dumps(dict(pid=p.pid,log=str(OUT/'logs/runner.log'),start_new_session=True)))
