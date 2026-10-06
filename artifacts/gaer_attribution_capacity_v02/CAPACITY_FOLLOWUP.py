"""Preregistered any-perview conditional shape and actual native style exports."""
import sys,json,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'experiments/gaer_attribution_capacity_v02'))
import numpy as np
import torch
from runtime import *
from binding import backend,scene_io
from operators import NativeWeights,binary
from shape import run_shape
from media import save

def main():
 torch.set_num_threads(2);guard('capacity_followup_start');P=json.loads((ART/'PROTOCOL.json').read_text());module=backend()
 for scene,record in P['scenes'].items():
  model=scene_io.load_model(record);views={v['key']:v for v in record['views']};cap=json.loads((ART/'results'/f'{scene}_capacity.json').read_text())
  def shape_unit():
   eligible=[f for f in cap['fits'] if f['scope']=='perview_known_target' and f['independent_FP64_certificate']['relative_dual_gap']<=.005 and f['metrics']['line_target_MSE']>.01]
   if not eligible:return dict(status='NOT_RUN',reason='no perview meets frozen any-view gap/residual condition',files=[])
   trigger=min(eligible,key=lambda f:f['independent_FP64_certificate']['relative_dual_gap']);key=P['shape']['views'][0];v=views[key];a=dict(np.load(v['source']));s=scene_io.make_settings(module,v['camera']);roi=json.loads((ART/'results'/f'{scene}_roi_{key}.json').read_text());strength=torch.tensor(np.load(ART/'downloads'/scene/f'{key}_perview_strengths.npz')['strength'],device='cuda')
   r=run_shape(scene,s,model,a,record['rois'][key],roi['groups'],ART/'downloads'/scene/f'{key}_ROI_full_CSR.npz',strength,trigger['independent_FP64_certificate'],P['shape']);r['conditional_trigger']=dict(view=trigger['view'],certificate=trigger['independent_FP64_certificate'],line_target_MSE=trigger['metrics']['line_target_MSE']);r['shape_view_original_fit_certificate']=next(f['independent_FP64_certificate'] for f in cap['fits'] if f.get('view')==key);r['gate_correction']='initial r_000-only gate NOT_RUN retained; frozen protocol permits any perview; capability in fixed r_000 with uncertified r_000 base strength, not r_000 impossibility proof';return r
  try:sealed(scene+'_shape_anyview_condition',shape_unit)
  except Exception as e:atomic_json(ART/'results'/f'{scene}_shape_ENGINEERING_FAILURE.json',dict(status='ENGINEERING_NOT_READY',error=str(e),traceback=traceback.format_exc()));print(traceback.format_exc(),flush=True)
  def export_native():
   files=[];checks=[]
   for key in P['diagnostic_views']:
    v=views[key];s=scene_io.make_settings(module,v['camera']);op=NativeWeights(module,s,model);d=np.load(ART/'downloads'/scene/f'{key}_perview_strengths.npz');x=torch.tensor(d['strength'],device='cuda');rgb=op.ink_rgb(x).cpu().numpy().transpose(1,2,0);err=float(np.abs(rgb-(1-d['ink'])[...,None]).max());assert err<3e-6;checks.append(dict(view=key,perview_native_RGB_formula_max_abs=err));p=ART/'downloads'/scene/f'{key}_perview_native_RGB.npz';npz(p,RGB=rgb,ink=1-rgb[...,0]);files.append(rel(p));files.append(save(ART/'media'/scene/'capacity'/f'{key}_perview_native.png',rgb))
   sets=np.load(ART/'downloads'/scene/'oracle_original_ID_sets.npz')
   for key in P['evaluation_views']:
    op=NativeWeights(module,scene_io.make_settings(module,views[key]['camera']),model)
    for label in ('raw_500','raw_2000','source8_oracle_500','source8_oracle_2000','diagnostic2_pooled_oracle_500','diagnostic2_pooled_oracle_2000'):
     rgb=op.ink_rgb(binary(record['count'],sets[label])).cpu().numpy().transpose(1,2,0);saved=np.load(ART/'downloads'/scene/f'{key}_{label}_fullT_ink.npz')['ink'];err=float(np.abs(rgb-(1-saved)[...,None]).max());assert err<3e-6;checks.append(dict(view=key,method=label,oracle_native_RGB_formula_max_abs=err));p=ART/'downloads'/scene/f'{key}_{label}_native_RGB.npz';npz(p,RGB=rgb);files.append(rel(p));files.append(save(ART/'media'/scene/'oracles'/f'{key}_{label}_native.png',rgb))
   return dict(checks=checks,original_geometry_opacity_all_N_retained=True,files=files)
  sealed(scene+'_native_style_exports',export_native);del model;torch.cuda.empty_cache()
if __name__=='__main__':main()
