"""Native contribution localization/coverage appendix; does not change frozen scoring.

Run after main RUNNER_COMPLETE.json. Inputs and source sealed before GPU units.
This appendix keeps the original failed synthetic gates unchanged.
"""
import json,sys,time
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'experiments/edge_responsibility_lego_chair_v2/src'))
from runtime import ART,OUT,sha,atomic_json,guard,event,unit
from adapter import load_model,make_camera,contribution
from evidence import sample_band

def longest_gap(values):
    longest=0;now=0
    for x in values:
        now=0 if x else now+1;longest=max(longest,now)
    return longest

def class_metrics(cm,a0,samples):
    if not samples:return dict(status='no_visible_edge',samples=0)
    shape=cm.shape
    bands={w:np.max(np.stack([sample_band(s,shape,w) for s in samples]),0) for w in [2,4]}
    ridge=np.zeros(shape,bool);coverage=[]
    for s in samples:
        normal=np.array(s['normal']);normal/=np.linalg.norm(normal);tangent=np.array([-normal[1],normal[0]])
        p=np.array(s['center'])+np.arange(-3,4)[:,None]*tangent
        y=np.clip(np.round(p[:,1]).astype(int),0,shape[0]-1);x=np.clip(np.round(p[:,0]).astype(int),0,shape[1]-1);ridge[y,x]=1
        selected=ndi.map_coordinates(cm,[p[:,1],p[:,0]],order=1,mode='nearest')
        total=ndi.map_coordinates(a0,[p[:,1],p[:,0]],order=1,mode='nearest')
        ratio=selected/np.maximum(total,1e-8)
        covered=(ratio>=.1)&(selected>=1e-4)
        coverage.append(dict(sample_id=s['id'],arc_unique_id=s['arc_unique_id'],covered_positions=int(covered.sum()),
                      fixed_positions=7,covered_fraction=float(covered.mean()),longest_gap_px=longest_gap(covered),
                      alphaT_fraction_samples=ratio.tolist(),selected_visible_mass_samples=selected.tolist(),
                      visibility_ratio_threshold=.1,absolute_selected_alphaT_floor=1e-4,
                      same_fixed_6px_tangent_segment=True))
    dist=ndi.distance_transform_edt(~ridge)
    edges=[0,2,4,8,16,32,64,128,1024]
    hist=np.histogram(dist,bins=edges,weights=cm)[0]
    total=float(cm.sum());h=hist/max(total,1e-20)
    q={}
    for target in [.25,.5,.75,.9,.95]:
        idx=np.searchsorted(np.cumsum(h),target);q[str(target)]=float(edges[min(idx+1,len(edges)-1)])
    return dict(status='measured',samples=len(samples),
               contribution_recall={str(w):float((cm*bands[w]).sum()/max((a0*bands[w]).sum(),1e-20)) for w in [2,4]},
               contribution_concentration={str(w):float((cm*bands[w]).sum()/max(total,1e-20)) for w in [2,4]},
               selected_mass_distance_histogram=dict(edges_px=edges,mass=hist.tolist(),fractions=h.tolist()),
               distance_quantile_upper_bin_edges_px=q,coverage=coverage,
               scope='distance to frozen local reference segments, not a full-object edge census',native_float_precision=True)

def scene_unit(scene,frozen):
    import torch
    data=frozen['scenes'][scene];score=json.loads((ART/'results'/f'{scene}_scores.json').read_text())
    val=json.loads((ART/'results'/f'{scene}_independent.json').read_text())
    assert sha(data['model'])==data['model_sha256']
    m=load_model(data['model']);rows=[]
    methods=['old_broad','old_trusted_equal','old_trusted_arc','absolute','signed','matched_random','accepted_diagnostic']
    sets={k:json.loads((ART/'selection_ids'/scene/f'{k}.json').read_text())['original_rows'] for k in methods}
    for v in data['views']:
        if v['entry']['role']!='edit-train':continue
        guard(f'post/{scene}/{v["entry"]["key"]}')
        camera=make_camera(v['entry']['camera'])
        with np.load(ROOT/score['cache'][v['entry']['key']]['baseline_path']) as z:a0=z['alpha']
        ref=v['reference'];samples=ref['samples']
        for method,ids in sets.items():
            with torch.no_grad():cm=contribution(m,camera,np.asarray(ids,int)).cpu().numpy().astype(float)
            classes={k:class_metrics(cm,a0,[s for s in samples if s['class_name']==k]) for k in ['outline','clear_color_transition']}
            classes['texture_detail']=dict(status='unknown_no_independent_semantic_annotation',included_in_main_structural_target=False)
            with np.load(ROOT/v['maps_path']) as z:unknown=z['unknown']
            rows.append(dict(view=v['entry']['key'],method=method,count=len(ids),model_sha256=data['model_sha256'],
                             classes=classes,unknown_support_mass=float((cm*(unknown>0)).sum()),
                             unknown_support_is_not_false_positive_truth=True,
                             flat_negative_patch_count=len(ref['flat']),
                             flat_cost_status='measured' if ref['flat'] else 'UNVERIFIED_NO_MATCHED_FLAT_ROI',
                             zero_flat_rms_when_mask_empty_is_undefined_not_evidence=True))
        event(f'post/{scene}/{v["entry"]["key"]}','COMPLETE',methods=len(methods))
    # Full effect-cost scatter using the actual independently rendered interventions.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    for method in ['old_relative','absolute','signed','matched_random']:
        rs=[r for r in val['groups'] if r['method']==method and r['target_class']!='flat_negative']
        x=[max(r['independent_probes'][p]['metrics']['plus']['outside_rms'] for p in ['dc','scale']) for r in rs]
        y=[max(r['independent_probes'][p]['metrics']['plus']['edge_rms'] for p in ['dc','scale']) for r in rs]
        axes[0].scatter(x,y,label=method,s=24)
        axes[1].scatter([r['signed_edge_attribution'] for r in rs],y,label=method,s=24)
    axes[0].axvline(frozen['config']['outside_rms_budget'],ls='--',color='gray')
    axes[0].axhline(frozen['config']['minimum_action_floor'],ls='--',color='gray')
    axes[0].set(xlabel='non-target full-image native RGB RMS',ylabel='fixed 4px target native RGB RMS',title='Independent direction/amplitude, full model')
    axes[1].set(xlabel='current centered signed normal attribution',ylabel='independent target response RMS',title='Accounting and operation are separate')
    axes[0].legend(fontsize=8);fig.tight_layout()
    plot=ART/'media'/scene/'independent_effect_cost.png';fig.savefig(plot,dpi=160);plt.close(fig)
    flat_groups=[r for r in val['groups'] if r['target_class']=='flat_negative']
    negative=dict(groups=len(flat_groups),construction_false_accepts=sum(r['construction_accepted'] for r in flat_groups),
                  diagnostic_false_accepts=sum(r['diagnostic_validated'] for r in flat_groups),
                  absence_rejection_is_reference_quality_gate=True)
    return dict(scene=scene,rows=rows,flat_negative_rejection=negative,source_score_sha256=sha(ART/'results'/f'{scene}_scores.json'),
                source_validation_sha256=sha(ART/'results'/f'{scene}_independent.json'),
                models_unchanged_after=sha(data['model'])==data['model_sha256'],
                sealed_files=[str(plot.relative_to(ROOT))])

if __name__=='__main__':
    if not (OUT/'RUNNER_COMPLETE.json').exists():raise RuntimeError('main runner must complete first')
    frozen=json.loads((ART/'INPUT_FREEZE.json').read_text())
    seal=ART/'SUPPLEMENTAL_INPUT_FREEZE.json'
    inputs=dict(source_sha256=sha(__file__),original_freeze_sha256=sha(ART/'INPUT_FREEZE.json'),
                methods=['old_broad','old_trusted_equal','old_trusted_arc','absolute','signed','matched_random','accepted_diagnostic'],
                evaluation_band_widths_px=[2,4],arc_samples=7,fixed_arc_half_length_px=3,
                selected_alphaT_fraction_threshold=.1,absolute_selected_alphaT_floor=.0001,
                retains_original_gate_failures=True)
    if seal.exists():assert json.loads(seal.read_text())==inputs
    else:atomic_json(seal,inputs)
    for scene in ['lego','chair']:
        unit(scene+'_localization_appendix',lambda s=scene:scene_unit(s,frozen),sha(seal))
    event('localization_appendix','COMPLETE')
