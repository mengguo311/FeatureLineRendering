"""Supplementary phase-10 score projection and all-method subset media validation.

Does not change the frozen selector, its settings, IDs, or original files.
"""
import io,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'experiments/gaer_view_selection_v01'))
import numpy as np
import torch
from PIL import Image
from stage_runtime import ROOT,ART,OUT,atomic_json,sha,digest,guard
from binding import backend,scene_io
from fixtures import cpu_ray_fixture,cpu_weights
from native_ops import feature_model,render_subset
from media import rgb_image,save_rgb,heat
from freeze import check_protected

def score_projection(m,s,model,score):
    colors=torch.as_tensor(np.repeat(np.asarray(score,np.float32)[:,None],3,1),device='cuda')
    with torch.no_grad():rgb,_=m.GaussianRasterizer(s._replace(bg=torch.zeros(3,device='cuda'),sh_degree=0))(**feature_model(model,colors))
    return rgb[0].cpu().numpy()

def main():
    f=json.loads((ART/'PREREGISTRATION.json').read_text())
    config=dict(source_sha256=sha(__file__),main_preregistration_sha256=sha(ART/'PREREGISTRATION.json'),
        score_projection='sum full-native accepted w_i * ratio_score_i; feature/bg0; display color scale=.25 only',
        selected_media='re-render each primary baseline selected-only original SH3 and recreate JPEG bytes quality93 subsampling0',
        CPU_truth_tolerance=dict(atol=2e-6,rtol=0),selection_or_threshold_changes=False)
    cfg=ART/'EXTRA_VALIDATION_FREEZE.json'
    if cfg.exists():assert digest(json.loads(cfg.read_text()))==digest(config)
    else:atomic_json(cfg,config)
    guard('extra_CPU_truth');m=backend();fixture,s=cpu_ray_fixture(m)
    score=np.linspace(.03,.7,len(fixture['means3D']))
    got=score_projection(m,s,fixture,score);want=(cpu_weights(fixture,s)*score).sum(2)
    np.testing.assert_allclose(got,want,atol=2e-6,rtol=0)
    checks=[]
    for name,r in f['scenes'].items():
        guard('extra_load_'+name);model=scene_io.load_model(r)
        for camera in r['cameras']:
            key=name+'_'+camera['key'];guard('extra_'+key);s=scene_io.make_settings(m,camera)
            archive=np.load(ART/'downloads'/(key+'_scores_ids.npz'))
            projected=score_projection(m,s,model,archive['score'])
            np.save(OUT/'units'/key/'supplemental_ratio_score_projection.npy',projected)
            save_rgb(ART/'figures'/(key+'_ratio_score_projection.jpg'),heat(projected,.25))
            media_checks={}
            for method in ('gaer_ratio','gaer_raw','alphaT_participation','visibility_matched_random'):
                chosen=archive[method+'_0.005_ids'];rgb=render_subset(m,s,model,chosen)
                np.save(OUT/'units'/key/(method+'_supplemental_selected_RGB.npy'),rgb)
                b=io.BytesIO();rgb_image(rgb).save(b,format='JPEG',quality=93,subsampling=0)
                canonical=ART/'figures'/(key+'_'+method+'_selected_only.jpg')
                assert b.getvalue()==canonical.read_bytes(),key+' '+method+' selected-only media differs'
                media_checks[method]=dict(original_SH3_JPEG_bitwise_reproduced=True,count=len(chosen),
                    canonical_sha256=sha(canonical),float_RGB_sha256=sha(OUT/'units'/key/(method+'_supplemental_selected_RGB.npy')))
            checks.append(dict(unit=key,score_projection_full_model_T=True,media_checks=media_checks,
                score_projection_sha256=sha(OUT/'units'/key/'supplemental_ratio_score_projection.npy')))
            print('EXTRA_VERIFIED',key,flush=True)
        del model;torch.cuda.empty_cache()
    protected=check_protected(f)
    result=dict(passed=len(checks)==8 and protected['passed'],units=checks,CPU_score_projection_max_error=float(np.abs(got-want).max()),
        protected_unchanged=protected['passed'],selector_unchanged=True)
    atomic_json(ART/'results/EXTRA_VALIDATION.json',result)
    if not result['passed']:raise SystemExit(1)

if __name__=='__main__':main()
