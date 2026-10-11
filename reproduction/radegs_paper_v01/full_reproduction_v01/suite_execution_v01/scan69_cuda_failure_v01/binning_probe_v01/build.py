import os,sys,subprocess,shutil,json,hashlib,zipfile,difflib
from pathlib import Path
from patch import instrument
H=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');O=H/'full_reproduction_v01/suite_execution_v01/scan69_cuda_failure_v01/binning_probe_v01';SRC=H/'sources/paper_text_precision_v01/submodules/diff-gaussian-rasterization';DST=O/'source';B=O/'build';B.mkdir()
assert shutil.disk_usage('/').free>10*1024**3 and shutil.disk_usage(H).free>55*1024**3
shutil.copytree(SRC,DST,ignore=shutil.ignore_patterns('.git','build','*.egg-info','__pycache__','*.so'))
p=DST/'cuda_rasterizer/rasterizer_impl.cu';old=p.read_text();p.write_text(instrument(old));setup=DST/'setup.py';setup.write_text(setup.read_text().replace('"nvcc": [','"nvcc": ["-lineinfo",'))
(O/'SOURCE_PATCH.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),p.read_text().splitlines(True),fromfile=str(SRC/'cuda_rasterizer/rasterizer_impl.cu'),tofile=str(p))))
env=os.environ.copy();E=H/'envs/c24_py39';env.update(CUDA_VISIBLE_DEVICES='',CUDA_HOME=str(E),PATH=str(E/'bin')+':/usr/bin:/bin',CC=str(E/'bin/x86_64-conda-linux-gnu-cc'),CXX=str(E/'bin/x86_64-conda-linux-gnu-c++'),TORCH_CUDA_ARCH_LIST='8.6',MAX_JOBS='2',TMPDIR=str(H/'tmp'),PIP_CACHE_DIR=str(H/'cache/pip'),PYTHONDONTWRITEBYTECODE='1')
cmd=[str(E/'bin/python'),'-m','pip','wheel','--no-build-isolation','--no-deps',str(DST),'--wheel-dir',str(B/'wheels')];(B/'COMMAND.json').write_text(json.dumps({'command':cmd,'CPU_build_only':True,'diagnostic_trap_only':True,'native_parent':'8e30fca654f14cc9b79ca987828ad01f2a27604744c057d00e2496f5f192bd10'},indent=2)+'\n')
with (B/'build.log').open('w') as f:r=subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT)
assert r.returncode==0,r.returncode
wheel=next((B/'wheels').glob('*.whl'));z=zipfile.ZipFile(wheel);assert all(not x.startswith('/') and '..' not in Path(x).parts for x in z.namelist());z.extractall(B/'variant_python')
files={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [*DST.rglob('*.cu'),*DST.rglob('*.h'),DST/'setup.py',*list((B/'variant_python').rglob('*.so'))]};(B/'MANIFEST.json').write_text(json.dumps({'files':files,'method_change':False,'diagnostic_not_production':True},indent=2)+'\n');print('BUILD_PASS',json.dumps({str(p):files[str(p)] for p in (B/'variant_python').rglob('*.so')}))
