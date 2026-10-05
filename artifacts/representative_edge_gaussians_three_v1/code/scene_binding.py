"""Scene-only binding, inherited metadata and hash-qualified read-only capacity reuse."""
from pathlib import Path
import json,hashlib
import numpy as np
SCENES=('lego','chair','ficus')
REFERENCE=Path('/home/u00134/3dgs_line/representative_edge_gaussians_v1')
HYBRID=Path('/home/u00134/3dgs_line/hybrid_raster_evidence_v2')
def scene_id(s):
 s='ficus' if s=='tree' else s
 if s not in SCENES:raise ValueError('Unknown scene '+s)
 return s
def display(s):return 'tree / Ficus (ficus)' if scene_id(s)=='ficus' else scene_id(s).capitalize()
def output_path(root,p):
 p=Path(p).resolve();allowed=[Path(root).resolve()/x/'representative_edge_gaussians_three_v1' for x in ('out','artifacts')]
 if not any(p==r or r in p.parents for r in allowed):raise ValueError('Output containment')
 return p
def budget_counts(n):return [int(np.ceil(n*p/100)) for p in (1,3,10)]
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for block in iter(lambda:f.read(1048576),b''):h.update(block)
 return h.hexdigest()
def inherited_normalization():
 return json.loads((REFERENCE/'out/representative_edge_gaussians_v1/NORMALIZATION.json').read_text())
def capacity64():
 path=REFERENCE/'out/representative_edge_gaussians_v1/native/top64/BUILD.json';b=json.loads(path.read_text());assert b['returncode']==0 and b['topk']==64
 assert b['library_sha256']=='57c8ffbe5fb190369548667097a9c9106bd566775747045749a2b2f976a49b5f'
 assert sha(b['library'])==b['library_sha256']
 d=path.parent
 assert sha(d/'cuda_rasterizer/render_forward.cu')==b['forward_sha256'] and sha(d/'capacity.patch')==b['patch_sha256']
 old=(Path('/mnt/hdd1/u00134/hybrid_raster_trained_models_v1/gaussian_edge_attribution_v1/native_extension/top32/cuda_rasterizer/render_forward.cu')).read_bytes()
 assert (d/'cuda_rasterizer/render_forward.cu').read_bytes()==old.replace(b'constexpr int ATTR_TOPK = 32;',b'constexpr int ATTR_TOPK = 64;')
 return dict(b,read_only_reuse=True,build_manifest_path=str(path),build_manifest_sha256=sha(path),new_build_seconds=0)
