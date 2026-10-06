"""Independent GPU rerender of every saved view and every K; audit all seals."""
import gc
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/'src'))
from runtime import ART, EXP, ROOT, SOURCE, atomic_json, guard, sha
from native import load_backend
from scene_io import load_model, make_settings
import numpy as np
import torch

def main():
    guard('verify_real_start'); torch.set_num_threads(2)
    protocol=json.loads((EXP/'protocol.json').read_text());tol=protocol['absolute_fp32_tolerance']
    before=json.loads((ART/'PROTECTED_BEFORE.json').read_text())
    after={p:sha(p) for p in before}
    if before!=after:
        raise AssertionError('protected checkpoint, uploaded instructions or original module changed')
    pinned=json.loads((ART/'PINNED_SOURCE.json').read_text())
    for name,h in pinned['files'].items():
        if sha(SOURCE/name)!=h:raise AssertionError('original source changed: '+name)
    seals=[]
    for p in sorted((ART/'seals').glob('*.json')):
        s=json.loads(p.read_text())
        for f,h in s['files'].items():
            if sha(ROOT/f)!=h:raise AssertionError('saved file hash mismatch: '+f)
        seals.append(p.name)
    # Exercise the public, self-contained import without overwriting production names.
    import gaer_attribution as module
    actual=load_backend('actual')
    frozen=json.loads((ART/'CAMERA_FREEZE.json').read_text());results=[]
    with torch.no_grad():
        for name,record in frozen['scenes'].items():
            guard('verify_model_'+name);model=load_model(record)
            for camera in record['cameras']:
                unit=name+'_r_'+str(camera['index']).zfill(3);guard('verify_'+unit)
                stock=actual.GaussianRasterizer(make_settings(actual,camera))(**model)[0]
                saved=np.load(ROOT/'out/gaer_attribution_buffer_v01/views'/unit/'baseline_rgb.npy',allow_pickle=False)
                if not np.array_equal(stock.cpu().numpy(),saved):raise AssertionError('saved original RGB differs')
                previous=None;mass_previous=None;checks=[]
                for K in (1,4,8,16):
                    r=module.GaussianRasterizer(make_settings(module,camera))(**model,attribution=True,K=K)
                    if not torch.equal(stock,r.rgb):raise AssertionError('RGB differs at K='+str(K))
                    for t in (r.gaussian_weights,r.all_contribution_sum,r.final_T):
                        if not torch.isfinite(t).all() or t.requires_grad:raise AssertionError('invalid debug tensor')
                    if tuple(r.gaussian_ids.shape)!=(800,800,K) or r.gaussian_ids.dtype!=torch.int32:
                        raise AssertionError('ID shape/dtype')
                    if r.gaussian_weights.dtype!=torch.float32:raise AssertionError('weight dtype')
                    if not torch.all(r.gaussian_weights[...,1:]<=r.gaussian_weights[...,:-1]):raise AssertionError('weight order')
                    unused=r.gaussian_ids==-1
                    if not torch.all(r.gaussian_weights[unused]==0):raise AssertionError('unused slots')
                    if not torch.all(r.gaussian_weights[~unused]>0):raise AssertionError('nonpositive accepted weight')
                    if not torch.all((r.gaussian_ids>=-1)&(r.gaussian_ids<record['count'])):raise AssertionError('row ID bounds')
                    error=float((r.all_contribution_sum-r.accumulated_alpha).abs().max())
                    if error>tol:raise AssertionError('sum/alpha error='+str(error))
                    mass=r.gaussian_weights.sum(-1)
                    if previous is not None:
                        n=previous.gaussian_ids.shape[-1]
                        if not torch.equal(previous.gaussian_ids,r.gaussian_ids[...,:n]):raise AssertionError('K prefix IDs')
                        if not torch.equal(previous.gaussian_weights,r.gaussian_weights[...,:n]):raise AssertionError('K prefix weights')
                        if not torch.all(mass+tol>=mass_previous):raise AssertionError('K mass nonmonotonic')
                        if not torch.equal(previous.final_T,r.final_T) or not torch.equal(previous.all_contribution_sum,r.all_contribution_sum):
                            raise AssertionError('full diagnostics depend on K')
                    checks.append(dict(K=K,rgb_bitwise_equal=True,prefix_equal=True,sum_alpha_max_error=error,
                        global_mass_coverage=float(mass.sum()/r.accumulated_alpha.sum()),
                        missing_mass_mean=float((r.accumulated_alpha-mass).mean()),
                        missing_mass_min=float((r.accumulated_alpha-mass).min()),
                        debug_bytes=sum(t.numel()*t.element_size() for t in (r.gaussian_ids,r.gaussian_weights,r.all_contribution_sum,r.final_T))))
                    previous=r;mass_previous=mass
                results.append(dict(unit=unit,checks=checks))
                print('VERIFIED',unit,flush=True)
                del previous,r,mass_previous,mass,stock
            del model;gc.collect();torch.cuda.synchronize()
    atomic_json(ART/'results/REAL_RERUN_VERIFICATION.json',dict(passed=True,tolerance=tol,seals=seals,
        protected_inputs_unchanged=True,source_files_unchanged=len(pinned['files']),units=results))
    atomic_json(ART/'PROTECTED_AFTER.json',after)

if __name__=='__main__':main()
