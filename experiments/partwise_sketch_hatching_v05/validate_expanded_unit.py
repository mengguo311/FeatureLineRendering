"""Read saved evidence, recompute memberships/support/edits and actual budgets."""
import runtime
from runtime import js,sha,now
from pathlib import Path
import argparse,json
import numpy as np
import base_model as base
from membership import load_binding,resolve,evaluated_tint_copy
from path_control import resolve_path,opacity_copy
from footprint import resolve_footprint,FootprintRenderer
from run_path_unit import load_scene,read_npz
from run_expanded_unit import load,ARMS
from run_transfer_unit import project_intent
from transfer_audit import coverage_assessment
from validate_path_unit import audit_trace
from run_unit import metrics,arrays_hash


def same_json(a,b):
    assert json.loads(json.dumps(a,default=runtime.json_default))==b


def validate(unit,scene):
    p=load(unit);s,a,mesh,meta,strokes,paths=load_scene(p,scene);root=unit/'results'/scene;n=len(a['means']);m=p['membership']
    for name,h in json.loads((root/'BINDING_LOCK.json').read_text())['files'].items():assert sha(root/name)==h
    b,_=load_binding(root/'SOURCE_BINDING.npz',s['source']['sha256'],n)
    old,_=load_binding(Path(p['prior_unit'])/'results'/scene/'SOURCE_BINDING.npz',s['source']['sha256'],n)
    pb=read_npz(root/'PATH_BINDING.npz');fp=read_npz(root/'FOOTPRINT_BINDING.npz');sel=read_npz(root/'EDIT_SELECTION.npz');cand=read_npz(root/'CANDIDATES.npz')
    rr=resolve(b['per_view_score'],m['min_exposure'],m['min_views'],m['min_fraction'],m['view_mass'])
    for k,v in rr.items():np.testing.assert_array_equal(v,b[k])
    rr=resolve_path(pb['per_view_total'],pb['per_view_accepted'],b)
    for k,v in rr.items():np.testing.assert_array_equal(v,pb[k])
    rr=resolve_footprint(fp['per_view_mass'],pb)
    for k,v in rr.items():np.testing.assert_array_equal(v,fp[k])
    np.testing.assert_array_equal(cand['specific'],fp['strength']);assert (cand['specific'][b['unknown']]==0).all()
    counts={k:int((cand[k]>0).sum()) for k in ARMS};assert counts['specific']==counts['nearest_path']==counts['shuffled']
    budget=json.loads((root/'BUDGET_MATCH.json').read_text());checks={}
    for arm in ARMS:np.testing.assert_array_equal(sel[arm],cand[arm]*budget['scales'][arm])
    for c in s['cameras']:
        folder=root/c['view'];t=read_npz(folder/'trace.npz');f=read_npz(folder/'baseline.npz');ps=read_npz(folder/'path_support.npz');row=json.loads((folder/'EVALUATION.json').read_text())
        check=audit_trace(a,c,t,f);sid=t['sample_index'];ids=t['source_index'];xx,yy=t['xy'].T
        np.testing.assert_array_equal(ps['segment_index'],s['selected_segment_indices'])
        for key in ('face','stroke_id'):np.testing.assert_array_equal(ps[key],strokes[4][key][ps['segment_index']])
        np.testing.assert_array_equal(ps['bary'],strokes[4]['bary'][ps['segment_index']].mean(1))
        np.testing.assert_allclose(np.einsum('ni,nij->nj',ps['bary'],mesh['tri'][ps['face']]),ps['world'],rtol=0,atol=1e-9)
        order=np.argsort(sid,kind='stable');ss=sid[order]
        for j,si in enumerate(ps['sample_index']):
            lo,hi=ps['offsets'][j:j+2];ix=order[np.searchsorted(ss,si,'left'):np.searchsorted(ss,si,'right')] if si>=0 else np.array([],int)
            np.testing.assert_array_equal(ps['source_index'][lo:hi],ids[ix]);np.testing.assert_array_equal(ps['weight'][lo:hi],t['weight'][ix])
            eligible=np.zeros(len(ix),bool)
            if si>=0 and ps['proxy_visible'][j] and t['sample_eligible'][si]:eligible=np.isfinite(t['depth'][ix])&(np.abs(t['depth'][ix]-t['proxy_depth'][si])<=m['contributor_proxy_z_tolerance'])
            np.testing.assert_array_equal(ps['eligible'][lo:hi],eligible)
            assert abs(ps['retained_mass'][j]-t['weight'][ix][eligible].sum())<1e-12
            assert abs(ps['total_mass'][j]-t['weight'][ix].sum())<1e-12
        check['all_anchor_CSR_depth_mass_and_identity_exact']=True
        for binding,name,statskey in [(b,'M1_PROJECTION.npz','M1_projection'),(old,'M1_PREVIOUS_PROJECTION.npz','M1_previous_projection')]:
            pred,stats=project_intent(t,binding,p);saved=read_npz(folder/name)
            for k,v in pred.items():np.testing.assert_array_equal(v,saved[k])
            same_json(stats,row[statskey])
        intent=np.where(f['proxy_regions']>0,1,0);intent[f['path_mask']]=4;col=base.source_colors(a,c)
        errors={}
        for arm in ARMS:
            e=read_npz(folder/('tint_'+arm+'.npz'));delta=np.zeros((len(t['xy']),3))
            np.add.at(delta,sid,t['weight'][:,None]*sel[arm][ids,None]*(np.asarray(p['diagnostic']['tint'])-col[ids]))
            err=float(np.abs(f['rgb'][yy,xx]+delta-e['rgb'][yy,xx]).max());assert err<1e-6;errors[arm]=err
            for key in ('alpha','median_camera_z','center_depth_proxy','expected_camera_z'):np.testing.assert_array_equal(e[key],f[key])
            mm=metrics(f['rgb'],e['rgb'],intent,f['contribution'],p);assert mm==row['arms'][arm]
            cv=coverage_assessment(ps,sel[arm],p['coverage_gate']);same_json(cv,row['coverage'][arm])
            assert bool(mm['intent_locality_gate'] and cv['coverage_gate'])==row['joint_transfer'][arm]
        weighted=np.bincount(sid,t['weight']*sel['specific'][ids],minlength=len(t['xy']))
        error=float(np.abs(weighted-f['contribution'][yy,xx]).max());assert error<1e-6
        ot=read_npz(folder/'opacity_trace.npz');of=read_npz(folder/'opacity_specific.npz')
        check['opacity']=audit_trace(opacity_copy(a,cand['specific'],.5),c,ot,of)
        fpv=read_npz(folder/'FOOTPRINT.npz')['mass'];np.testing.assert_allclose(fpv[:,1:4].sum(1),fpv[:,0],rtol=1e-12,atol=1e-10)
        assert abs(fpv[:,0].sum()-f['alpha'].sum(dtype=float))<.001
        check.update(M1_both_versions_exact=True,all_four_saved_RGB_metrics_and_joint_gates_exact=True,tint_reconstruction_errors=errors,full_T_sample_error=error)
        checks[c['view']]=check
        print('VALIDATED',scene,c['view'],flush=True)
    # Verify the frozen linear budget with actual scaled source renders; no fit.
    r=FootprintRenderer(unit/'build');actual={k:0. for k in ARMS};perview={};original=arrays_hash(a)
    for c in s['budget_cameras']:
        baseline=read_npz(root/c['view']/'baseline.npz');values={}
        for arm in ARMS:
            e,_=r.render(evaluated_tint_copy(a,c,sel[arm],p['diagnostic']['tint']),c)
            value=float(np.abs(e['rgb'].astype(float)-baseline['rgb'].astype(float)).sum());actual[arm]+=value;values[arm]=value
        perview[c['view']]=values
        print('ACTUAL_SCALED_BUILD_BUDGET',scene,c['view'],values,flush=True)
    relative={k:abs(v-budget['target'])/max(budget['target'],1e-30) for k,v in actual.items()}
    assert max(relative.values())<1e-4,relative
    assert original==arrays_hash(a) and sha(s['source']['original_ply'])==s['source']['sha256']
    result=dict(utc=now(),source_count=n,all_saved_binding_rows_recomputed_exact=True,counts=counts,checks=checks,
        actual_scaled_BUILD_RGB_L1=actual,per_view_actual_scaled_BUILD_RGB_L1=perview,target_BUILD_RGB_L1=budget['target'],
        budget_relative_errors=relative,actual_scaled_matching_valid=True,original_arrays_and_PLY_unchanged=True,
        scope='Validated finite CPU mapping and matched source edits; no native/semantic certification')
    js(unit/('VALIDATION_'+scene+'.json'),result)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--unit',type=Path,required=True);ap.add_argument('--scene',choices=['chair','lego'],required=True)
    args=ap.parse_args();validate(args.unit,args.scene)
