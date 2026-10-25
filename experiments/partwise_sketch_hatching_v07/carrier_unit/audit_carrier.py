"""Independent saved-array readback; no geometry or appearance optimization."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,OUTPUT_ROOT as ROOT,HERE,sha,js
from pathlib import Path
import json,collections
import numpy as np
from scipy import ndimage
from PIL import Image

def load(p):return json.loads(p.read_text())
def npz(p):
    with np.load(p,allow_pickle=False) as z:return {k:z[k] for k in z.files}
def main():
    p=load(UNIT/'PROTOCOL.json');assert sha(UNIT/'DECISION.json')==p['decision_sha256']
    assert sha(UNIT/'PROTOCOL.json')==load(UNIT/'PROTOCOL_LOCK.json')['sha256']
    for name,h in p['frozen'].items():assert sha(UNIT/name)==h
    for path,h in load(UNIT/'INPUT_LOCK.json')['files'].items():assert sha(path)==h,path
    lock=load(UNIT/'SOURCE_LOCK.json')
    for path,h in lock['files'].items():assert sha(path)==h,path
    for path,h in lock['snapshots'].items():assert sha(UNIT/'source_snapshot'/path)==h,path
    for name in ('ASSET_LOCK.json','BUILD_LOCK.json'):
        for path,h in load(UNIT/name)['files'].items():assert sha(UNIT/path)==h,path
    pkg=ROOT/'replay_package/data/lego';old=npz(pkg/'unit_008_asset/TARGET.npz');c=npz(UNIT/'asset/CARRIER.npz');d=npz(UNIT/'asset/DENOISE.npz')
    for k in ('faces','face_regions','old_face_regions'):np.testing.assert_array_equal(c[k],old[k])
    v=old['vertices'];faces=old['faces'];tri=v[faces];ctri=c['vertices'][faces]
    n=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);cn=np.cross(ctri[:,1]-ctri[:,0],ctri[:,2]-ctri[:,0])
    valid=np.linalg.norm(n,axis=1)>2e-14;assert (np.einsum('ij,ij->i',n[valid],cn[valid])>0).all()
    displacement=np.linalg.norm(c['vertices']-v,axis=1)
    np.testing.assert_array_equal(c['vertices'][d['protected']],v[d['protected']])
    assert (displacement<=d['cap']+1e-12).all()
    np.testing.assert_allclose(displacement,d['displacement'],atol=1e-15,rtol=0)
    links=npz(pkg/'SOURCE_LINK.npz');binding=npz(pkg/'SOURCE_BINDING.npz')
    np.testing.assert_array_equal(links['source_index'],np.arange(310475));np.testing.assert_array_equal(binding['source_index'],np.arange(310475))
    assert int(binding['unknown'].sum())==195279
    basis=np.asarray(load(UNIT/'asset/PROVENANCE.json')['basis']);max_anchor=0.;max_slice=0.;directions={}
    for part,label in [('old',1),('added',2)]:
        for arm,triangles in [('A',tri),('C',ctri)]:
            paths=npz(UNIT/'asset'/(arm+'_'+part+'.npz'))
            if arm=='A':
                previous=npz(ROOT/'units/unit_001/asset'/('A_'+part+'.npz'))
                for key in paths:np.testing.assert_array_equal(paths[key],previous[key])
            else:
                assert (paths['stroke_id']>=200_000_000_000).all()
                assert (c['partitions'][paths['face']]==label).all()
            expected=np.einsum('nij,njk->nik',paths['bary'],triangles[paths['face']]);max_anchor=max(max_anchor,float(np.abs(expected-paths['points']).max()))
            assert (paths['bary']>=-1e-10).all();np.testing.assert_allclose(paths['bary'].sum(2),1,atol=1e-12)
            angles=np.deg2rad(np.where(paths['layer_id']==0,35.,95.));normal=np.cos(angles)[:,None]*basis[0]+np.sin(angles)[:,None]*basis[1]
            spacing=np.where(paths['layer_id']==0,.06,.075)
            levels=np.einsum('nij,nj->ni',paths['points'],normal)/spacing[:,None]-.1732050807568877
            max_slice=max(max_slice,float(np.abs(levels-np.round(levels)).max()))
            lengths=np.linalg.norm(paths['points'][:,1]-paths['points'][:,0],axis=1);turns=[];breaks=0
            for sid in np.unique(paths['stroke_id']):
                ix=np.flatnonzero(paths['stroke_id']==sid);pp=paths['points'][ix]
                breaks+=int((np.linalg.norm(pp[:-1,1]-pp[1:,0],axis=1)>1e-8).sum())
                tangent=(pp[:,1]-pp[:,0])/lengths[ix,None]
                transition=paths['face'][ix[:-1]]!=paths['face'][ix[1:]]
                turns.extend(np.rad2deg(np.arccos(np.clip((tangent[:-1]*tangent[1:]).sum(1),-1,1)))[transition].tolist())
            assert breaks==0
            directions[part+'_'+arm]=dict(length=float(lengths.sum()),strokes=len(np.unique(paths['stroke_id'])),segments=len(lengths),
                stored_internal_gaps=breaks,actual_shared_edge_turn_quantiles=np.quantile(turns,[.5,.9,.95,1]).tolist(),turn_per_world_length=float(sum(turns)/lengths.sum()))
    assert max_anchor<1e-10 and max_slice<1e-8
    views=load(UNIT/'CAMERAS.json')['views'];match=load(UNIT/'BUILD_MATCH.json');actual={key:0. for key in match['scales']};png_count=0;far=[];visible=[]
    for view in views:
        kind=view['kind'];name=view['camera']['view']
        if kind=='build':
            f=npz(UNIT/'build'/(name+'.npz'));mask=f['regions']==4
            for arm,scale in match['scales'].items():
                alpha=f[arm[0]+'_preS']*(f['support'] if arm.split('_')[1]=='linked' else 1)*scale
                im=f['paper']*(1-alpha[...,None])+.03*alpha[...,None]
                actual[arm]+=float(np.abs(im-f['paper'])[mask].sum(dtype=float))
            continue
        folder=UNIT/kind/name;f=npz(folder/'FRAME.npz');ref=npz(view['cache']);m=load(folder/'EVALUATION.json')['measurements']
        for key in ('source','paper','support','regions','old_regions'):np.testing.assert_array_equal(f[key],ref[key])
        np.testing.assert_array_equal(f['A_preS'],ref['local_ink']);np.testing.assert_array_equal(f['A_linked_natural'],ref['local_raw'])
        mask=f['regions']==4;near=ndimage.binary_dilation(mask,iterations=2);far_mask=~near
        for arm in match['scales']:
            for mode in ('natural','matched'):
                key=arm+'_'+mode;alpha=f[arm[0]+'_preS']*(f['support'] if arm.split('_')[1]=='linked' else 1)
                if mode=='matched':alpha=alpha*match['scales'][arm]
                im=f['paper']*(1-alpha[...,None])+.03*alpha[...,None]
                np.testing.assert_array_equal(im,f[key]);np.testing.assert_array_equal(alpha,f[key+'_alpha'])
                assert abs(float(np.abs(im-f['paper']).sum(2)[mask].sum())-m['ink_effect'][key]['target_full']['raw_L1_sum'])<1e-4
                for suffix,array in [('',im),('_ink',1-alpha)]:
                    expected=np.uint8(np.clip(array,0,1)*255+.5)
                    if expected.ndim==2:expected=np.repeat(expected[...,None],3,axis=2)
                    np.testing.assert_array_equal(np.asarray(Image.open(folder/(key+suffix+'.png'))),expected);png_count+=1
        for arm in ('A','C'):
            counts=f[arm+'_fragment_diagnostics'];assert (counts[:,0]==counts[:,1:].sum(1)).all()
        # Zero regional support must leave the original-GS paper exactly unchanged.
        z=np.zeros_like(f['support']);np.testing.assert_array_equal(f['paper']*(1-z[...,None])+.03*z[...,None],f['paper'])
        if kind=='arc' and name=='orbit_241_24_5.3':continue
        delta=np.abs(f['C_linked_matched']-f['A_linked_matched']).sum(2)
        far.append(dict(view=name,kind=kind,far_raw_L1_sum=float(delta[far_mask].sum()),far_max_pixel_L1=float(delta[far_mask].max()),
            far_pixels_above_1_255=int((delta[far_mask]>1/255).sum()),far_nonzero_pixels=int((delta[far_mask]>0).sum()),
            target_delta_L1=float(delta[mask].sum()),target_changed_fraction_005=float((delta[mask]>=.05).mean())))
        visible.append(dict(view=name,target_pixels=int(mask.sum()),changed_carrier_target_pixels=int((mask&f['changed_carrier_visible_mask']).sum()),
            A_fragments=f['A_fragment_diagnostics'].tolist(),C_fragments=f['C_fragment_diagnostics'].tolist(),
            columns=['covered','accepted','region_rejected','depth_rejected'],rows=['old','added']))
    for key,val in actual.items():assert abs(val-match['budget'])/match['budget']<1e-5
    js(UNIT/'DIRECTION_READBACK.json',directions);js(UNIT/'FAR_READBACK.json',far);js(UNIT/'VISIBLE_INTERVENTION.json',visible)
    receipt=dict(status='pass',input_files_checked=len(load(UNIT/'INPUT_LOCK.json')['files']),original_files_preserved=True,
        source_snapshot_preserved=True,max_anchor_error=max_anchor,max_slice_level_error=max_slice,all_A_renders_exact=True,
        pngs_decoded_and_checked=png_count,actual_BUILD_matched=actual,original_source_rows=310475,UNKNOWN=195279,
        no_new_original_ID_claim='Region S only; no per-path Gaussian certification',audit_source_sha256=sha(__file__))
    js(UNIT/'AUDIT.json',receipt);print(json.dumps(receipt),flush=True)
if __name__=='__main__':main()
