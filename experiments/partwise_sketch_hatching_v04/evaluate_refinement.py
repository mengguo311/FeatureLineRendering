"""Finite evidence for the saved real-model candidate; no scientific seal."""
import runtime
from runtime import js, now, sha
from pathlib import Path
import argparse
import json
import numpy as np
from scipy import ndimage
from PIL import Image
from demo import load_asset
from geometry import ray_surface, resize_camera, depth_valid, region_ids


def path_stats(strokes):
    result={}
    for region,s in strokes.items():
        vector=s['points'][:,1]-s['points'][:,0]
        length=np.linalg.norm(vector,axis=1)
        tangent=vector/np.maximum(length[:,None],1e-30)
        connected=(s['stroke_id'][1:]==s['stroke_id'][:-1])
        connected &= np.linalg.norm(s['points'][1:,0]-s['points'][:-1,1],axis=1)<1e-9
        turn=np.arccos(np.clip(np.einsum('ij,ij->i',tangent[1:],tangent[:-1]),-1,1))[connected]
        _,inv=np.unique(s['stroke_id'],return_inverse=True)
        arcs=np.bincount(inv,weights=length)
        result[str(region)]=dict(paths=len(arcs),segments=len(length),total_length=float(length.sum()),
            length_p50=float(np.median(arcs)),length_max=float(arcs.max()),
            paths_shorter_than_half_requested=int((arcs<.11).sum()),
            connected_joints=int(connected.sum()),turn_radians=float(turn.sum()),
            turning_radians_per_world_length=float(turn.sum()/length.sum()),
            scope='includes true shape curvature; not an independent aesthetic score or matched path correspondence')
    return result


def distributions(a):
    if not len(a):return dict(count=0,mean=None,p50=None,p95=None,max=None)
    return dict(count=len(a),mean=float(a.mean()),p50=float(np.median(a)),
                p95=float(np.quantile(a,.95)),max=float(a.max()))


def evaluate(unit):
    unit=Path(unit);p=json.loads((unit/'PROTOCOL.json').read_text())
    original,os,om=load_asset(unit/'assets/original')
    mesh,bs,bm=load_asset(unit/'assets/baseline')
    _,es,em=load_asset(unit/'assets/edited')
    np.testing.assert_array_equal(original['faces'],mesh['faces'])
    np.testing.assert_array_equal(original['regions'],mesh['regions'])
    pinned_lower=np.unique(original['faces'][original['regions']==1])
    np.testing.assert_array_equal(original['vertices'][pinned_lower],mesh['vertices'][pinned_lower])
    assert sha(unit/'assets/original/region_1.npz')==sha(unit/'assets/baseline/region_1.npz')
    for r in (1,3):assert sha(unit/f'assets/baseline/region_{r}.npz')==sha(unit/f'assets/edited/region_{r}.npz')
    assert sha(unit/'assets/baseline/region_2.npz')!=sha(unit/'assets/edited/region_2.npz')
    anchor={}
    for name,strokes in [('baseline',bs),('edited',es)]:
        anchor[name]={}
        for r,s in strokes.items():
            reconstructed=np.einsum('nij,njk->nik',s['bary'],mesh['tri'][s['face']])
            error=float(np.abs(s['points']-reconstructed).max())
            assert error<1e-9 and s['bary'].min()>-1e-9
            assert np.max(np.abs(s['bary'].sum(2)-1))<1e-9
            assert (mesh['regions'][s['face']]==r).all()
            anchor[name][str(r)]=dict(max_error=error,min_bary=float(s['bary'].min()))
    rows=[]
    for i,c in enumerate(p['static_cameras']):
        c=resize_camera(c,512)
        with np.load(unit/f'renders/static_original/frame_{i:03d}_arrays.npz') as f:a={k:f[k] for k in f.files}
        with np.load(unit/f'renders/static_baseline/frame_{i:03d}_arrays.npz') as f:b={k:f[k] for k in f.files}
        with np.load(unit/f'renders/static_edited/frame_{i:03d}_arrays.npz') as f:e={k:f[k] for k in f.files}
        with np.load(unit/f'source_model/frame_{i:03d}.npz') as f:source={k:f[k] for k in f.files}
        z0,_,labels0,_=ray_surface(original,c,1)
        z1,_,labels1,_=ray_surface(mesh,c,1)
        qualified=depth_valid(source['median_camera_z'],source['alpha'],source['center_depth_proxy'])
        source_mask=source['alpha']>=.5
        common=qualified & np.isfinite(z0) & np.isfinite(z1)
        depth0=np.abs(z0[common]-source['median_camera_z'][common])
        depth1=np.abs(z1[common]-source['median_camera_z'][common])
        geometry={}
        for name,z,labels in [('original',z0,labels0),('candidate',z1,labels1)]:
            hit=np.isfinite(z)
            geometry[name]=dict(source_alpha_silhouette_iou=float((hit&source_mask).sum()/(hit|source_mask).sum()),
                qualified_source_pixels_missing_proxy=int((qualified&~hit).sum()),proxy_pixels=int(hit.sum()))
            if c['view'] in p['references']:
                ref=np.asarray(Image.open(p['references'][c['view']]).convert('RGBA').resize((512,512),Image.Resampling.NEAREST))[:,:,3]>=128
                geometry[name]['reference_rgba_silhouette_iou']=float((hit&ref).sum()/(hit|ref).sum())
        geometry.update(qualified_source_pixels=int(qualified.sum()),common_depth_pixels=int(common.sum()),
                        original_depth_residual=distributions(depth0),candidate_depth_residual=distributions(depth1),
                        candidate_original_depth_change=distributions(np.abs(z1[common]-z0[common])),
                        scope='centered rays; source covariance depth shares checkpoint, not independent measured surface')
        regions={}
        for r in (1,2,3):
            mask=a['regions']==r
            regions[str(r)]={}
            for name,arr in [('original',a),('candidate',b)]:
                layer=arr[f'layer_{r}']
                regions[str(r)][name]=dict(fixed_original_visible_pixels=int(mask.sum()),
                    ink_mass_on_fixed_mask=float(layer[mask].sum()),
                    support_on_fixed_mask_pixels=int((layer[mask]>.1).sum()),
                    support_fraction_on_fixed_mask=float((layer[mask]>.1).sum()/max(1,mask.sum())),
                    total_layer_ink=float(layer.sum()),
                    distance_to_hatch_p95_px=float(np.quantile(ndimage.distance_transform_edt(~(layer>.1))[mask],.95)))
        for k in ('depth','regions','contour','layer_1','layer_3'):
            np.testing.assert_array_equal(b[k],e[k])
        delta=np.abs(b['image']-e['image']);target=b['regions']==2
        band=ndimage.binary_dilation(target,iterations=2)&~ndimage.binary_erosion(target,iterations=2)
        far_other=(b['regions']>0)&~target&~band;far_bg=(b['regions']==0)&~band
        locality=dict(target_delta=float(delta[target].sum()),total_delta=float(delta.sum()),
            far_other_delta=float(delta[far_other].sum()),far_background_delta=float(delta[far_bg].sum()),
            boundary_band_delta=float(delta[band].sum()),
            far_changed_pixel_yx=np.argwhere((far_other|far_bg)&(delta>0)).tolist(),
            non_target_layers_exact=True,
            scope='saved proxy labels and fixed 2px band, not independent semantic mask')
        locality['strict_zero_far_delta_pass']=locality['far_other_delta']==0 and locality['far_background_delta']==0
        locality['far_delta_fraction']=(locality['far_other_delta']+locality['far_background_delta'])/max(float(delta.sum()),1e-30)
        assert locality['target_delta']>0
        bounds=[json.loads((unit/f'renders/static_{arm}/frame_{i:03d}.json').read_text())['bounds']['all_proxy_vertices_inside']
                for arm in ('original','baseline','edited')]
        assert all(bounds)
        rows.append(dict(view=c['view'],geometry=geometry,regions=regions,local_edit=locality,
                         original_hatch_ink=float(a['hatch'].sum()),candidate_hatch_ink=float(b['hatch'].sum()),
                         original_contour_ink=float(a['contour'].sum()),candidate_contour_ink=float(b['contour'].sum()),
                         all_three_complete_objects_inside=True))
    cold=[]
    with np.load(unit/'renders/static_edited/frame_000_arrays.npz') as a,np.load(unit/'renders/cold_reload/frame_000_arrays.npz') as b:
        for k in a.files:np.testing.assert_array_equal(a[k],b[k]);cold.append(k)
    assert sha(unit/'renders/static_edited/frame_000_image.png')==sha(unit/'renders/cold_reload/frame_000_image.png')
    prior=Path(p['previous_unit'])
    replay_original={}
    for i in range(4):
        f=f'frame_{i:03d}_image.png'
        replay_original[f]=sha(unit/'renders/static_original'/f)==sha(prior/'renders/static_baseline'/f)
    assert all(replay_original.values())
    inputs={path:sha(path)==h for path,h in p['inputs_sha256'].items()}
    assert all(inputs.values())
    trajectories={}
    for name in ('orbit','zoom'):
        files=sorted((unit/'renders'/name).glob('frame_*_image.png'))
        receipt=json.loads((unit/'renders'/name/'RENDER_RECEIPT.json').read_text())
        assert len(files)==len(p[name]) and len({sha(f) for f in files})==len(files)
        assert all(f['bounds']['all_proxy_vertices_inside'] for f in receipt['frames'])
        trajectories[name]=dict(frames=len(files),all_distinct=True,all_full_object=True,
                                seconds=[f['seconds'] for f in receipt['frames']])
    result=dict(utc=now(),execution_validation='PASS' if all(r['local_edit']['strict_zero_far_delta_pass'] for r in rows)
                  else 'PARTIAL_STRICT_LOCALITY_RESIDUAL',
        original_baseline_replay_exact=replay_original,face_topology_and_labels_exact=True,
        lower_vertices_and_paths_exact=True,edit_non_target_paths_exact=True,
        rethreshold_would_change_faces=int((region_ids(mesh['tri'].mean(1))!=mesh['regions']).sum()),
        paths={name:path_stats(s) for name,s in [('original',os),('candidate',bs),('edited',es)]},
        anchors=anchor,views=rows,cold_reload_arrays_exact=cold,trajectories=trajectories,
        input_hashes_unchanged=inputs,
        claim='finite engineering comparison; no H1/H2 or independent geometry/temporal certification')
    js(unit/'metrics/REFINEMENT_VALIDATION.json',result)
    print(json.dumps(dict(validation=result['execution_validation'],views=len(rows),paths=result['paths'])),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--unit',required=True);evaluate(p.parse_args().unit)
