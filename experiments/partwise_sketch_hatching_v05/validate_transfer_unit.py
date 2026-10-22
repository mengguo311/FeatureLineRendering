"""Independent persisted-data audit of fresh-view source controls."""
import runtime
from runtime import js,sha,now
from pathlib import Path
import argparse,json
import numpy as np
from scipy import ndimage
from run_transfer_unit import load,ARMS
from run_path_unit import read_npz
from membership import load_binding


def validate(unit,scene,output=None):
    destination=Path(output) if output is not None else unit/'results'/scene/'VALIDATION.json'
    runtime.output_guard(destination)
    if output is None and (unit/'EVIDENCE_LOCK.json').exists():
        raise FileExistsError('sealed evidence: specify --output with a new validation receipt path')
    if output is not None and destination.exists():raise FileExistsError(destination)
    p=load(unit);s=p['scenes'][scene];root=unit/'results'/scene;n=s['source_count']
    b,_=load_binding(root/'SOURCE_BINDING.npz',s['source']['sha256'],n)
    selection=read_npz(root/'EDIT_SELECTION.npz');checks={}
    for c in s['cameras']:
        folder=root/c['view'];row=json.loads((folder/'EVALUATION.json').read_text())
        assert row['camera']==c
        t=read_npz(folder/'trace.npz');ps=read_npz(folder/'path_support.npz');base=read_npz(folder/'baseline.npz')
        mp=read_npz(folder/'M1_PROJECTION.npz');foot=read_npz(folder/'FOOTPRINT.npz')
        assert str(foot['source_sha256'])==s['source']['sha256']
        np.testing.assert_array_equal(foot['source_index'],np.arange(n))
        np.testing.assert_array_equal(ps['segment_index'],s['selected_segment_indices'])
        assert len(ps['offsets'])==len(ps['segment_index'])+1
        assert ps['offsets'][0]==0 and ps['offsets'][-1]==len(ps['weight'])
        sid=t['sample_index'];ids=t['source_index'];w=t['weight'];ns=len(t['xy']);xx,yy=t['xy'].T
        assert (ids>=0).all() and (ids<n).all()
        mass=np.zeros(ns);np.add.at(mass,sid,w)
        np.testing.assert_allclose(mass,base['alpha'][yy,xx],rtol=0,atol=1e-6)
        evidence=np.zeros((ns,6));hard=np.zeros_like(evidence)
        np.add.at(evidence,sid,w[:,None]*b['membership'][ids])
        qq=b['membership'][ids].copy();qq[b['unknown'][ids]]=np.eye(6)[0]
        np.add.at(hard,sid,w[:,None]*qq)
        for name,q in [('soft_q',evidence),('abstaining_q',hard)]:
            np.testing.assert_allclose(q.sum(1),mass,rtol=0,atol=1e-12)
            q=np.divide(q,mass[:,None],out=np.zeros_like(q),where=mass[:,None]>0);q[mass==0,0]=1
            np.testing.assert_allclose(q,mp[name],rtol=0,atol=1e-12)
        # Reconstruct every anchor's CSR by the actual accepted source events.
        order=np.argsort(sid,kind='stable');ordered=sid[order]
        for j,sample in enumerate(ps['sample_index']):
            lo,hi=ps['offsets'][j:j+2]
            ix=order[np.searchsorted(ordered,sample,'left'):np.searchsorted(ordered,sample,'right')] if sample>=0 else np.array([],int)
            np.testing.assert_array_equal(ps['source_index'][lo:hi],ids[ix])
            np.testing.assert_array_equal(ps['weight'][lo:hi],w[ix])
            eligible=np.zeros(len(ix),bool)
            if sample>=0 and ps['proxy_visible'][j] and t['sample_eligible'][sample]:
                eligible=np.isfinite(t['depth'][ix])&(np.abs(t['depth'][ix]-t['proxy_depth'][sample])<=p['membership']['contributor_proxy_z_tolerance'])
            np.testing.assert_array_equal(eligible,ps['eligible'][lo:hi])
            assert abs(w[ix][eligible].sum()-ps['retained_mass'][j])<1e-12
        g=p['coverage_gate'];valid=(~ps['unknown'])&ps['proxy_visible']&(ps['retained_mass']>.01)
        target=base['path_mask'];inner=ndimage.binary_erosion(target,iterations=2)
        far=~ndimage.binary_dilation(target,iterations=2)
        armchecks={}
        for arm in ARMS:
            edit=read_npz(folder/('tint_'+arm+'.npz'))
            for key in ('alpha','median_camera_z','center_depth_proxy','expected_camera_z'):np.testing.assert_array_equal(base[key],edit[key])
            delta=np.abs(edit['rgb']-base['rgb']).sum(2)
            far_fraction=float(delta[far].sum()/max(delta.sum(),1e-30))
            mean=float(delta[inner].mean()) if inner.any() else None
            m=row['arms'][arm]
            assert abs(far_fraction-m['far_non_target_fraction'])<1e-8
            assert (mean is None and m['target_interior']['L1_mean'] is None) or abs(mean-m['target_interior']['L1_mean'])<1e-8
            local=bool(mean is not None and mean>=.02 and far_fraction<=.02)
            assert local==m['intent_locality_gate']
            per=np.array([(ps['weight'][lo:hi]*ps['eligible'][lo:hi]*selection[arm][ps['source_index'][lo:hi]]).sum() for lo,hi in zip(ps['offsets'][:-1],ps['offsets'][1:])])
            cv=row['coverage'][arm];np.testing.assert_allclose(per,cv['edited_mass_per_anchor'],rtol=0,atol=1e-12)
            count=int(valid.sum());hit=int(((per>g['edit_mass_threshold'])&valid).sum())
            retained=float(per[valid].sum()/ps['retained_mass'][valid].sum()) if count else None
            coverage=bool(count>=g['min_supported_anchors'] and hit/count>=g['min_edited_anchor_fraction'] and retained>=g['min_retained_mass_fraction'])
            assert coverage==cv['coverage_gate'] and (local and coverage)==row['joint_transfer'][arm]
            armchecks[arm]=dict(locality=local,coverage=coverage,joint=local and coverage)
        np.testing.assert_allclose(foot['mass'][:,1:4].sum(1),foot['mass'][:,0],rtol=1e-12,atol=1e-10)
        diag=read_npz(folder/'SELECTED_KERNEL_DIAGNOSTICS.npz');chosen=np.flatnonzero(selection['specific']>0)
        np.testing.assert_array_equal(diag['source_index'],chosen)
        np.testing.assert_array_equal(diag['full_pixel_mass'],foot['mass'][chosen])
        assert (diag['M1_unknown']==False).all()
        checks[c['view']]=dict(camera_and_original_IDs_exact=True,M1_both_projections_independently_reconstructed=True,
            all_anchors_raw_ID_weight_depth_CSR_exact=True,all_controls_actual_RGB_and_coverage_recomputed=True,
            full_footprint_partition=True,all_selected_kernel_diagnostics_identity_exact=True,arms=armchecks)
    result=dict(utc=now(),scene=scene,source_count=n,all_scheduled_views_validated=len(checks)==len(s['cameras']),
        views=checks,frozen_binding_and_selection_bytes_exact=True,
        source_PLY_unchanged=sha(s['source']['original_ply'])==s['source']['sha256'],
        validator_sha256=sha(__file__),scientific_seal=False,scope='Finite engineering evidence only; negative gates retained')
    assert result['source_PLY_unchanged']
    js(destination,result);print('VALIDATED',scene,len(checks),'fresh views',flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--unit',type=Path,required=True);ap.add_argument('--scene',required=True,choices=['chair','lego'])
    ap.add_argument('--output',type=Path)
    args=ap.parse_args();validate(args.unit,args.scene,args.output)
