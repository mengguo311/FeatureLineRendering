"""CPU-only isolated official-semantics native build; no installation."""
import os,sys,subprocess,json,hashlib,shutil,zipfile,time
from pathlib import Path

H=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');D=H/'depth_only_v01/scan55_failure_v01/repair_v01';E=H/'official_code_fix_v01/env';S=D/'source/diff-gaussian-rasterization';B=D/'build'
assert not B.exists();assert shutil.disk_usage('/').free>10*2**30 and shutil.disk_usage(H).free>55*2**30
assert (E/'bin/nvcc').exists() and (S/'third_party/glm/glm/glm.hpp').exists()
B.mkdir();setup=S/'setup.py';before=setup.read_text();assert before.count('"nvcc": [')==1;assert '"-lineinfo"' in before
env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES='',CUDA_HOME=str(E),PATH=str(E/'bin')+':/usr/bin:/bin',CC=str(E/'bin/x86_64-conda-linux-gnu-cc'),CXX=str(E/'bin/x86_64-conda-linux-gnu-c++'),TORCH_CUDA_ARCH_LIST='8.6',MAX_JOBS='2',TMPDIR=str(H/'tmp'),PIP_CACHE_DIR=str(D/'cache/pip'),PYTHONDONTWRITEBYTECODE='1')
cmd=[str(E/'bin/python'),'-m','pip','wheel','--no-index','--no-build-isolation','--no-deps',str(S),'--wheel-dir',str(B/'wheels')]
(B/'COMMAND.json').write_text(json.dumps({'command':cmd,'CPU_build_only':True,'compiler':env['CXX'],'CUDA_HOME':str(E),'architecture':'8.6','max_jobs':2,'scientificdone':False},indent=2)+'\n')
with (B/'build.log').open('w') as f:r=subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT)
if r.returncode:raise RuntimeError('private native build failed; log preserved')
w=next((B/'wheels').glob('*.whl'))
with zipfile.ZipFile(w) as z:
    assert all(not n.startswith('/') and '..' not in Path(n).parts for n in z.namelist());z.extractall(B/'official_python')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
files=[*S.glob('*.cu'),*S.glob('*.h'),S/'setup.py',S/'ext.cpp',S/'diff_gaussian_rasterization/__init__.py',*list((S/'cuda_rasterizer').glob('*')),*list((S/'third_party/glm/glm').rglob('*.hpp')),*list((S/'third_party/glm/glm').rglob('*.inl')),*list((S/'third_party/glm/glm').rglob('*.h'))]
files=[p for p in files if p.is_file()]
native=next((B/'official_python').rglob('*.so'));report={'method_variant':'official_code_fix_v01','native':str(native),'native_sha256':sha(native),'wheel_sha256':sha(w),'source_files':{str(p):sha(p) for p in files},'isolated_import_path':str(B/'official_python'),'official_C24_loss_native':True,'GPU_validation_pending':True,'installed_into_environment':False,'scientificdone':False}
(B/'MANIFEST.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'build':'PASS','native_sha256':sha(native),'source_files':len(files),'GPU_validation_pending':True}),flush=True)
