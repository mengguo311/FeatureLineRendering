"""Read back immutable inputs, paired deletions, anchors and actual image effects."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,OUTPUT_ROOT as ROOT,sha,js
import json
import numpy as np
from scipy import ndimage
from PIL import Image

def load(p):return json.loads(p.read_text())
def npz(p):
    with np.load(p,allow_pickle=False) as z:return {k:z[k] for k in z.files}
def length(p):return float(np.linalg.norm(p['points'][:,1]-p['points'][:,0],axis=1).sum())

def independent_choice(total,crossings,gap):
    for center in crossings:
        low,high=center-gap/2,center+gap/2
        if low<=1e-11 or high>=total-1e-11:continue
        knots=np.array(sorted(set([0.,total,low,high]+crossings)))
        left,right=knots[:-1],knots[1:];mid=(left+right)/2
        valid=((mid<low)|(mid>high))&((right-left)>gap+2e-11)
        ids=np.flatnonzero(valid)
        if not len(ids):continue
        best=min(ids,key=lambda i:(-(right[i]-left[i]),left[i]))
        c=float(mid[best]);return [low,high],[c-gap/2,c+gap/2]
    return None

def expected_span(p,start,end):
    ll=np.linalg.norm(p['points'][:,1]-p['points'][:,0],axis=1);cs=np.r_[0.,np.cumsum(ll)]
    ids=np.flatnonzero(np.minimum(end,cs[1:])-np.maximum(start,cs[:-1])>1e-11)
    t=np.stack([(np.maximum(start,cs[ids])-cs[ids])/ll[ids],(np.minimum(end,cs[ids+1])-cs[ids])/ll[ids]],axis=1)
    return ids,(1-t[:,:,None])*p['points'][ids,0,None,:]+t[:,:,None]*p['points'][ids,1,None,:]

def main():
    protocol=load(UNIT/'PROTOCOL.json');assert sha(UNIT/'DECISION.json')==protocol['decision_sha256']
    assert sha(UNIT/'PROTOCOL.json')==load(UNIT/'PROTOCOL_LOCK.json')['sha256']
    for name,h in protocol['frozen'].items():assert sha(UNIT/name)==h,name
    inputs=load(UNIT/'INPUT_LOCK.json')['files']
    for path,h in inputs.items():assert sha(path)==h,path
    lock=load(UNIT/'SOURCE_LOCK.json')
    for path,h in lock['files'].items():assert sha(path)==h,path
    for path,h in lock['snapshots'].items():assert sha(UNIT/'source_snapshot'/path)==h,path
    for name in ('ASSET_LOCK.json','BUILD_LOCK.json'):
        for path,h in load(UNIT/name)['files'].items():assert sha(UNIT/path)==h,path
    pkg=ROOT/'replay_package/data/lego';t=npz(pkg/'unit_008_asset/TARGET.npz');tri=t['vertices'][t['faces']]
    fields=npz(UNIT/'asset/FIELDS.npz');assert sha(UNIT/'asset/FIELDS.npz')==sha(ROOT/'units/unit_007/asset/FIELDS.npz')
    excluded={tuple(sorted(map(int,x))) for x in fields['excluded_pairs']}
    error=0.;length_error=0.;eligible=0;unchanged=0;all_ids={'B':set(),'C':set()};records_out=[]
    for part,label in [('old',1),('added',2)]:
        a=npz(UNIT/'asset'/('A_'+part+'.npz'));assert sha(UNIT/'asset'/('A_'+part+'.npz'))==sha(ROOT/'units/unit_007/asset'/('H_'+part+'.npz'))
        arms={arm:npz(UNIT/'asset'/(arm+'_'+part+'.npz')) for arm in ('B','C')}
        records=load(UNIT/'asset'/(part+'_PAIRS.json'));assert len(records)==len(np.unique(a['stroke_id']))
        assert {r['source_h_stroke_id'] for r in records}==set(map(int,a['stroke_id']))
        for r in records:
            sid=r['source_h_stroke_id'];parent={k:v[a['stroke_id']==sid] for k,v in a.items()};total=length(parent)
            lens=np.linalg.norm(parent['points'][:,1]-parent['points'][:,0],axis=1);cs=np.cumsum(lens)
            crosses=[float(cs[i]) for i in range(len(cs)-1) if parent['face'][i]!=parent['face'][i+1] and tuple(sorted(map(int,parent['face'][i:i+2]))) in excluded]
            choice=independent_choice(total,crosses,.035);assert (choice is not None)==r['eligible']
            if not r['eligible']:
                unchanged+=1
                for arm,x in arms.items():
                    for k,v in parent.items():np.testing.assert_array_equal(v,x[k][x['stroke_id']==sid])
                continue
            eligible+=1
            np.testing.assert_allclose(r['B_interval'],choice[0],atol=1e-12,rtol=0);np.testing.assert_allclose(r['C_interval'],choice[1],atol=1e-12,rtol=0)
            assert max(r['B_interval'][0],r['C_interval'][0])>=min(r['B_interval'][1],r['C_interval'][1])-1e-12
            bpair=r['excluded_face_pair'];assert tuple(sorted(bpair)) in excluded
            assert len(set(t['faces'][bpair[0]])&set(t['faces'][bpair[1]]))==2
            for arm,x in arms.items():
                low,high=r[arm+'_interval'];assert low>0 and high<total
                if arm=='C':assert all(not low<=c<=high for c in crosses)
                ids=r[arm+'_child_ids'];assert not set(ids)&set(map(int,a['stroke_id']))
                total_retained=0.
                for child,start,end in [(ids[0],0.,low),(ids[1],high,total)]:
                    out={k:v[x['stroke_id']==child] for k,v in x.items()};assert len(out['face'])
                    ix,expected=expected_span(parent,start,end)
                    np.testing.assert_array_equal(out['face'],parent['face'][ix]);np.testing.assert_allclose(out['points'],expected,atol=1e-12,rtol=0)
                    for k in ('layer_id','visibility_mask','parent_stroke_id'):np.testing.assert_array_equal(out[k],parent[k][ix])
                    np.testing.assert_allclose(out['points'][:-1,1],out['points'][1:,0],atol=1e-8,rtol=0)
                    total_retained+=length(out);all_ids[arm].add(child)
                length_error=max(length_error,abs(total-total_retained-.035))
                assert abs(total-total_retained-.035)<1e-12
            records_out.append(dict(part=part,parent=sid,B=r['B_interval'],C=r['C_interval']))
        for arm,x in arms.items():
            assert (fields['partitions'][x['face']]==label).all()
            recon=np.einsum('nij,njk->nik',x['bary'],tri[x['face']]);error=max(error,float(np.max(np.abs(recon-x['points']))))
            assert (x['bary']>=-1e-8).all();np.testing.assert_allclose(recon,x['points'],atol=1e-10,rtol=0)
    assert not all_ids['B']&all_ids['C']
    binding=npz(pkg/'SOURCE_BINDING.npz');link=npz(pkg/'SOURCE_LINK.npz')
    np.testing.assert_array_equal(binding['source_index'],np.arange(310475))
    far=[];effects=[];png_count=0
    for v in load(UNIT/'CAMERAS.json')['views']:
        if v['kind']=='build' or (v['kind']=='arc' and v['camera']['view']=='orbit_241_24_5.3'):continue
        folder=UNIT/v['kind']/v['camera']['view'];f=npz(folder/'FRAME.npz');ref=npz(v['cache']);target=f['regions']==4;near=ndimage.binary_dilation(target,iterations=2)
        masks={'other':(f['regions']>0)&~near,'background':(f['regions']==0)&~near}
        for key in ('source','paper','support','regions','old_regions'):np.testing.assert_array_equal(f[key],ref[key])
        for aa,bb in [('A','B'),('A','C'),('B','C')]:
            for link_mode in ('linked','ungated'):
                for mode in ('natural','matched'):
                    key=link_mode+'_'+mode;d=np.abs(f[aa+'_'+key]-f[bb+'_'+key]).sum(2)
                    far.append(dict(view=v['camera']['view'],pair=aa+'_'+bb,mode=key,**{n:dict(L1=float(d[m].sum(dtype=float)),max=float(d[m].max()) if m.any() else 0.,nonzero=int((d[m]>0).sum()),above_1_255=int((d[m]>1/255).sum())) for n,m in masks.items()}))
                    effects.append(dict(view=v['camera']['view'],pair=aa+'_'+bb,mode=key,target_pixels=int(target.sum()),target_L1=float(d[target].sum(dtype=float)),changed_pixels=int((d[target]>0).sum()),above_005_fraction=float((d[target]>=.05).mean())))
        for file in folder.glob('*.png'):
            key=file.stem;expected=None
            if key in f:expected=f[key]
            elif key.endswith('_ink') and key[:-4]+'_alpha' in f:expected=1-f[key[:-4]+'_alpha']
            elif key.endswith('_preS_ink'):expected=1-f[key[:-4]]
            if expected is None:continue
            if key.endswith('_preS') and 'layer' in key:expected=1-expected
            if expected.ndim==2:expected=np.repeat(expected[:,:,None],3,axis=2)
            with Image.open(file) as im:im.load();np.testing.assert_array_equal(np.array(im.convert('RGB')),np.uint8(np.clip(expected,0,1)*255+.5))
            png_count+=1
    decoded=0
    for file in UNIT.rglob('*.png'):
        with Image.open(file) as im:im.load()
        decoded+=1
    js(UNIT/'FAR_READBACK.json',far);js(UNIT/'VISIBLE_INTERVENTION.json',effects)
    js(UNIT/'PAIR_READBACK.json',dict(eligible=eligible,unchanged=unchanged,max_length_error=length_error,max_anchor_error=error,records=records_out))
    result=dict(status='pass',input_files_checked=len(inputs),eligible_parents=eligible,unchanged_parents=unchanged,max_anchor_error=error,max_removed_length_error=length_error,
        original_rows=len(binding['source_index']),source_row_weights_hash_fixed=True,pngs_checked=png_count,all_png_fully_decoded=decoded,
        scope='Independent interval selection/subset, anchors and stored pixels; proxy self-consistency, not physical or semantic truth.')
    js(UNIT/'AUDIT.json',result);print(json.dumps(result),flush=True)

if __name__=='__main__':main()
