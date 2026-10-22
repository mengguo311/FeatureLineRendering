"""Independent persisted-row audit and actual BUILD effect-match verification."""
import runtime
from runtime import js,sha,now,output_guard
from pathlib import Path
import argparse,json
import numpy as np
import base_model as base
from footprint import FootprintRenderer
from membership import load_binding,evaluated_tint_copy
from run_footprint_unit import load,ARMS
from run_path_unit import read_npz
from run_unit import metrics

def validate(unit,scene,output=None):
    p=load(unit);s=p['scenes'][scene];root=unit/'results'/scene;n=s['source_count']
    destination=output_guard(output) if output is not None else root/'VALIDATION.json'
    if destination.exists():raise FileExistsError('validation output exists; choose a fresh --output path')
    q=read_npz(root/'FOOTPRINT_BINDING.npz');prior=read_npz(root/'PATH_BINDING.npz')
    binding,_=load_binding(root/'SOURCE_BINDING.npz',s['source']['sha256'],n)
    sel=read_npz(root/'EDIT_SELECTION.npz');cand=read_npz(root/'CANDIDATES.npz')
    for obj in (q,prior,binding,sel,cand):np.testing.assert_array_equal(obj['source_index'],np.arange(n))
    pv=np.stack([read_npz(root/c['view']/'FOOTPRINT.npz')['mass'] for c in s['cameras'] if c['split']=='build'])
    np.testing.assert_array_equal(pv,q['per_view_mass'])
    sums=pv.sum(0);tot=sums[:,0];inside=sums[:,1];far=sums[:,3];accepted=sums[:,4]
    ratio=np.divide(far,tot,out=np.ones(n),where=tot>0)
    vr=np.divide(pv[:,:,3],pv[:,:,0],out=np.zeros((4,n)),where=pv[:,:,0]>0)
    worst=np.where(pv[:,:,0]>=.02,vr,0).max(0)
    df=np.divide(accepted,inside,out=np.zeros(n),where=inside>0)
    good=(prior['strength']>0)&~prior['unknown']&(accepted>=.02)&((pv[:,:,4]>=.002).sum(0)>=2)&(df>=.7)&(ratio<=.02)&(worst<=.05)
    np.testing.assert_array_equal(~q['unknown'],good)
    np.testing.assert_array_equal(q['strength'],np.where(good,prior['strength'],0))
    assert not np.any(good&binding['unknown'])
    np.testing.assert_array_equal(cand['specific'],q['strength'])
    np.testing.assert_array_equal(cand['previous_path'],prior['strength'])
    assert sum(cand['specific']>0)==sum(cand['nearest_path']>0)==sum(cand['shuffled']>0)
    receipt=json.loads((root/'BUDGET_MATCH.json').read_text());actual={k:0. for k in ARMS};displayed={k:0. for k in ARMS}
    for c in [v for v in s['cameras'] if v['split']=='build']:
        base_rgb=read_npz(root/c['view']/'baseline.npz')['rgb'].astype(float)
        for arm in ARMS:
            d=read_npz(root/c['view']/('budget_'+arm+'.npz'))['delta']
            actual[arm]+=float(np.abs(d*receipt['scales'][arm]).sum())
            displayed[arm]+=float(np.abs(np.clip(base_rgb+d*receipt['scales'][arm],0,1)-np.clip(base_rgb,0,1)).sum())
            np.testing.assert_array_equal(sel[arm],cand[arm]*receipt['scales'][arm])
    assert max(abs(v-receipt['target']) for v in actual.values())<1e-8
    # Actual new render at locked scale, separate from linear budget arithmetic.
    a=base.load_source(s['source']['original_ply'],s['source']['sha256']);a['source_index']=np.arange(n)
    r=FootprintRenderer(unit/'build');c=[v for v in s['cameras'] if v['split']=='build'][0]
    baseline=read_npz(root/c['view']/'baseline.npz');match={}
    for arm in ARMS:
        f,_=r.render(evaluated_tint_copy(a,c,sel[arm],sel['tint']),c)
        prediction=baseline['rgb'].astype(float)+read_npz(root/c['view']/('budget_'+arm+'.npz'))['delta']*receipt['scales'][arm]
        err=float(np.max(np.abs(prediction-f['rgb'])));assert err<1e-6
        measured=float(np.abs(f['rgb'].astype(float)-baseline['rgb']).sum())
        predicted=float(np.abs(prediction-baseline['rgb']).sum())
        relative=abs(measured-predicted)/max(predicted,1e-30);assert relative<.0001
        match[arm]=dict(actual_L1=measured,predicted_L1=predicted,relative_error=relative,RGB_max_error=err)
    evals={};passes={k:0 for k in ARMS}
    for c in [v for v in s['cameras'] if v['split']=='evaluation']:
        f=read_npz(root/c['view']/'baseline.npz');row=json.loads((root/c['view']/'EVALUATION.json').read_text())
        intent=np.where(f['proxy_regions']>0,1,0);intent[f['path_mask']]=4
        evals[c['view']]={}
        for arm in ARMS:
            ef=read_npz(root/c['view']/('tint_'+arm+'.npz'))
            met=metrics(f['rgb'],ef['rgb'],intent,f['contribution'],p)
            assert met==row['arms'][arm]
            passes[arm]+=int(met['intent_locality_gate']);evals[c['view']][arm]=met
    result=dict(utc=now(),scene=scene,original_rows=n,all_ID_order_exact=True,all_footprint_rows_and_UNKNOWN_recomputed=True,
        no_prior_UNKNOWN_promoted=True,source_count_order_and_PLY_unchanged=sha(s['source']['original_ply'])==s['source']['sha256'],
        matched_full_image_BUILD_L1=actual,clipped_display_BUILD_L1=displayed,
        display_budget_max_min_ratio=max(displayed.values())/max(min(displayed.values()),1e-30),
        actual_BUILD_rerender_at_frozen_scales=match,independent_evaluation_metrics=evals,
        locality_pass_counts=passes,scope='Validated finite CPU engineering evidence; all evaluation cameras previously exposed; no scientific seal')
    js(destination,result);print(json.dumps(dict(scene=scene,passes=passes,BUILD_budget=actual)),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--unit',type=Path,required=True);p.add_argument('--scene',choices=['chair','lego'],required=True);p.add_argument('--output',type=Path)
    a=p.parse_args();validate(a.unit,a.scene,a.output)
