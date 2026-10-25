"""Read back frozen inputs, per-parent lengths/components and actual pixels."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,OUTPUT_ROOT as ROOT,sha,js
import json,collections
import numpy as np
from scipy import ndimage
from PIL import Image

def load(p):return json.loads(p.read_text())
def npz(p):
    with np.load(p,allow_pickle=False) as z:return {k:z[k] for k in z.files}

def components(faces,allowed):
    edges=collections.defaultdict(list)
    for i,face in enumerate(faces):
        for a,b in ((0,1),(1,2),(2,0)):edges[tuple(sorted((int(face[a]),int(face[b]))))].append(i)
    graph=collections.defaultdict(list)
    for fs in edges.values():
        if len(fs)==2 and allowed[fs].all():a,b=fs;graph[a].append(b);graph[b].append(a)
    labels=np.full(len(faces),-1,int);n=0
    for i in np.flatnonzero(allowed):
        if labels[i]>=0:continue
        queue=[i];labels[i]=n
        while queue:
            for j in graph[queue.pop()]:
                if labels[j]<0:labels[j]=n;queue.append(j)
        n+=1
    return labels

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
    fields=npz(UNIT/'asset/FIELDS.npz');reference_fields=npz(ROOT/'units/unit_003/asset/FIELDS.npz')
    for key,value in fields.items():np.testing.assert_array_equal(value,reference_fields[key])
    paths_stats={};max_anchor=0.;max_length=0.;max_level=0.;counts=collections.Counter();quotas={};moved=[]
    for part,label in [('old',1),('added',2)]:
        old=npz(ROOT/'units/unit_001/asset'/('A_'+part+'.npz'));oldrec=load(ROOT/'units/unit_003/asset'/('F0_'+part+'_SEEDS.json'))
        previous={r['parent_stroke_id']:r for r in oldrec};comp=components(faces,fields['partitions']==label)
        for k,val in npz(UNIT/'asset'/('A_'+part+'.npz')).items():np.testing.assert_array_equal(val,old[k])
        expected_quota=collections.Counter((int(comp[r['seed_face']]),r['layer_id']) for r in oldrec)
        for arm,offset in [('G0',500_000_000_000),('G1',600_000_000_000)]:
            paths=npz(UNIT/'asset'/(arm+'_'+part+'.npz'));records=load(UNIT/'asset'/(arm+'_'+part+'_SEEDS.json'));actual_quota=collections.Counter()
            np.testing.assert_array_equal(paths['stroke_id'],paths['parent_stroke_id']+offset)
            anchor=np.einsum('nij,njk->nik',paths['bary'],tri[paths['face']]);max_anchor=max(max_anchor,float(np.abs(anchor-paths['points']).max()))
            assert (paths['bary']>=-1e-10).all();np.testing.assert_allclose(paths['bary'].sum(2),1.,atol=1e-12)
            lengths=np.linalg.norm(paths['points'][:,1]-paths['points'][:,0],axis=1);turns=[];gaps=0
            for r in records:
                prior=previous[r['parent_stroke_id']];counts[arm]+=1
                assert r['layer_id']==prior['layer_id'];assert abs(r['requested_length']-prior['requested_length'])<1e-12
                component=int(comp[prior['seed_face']]);assert comp[r['seed_face']]==component
                actual_quota[(component,r['layer_id'])]+=1
                ix=np.flatnonzero(paths['stroke_id']==r['stroke_id']);pp=paths['points'][ix]
                assert (comp[paths['face'][ix]]==component).all()
                actual=float(lengths[ix].sum());max_length=max(max_length,abs(actual-r['requested_length']))
                assert abs(actual-r['actual_length'])<1e-10 and r['minus_stop']==r['plus_stop']=='requested_length'
                np.testing.assert_allclose(np.asarray(r['seed_bary'])@tri[r['seed_face']],r['seed_point'],atol=1e-12)
                gaps+=int((np.linalg.norm(pp[:-1,1]-pp[1:,0],axis=1)>1e-8).sum())
                q=fields['cutting_normals'][r['layer_id']];level=np.asarray(r['seed_point'])@q
                max_level=max(max_level,float(np.abs(pp@q-level).max()))
                tangent=(pp[:,1]-pp[:,0])/lengths[ix,None];transition=paths['face'][ix[:-1]]!=paths['face'][ix[1:]]
                if len(ix)>1:turns.extend(np.rad2deg(np.arccos(np.clip((tangent[:-1]*tangent[1:]).sum(1),-1,1)))[transition].tolist())
                if arm=='G1':
                    assert r['component']==component
                    dis=float(np.linalg.norm(np.asarray(r['seed_point'])-prior['seed_point']));assert abs(dis-r['seed_displacement'])<1e-12
                    if r['chosen_candidate']==0:np.testing.assert_array_equal(r['seed_bary'],prior['seed_bary']);assert r['seed_face']==prior['seed_face']
                    moved.append(dict(part=part,parent=r['parent_stroke_id'],moved=dis>1e-10,displacement=dis,layer=r['layer_id'],component=component))
            assert gaps==0 and actual_quota==expected_quota
            quotas[part+'_'+arm]={str(k):n for k,n in sorted(actual_quota.items())}
            paths_stats[part+'_'+arm]=dict(strokes=len(records),segments=len(lengths),length=float(lengths.sum()),internal_gaps=gaps,
                shared_edge_turn_degrees_quantiles=np.quantile(turns,[.5,.9,.95,1]).tolist() if turns else [],turn_per_world_length=float(sum(turns)/lengths.sum()))
            if arm=='G0':
                original=npz(ROOT/'units/unit_003/asset'/('F0_'+part+'.npz'))
                for key in ('points','bary','face','layer_id','visibility_mask','parent_stroke_id'):np.testing.assert_array_equal(paths[key],original[key])
    assert counts=={'G0':380,'G1':380} and max_anchor<1e-10 and max_length<1e-9 and max_level<1e-8
    links=npz(pkg/'SOURCE_LINK.npz');binding=npz(pkg/'SOURCE_BINDING.npz')
    for a in (links,binding):np.testing.assert_array_equal(a['source_index'],np.arange(310475))
    assert int(binding['unknown'].sum())==195279 and int((links['paper_strength']>0).sum())==41058 and int((links['ink_strength']>0).sum())==21006
    match=load(UNIT/'BUILD_MATCH.json');actual={k:0. for k in match['scales']};far=[];visible=[];png_count=0
    for view in load(UNIT/'CAMERAS.json')['views']:
        kind=view['kind'];name=view['camera']['view'];folder=UNIT/kind/name
        f=npz(UNIT/'build'/(name+'.npz')) if kind=='build' else npz(folder/'FRAME.npz');ref=npz(view['cache'])
        for key in ('source','paper','support','regions','old_regions'):np.testing.assert_array_equal(f[key],ref[key])
        np.testing.assert_array_equal(f['G0_preS'],ref['local_ink']);np.testing.assert_array_equal(f['G0_linked_natural'],ref['local_raw']);target=f['regions']==4
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
        for arm in ('G0','G1'):
            counts_frag=f[arm+'_fragment_diagnostics'];assert (counts_frag[:,0]==counts_frag[:,1:].sum(1)).all()
            for layer in (0,1):
                a=f[arm+'_layer'+str(layer)+'_preS'];assert (a<=f[arm+'_preS']+1e-7).all()
                expected=np.repeat(np.uint8(np.clip(1-a,0,1)*255+.5)[...,None],3,axis=2)
                np.testing.assert_array_equal(np.asarray(Image.open(folder/(arm+'_layer'+str(layer)+'_preS.png'))),expected);png_count+=1
        if kind=='arc' and name=='orbit_241_24_5.3':continue
        near=ndimage.binary_dilation(target,iterations=2);delta=np.abs(f['G1_linked_matched']-f['G0_linked_matched']).sum(2)
        far.append(dict(view=name,far_raw_L1_sum=float(delta[~near].sum()),far_max_pixel_L1=float(delta[~near].max()),
            far_pixels_above_1_255=int((delta[~near]>1/255).sum()),far_nonzero_pixels=int((delta[~near]>0).sum()),
            target_delta_L1=float(delta[target].sum()),target_changed_fraction_005=float((delta[target]>=.05).mean())))
        visible.append(dict(view=name,target_pixels=int(target.sum()),G0_fragments=f['G0_fragment_diagnostics'].tolist(),G1_fragments=f['G1_fragment_diagnostics'].tolist(),
            per_layer_target_mass={arm:[float(f[arm+'_layer'+str(l)+'_preS'][target].sum()) for l in (0,1)] for arm in ('G0','G1')}))
    for arm,value in actual.items():assert abs(value-match['budget'])/match['budget']<1e-5
    js(UNIT/'PATH_READBACK.json',dict(paths=paths_stats,quotas=quotas,per_parent_moves=moved,max_request_length_error=max_length,max_cutting_plane_residual=max_level))
    js(UNIT/'FAR_READBACK.json',far);js(UNIT/'VISIBLE_INTERVENTION.json',visible)
    result=dict(status='pass',input_files_checked=len(load(UNIT/'INPUT_LOCK.json')['files']),original_files_preserved=True,source_snapshot_preserved=True,
        max_anchor_error=max_anchor,max_request_length_error=max_length,max_cutting_plane_residual=max_level,strokes_checked=dict(counts),
        G0_all_saved_geometry_and_renders_exact=True,pngs_decoded_and_checked=png_count,actual_BUILD_matched=actual,
        original_source_rows=310475,UNKNOWN=195279,scope='Regional original-ID S only; no per-path Gaussian certification',audit_source_sha256=sha(__file__))
    js(UNIT/'AUDIT.json',result);print(json.dumps(result),flush=True)

if __name__=='__main__':main()
