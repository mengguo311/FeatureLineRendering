"""Separate-process native re-render verification; no old-stage rerun writes."""
import gc,json
import numpy as np
import torch
from stage_runtime import ROOT,ART,OUT,EXP,atomic_json,sha,guard
from binding import backend,scene_io
from freeze import check_protected
from selection import silhouette,compare_sides,normalize_scores
from native_ops import feature_mass,deletion,render_subset,render_features

def verify():
    f=json.loads((ART/'PREREGISTRATION.json').read_text());p=f['protocol'];m=backend();torch.set_num_threads(2)
    checks=[]
    for name,r in f['scenes'].items():
        guard('verify_load_'+name);model=scene_io.load_model(r)
        for c in r['cameras']:
            key=name+'_'+c['key'];seal=ART/'seals'/(key+'.json')
            if not seal.exists():checks.append(dict(unit=key,passed=False,error='NOT_COMPLETED'));continue
            guard('verify_'+key)
            for path,h in json.loads(seal.read_text())['files'].items():
                if sha(ROOT/path)!=h:raise AssertionError('seal mismatch '+path)
            dst=OUT/'units'/key;s=scene_io.make_settings(m,c)
            with torch.no_grad():o=m.GaussianRasterizer(s)(**model,attribution=True,K=8)
            assert np.array_equal(o.rgb.cpu().numpy(),np.load(dst/'baseline_RGB.npy'))
            ids=o.gaussian_ids.cpu().numpy();w=o.gaussian_weights.cpu().numpy();full=o.all_contribution_sum.cpu().numpy()
            assert np.array_equal(ids,np.load(dst/'topk_ids.npy'));assert np.array_equal(w,np.load(dst/'topk_weights.npy'))
            edge,points,n,sdf=silhouette(o.accumulated_alpha.cpu().numpy(),p['alpha_threshold'])
            _,raw,_,bound=compare_sides(ids,w,full,points-2*n,points+2*n,r['count'])
            assert np.array_equal(raw,np.load(dst/'raw_score.npy'))
            mass,_=feature_mass(m,s,model);oldmass=np.load(dst/'full_visible_mass.npy')
            # Float32 atomics have nondeterministic sum order; tolerance explicit.
            assert np.allclose(mass,oldmass,rtol=3e-5,atol=2e-5)
            archive=np.load(ART/'downloads'/(key+'_scores_ids.npz'),allow_pickle=False)
            chosen=archive['gaer_ratio_0.005_ids']
            rgb=render_subset(m,s,model,chosen)
            # JPEG is a review artifact; float deletion/contribution remain exact.
            contribution=render_features(m,s,model,chosen)
            assert np.array_equal(contribution,np.load(dst/'gaer_ratio_fullT_contribution.npy'))
            deleted,alpha=deletion(m,s,model,chosen)
            assert np.array_equal(deleted,np.load(dst/'gaer_ratio_deleted_RGB.npy'))
            assert np.array_equal(alpha,np.load(dst/'gaer_ratio_deleted_alpha.npy'))
            checks.append(dict(unit=key,passed=True,selected_count=len(chosen),RGB_topK_raw_fullT_deletion_exact=True,
                full_mass_max_rerun_error=float(np.abs(mass-oldmass).max())))
            print('VERIFIED',key,flush=True);del o;gc.collect();torch.cuda.empty_cache()
        del model;gc.collect();torch.cuda.empty_cache()
    protected=check_protected(f)
    result=dict(passed=all(c['passed'] for c in checks) and len(checks)==8 and protected['passed'],units=checks,
                protected_unchanged=protected['passed'],new_native_compilation=False)
    atomic_json(ART/'results/VERIFICATION.json',result)
    if not result['passed']:raise SystemExit(1)
    return result

if __name__=='__main__':verify()
