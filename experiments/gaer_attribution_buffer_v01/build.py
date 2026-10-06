"""Rebuild pinned vanilla source and minimal GAER patch inside ignored stage output."""
from pathlib import Path
import json
import shutil
import subprocess
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))
from runtime import ART, EXP, OUT, SOURCE, atomic_json, guard, sha

def main():
    guard('build', gpu=False)
    import torch
    from torch.utils.cpp_extension import load
    torch.set_num_threads(2)
    pinned = json.loads((ART / 'PINNED_SOURCE.json').read_text())
    # Verify every original byte before copying any source. No download/install.
    for name, expected in pinned['files'].items():
        if sha(SOURCE / name) != expected:
            raise RuntimeError('pinned source changed: ' + name)
    existing = json.loads((ART/'BUILD.json').read_text()) if (ART/'BUILD.json').exists() else None
    if existing and (existing['source_aggregate_sha256'] != pinned['aggregate_sha256']
                     or existing['patch_sha256'] != sha(EXP/'native.patch')):
        raise RuntimeError('existing build belongs to different source/patch; preserve it and use a fresh stage')
    results = {}
    for variant, extension in [('original', 'gaer_original_C'), ('patched', 'gaer_native_C')]:
        guard('build_' + variant, gpu=False)
        stage = OUT / 'native' / variant
        staged_ok = existing and all((stage/n).is_file() and sha(stage/n)==h
                                    for n,h in existing['variants'][variant]['files'].items())
        if not staged_ok:
            for name in pinned['files']:
                q = stage / name
                q.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(SOURCE / name, q)
            if variant == 'patched':
                subprocess.run(['patch', '--batch', '--fuzz=0', '-p1', '-i', str(EXP / 'native.patch')], cwd=stage, check=True)
        sources = [stage / n for n in ['ext.cpp', 'rasterize_points.cu',
                   'cuda_rasterizer/rasterizer_impl.cu', 'cuda_rasterizer/forward.cu',
                   'cuda_rasterizer/backward.cu']]
        start = time.perf_counter()
        # Match actual onec_stock_C flags: no fast-math or new optimization flags.
        module = load(name=extension, sources=[str(p) for p in sources],
                      extra_cuda_cflags=['-I' + str(stage / 'third_party/glm'), '-include', 'cstdint'],
                      verbose=True)
        results[variant] = dict(extension=extension, seconds=time.perf_counter() - start,
                                binary=str(module.__file__), binary_sha256=sha(module.__file__),
                                files={n: sha(stage / n) for n in pinned['files']})
    build = dict(python=sys.executable, torch=torch.__version__,
                source_aggregate_sha256=pinned['aggregate_sha256'], patch_sha256=sha(EXP / 'native.patch'),
                CUDA_HOME='/usr/local/cuda', architecture='8.6', MAX_JOBS=2, variants=results)
    if existing:
        for variant in results:
            if results[variant]['binary_sha256'] != existing['variants'][variant]['binary_sha256']:
                raise RuntimeError('rebuild binary differs from sealed canonical build')
        atomic_json(OUT/'last_rebuild.json', build)
    else:
        atomic_json(ART/'BUILD.json', build)
    print(json.dumps({k: {x: v[x] for x in ('binary', 'binary_sha256', 'seconds')} for k,v in results.items()}, indent=2))

if __name__ == '__main__':
    main()
