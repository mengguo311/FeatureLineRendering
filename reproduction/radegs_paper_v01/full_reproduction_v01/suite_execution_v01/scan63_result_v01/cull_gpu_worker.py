"""Admitted GPU replay of literal C24 cull math; original failure is diagnostic evidence.

Raw TSDF mesh/data untouched. No claim of GPU/CPU bitwise equivalence.
"""
import ast,json,math,sys,traceback,os,argparse,time
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
assert os.environ['CUDA_VISIBLE_DEVICES']=='GPU-d2d1e4fd-e246-0633-3343-ccc0a0bd981a'
functions=lambda p:[x for x in ast.parse(p.read_text()).body if isinstance(x,ast.FunctionDef) and x.name in ['cull_mesh','fov2focal']]
a=functions(SOURCE);assert [ast.dump(x,include_attributes=False) for x in a]==[ast.dump(x,include_attributes=False) for x in functions(VARIANT)]
ap=argparse.ArgumentParser();ap.add_argument('--config',required=True);args=ap.parse_args();config=json.loads(Path(args.config).read_text());O=Path(config['diagnostic_output'])/os.environ['RADEGS_ATTEMPT'];O.mkdir(parents=True,exist_ok=False)
meta=json.loads((MODEL/'depth_normal/cameras_and_conventions.json').read_text());cams=[];samples=[];grids=[];events=[]
for cam in meta:
 width,height=cam['width'],cam['height']
 with Image.open(H/'data/prepared/scan63/images'/(cam['view']+'.png')) as im:mask=np.asarray(im.split()[3].resize((width,height)),dtype=np.float32)/255
 cams.append(SimpleNamespace(world_view_transform=torch.tensor(cam['extrinsic'],dtype=torch.float32,device='cuda').T,gt_mask=torch.from_numpy(mask)[None],FoVx=2*math.atan(width/(2*cam['fx'])),FoVy=2*math.atan(height/(2*cam['fy'])),image_width=width,image_height=height))
real_grid=F.grid_sample
def sample(*args,**kwargs):
 value=real_grid(*args,**kwargs);grids.append(args[1].detach().cpu().numpy()[0,0].copy());samples.append(value.detach().cpu().numpy()[0,-1,0].copy());return value
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
 result=scope['cull_mesh'](cams,Recorder())
except Exception as e:error={'type':type(e).__name__,'message':str(e)};traceback.print_exc()
assert torch.cuda.is_initialized();g=np.stack(grids);sampled=np.stack(samples);valid=((g>-1)&(g<1)).all(-1);kept=(sampled+(1-valid)>0).all(0);assert np.array_equal(kept,final_mask)
rows=[]
for j,cam in enumerate(meta):
 pixels=(g[j]+1)*.5*np.array([cam['width']-1,cam['height']-1]);frac=pixels-np.floor(pixels)
 rows.append({'view':cam['view'],'in_frame_vertices':int(valid[j].sum()),'in_frame_rejected_by_mask':int((valid[j]&(sampled[j]==0)).sum()),'per_view_kept_including_outside_frame':int((sampled[j]+1-valid[j]>0).sum()),'nearest_sampling_boundary_min_pixel_margin':float(np.abs(frac-.5).min())})
r={'method':'literal C24 cull function AST on admitted GPU0; sealed exported camera matrices on CUDA and exact PIL mask resize','author_variant_math_AST_equal':True,'torch_CUDA_initialized':True,'raw_mesh_sha256':sha256(MODEL/'recon.ply'),'raw_vertices':len(raw_vertices),'raw_faces':len(raw_faces),'trimesh_version':trimesh.__version__,'error':error,'events':events,'kept_vertices_original_mask':int(final_mask.sum()),'kept_faces_original_indices':int(kept[raw_faces].all(1).sum()),'views':rows,'CPU_GPU_bitexact_claim':False,'scientificdone':False}
np.savez(O/'cull_gpu_arrays.npz',raw_vertices=raw_vertices,raw_faces=raw_faces,grids=g,sampled_masks=sampled,valid=valid,final_vertex_mask=kept,final_face_mask=kept[raw_faces].all(1));from cull_outcome import classify_author_mask
r['classification']=classify_author_mask(kept,raw_faces)
with np.load(H/'full_reproduction_v01/suite_execution_v01/scan63_result_v01/diagnosis/cull_cpu_arrays.npz') as z:
 r['CPU_GPU_final_mask_identical']=bool(np.array_equal(kept,z['final_vertex_mask']))
 r['CPU_GPU_sampled_masks_identical']=bool(np.array_equal(sampled,z['sampled_masks']))
 r['CPU_GPU_grid_max_abs_error']=float(np.abs(g-z['grids']).max())
assert r['CPU_GPU_final_mask_identical'] and r['CPU_GPU_sampled_masks_identical']
assert r['classification']['status']=='EMPTY_AFTER_AUTHOR_MASK' and error and error['type']=='IndexError'
assert sha256(MODEL/'recon.ply')==r['raw_mesh_sha256']
r['diagnostic_pass_meaning']='same actual author negative cull outcome verified on GPU; original evaluator failure retained, no official metric/evaluation success'
r['optimizer_steps']=0
result=O/'cull_gpu_reproduction.json';atomic_json(result,r)
outputs=[result,O/'cull_gpu_arrays.npz']
atomic_json(config['reports']['smoke'],{'status':'PASS','stage':'smoke','inputs':config['inputs'],'attempt':os.environ['RADEGS_ATTEMPT'],'outputs':{str(q):sha256(q) for q in outputs},'details':{'diagnostic_only':True,'original_evaluator_succeeded':False,'official_metric':None,'result':str(result)},'unix':time.time(),'scientificdone':False})
print(json.dumps(r,indent=2))
