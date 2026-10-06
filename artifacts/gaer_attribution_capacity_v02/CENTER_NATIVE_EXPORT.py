"""Actual full-T black ink for both old center budgets on both reserved views."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'experiments/gaer_attribution_capacity_v02'))
import numpy as np
import torch
from runtime import *
from binding import backend,scene_io
from operators import NativeWeights,binary
from media import save

def main():
 torch.set_num_threads(2);P=json.loads((ART/'PROTOCOL.json').read_text());m=backend()
 for scene,record in P['scenes'].items():
  model=scene_io.load_model(record);vs={v['key']:v for v in record['views']};sets=np.load(ART/'downloads'/scene/'oracle_original_ID_sets.npz')
  def calculate():
   files=[];checks=[]
   for key in P['evaluation_views']:
    op=NativeWeights(m,scene_io.make_settings(m,vs[key]['camera']),model)
    for B in P['budgets']:
     label=f'center_{B}';rgb=op.ink_rgb(binary(record['count'],sets[label])).cpu().numpy().transpose(1,2,0);old=np.load(ART/'downloads'/scene/f'{key}_{label}_fullT_ink.npz')['ink'];err=float(np.abs(rgb-(1-old)[...,None]).max());assert err<3e-6;p=ART/'downloads'/scene/f'{key}_{label}_native_RGB.npz';npz(p,RGB=rgb);files.append(rel(p));files.append(save(ART/'media'/scene/'oracles'/f'{key}_{label}_native.png',rgb));checks.append(dict(view=key,budget=B,formula_max_abs=err))
   return dict(script_sha256=sha(ART/'CENTER_NATIVE_EXPORT.py'),checks=checks,files=files)
  sealed(scene+'_native_center_exports',calculate);del model;torch.cuda.empty_cache()
if __name__=='__main__':main()
