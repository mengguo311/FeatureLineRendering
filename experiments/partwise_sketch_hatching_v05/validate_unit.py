"""Read back actual traces; audit IDs, acceptance, anchors, mass and budgets."""
import runtime
from runtime import js,sha
from pathlib import Path
import argparse,json
import numpy as np
import base_model as base
from link_renderer import prepare,validate_trace
from membership import load_binding,accumulate,resolve
from run_unit import delta_budget

def validate(unit):
    p=json.loads((unit/'PROTOCOL.json').read_text());out=unit/'results'
    a=base.load_source(p['source']['original_ply'],p['source']['sha256']);n=len(a['means'])
    b,meta=load_binding(out/'SOURCE_BINDING.npz',p['source']['sha256'],n)
    with np.load(Path(p['asset'])/'mesh.npz') as z:tri=z['vertices'][z['faces']]
    with np.load(Path(p['asset'])/'region_4.npz') as z:paths={k:z[k] for k in z.files}
    scores=[];checks={};path_checks={};budgets={k:0. for k in ('linked','nearest_proxy','shuffled')}
    with np.load(out/'EDIT_SELECTION.npz') as z:strengths={k:z[k] for k in budgets}
    for c in p['cameras']:
        folder=out/c['view']
        with np.load(folder/'trace.npz') as z:t={k:z[k] for k in z.files}
        with np.load(folder/('frame.npz' if c['split']=='build' else 'baseline.npz')) as z:f={k:z[k] for k in z.files}
        ar,original,ok=prepare(a,c)
        np.testing.assert_array_equal(original[t['culled_local_index']],t['source_index'])
        assert (t['source_index']>=0).all() and (t['source_index']<n).all()
        s=t['sample_index'];idx=t['culled_local_index'];xy=t['xy'];uv,z,S,plane,opacity,col=ar
        dx=xy[s,0]-uv[idx,0];dy=xy[s,1]-uv[idx,1]
        aa=S[idx,0,0];bb=S[idx,0,1];cc=S[idx,1,1];det=aa*cc-bb*bb
        q=(cc*dx*dx-2*bb*dx*dy+aa*dy*dy)/det
        expected_alpha=np.minimum(.99,opacity[idx]*np.exp(-q/2))
        np.testing.assert_allclose(t['alpha'],expected_alpha,rtol=2e-13,atol=2e-14)
        assert (t['alpha']>=1/255).all() and (t['alpha']<=.99).all()
        assert (t['T']*(1-t['alpha'])>=.0001).all()
        np.testing.assert_allclose(t['depth'],z[idx]-plane[idx,0]*dx/c['fx']-plane[idx,1]*dy/c['fy'],rtol=2e-14,atol=2e-14)
        # Every sample has a complete front-to-back transmittance chain.
        order=np.argsort(s,kind='stable');ss=s[order];ww=t['weight'][order]
        boundaries=np.r_[0,np.flatnonzero(np.diff(ss))+1,len(ss)]
        chain_error=0.;depth_order=True
        for start,end in zip(boundaries[:-1],boundaries[1:]):
            ii=order[start:end];expected_T=1-np.r_[0,np.cumsum(ww[start:end-1])]
            chain_error=max(chain_error,float(np.max(np.abs(t['T'][ii]-expected_T))))
            depth_order &= bool((np.diff(t['center_z'][ii])>=0).all())
        assert chain_error<1e-12 and depth_order
        check=validate_trace(a,c,xy,f,t);check.update(original_ID_remap_exact=True,acceptance_recomputed=True,
            transmittance_chain_max_error=chain_error,depth_order=depth_order,source_index_min=int(t['source_index'].min()),source_index_max=int(t['source_index'].max()))
        checks[c['view']]=check
        if c['split']=='evaluation':
            # Independent from the render-time colors override: reconstruct the
            # edit directly from saved accepted original-ID responsibilities.
            colors=base.source_colors(a,c);source=t['source_index'];xx,yy=xy.T
            predicted_base=np.ones((len(xy),3))
            mass=np.bincount(s,t['weight'],minlength=len(xy));predicted_base-=mass[:,None]
            np.add.at(predicted_base,s,t['weight'][:,None]*colors[source])
            edit_errors={}
            for arm,strength in strengths.items():
                delta=np.zeros_like(predicted_base)
                np.add.at(delta,s,t['weight'][:,None]*strength[source,None]*(np.asarray(p['diagnostic']['tint'])-colors[source]))
                with np.load(folder/(arm+'_edit.npz')) as z:
                    error=float(np.max(np.abs(predicted_base+delta-z['rgb'][yy,xx])))
                    assert error<1e-6
                    np.testing.assert_array_equal(z['alpha'],f['alpha'])
                    np.testing.assert_array_equal(z['median_camera_z'],f['median_camera_z'])
                edit_errors[arm]=error
            with np.load(out/'EDIT_SELECTION.npz') as z:support=z['linked_unscaled']
            contribution=np.bincount(s,t['weight']*support[source],minlength=len(xy))
            ce=float(np.max(np.abs(contribution-f['contribution'][yy,xx])));assert ce<1e-6
            check.update(actual_edit_reconstruction_max_errors=edit_errors,full_T_contribution_max_error=ce)
        with np.load(folder/'path_support.npz') as z:ps={k:z[k] for k in z.files}
        seg=ps['segment_index'];np.testing.assert_array_equal(ps['stroke_id'],paths['stroke_id'][seg])
        np.testing.assert_array_equal(ps['face'],paths['face'][seg]);np.testing.assert_array_equal(ps['bary'],paths['bary'][seg].mean(1))
        np.testing.assert_allclose(np.einsum('ni,nij->nj',ps['bary'],tri[ps['face']]),ps['world'],rtol=0,atol=1e-9)
        assert ps['offsets'][0]==0 and ps['offsets'][-1]==len(ps['weight'])
        raw_equal=True
        for k,sid in enumerate(ps['sample_index']):
            start,end=ps['offsets'][k:k+2];ix=order[np.searchsorted(ss,sid,'left'):np.searchsorted(ss,sid,'right')]
            raw_equal &= np.array_equal(t['source_index'][ix],ps['source_index'][start:end])
            raw_equal &= np.array_equal(t['weight'][ix],ps['weight'][start:end])
            assert abs(ps['weight'][start:end].sum()-ps['total_mass'][k])<1e-12
            assert abs(ps['weight'][start:end][ps['eligible'][start:end]].sum()-ps['retained_mass'][k])<1e-12
        assert raw_equal
        eligible=ps['proxy_visible'];mass=ps['retained_mass'][eligible].sum()/max(ps['total_mass'][eligible].sum(),1e-30)
        path_checks[c['view']]=dict(attempted=len(seg),unique_strokes=len(np.unique(ps['stroke_id'])),raw_edges=len(ps['weight']),
            supported=int((~ps['unknown']).sum()),unknown=int(ps['unknown'].sum()),proxy_visible=int(eligible.sum()),
            visible_retained_mass_fraction=float(mass),all_saved_anchor_and_raw_trace_exact=True,
            states=dict(zip(*np.unique(ps['state'],return_counts=True))))
        if c['split']=='build':
            score,exposure,_=accumulate(n,t,t['proxy_region'],t['proxy_depth'],t['sample_eligible'],t['sampling_weight'],p['membership']['contributor_proxy_z_tolerance'])
            scores.append(score)
            for arm,strength in strengths.items():budgets[arm]+=delta_budget(a,c,t,t['grid_sample_index'],strength,p['diagnostic']['tint'],len(xy))
    m=p['membership'];recomputed=resolve(np.stack(scores),m['min_exposure'],m['min_views'],m['min_fraction'],m['view_mass'])
    for k,v in recomputed.items():np.testing.assert_array_equal(v,b[k])
    matched=max(budgets.values())-min(budgets.values());assert matched<1e-8
    assert np.all(strengths['linked'][b['region_id']!=4]==0)
    result=dict(utc=runtime.now(),views=checks,path_checks=path_checks,all_binding_arrays_recomputed_exact=True,
        matched_actual_BUILD_sample_L1=budgets,budget_max_spread=matched,source_PLY_unchanged=sha(p['source']['original_ply'])==p['source']['sha256'],
        confidence_scope='CPU internal acceptance and persistent linkage audit, not independent physical/native calibration')
    js(unit/'VALIDATION.json',result);print(json.dumps(result,default=runtime.json_default),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--unit',type=Path,required=True);validate(p.parse_args().unit)
