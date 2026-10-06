"""Same centered analytic fixture for stock/OFF/K=1,4,8,16 performance."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/'src'))
sys.path.insert(0,str(Path(__file__).resolve().parent/'tests'))
from runtime import ART, atomic_json, guard
from native import load_backend
from test_native import center_fixture, settings
from benchmark import run_benchmark
import torch

if __name__=='__main__':
    guard('synthetic_benchmark');torch.set_num_threads(2)
    modules={k:load_backend(k) for k in ('actual','original','patched')}
    rasterizers={k:m.GaussianRasterizer(settings(m)) for k,m in modules.items()}
    fixture=center_fixture('center_many')
    results=[]
    with torch.no_grad():
        for label,backend,K in [('actual_stock','actual',None),('isolated_original','original',None),
                ('debug_off','patched',None)]+[('K'+str(k),'patched',k) for k in (1,4,8,16)]:
            print('BENCHMARK',label,flush=True)
            results.append(run_benchmark(lambda b=backend,k=K:rasterizers[b](**fixture, **(dict(attribution=True,K=k) if k else {})),
                                        'synthetic_'+label,attribution=K is not None))
    atomic_json(ART/'results/SYNTHETIC_BENCHMARK.json',dict(fixture='center_many',resolution=[1,1],
                                                        gaussian_count=20,benchmarks=results))
