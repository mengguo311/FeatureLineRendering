"""CPU replay of unchanged C24 cull math; cuda() mapped to identity only here.

Raw TSDF mesh/data untouched. No claim of GPU/CPU bitwise equivalence.
"""
import ast,json,math,sys,traceback
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from PIL import Image
import torch
import torch.nn.functional as F
import trimesh
from skimage.morphology import binary_dilation,disk
W=Path(__file__).resolve().parents[5];H=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');O=H/'full_reproduction_v01/suite_execution_v01/scan63_result_v01';MODEL=H/'models/scan63_paper_text_precision_v01_half_30k';SOURCE=H/'sources/RaDe-GS/evaluate_dtu_mesh.py';VARIANT=H/'sources/paper_text_precision_v01/evaluate_dtu_mesh.py'
sys.path.insert(0,str(W/'reproduction/radegs_paper_v01/stage2'));from safety import atomic_json,sha256
assert not torch.cuda.is_initialized()
functions=lambda p:[x for x in ast.parse(p.read_text()).body if isinstance(x,ast.FunctionDef) and x.name in ['cull_mesh','fov2focal']]
a=functions(SOURCE);assert [ast.dump(x,include_attributes=False) for x in a]==[ast.dump(x,include_attributes=False) for x in functions(VARIANT)]
meta=json.loads((MODEL/'depth_normal/cameras_and_conventions.json').read_text());cams=[];samples=[];grids=[];events=[]
for cam in meta:
 width,height=cam['width'],cam['height']
 with Image.open(H/'data/prepared/scan63/images'/(cam['view']+'.png')) as im:mask=np.asarray(im.split()[3].resize((width,height)),dtype=np.float32)/255
 cams.append(SimpleNamespace(world_view_transform=torch.tensor(cam['extrinsic'],dtype=torch.float32).T,gt_mask=torch.from_numpy(mask)[None],FoVx=2*math.atan(width/(2*cam['fx'])),FoVy=2*math.atan(height/(2*cam['fy'])),image_width=width,image_height=height))
real_grid=F.grid_sample
def sample(*args,**kwargs):
 value=real_grid(*args,**kwargs);grids.append(args[1].detach().numpy()[0,0].copy());samples.append(value.detach().numpy()[0,-1,0].copy());return value
mesh=trimesh.load(MODEL/'recon.ply');raw_vertices=np.array(mesh.vertices);raw_faces=np.array(mesh.faces);final_mask=None;final_faces=None
class Recorder:
 def __getattr__(self,key):return getattr(mesh,key)
 def update_vertices(self,mask):
  global final_mask
  final_mask=np.array(mask);events.append({'operation':'before_update_vertices','vertices':len(mesh.vertices),'faces':len(mesh.faces),'kept_vertices':int(mask.sum()),'kept_faces_by_original_indices':int(mask[mesh.faces].all(1).sum())});mesh.update_vertices(mask);events.append({'operation':'after_update_vertices','vertices':len(mesh.vertices),'faces':len(mesh.faces)})
 def update_faces(self,mask):
  global final_faces
  final_faces=np.array(mask);events.append({'operation':'before_update_faces','mask_true':int(mask.sum())});mesh.update_faces(mask);events.append({'operation':'after_update_faces','vertices':len(mesh.vertices),'faces':len(mesh.faces)})
 def split(self,**kw):return mesh.split(**kw)
scope={'np':np,'torch':torch,'F':SimpleNamespace(grid_sample=sample),'math':math,'binary_dilation':binary_dilation,'disk':disk};exec(compile(ast.Module(body=a,type_ignores=[]),'C24_cull_math_cpu_mapping','exec'),scope)
error=None
try:
 with patch.object(torch.Tensor,'cuda',lambda t,*a,**k:t):result=scope['cull_mesh'](cams,Recorder())
except Exception as e:error={'type':type(e).__name__,'message':str(e)};traceback.print_exc()
assert not torch.cuda.is_initialized();g=np.stack(grids);sampled=np.stack(samples);valid=((g>-1)&(g<1)).all(-1);kept=(sampled+(1-valid)>0).all(0);assert np.array_equal(kept,final_mask)
rows=[]
for j,cam in enumerate(meta):
 pixels=(g[j]+1)*.5*np.array([cam['width']-1,cam['height']-1]);frac=pixels-np.floor(pixels)
 rows.append({'view':cam['view'],'in_frame_vertices':int(valid[j].sum()),'in_frame_rejected_by_mask':int((valid[j]&(sampled[j]==0)).sum()),'per_view_kept_including_outside_frame':int((sampled[j]+1-valid[j]>0).sum()),'nearest_sampling_boundary_min_pixel_margin':float(np.abs(frac-.5).min())})
r={'method':'literal C24 cull function AST with Tensor.cuda identity mapping on CPU; saved exported camera matrices and exact PIL mask resize','author_variant_math_AST_equal':True,'torch_CUDA_initialized':False,'raw_mesh_sha256':sha256(MODEL/'recon.ply'),'raw_vertices':len(raw_vertices),'raw_faces':len(raw_faces),'trimesh_version':trimesh.__version__,'error':error,'events':events,'kept_vertices_original_mask':int(final_mask.sum()),'kept_faces_original_indices':int(kept[raw_faces].all(1).sum()),'views':rows,'CPU_GPU_bitexact_claim':False,'scientificdone':False}
np.savez(O/'diagnosis/cull_cpu_arrays.npz',raw_vertices=raw_vertices,raw_faces=raw_faces,grids=g,sampled_masks=sampled,valid=valid,final_vertex_mask=kept,final_face_mask=kept[raw_faces].all(1));atomic_json(O/'diagnosis/cull_cpu_reproduction.json',r);print(json.dumps(r,indent=2))
if error:raise SystemExit(1)
