"""Build untouched official CUDA source in local cache, without pip installation."""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from runtime import OUT, ART, atomic_json, resource_guard, sha, command

os.environ.setdefault('CUDA_HOME', '/usr/local/cuda')
os.environ.setdefault('TORCH_CUDA_ARCH_LIST', '8.6')
os.environ.setdefault('MAX_JOBS', '2')
os.environ.setdefault('OMP_NUM_THREADS', '2')
from torch.utils.cpp_extension import load

def build():
    preflight = resource_guard()
    base = OUT / 'vendor/gaussian-splatting/submodules'
    rast = base / 'diff-gaussian-rasterization'
    # glm is itself the only nested dependency required by the stock rasterizer.
    subprocess_args = ['git','-C',str(rast),'submodule','update','--init','--depth','1']
    import subprocess
    subprocess.run(subprocess_args, check=True)
    cache = OUT / 'build/stock'
    cache.mkdir(parents=True, exist_ok=True)
    sources = [rast/p for p in ('ext.cpp','rasterize_points.cu','cuda_rasterizer/rasterizer_impl.cu',
                                'cuda_rasterizer/forward.cu','cuda_rasterizer/backward.cu')]
    load(name='onec_stock_C', sources=list(map(str,sources)), build_directory=str(cache),
         extra_cuda_cflags=['-I'+str(rast/'third_party/glm'), '-include', 'cstdint'], verbose=True)
    knn = base/'simple-knn'
    cache = OUT/'build/knn'
    cache.mkdir(parents=True,exist_ok=True)
    load(name='onec_knn_C',sources=[str(knn/p) for p in ('ext.cpp','simple_knn.cu','spatial.cu')],
         build_directory=str(cache),extra_cuda_cflags=['-include','cfloat'],verbose=True)
    atomic_json(ART/'environment/native_build.json',{
        'guard':preflight,'rasterizer_sha':command(['git','-C',str(rast),'rev-parse','HEAD']),
        'source_files':{str(p.relative_to(OUT)):sha(p) for p in sources},
        'module_files':{str(p.relative_to(OUT)):sha(p) for p in (OUT/'build').rglob('*.so')},
        'global_install':False, 'max_jobs':2,'architecture':'8.6'})

if __name__ == '__main__':
    build()
