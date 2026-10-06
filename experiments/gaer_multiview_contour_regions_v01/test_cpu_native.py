"""CPU replica validation; execute before/after implementation for true RED/GREEN."""
import json
import hashlib
import sys
import time
from pathlib import Path
import numpy as np
import cpu_native
from cpu_native import load_model_cpu, preprocess, rasterize, render, sha

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT/'artifacts/gaer_multiview_contour_regions_v01/tdd'

def synthetic():
    c=dict(width=32,height=32,FoVx=0.7,FoVy=0.7,w2c=np.eye(4).tolist())
    m=dict(xyz=np.array([[0,0,2],[0,0,3]],np.float32),
           scales=np.full((2,3),.05,np.float32),rotations=np.array([[1,0,0,0]]*2,np.float32),
           opacity=np.array([.6,.8],np.float32),shs=np.zeros((2,16,3),np.float32))
    p=preprocess(m,c)
    assert np.allclose(p['xy'],15.5),p['xy']
    r=rasterize(p,np.ones((32,32,1),np.float32))
    assert np.max(np.abs(r['mass']-r['adjoints'][:,0]))<1e-5
    assert abs(float(r['mass'].sum())-float(r['alpha'].sum()))<1e-3
    assert r['mass'][0]>r['mass'][1],r['mass']
    assert np.allclose(r['rgb'],1-r['alpha'][...,None]*.5,atol=1e-6)
    # Feature forward/adjoint duality with original IDs, without K truncation.
    f=np.array([[.2],[.7]],np.float32)
    g=np.arange(1024,dtype=np.float32).reshape(32,32,1)/1024
    r=rasterize(p,g,features=f)
    assert np.allclose((r['features']*g).sum(),(f*r['adjoints']).sum(),atol=1e-5)
    return dict(status='PASS',mass=r['mass'].tolist())

def calibrate(scene,key):
    assert key in ('r_7','r_33')
    frozen=json.loads(Path('/home/u00134/3dgs_line/gaer_object_contours_v01/artifacts/gaer_object_contours_v01/INPUT_FREEZE.json').read_text())['scenes'][scene]
    camera=next(c for c in frozen['cameras'] if c['key']==key)
    old=Path('/home/u00134/3dgs_line/gaer_view_selection_v01/out/gaer_view_selection_v01/units')/(scene+'_'+key)
    t=time.time(); m=load_model_cpu(frozen); r=render(m,camera); seconds=time.time()-t
    rgb=np.load(old/'baseline_RGB.npy').transpose(1,2,0);a=np.load(old/'alpha.npy');mass=np.load(old/'full_visible_mass.npy')
    dr=np.abs(rgb-r['rgb']);da=np.abs(a-r['alpha']);dm=np.abs(mass-r['mass'])
    result=dict(scene=scene,camera=key,seconds=seconds,rgb_mae=float(dr.mean()),rgb_max=float(dr.max()),alpha_mae=float(da.mean()),alpha_max=float(da.max()),mass_l1_relative=float(dm.sum()/mass.sum()),mass_max=float(dm.max()),status='UNDETERMINED')
    result.update(rgb_p99=float(np.quantile(dr,.99)),rgb_p999=float(np.quantile(dr,.999)),alpha_p99=float(np.quantile(da,.99)),alpha_p999=float(np.quantile(da,.999)),rgb_pixels_abs_gt_001_fraction=float((dr.max(axis=2)>.01).mean()),alpha_pixels_abs_gt_001_fraction=float((da>.01).mean()),mass_sum_relative_error=float(abs(r['mass'].sum()-mass.sum())/mass.sum()))
    top=max(1,len(mass)//100);i=np.argsort(mass)[-top:];j=np.argsort(r['mass'])[-top:]
    result['top_1pct_mass_id_jaccard']=float(len(np.intersect1d(i,j))/len(np.union1d(i,j)))
    errors=np.argsort(dm)[-10:][::-1]
    result['largest_mass_discrepancies']=[dict(original_id=int(k),native_mass=float(mass[k]),cpu_mass=float(r['mass'][k]),abs_error=float(dm[k])) for k in errors]
    result['interpretation']='CPU replica calibrated against pinned full-native cache; not exact CUDA execution. Threshold crossings and CUDA fused arithmetic may cause sparse cutoff-sized differences.'
    archive=Path('/home/u00134/3dgs_line/gaer_view_selection_v01/artifacts/gaer_view_selection_v01/downloads')/(scene+'_'+key+'_scores_ids.npz')
    with np.load(archive) as z:
        selected=z['gaer_raw_0.005_ids'];native_adjoint=z['full_alphaT_edge_participation']
    membership=np.zeros(len(mass),np.float32);membership[selected]=1
    edge=np.load(old/'edge.npy').astype(np.float32)
    second=rasterize(r['projected'],maps=edge,features=membership)
    native_footprint=np.load(old/'gaer_raw_fullT_contribution.npy')
    df=np.abs(second['features'][...,0]-native_footprint)
    result['selected_fullT_footprint']=dict(selected_count=len(selected),mae=float(df.mean()),max=float(df.max()),p999=float(np.quantile(df,.999)))
    result['edge_map_adjoint_l1_relative']=float(np.abs(second['adjoints'][:,0]-native_adjoint).sum()/max(native_adjoint.sum(),1e-12))
    result['input_sha256']={str(p):sha(p) for p in [old/'baseline_RGB.npy',old/'alpha.npy',old/'full_visible_mass.npy',old/'edge.npy',old/'gaer_raw_fullT_contribution.npy',archive]}
    result['code_binding']={
        'cpu_native_py_sha256':sha(Path(cpu_native.__file__)),
        'cpp_sha256':hashlib.sha256(cpu_native.CPP.encode()).hexdigest(),
        'test_cpu_native_py_sha256':sha(Path(__file__)),
    }
    # Frozen before first calibration run: aggregate agreement and tail robustness.
    passed=result['rgb_mae']<1e-4 and result['alpha_mae']<1e-4 and result['mass_l1_relative']<.002 and result['rgb_max']<.08 and result['alpha_max']<.08 and result['selected_fullT_footprint']['mae']<1e-4 and result['edge_map_adjoint_l1_relative']<.002
    result['status']='PASS' if passed else 'FAIL'
    (ART/('native_calibration_'+scene+'_'+key+'.json')).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)
    assert passed,result
    return result

if __name__=='__main__':
    ART.mkdir(parents=True,exist_ok=True)
    print(json.dumps(synthetic()),flush=True)
    if '--calibrate' in sys.argv:
        for s in ('lego','chair'):
            for k in ('r_7','r_33'):calibrate(s,k)
