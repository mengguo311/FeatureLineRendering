"""Independent frozen-source, saved-path and actual-pixel readback."""
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
    pkg=ROOT/'replay_package/data/lego';carrier=npz(pkg/'unit_008_asset/TARGET.npz');v=carrier['vertices'];faces=carrier['faces'];tri=v[faces]
    normals=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-30)
    fields=npz(UNIT/'asset/FIELDS.npz');selected=fields['partitions']>0
    q=fields['cutting_normals'];expected=np.cross(normals[:,None,:],q[None,:,:]);expected/=np.maximum(np.linalg.norm(expected,axis=2,keepdims=True),1e-30)
    np.testing.assert_allclose(fields['F0'],expected,atol=1e-12)
    from audit_tensor import audit_tensor,path_transitions
    tensor_audit=audit_tensor(carrier,fields,p['field'])
    js(UNIT/'TENSOR_READBACK.json',tensor_audit)
    for arm in ('F0','H'):
        np.testing.assert_allclose(np.linalg.norm(fields[arm][selected],axis=2),1.,atol=1e-12)
        np.testing.assert_allclose(np.sum(fields[arm][selected]*normals[selected,None,:],axis=2),0.,atol=1e-12)
    cross={}
    for arm in ('F0','H'):
        a=fields[arm][selected];angles=np.rad2deg(np.arccos(np.clip(np.abs(np.sum(a[:,0]*a[:,1],axis=1)),0,1)))
        areas=.5*np.linalg.norm(np.cross(tri[selected,1]-tri[selected,0],tri[selected,2]-tri[selected,0]),axis=1)
        cross[arm]=dict(area_weighted_mean_degrees=float(np.average(angles,weights=areas)),area_fraction_below15=float(areas[angles<15].sum()/areas.sum()),quantiles=np.quantile(angles,[.1,.5,.9]).tolist())
    previous={r['parent_stroke_id']:r for r in load(ROOT/'units/unit_001/asset/SEEDS_AND_STOPS.json')}
    directions={};max_anchor=0.;max_seed=0.;max_F0_end=0.;seed_count=collections.Counter()
    for part,label in [('old',1),('added',2)]:
        original=npz(ROOT/'units/unit_001/asset'/('A_'+part+'.npz'))
        for key,value in npz(UNIT/'asset'/('A_'+part+'.npz')).items():np.testing.assert_array_equal(value,original[key])
        for arm,offset in [('F0',900_000_000_000),('H',1_000_000_000_000)]:
            paths=npz(UNIT/'asset'/(arm+'_'+part+'.npz'));records=load(UNIT/'asset'/(arm+'_'+part+'_SEEDS.json'))
            assert (fields['partitions'][paths['face']]==label).all()
            np.testing.assert_array_equal(paths['stroke_id'],paths['parent_stroke_id']+offset)
            anchored=np.einsum('nij,njk->nik',paths['bary'],tri[paths['face']]);max_anchor=max(max_anchor,float(np.abs(anchored-paths['points']).max()))
            assert (paths['bary']>=-1e-10).all();np.testing.assert_allclose(paths['bary'].sum(2),1.,atol=1e-12)
            lengths=np.linalg.norm(paths['points'][:,1]-paths['points'][:,0],axis=1);turns=[];stops=collections.Counter();shortfalls=[];gaps=0
            for rec in records:
                oldrec=previous[rec['parent_stroke_id']];seed_count[arm]+=1
                assert rec['seed_face']==oldrec['seed_face'] and rec['layer_id']==oldrec['layer_id']
                np.testing.assert_array_equal(rec['seed_bary'],oldrec['seed_bary'])
                max_seed=max(max_seed,float(np.abs(np.asarray(rec['seed_point'])-oldrec['seed_point']).max()))
                assert abs(rec['requested_length']-oldrec['requested_length'])<1e-12
                ix=np.flatnonzero(paths['stroke_id']==rec['stroke_id']);pp=paths['points'][ix];actual=float(lengths[ix].sum())
                assert len(ix)>0 and abs(actual-rec['actual_length'])<1e-10
                assert actual<=rec['requested_length']+1e-10;shortfalls.append(rec['requested_length']-actual)
                gaps+=int((np.linalg.norm(pp[:-1,1]-pp[1:,0],axis=1)>1e-8).sum())
                tangent=(pp[:,1]-pp[:,0])/lengths[ix,None];transition=paths['face'][ix[:-1]]!=paths['face'][ix[1:]]
                turns.extend(np.rad2deg(np.arccos(np.clip((tangent[:-1]*tangent[1:]).sum(1),-1,1)))[transition].tolist())
                stops.update([rec['minus_stop'],rec['plus_stop']])
                if arm=='F0':
                    op=original['points'][original['stroke_id']==rec['parent_stroke_id']]
                    max_F0_end=max(max_F0_end,float(np.abs(pp[0,0]-op[0,0]).max()),float(np.abs(pp[-1,1]-op[-1,1]).max()))
            assert gaps==0
            directions[part+'_'+arm]=dict(length=float(lengths.sum()),strokes=len(records),segments=len(lengths),internal_gaps=gaps,
                shared_edge_turn_degrees_quantiles=np.quantile(turns,[.5,.9,.95,1]).tolist(),turn_per_world_length=float(sum(turns)/lengths.sum()),
                shortfall_quantiles=np.quantile(shortfalls,[.5,.9,.95,1]).tolist(),strokes_shorter_by_over_1e_6=int((np.array(shortfalls)>1e-6).sum()),stops=dict(stops))
    assert seed_count=={'F0':380,'H':380} and max_anchor<1e-10 and max_seed<1e-12 and max_F0_end<1e-8
    js(UNIT/'TRANSITION_READBACK.json',path_transitions(carrier,fields,lambda arm,part:npz(UNIT/'asset'/(arm+'_'+part+'.npz'))))
    links=npz(pkg/'SOURCE_LINK.npz');binding=npz(pkg/'SOURCE_BINDING.npz')
    for a in (links,binding):np.testing.assert_array_equal(a['source_index'],np.arange(310475))
    assert int(binding['unknown'].sum())==195279 and int((links['paper_strength']>0).sum())==41058 and int((links['ink_strength']>0).sum())==21006
    match=load(UNIT/'BUILD_MATCH.json');actual={key:0. for key in match['scales']};far=[];visible=[];png_count=0
    for view in load(UNIT/'CAMERAS.json')['views']:
        kind=view['kind'];name=view['camera']['view'];folder=UNIT/kind/name
        f=npz(UNIT/'build'/(name+'.npz')) if kind=='build' else npz(folder/'FRAME.npz');ref=npz(view['cache'])
        for key in ('source','paper','support','regions','old_regions'):np.testing.assert_array_equal(f[key],ref[key])
        np.testing.assert_array_equal(f['F0_preS'],ref['local_ink']);np.testing.assert_array_equal(f['F0_linked_natural'],ref['local_raw'])
        target=f['regions']==4
        if kind=='build':
            for arm,scale in match['scales'].items():
                alpha=f[arm.split('_')[0]+'_preS']*(f['support'] if arm.split('_')[1]=='linked' else 1)*scale
                im=f['paper']*(1-alpha[...,None])+.03*alpha[...,None];actual[arm]+=float(np.abs(im-f['paper'])[target].sum(dtype=float))
            continue
        measured=load(folder/'EVALUATION.json')['measurements']
        for arm,scale in match['scales'].items():
            for mode in ('natural','matched'):
                key=arm+'_'+mode;alpha=f[arm.split('_')[0]+'_preS']*(f['support'] if arm.split('_')[1]=='linked' else 1)
                if mode=='matched':alpha=alpha*scale
                im=f['paper']*(1-alpha[...,None])+.03*alpha[...,None]
                np.testing.assert_array_equal(im,f[key]);np.testing.assert_array_equal(alpha,f[key+'_alpha'])
                assert abs(float(np.abs(im-f['paper']).sum(2)[target].sum())-measured['ink_effect'][key]['target_full']['raw_L1_sum'])<1e-4
                for suffix,array in [('',im),('_ink',1-alpha)]:
                    expected=np.uint8(np.clip(array,0,1)*255+.5)
                    if expected.ndim==2:expected=np.repeat(expected[...,None],3,axis=2)
                    np.testing.assert_array_equal(np.asarray(Image.open(folder/(key+suffix+'.png'))),expected);png_count+=1
        for arm in ('F0','H'):
            for layer in (0,1):
                key=arm+'_layer'+str(layer)+'_preS';expected=np.uint8(np.clip(1-f[key],0,1)*255+.5)
                np.testing.assert_array_equal(np.asarray(Image.open(folder/(key+'.png'))),np.repeat(expected[...,None],3,axis=2));png_count+=1
            counts=f[arm+'_fragment_diagnostics'];assert (counts[:,0]==counts[:,1:].sum(1)).all()
        if kind=='arc' and name=='orbit_241_24_5.3':continue
        near=ndimage.binary_dilation(target,iterations=2);delta=np.abs(f['H_linked_matched']-f['F0_linked_matched']).sum(2)
        far.append(dict(view=name,far_raw_L1_sum=float(delta[~near].sum()),far_max_pixel_L1=float(delta[~near].max()),far_pixels_above_1_255=int((delta[~near]>1/255).sum()),
            far_nonzero_pixels=int((delta[~near]>0).sum()),target_delta_L1=float(delta[target].sum()),target_changed_fraction_005=float((delta[target]>=.05).mean())))
        visible.append(dict(view=name,target_pixels=int(target.sum()),field_change_degrees_quantiles=np.quantile(f['visible_field_change_degrees'][target],[.5,.9,.95,1]).tolist(),
            changed_field_target_pixels_over_1deg=int((f['visible_field_change_degrees'][target]>1).sum()),F0_fragments=f['F0_fragment_diagnostics'].tolist(),H_fragments=f['H_fragment_diagnostics'].tolist()))
    for arm,val in actual.items():assert abs(val-match['budget'])/match['budget']<1e-5
    js(UNIT/'DIRECTION_READBACK.json',dict(paths=directions,cross_layer=cross));js(UNIT/'FAR_READBACK.json',far);js(UNIT/'VISIBLE_INTERVENTION.json',visible)
    result=dict(status='pass',input_files_checked=len(load(UNIT/'INPUT_LOCK.json')['files']),original_files_preserved=True,source_snapshot_preserved=True,
        max_anchor_error=max_anchor,max_seed_error=max_seed,max_F0_endpoint_error=max_F0_end,seeds_checked=dict(seed_count),all_F0_renders_exact=True,
        pngs_decoded_and_checked=png_count,actual_BUILD_matched=actual,original_source_rows=310475,UNKNOWN=195279,scope='Regional original-ID S only, no per-path certification',audit_source_sha256=sha(__file__),tensor_audit=tensor_audit)
    js(UNIT/'AUDIT.json',result);print(json.dumps(result),flush=True)

if __name__=='__main__':main()
