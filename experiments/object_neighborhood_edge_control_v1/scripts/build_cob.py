"""Build official COB mask renderer only as isolated B4 baseline, no pip mutation."""
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from runtime import OUT,ART,resource_guard,atomic_json,sha
os.environ.setdefault('CUDA_HOME','/usr/local/cuda')
os.environ.setdefault('TORCH_CUDA_ARCH_LIST','8.6')
os.environ.setdefault('MAX_JOBS','2')
guard=resource_guard()
from torch.utils.cpp_extension import load
r=OUT/'vendor/COB-GS/submodules/diff-gaussian-rasterization'
cache=OUT/'build/cob';cache.mkdir(parents=True,exist_ok=True)
sources=[r/p for p in ('ext.cpp','rasterize_points.cu','cuda_rasterizer/rasterizer_impl.cu','cuda_rasterizer/forward.cu','cuda_rasterizer/backward.cu')]
load(name='onec_cob_C',sources=list(map(str,sources)),build_directory=str(cache),
     extra_cuda_cflags=['-I'+str(r/'third_party/glm'),'-include','cstdint'],verbose=True)
atomic_json(ART/'environment/cob_build.json',{'guard':guard,'files':{str(p.relative_to(OUT)):sha(p) for p in sources},
                                          'binary_sha256':sha(cache/'onec_cob_C.so')})
