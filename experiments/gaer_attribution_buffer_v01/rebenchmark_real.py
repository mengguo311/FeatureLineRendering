"""Repeat scene benchmarks without replacing canonical saved evidence or seals."""
import gc
import json
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parent/'src'))
from runtime import ART, OUT, atomic_json, guard
from native import load_backend
from scene_io import load_model, make_settings
from benchmark import run_benchmark
import torch

if __name__=='__main__':
    guard('rebenchmark_start');torch.set_num_threads(2)
    freeze=json.loads((ART/'CAMERA_FREEZE.json').read_text())
    modules={k:load_backend(k) for k in ('actual','original','patched')};results=[]
    with torch.no_grad():
        for scene,record in freeze['scenes'].items():
            guard('rebenchmark_model_'+scene);model=load_model(record)
            for camera in record['cameras']:
                unit=scene+'_r_'+str(camera['index']).zfill(3)
                rasters={k:m.GaussianRasterizer(make_settings(m,camera)) for k,m in modules.items()}
                benches=[]
                for label,backend,K in [('actual_stock','actual',None),('isolated_original','original',None),
                        ('debug_off','patched',None)]+[('K'+str(k),'patched',k) for k in (1,4,8,16)]:
                    print('BENCHMARK',unit,label,flush=True)
                    benches.append(run_benchmark(lambda b=backend,k=K:rasters[b](**model,**(dict(attribution=True,K=k) if k else {})),
                                                'rerun_'+unit+'_'+label,attribution=K is not None))
                results.append(dict(unit=unit,benchmarks=benches))
            del model;gc.collect();torch.cuda.synchronize()
    result=dict(units=results,method='independent repeat; canonical benchmark retained')
    atomic_json(OUT/'rebenchmarks'/('repeat_'+str(time.time_ns())+'.json'),result)
    atomic_json(ART/'results/REBENCHMARK_REAL.json',result)
