"""Renderer-only calibration; C/arcs require an existing fit seal, no photos opened."""
import sys,os,json,time,ctypes,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
import torch
from src.foundation import load_asset,native_render,freeze_json,restrict_filesystem,STOCK_SITE
from src.direct_curve import native_quantiles
from scripts.run_direct_curve_probe import sha

def main():
 import argparse
 ap=argparse.ArgumentParser();ap.add_argument('--scene',required=True);ap.add_argument('--run',default='run');ap.add_argument('--domain',choices=['F','all'],required=True);ap.add_argument('--output',required=True);a=ap.parse_args()
 art=ROOT/'artifacts/direct_curve_global_fit_probe';cfg=json.loads((art/'INPUTS.json').read_text());s=cfg['scenes'][a.scene];output=Path(a.output).resolve();output.mkdir(parents=True,exist_ok=False)
 frozen=json.loads((art/'FREEZE.json').read_text());assert sha(art/'PROTOCOL.md')==frozen['protocol_sha256'];assert sha(art/'INPUTS.json')==frozen['inputs_sha256']
 fitdir=ROOT/'out/direct_curve_global_fit_probe'/a.run/a.scene/'fit'
 if a.domain=='all':
  seal=json.loads((fitdir/'SEAL.json').read_text());assert sha(fitdir/'SEAL.json')==(fitdir/'SEAL.json.sha256').read_text().strip()
  assert len(seal['assets'])==18 and all(sha(fitdir/(k+'.npz'))==h for k,h in seal['assets'].items())
 sys.path.insert(0,str(STOCK_SITE));import diff_gaussian_rasterization
 torch.cuda.init();torch.set_num_threads(1)
 for name in ['quantiles.so','quantiles_cuda_v1.so']:ctypes.CDLL(str(ROOT/'out/direct_curve_global_fit_probe/setup'/name))
 readonly=[ROOT/'src',ROOT/'scripts',art,fitdir,ROOT/'out/direct_curve_global_fit_probe/setup',ROOT/'out/vrss/vendor/official_rasterizer/cuda_rasterizer/forward.cu',Path(s['checkpoint']['path']),Path(sys.prefix),Path('/usr'),Path('/lib'),Path('/lib64'),Path('/etc'),Path('/proc'),Path('/sys'),STOCK_SITE]
 policy=dict(readonly=[str(p.resolve()) for p in readonly if p.exists()],writable=[str(output),'/dev','/tmp'],photographs=[],domain=a.domain,scene=a.scene)
 freeze_json(output/'allowlist.json',policy);restrict_filesystem(policy['readonly'],policy['writable'])
 assert sha(s['checkpoint']['path'])==s['checkpoint']['sha256'];asset=load_asset(s['checkpoint']['path']);rows=[];started=time.monotonic()
 cameras=[('F_'+str(i),s['cameras'][str(i)]) for i in cfg['F']]
 if a.domain=='all':cameras += [('C_'+str(i),s['cameras'][str(i)]) for i in cfg['C']]+[(f'arc{j}_{i:03d}',c) for j,arc in enumerate(s['arcs']) for i,c in enumerate(arc['frames'])]
 for name,c in cameras:
  state=native_render(asset,c['native_K'],c['w2c'],800,800,1.);new=native_quantiles(state,800,800);old=native_quantiles(state,800,800,library='out/direct_curve_global_fit_probe/setup/quantiles.so')
  errors=dict(rgb_max=float(abs(new['rgb']-state['stock_rgb']).max()),alpha_max=float(abs(new['alpha']-(1-state['final_T'])).max()),wrapper_max=float(abs(state['wrapper_rgb']-state['stock_rgb']).max()))
  changes={k:int(np.count_nonzero(~((new[k]==old[k])|(np.isnan(new[k])&np.isnan(old[k]))))) for k in ['alpha','quantiles','front']}
  row=dict(frame=name,errors=errors,legacy_changed_values=changes,passed=max(errors.values())<=1/255)
  freeze_json(output/(name+'.json'),row);rows.append(row);print(a.scene,name,row,flush=True)
 result=dict(passed=all(r['passed'] for r in rows),frames=len(rows),rows=rows,seconds=time.monotonic()-started,threshold=1/255,source_hashes={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'src/direct_curve.py',ROOT/'src/direct_curve_quantiles.cu',ROOT/'out/direct_curve_global_fit_probe/setup/quantiles_cuda_v1.so',ROOT/'out/vrss/vendor/official_rasterizer/cuda_rasterizer/forward.cu']})
 freeze_json(output/'RESULT.json',result);raise SystemExit(0 if result['passed'] else 1)
if __name__=='__main__':main()
