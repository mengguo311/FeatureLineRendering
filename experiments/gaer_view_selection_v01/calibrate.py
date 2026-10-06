"""Independent null floor, not adjusted with Lego/Chair scores or deletion outcomes."""
import json
import numpy as np
import torch
from stage_runtime import ART,EXP,atomic_json,guard,sha
from binding import backend
from fixtures import cpu_ray_fixture,cpu_weights,flat_fixture
from native_ops import feature_mass
from selection import compare_sides,normalize_scores
from media import sheet,heat

def calibrate():
    path=ART/'results/SYNTHETIC.json'
    if path.exists():return json.loads(path.read_text())
    guard('synthetic_calibration');m=backend();p=json.loads((EXP/'protocol.json').read_text())
    f,s=cpu_ray_fixture(m);expected=cpu_weights(f,s);mass,alpha=feature_mass(m,s,f)
    error=float(np.abs(expected.sum((0,1))-mass).max())
    if not np.allclose(expected.sum((0,1)),mass,rtol=2e-5,atol=2e-6):raise RuntimeError('full mass oracle failed')
    np.savez_compressed(ART/'downloads/CPU_RAY_TRUTH.npz',weights=expected,mass=mass,alpha=alpha)
    a,s,truth=flat_fixture(m,False);b,_,_=flat_fixture(m,True)
    with torch.no_grad():
        ra=m.GaussianRasterizer(s)(**a,attribution=True,K=8)
        rb=m.GaussianRasterizer(s)(**b,attribution=True,K=8)
    ids=ra.gaussian_ids.cpu().numpy();w=ra.gaussian_weights.cpu().numpy();full=ra.all_contribution_sum.cpu().numpy()
    # Independent truth: this fixed grid is well inside the z=1 square, away
    # from its silhouette; ALL points are negative geometry examples.
    yy,xx=np.meshgrid(np.arange(22,43),np.arange(22,43),indexing='ij')
    points=np.column_stack([yy.ravel(),xx.ravel()]);normal=np.tile([0.,1.],(len(points),1))
    l1,raw,_,bound=compare_sides(ids,w,full,points-2*normal,points+2*normal,len(a['means3D']))
    fm,_=feature_mass(m,s,a);ratio=normalize_scores(raw,fm,p['min_visibility_mass'],p['epsilon'])
    floor=max(p['numerical_ratio_floor'],2*float(np.percentile(ratio,99.9)))
    native_same=torch.equal(ra.gaussian_ids,rb.gaussian_ids) and torch.equal(ra.gaussian_weights,rb.gaussian_weights)
    out=dict(passed=error<.001 and native_same,cpu_ray_max_mass_error=error,
        cpu_ray_shape=list(expected.shape),truth=truth,full_visibility_method='native RGB[0].sum gradient wrt per-original-row precomputed color[0], bg0',
        null_region='441 fixed interior pixels (22..42)^2; analytic coplanar truth says no geometry edges',
        null_observed_L1_mean=float(l1.mean()),null_observed_L1_max=float(l1.max()),
        null_residual_bound_mean=float(bound.mean()),null_ratio_p999=float(np.percentile(ratio,99.9)),auto_ratio_floor=floor,
        texture_weights_bitwise_identical=bool(native_same),texture_RGB_max_change=float((ra.rgb-rb.rgb).abs().max()),
        standalone_B4_detection='NOT_RUN; no edge-gated AUROC/AP or independent detector claim',
        conclusion='smooth coplanar individual footprint derivatives produce attribution differences without interior geometry edges')
    maps=np.zeros((65,65));maps[points[:,0],points[:,1]]=l1
    sheet(ART/'figures/synthetic_flat_null.jpg',[
        ('constant coplanar native',ra.rgb.cpu().numpy()),('texture-only native',rb.rgb.cpu().numpy()),
        ('fixed interior attribution L1; geometry truth=0',heat(maps)),('alpha; silhouette distinct from interior truth',ra.accumulated_alpha.cpu().numpy())],tile=390)
    atomic_json(path,out);return out

if __name__=='__main__': print(json.dumps(calibrate()))
