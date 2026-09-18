"""Recorded administrative use of the tested staging/seed/manifest functions."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path('/home/u00134/3dgs_line/tier1'); sys.path.insert(0,str(ROOT))
from src.foundation import freeze_json,verified_json,STOCK_SITE,STOCK_BINARY_SHA
from src.multiscene_training import seed_sources,stage_training_data,job_manifests,sha256,utc
out=ROOT/'out/multiscene_foundation'; gs=out/'vendor/gaussian-splatting'
cfg=verified_json(out/'config.json',(out/'config.json.sha256').read_text().strip())
original={p:subprocess.check_output(['git','show','HEAD:'+p],cwd=gs).decode() for p in ['train.py','utils/general_utils.py']}
for p,text in seed_sources(original).items():
 assert (gs/p).read_text()==original[p]
 (gs/p).write_text(text)
diff=subprocess.check_output(['git','diff','--binary'],cwd=gs)
(out/'setup/seed_injection.patch').write_bytes(diff)
assert subprocess.check_output(['git','diff','--name-only'],cwd=gs,text=True).splitlines()==['train.py','utils/general_utils.py']
sources={}
for p in subprocess.check_output(['git','ls-files','--recurse-submodules'],cwd=gs,text=True).splitlines():
 if (gs/p).is_file(): sources[p]=dict(sha256=sha256(gs/p),bytes=(gs/p).stat().st_size)
site=out/'vendor/training_site'
sys.path[:0]=[str(site),str(STOCK_SITE),str(gs)]
import torch,simple_knn._C,diff_gaussian_rasterization
assert sha256(diff_gaussian_rasterization._C.__file__)==STOCK_BINARY_SHA
runtime=dict(python=sys.version,torch=torch.__version__,cuda=torch.version.cuda,
 binaries=[dict(path=str(p),bytes=Path(p).stat().st_size,sha256=sha256(p)) for p in [simple_knn._C.__file__,diff_gaussian_rasterization._C.__file__]],
 build_repair='First build missing FLT_MAX; NVCC preinclude cfloat in addition to cstdint. No source changes.',
 build_environment=dict(CUDA_HOME='/usr/local/cuda-12.6',NVCC_PREPEND_FLAGS='--pre-include=cstdint --pre-include=cfloat',MAX_JOBS=2,TORCH_CUDA_ARCH_LIST='8.6'))
freeze_json(out/'setup/training_source.json',dict(created_utc=utc(),source_commit=cfg['training']['source_commit'],diff_sha256=hashlib.sha256(diff).hexdigest(),files=sources,runtime=runtime))
jobs=job_manifests(cfg,out,sys.executable)
for j in jobs:
 d=Path(j['directory']); d.mkdir(parents=True,exist_ok=False); Path(j['output']).mkdir()
 data=stage_training_data(cfg['scenes'][j['scene']]['dataset'],j['data'],cfg)
 freeze_json(d/'manifest.json',dict(**j,staged_data=data,config_sha256=sha256(out/'config.json'),source_manifest_sha256=sha256(out/'setup/training_source.json')))
 freeze_json(d/'entry.json',dict(source=str(gs),data=j['data'],output=j['output'],site=[str(site),str(STOCK_SITE)],arguments=j['command'][2:]))
freeze_json(out/'training_jobs.json',jobs)
print('Prepared eight isolated jobs; no training launched')
