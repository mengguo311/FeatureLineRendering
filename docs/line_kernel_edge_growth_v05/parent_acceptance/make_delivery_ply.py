"""Derived visualization exports only; no numerical fitting or source edits."""
import os,sys
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='2'
os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2])
from pathlib import Path
import json,hashlib
import numpy as np
from plyfile import PlyData,PlyElement
A=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01/line_kernel_edge_growth_v05_20261031/orchestration/parent_acceptance')
V=json.loads((A/'PARENT_INDEPENDENT_ACCEPTANCE.json').read_text());audit=[]
for item in V['scenes']:
 root=A/'assets'/item['scene'];mp=np.load(root/'MEMBERSHIP.npz');src=Path(json.loads((root/'DISPLAY_SOURCE.json').read_text())['gaussians']).with_suffix('.ply');before=hashlib.sha256(src.read_bytes()).hexdigest();raw=PlyData.read(src)['vertex'].data;N=len(raw);assert N==item['kernel_count'];assert not {'edge_id','line_kernel_id'}&set(raw.dtype.names);assert all(np.all(raw[k]==0) for k in raw.dtype.names if k.startswith('f_rest_'));assert np.max(mp['edge_id'])<2**31
 rec=np.empty(N,dtype=raw.dtype.descr+[('line_kernel_id','<i4'),('edge_id','<i4')])
 for k in raw.dtype.names:rec[k]=raw[k]
 rec['line_kernel_id']=np.arange(N,dtype=np.int32);rec['edge_id']=mp['edge_id'];cols=np.load(root/'DISPLAY_COLORS.npz')['colors']
 for k in range(3):rec['f_dc_'+str(k)]=(cols[:,k]-.5)/.28209479177387814
 out=root/'DISPLAY_WITH_EDGE_IDS.ply';assert not out.exists();PlyData([PlyElement.describe(rec,'vertex')],text=False,byte_order='<',comments=['Derived dedicated-line Gaussian grouping display; not source-scene RGB GS','Original non-color vertex fields preserved exactly; only f_dc display color changed','line_kernel_id=original row; edge_id=-1 UNKNOWN; all groups provisional','No kernel motion, geometry repair or interpolated gap primitives']).write(out)
 cold=PlyData.read(out)['vertex'].data
 for k in raw.dtype.names:
  if not k.startswith('f_dc_'):assert cold[k].dtype==raw[k].dtype and cold[k].tobytes()==raw[k].tobytes(),(item['scene'],k)
 assert np.array_equal(cold['edge_id'],mp['edge_id']);assert np.array_equal(cold['line_kernel_id'],mp['line_kernel_id']);assert hashlib.sha256(src.read_bytes()).hexdigest()==before
 row={'scene':item['scene'],'original_ply':str(src),'original_sha256':before,'display_ply':str(out),'display_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'vertices':N,'all_original_noncolor_fields_bitexact':True,'additional_fields':['line_kernel_id','edge_id'],'native_viewer_shader_parity_claim':False};audit.append(row);(root/'PLY_COPY_AUDIT.json').write_text(json.dumps(row,indent=2)+'\n');print(item['scene'],'PLY_ROUNDTRIP_PASS',out.stat().st_size,flush=True)
(A/'PLY_COPY_AUDIT.json').write_text(json.dumps(audit,indent=2)+'\n')
