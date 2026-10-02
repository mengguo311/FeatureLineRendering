#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
export PATH=/home/u00134/bin/miniconda3/envs/codex-cli/bin:/home/u00134/bin/miniconda3/bin:$PATH
export PYTHONDONTWRITEBYTECODE=1
export CUDA_HOME=/usr/local/cuda
export TORCH_CUDA_ARCH_LIST=8.6
export MAX_JOBS=2
export TMPDIR="$ROOT/out/hybrid_raster_evidence_v2/tmp"
export XDG_CACHE_HOME="$ROOT/out/hybrid_raster_evidence_v2/cache"
export TORCH_EXTENSIONS_DIR="$ROOT/out/hybrid_raster_evidence_v2/torch_extensions"
mkdir -p "$TMPDIR" "$XDG_CACHE_HOME" "$TORCH_EXTENSIONS_DIR" out/hybrid_raster_evidence_v2/native_logs
PY=/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python
"$PY" -B - <<'PY'
import hashlib, json, pathlib, shutil, subprocess
root=pathlib.Path.cwd()
source=pathlib.Path('/home/u00134/3dgs_line/hao_mukai_rade_native_f1/native/rasterizer')
out=root/'out/hybrid_raster_evidence_v2/native'
patch=root/'native_patches/rade_f1.patch'
if not patch.is_file():
    raise SystemExit('Missing tracked historical instrumentation patch')
for variant in ('patched','unpatched'):
    dest=out/variant
    dest.mkdir(parents=True,exist_ok=True)
    files=list(source.glob('*.cu'))+list(source.glob('*.cpp'))+list(source.glob('*.h'))
    files += [source/'setup.py',source/'LICENSE.md',source/'README.md',
              source/'diff_gaussian_rasterization/__init__.py',source/'third_party/glm/copying.txt']
    files += list((source/'cuda_rasterizer').glob('*'))
    files += [p for p in (source/'third_party/glm/glm').rglob('*') if p.is_file()]
    for p in files:
        q=dest/p.relative_to(source)
        q.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(p,q)
    if variant=='unpatched':
        subprocess.run(['patch','--batch','-R','-p1','-i',str(patch)],cwd=dest,check=True)
manifest={'source_reference':str(source),'upstream_commit':'d72f20792005ae1d6555a82aa2d15345f247604e',
          'instrumentation_patch_sha256':hashlib.sha256(patch.read_bytes()).hexdigest(),'files':{}}
for variant in ('patched','unpatched'):
    d=out/variant
    manifest['files'][variant]={str(p.relative_to(d)):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(d.rglob('*')) if p.is_file() and p.suffix in ('.py','.cu','.cpp','.h','.hpp','.inl','.txt','.md') and 'build' not in p.relative_to(d).parts}
manifest['source_hash']=hashlib.sha256(json.dumps(manifest['files'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
(out/'SOURCE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('SOURCE_HASH',manifest['source_hash'],flush=True)
PY
for variant in patched unpatched; do
  (
    cd "out/hybrid_raster_evidence_v2/native/$variant"
    "$PY" -B setup.py build_ext --inplace
  ) > "out/hybrid_raster_evidence_v2/native_logs/build_${variant}.log" 2>&1
done
"$PY" -B - <<'PY'
import hashlib,json,pathlib,sys
out=pathlib.Path('out/hybrid_raster_evidence_v2/native')
manifest=json.loads((out/'SOURCE_MANIFEST.json').read_text())
build={'source_hash':manifest['source_hash'],'python':sys.executable,'variants':{}}
for variant in ('patched','unpatched'):
    binaries=list((out/variant/'diff_gaussian_rasterization').glob('_C*.so'))
    assert len(binaries)==1,binaries
    p=binaries[0]
    build['variants'][variant]={'path':str(p.resolve()),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
build['build_hash']=hashlib.sha256(json.dumps(build,sort_keys=True,separators=(',',':')).encode()).hexdigest()
(out/'BUILD.json').write_text(json.dumps(build,indent=2)+'\n')
print(json.dumps(build,indent=2))
PY
