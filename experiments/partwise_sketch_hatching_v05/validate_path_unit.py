"""Read persisted evidence and independently reconstruct real source controls."""
import runtime
from runtime import js,sha,now
from pathlib import Path
import argparse,json
import numpy as np
import base_model as base
from link_renderer import Renderer,prepare,validate_trace
from membership import accumulate,resolve,load_binding
from path_control import aggregate_path,resolve_path,opacity_copy
from run_path_unit import load_protocol,load_scene,read_npz
from run_unit import delta_budget,metrics

def audit_trace(a,c,t,frame):
    ar,original,_=prepare(a,c)
    ids=t['source_index'];idx=t['culled_local_index'];s=t['sample_index'];xy=t['xy']
    np.testing.assert_array_equal(original[idx],ids)
    uv,z,S,plane,opacity,col=ar
    dx=xy[s,0]-uv[idx,0];dy=xy[s,1]-uv[idx,1]
    aa=S[idx,0,0];bb=S[idx,0,1];cc=S[idx,1,1];det=aa*cc-bb*bb
    q=(cc*dx*dx-2*bb*dx*dy+aa*dy*dy)/det
    al=np.minimum(.99,opacity[idx]*np.exp(-q/2))
    np.testing.assert_allclose(t['alpha'],al,rtol=2e-13,atol=2e-14)
    assert (al>=1/255-1e-14).all() and (al<=.99).all()
    assert (t['T']*(1-t['alpha'])>=.0001).all()
    np.testing.assert_allclose(t['depth'],z[idx]-plane[idx,0]*dx/c['fx']-plane[idx,1]*dy/c['fy'],rtol=2e-14,atol=2e-14)
    order=np.argsort(s,kind='stable');ss=s[order];ww=t['weight'][order]
    boundaries=np.r_[0,np.flatnonzero(np.diff(ss))+1,len(ss)];error=0.
    for start,end in zip(boundaries[:-1],boundaries[1:]):
        if start==end:continue
        ix=order[start:end];T=1-np.r_[0,np.cumsum(ww[start:end-1])]
        error=max(error,float(np.max(np.abs(t['T'][ix]-T))))
        assert (np.diff(t['center_z'][ix])>=0).all()
    assert error<1e-12
    result=validate_trace(a,c,xy,frame,t)
    result.update(original_ID_remap_exact=True,acceptance_recomputed=True,T_chain_max_error=error)
    return result

def validate(unit,scene):
    p=load_protocol(unit);s,a,mesh,meta,strokes,paths=load_scene(p,scene);out=unit/'results'/scene
    n=len(a['means']);binding,_=load_binding(out/'SOURCE_BINDING.npz',s['source']['sha256'],n)
    pb=read_npz(out/'PATH_BINDING.npz');selection=read_npz(out/'EDIT_SELECTION.npz');m=p['membership']
    np.testing.assert_array_equal(selection['source_index'],np.arange(n));assert str(selection['source_sha256'])==s['source']['sha256']
    scores=[];totals=[];accepted=[];checks={};tbudgets={k:0. for k in p['diagnostic']['arms']};obudgets=dict(tbudgets)
    r=Renderer(unit/'build')
    for c in s['cameras']:
        folder=out/c['view'];t=read_npz(folder/'trace.npz');f=read_npz(folder/'baseline.npz');ps=read_npz(folder/'path_support.npz')
        check=audit_trace(a,c,t,f)
        seg=ps['segment_index'];np.testing.assert_array_equal(seg,s['selected_segment_indices'])
        for key in ('face','stroke_id'):np.testing.assert_array_equal(ps[key],strokes[4][key][seg])
        np.testing.assert_array_equal(ps['bary'],strokes[4]['bary'][seg].mean(1))
        np.testing.assert_allclose(np.einsum('ni,nij->nj',ps['bary'],mesh['tri'][ps['face']]),ps['world'],rtol=0,atol=1e-9)
        order=np.argsort(t['sample_index'],kind='stable');ss=t['sample_index'][order]
        assert ps['offsets'][0]==0 and ps['offsets'][-1]==len(ps['weight'])
        for k,sid in enumerate(ps['sample_index']):
            start,end=ps['offsets'][k:k+2]
            ix=order[np.searchsorted(ss,sid,'left'):np.searchsorted(ss,sid,'right')] if sid>=0 else np.array([],int)
            np.testing.assert_array_equal(t['source_index'][ix],ps['source_index'][start:end])
            np.testing.assert_array_equal(t['weight'][ix],ps['weight'][start:end])
            expected=np.zeros(len(ix),bool)
            if sid>=0 and ps['proxy_visible'][k] and t['sample_eligible'][sid]:
                expected=np.isfinite(t['depth'][ix])&(np.abs(t['depth'][ix]-t['proxy_depth'][sid])<=m['contributor_proxy_z_tolerance'])
            np.testing.assert_array_equal(expected,ps['eligible'][start:end])
            assert abs(t['weight'][ix].sum()-ps['total_mass'][k])<1e-12
            assert abs(t['weight'][ix][expected].sum()-ps['retained_mass'][k])<1e-12
        check['all_path_anchors_CSR_and_depth_rejections_exact']=True
        if c['split']=='build':
            score,_,_=accumulate(n,t,t['proxy_region'],t['proxy_depth'],t['sample_eligible'],t['sampling_weight'],m['contributor_proxy_z_tolerance'])
            scores.append(score);total,accept=aggregate_path(n,ps);totals.append(total);accepted.append(accept)
            for arm in p['diagnostic']['arms']:
                tbudgets[arm]+=delta_budget(a,c,t,t['grid_sample_index'],selection['tint_'+arm],p['diagnostic']['tint'],len(t['xy']))
                ef,_=r.render(opacity_copy(a,selection['opacity_'+arm]),c)
                xx,yy=t['xy'][t['grid_sample_index']].T
                obudgets[arm]+=float(np.abs(ef['rgb'][yy,xx]-f['rgb'][yy,xx]).sum(dtype=np.float64))
        else:
            col=base.source_colors(a,c);sid=t['sample_index'];ids=t['source_index'];xy=t['xy'];xx,yy=xy.T
            mass=np.bincount(sid,t['weight'],minlength=len(xy));pred=np.ones((len(xy),3))-mass[:,None]
            np.add.at(pred,sid,t['weight'][:,None]*col[ids])
            reconstructed={};opacity_checks={};effectchecks={}
            for arm in p['diagnostic']['arms']:
                key='tint_'+arm;ef=read_npz(folder/(key+'.npz'));delta=np.zeros_like(pred)
                np.add.at(delta,sid,t['weight'][:,None]*selection[key][ids,None]*(np.asarray(p['diagnostic']['tint'])-col[ids]))
                err=float(np.max(np.abs(pred+delta-ef['rgb'][yy,xx])));assert err<1e-6
                np.testing.assert_array_equal(ef['alpha'],f['alpha']);reconstructed[key]=err
                key='opacity_'+arm;ef=read_npz(folder/(key+'.npz'));et=read_npz(folder/(key+'_trace.npz'))
                changed=opacity_copy(a,selection[key]);oc=audit_trace(changed,c,et,ef)
                before_pairs=np.unique(sid.astype(np.int64)*n+ids)
                after_pairs=np.unique(et['sample_index'].astype(np.int64)*n+et['source_index'])
                oc['newly_accepted_pixel_ID_pairs']=len(np.setdiff1d(after_pairs,before_pairs))
                oc['removed_pixel_ID_pairs']=len(np.setdiff1d(before_pairs,after_pairs))
                oc['alpha_changed_pixels']=int((ef['alpha']!=f['alpha']).sum())
                opacity_checks[arm]=oc
                for op in ('tint','opacity'):
                    ee=read_npz(folder/(op+'_'+arm+'.npz'))
                    intent=np.where(f['proxy_regions']>0,1,0);intent[f['path_mask']]=4
                    effectchecks[op+'_'+arm]=metrics(f['rgb'],ee['rgb'],intent,np.zeros_like(f['alpha']),p)
            support=np.bincount(sid,t['weight']*pb['strength'][ids],minlength=len(xy))
            heat=read_npz(folder/'full_T_contribution.npz')['contribution']
            ce=float(np.max(np.abs(support-heat[yy,xx])));assert ce<1e-6
            check.update(tint_reconstruction_errors=reconstructed,opacity=opacity_checks,full_T_contribution_max_error=ce,
                         independently_recomputed_path_metrics=effectchecks)
        checks[c['view']]=check
    b=resolve(np.stack(scores),m['min_exposure'],m['min_views'],m['min_fraction'],m['view_mass'])
    for k,v in b.items():np.testing.assert_array_equal(v,binding[k])
    q=resolve_path(np.stack(totals),np.stack(accepted),b)
    for k,v in q.items():np.testing.assert_array_equal(v,pb[k])
    assert (selection['unscaled_path_linked'][b['unknown']]==0).all()
    np.testing.assert_array_equal(selection['unscaled_path_linked'],q['strength'])
    counts={k:int((selection['unscaled_'+k]>0).sum()) for k in p['diagnostic']['arms']}
    assert len(set(counts.values()))==1
    budget=json.loads((out/'BUDGET_MATCH.json').read_text())
    assert max(tbudgets.values())-min(tbudgets.values())<1e-8
    for k,v in obudgets.items():assert abs(v-budget['opacity']['actual'][k])<1e-9
    opacity_relative_error=max(abs(v-budget['opacity']['target'])/max(budget['opacity']['target'],1e-30) for v in obudgets.values())
    assert (opacity_relative_error<=.01)==budget['opacity']['valid']
    result=dict(utc=now(),scene=scene,source_count=n,views=checks,region_binding_all_rows_recomputed_exact=True,
        path_binding_all_rows_recomputed_exact=True,save_load_identity=True,selected_counts=counts,
        actual_BUILD_tint_L1=tbudgets,actual_BUILD_opacity_L1=obudgets,opacity_matching_max_relative_error=opacity_relative_error,
        original_PLY_unchanged=sha(s['source']['original_ply'])==s['source']['sha256'],
        verdict='VALIDATED_ENGINEERING_EVIDENCE_ONLY; UNCERTIFIED_CPU_MAPPING')
    js(unit/('VALIDATION_'+scene+'.json'),result)
    print(json.dumps({k:v for k,v in result.items() if k!='views'},default=runtime.json_default))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--unit',type=Path,required=True);p.add_argument('--scene',choices=['chair','lego'],required=True)
    args=p.parse_args();validate(args.unit,args.scene)
