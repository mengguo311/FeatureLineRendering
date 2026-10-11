"""CPU execution of exact C24 reset method and actual parameter boundary audit.
No CUDA import/init, no model writes, no alternate training loss or reset patch.
"""
import ast,json,sys,types
from pathlib import Path
import torch,numpy as np
from plyfile import PlyData
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'reproduction/radegs_paper_v01/stage2'))
from safety import sha256,atomic_json
HDD=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');SRC=HDD/'sources/RaDe-GS/scene/gaussian_model.py';OUT=HDD/'full_reproduction_v01/suite_execution_v01'
module=ast.parse(SRC.read_text());cls=next(x for x in module.body if isinstance(x,ast.ClassDef) and x.name=='GaussianModel');fn=next(x for x in cls.body if isinstance(x,ast.FunctionDef) and x.name=='reset_opacity');scope={'torch':torch};exec(compile(ast.Module(body=[fn],type_ignores=[]),'C24_exact_reset_opacity','exec'),scope)
class Fixture:
 def __init__(self,logit):
  self._opacity=torch.tensor([[logit]],dtype=torch.float32);self.get_scaling=torch.tensor([[.0001,.0001,.0001]],dtype=torch.float32);self.filter_3D=torch.tensor([[.001]],dtype=torch.float32);self.inverse_opacity_activation=lambda x:torch.log(x/(1-x))
 @property
 def get_opacity_with_3D_filter(self):
  s=self.get_scaling.square();coef=torch.sqrt(s.prod(1)/(s+self.filter_3D.square()).prod(1));return torch.sigmoid(self._opacity)*coef[:,None]
 def replace_tensor_to_optimizer(self,t,name):return {name:t}
rows=[]
for value in [0.,10.,16.,17.,18.,20.,30.]:
 x=Fixture(value);before=float(x.get_opacity_with_3D_filter[0,0]);scope['reset_opacity'](x);after=float(x.get_opacity_with_3D_filter[0,0]);v=float(x._opacity[0,0]);rows.append({'initial_finite_logit':value,'effective_before':before,'effective_after':after,'logit_after':v if np.isfinite(v) else '+inf' if v>0 else 'nonfinite','activated_opacity_after':float(torch.sigmoid(x._opacity)[0,0]),'real_method_produces_nonfinite':not np.isfinite(v)})
assert any(x['real_method_produces_nonfinite'] for x in rows)
actual=[]
for it in [15000,30000]:
 path=HDD/f'models/scan24_paper_text_precision_v01_half_30k/point_cloud/iteration_{it}/point_cloud.ply';p=PlyData.read(path)['vertex'].data;s=np.exp(np.stack([p[f'scale_{i}'] for i in range(3)],1).astype(float));coef=np.sqrt(np.prod(s*s/(s*s+p['filter_3D'][:,None].astype(float)**2),axis=1));bad=~np.isfinite(p['opacity']);eff=coef/(1+np.exp(-p['opacity'].astype(float)))
 actual.append({'iteration':it,'count':len(p),'nonfinite_opacity':int(bad.sum()),'nonfinite_fraction':float(bad.mean()),'nonfinite_effective_opacity':eff[bad].tolist(),'nonfinite_above_pixel_cutoff_upper_bound':int((eff[bad]>=1/255).sum()),'finite_opacity_below_pixel_cutoff':int(((eff<1/255)&~bad).sum()),'indices':np.flatnonzero(bad).tolist(),'source_ply_sha256':sha256(path)})
result={'source':str(SRC),'source_sha256':sha256(SRC),'exact_AST_function':'GaussianModel.reset_opacity','synthetic_cases':rows,'actual':actual,'scope':'CPU mechanism reproduction, not historical proof of exactly which training reset created each+Inf; per-reset histories were not saved','conclusion':'float32 sigmoid can round a finite logit to1; C24 unneeded inverse-sigmoid roundtrip can produce+Inf. Activated opacity remains finite.34points cannot by their count account for84%finite-point opacity collapse; complete optimization causality remains unproven.','production_patch_applied':False,'optimizer_steps':0,'CUDA_initialized':torch.cuda.is_initialized()}
assert not result['CUDA_initialized'];atomic_json(OUT/'OPACITY_BOUNDARY_AUDIT.json',result);print(json.dumps(result,indent=2))
