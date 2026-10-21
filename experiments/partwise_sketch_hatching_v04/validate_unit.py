"""Finite engineering validation of actual saved assets and actual rendered frames."""
import runtime
from runtime import js,sha,now
from pathlib import Path
import json
import argparse
import numpy as np
from scipy import ndimage
from PIL import Image
from demo import load_asset

def validate(unit):
    unit=Path(unit);protocol=json.loads((unit/'PROTOCOL.json').read_text())
    b=unit/'assets/baseline';e=unit/'assets/edited'
    mesh,base,bmeta=load_asset(b);_,edited,emeta=load_asset(e)
    unchanged={str(i):sha(b/f'region_{i}.npz')==sha(e/f'region_{i}.npz') for i in (1,3)}
    assert all(unchanged.values())
    assert sha(b/'mesh.npz')==sha(e/'mesh.npz')
    assert sha(b/'region_2.npz')!=sha(e/'region_2.npz')
    assert bmeta['styles']['1']==emeta['styles']['1'] and bmeta['styles']['3']==emeta['styles']['3']
    anchors={}
    for name,strokes in [('baseline',base),('edited',edited)]:
        per={}
        for region,s in strokes.items():
            reconstructed=np.einsum('nij,njk->nik',s['bary'],mesh['tri'][s['face']])
            lengths=np.linalg.norm(s['points'][:,1]-s['points'][:,0],axis=1)
            _,indices=np.unique(s['stroke_id'],return_inverse=True)
            path_lengths=np.bincount(indices,weights=lengths)
            per[str(region)]=dict(max_attachment_error=float(np.abs(s['points']-reconstructed).max()),
                 min_barycentric=float(s['bary'].min()),max_bary_sum_error=float(np.abs(s['bary'].sum(2)-1).max()),
                 paths=len(path_lengths),segments=len(lengths),max_path_length=float(path_lengths.max()),
                 total_length=float(lengths.sum()),shorter_than_half_requested=int((path_lengths<.11).sum()))
            assert per[str(region)]['max_attachment_error']<1e-9 and per[str(region)]['min_barycentric']>-1e-9
            assert path_lengths.max()<=.22000001
        anchors[name]=per
    frames=[]
    for i,c in enumerate(protocol['static_cameras']):
        with np.load(unit/f'renders/static_baseline/frame_{i:03d}_arrays.npz') as f:a={k:f[k] for k in f.files}
        with np.load(unit/f'renders/static_edited/frame_{i:03d}_arrays.npz') as f:d={k:f[k] for k in f.files}
        for k in ('regions','depth','contour','layer_1','layer_3'):np.testing.assert_array_equal(a[k],d[k])
        delta=np.abs(a['image']-d['image']);target=a['regions']==2
        band=ndimage.binary_dilation(target,iterations=2)&~ndimage.binary_erosion(target,iterations=2)
        far_other=(a['regions']>0)&~target&~band;far_bg=(a['regions']==0)&~band
        reference=np.asarray(Image.open(protocol['references'][c['view']]).convert('RGBA').resize((512,512),Image.Resampling.NEAREST))
        refmask=reference[:,:,3]>=128;proxy=a['regions']>0
        iou=float((proxy&refmask).sum()/max(1,(proxy|refmask).sum()))
        row=dict(view=c['view'],delta_total=float(delta.sum()),target_delta=float(delta[target].sum()),
                 far_other_delta=float(delta[far_other].sum()),far_background_delta=float(delta[far_bg].sum()),
                 boundary_band_delta=float(delta[band].sum()),non_target_layers_exact=True,
                 proxy_silhouette_reference_alpha_iou=iou,reference_mask_pixels=int(refmask.sum()),proxy_pixels=int(proxy.sum()),
                 baseline_ink=float((1-a['image']).sum()),edited_ink=float((1-d['image']).sum()))
        row['strict_zero_far_delta_pass']=row['far_other_delta']==0 and row['far_background_delta']==0
        row['far_delta_fraction']=float((row['far_other_delta']+row['far_background_delta'])/max(1e-30,row['delta_total']))
        locations=np.argwhere((far_other|far_bg)&(delta>0))
        row['far_changed_pixel_yx']=locations.tolist()
        # Preserve the original strict-zero failure; do not silently enlarge the
        # frozen two-pixel band or modify the saved rendering to pass it.
        assert row['target_delta']>0
        frames.append(row)
    cold=[]
    with np.load(unit/'renders/static_edited/frame_000_arrays.npz') as f,np.load(unit/'renders/cold_reload/frame_000_arrays.npz') as g:
        for k in f.files:np.testing.assert_array_equal(f[k],g[k]);cold.append(k)
    a=unit/'renders/static_edited/frame_000_image.png';b=unit/'renders/cold_reload/frame_000_image.png'
    assert sha(a)==sha(b)
    trajectories={}
    for name in ('orbit','zoom'):
        receipt=json.loads((unit/f'renders/{name}/RENDER_RECEIPT.json').read_text())
        files=sorted((unit/f'renders/{name}').glob('frame_*_image.png'))
        assert len(files)==len(protocol[name]) and len({sha(p) for p in files})==len(files)
        assert all(f['bounds']['all_proxy_vertices_inside'] for f in receipt['frames'])
        trajectories[name]=dict(frame_count=len(files),all_images_distinct=True,all_proxy_vertices_inside=True,
                                render_seconds=[f['seconds'] for f in receipt['frames']])
    input_hashes={p:sha(p)==h for p,h in protocol['inputs_sha256'].items()}
    assert all(input_hashes.values())
    locality=all(x['strict_zero_far_delta_pass'] for x in frames)
    result=dict(utc=now(),execution_validation='PASS' if locality else 'PARTIAL_STRICT_LOCALITY_RESIDUAL',genuinely_ran_old_model=True,
                non_target_paths_byte_exact=unchanged,proxy_unchanged=True,anchors=anchors,static=frames,
                cold_reload_arrays_exact=cold,cold_reload_png_sha256=sha(a),trajectories=trajectories,
                input_hashes_unchanged=input_hashes,
                scope='self validation, finite cameras; proxy-relative attachment/locality only, no independent temporal correspondence or H1/H2 evidence')
    js(unit/'metrics/VALIDATION.json',result);print(json.dumps(result),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--unit',required=True);validate(p.parse_args().unit)
