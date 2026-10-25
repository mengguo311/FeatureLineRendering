"""Independent saved-layout, coordinate, composition and whole-frame readback."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,sha,js
import json
from pathlib import Path
import numpy as np
from scipy import ndimage
from PIL import Image
from run_integration import protocol,check_assets,npz,load_assets,BASE,PACKAGE,PATH_ARMS,ARMS,PAIRS,prior_frame,CBASE

def load(p):return json.loads(Path(p).read_text())
def quantiles(v):return np.quantile(v,[.5,.9,.95,1]).tolist() if len(v) else []
def turns(p):
    d=p['points'][:,1]-p['points'][:,0];d/=np.linalg.norm(d,axis=1)[:,None]
    good=(p['stroke_id'][:-1]==p['stroke_id'][1:])&(p['face'][:-1]!=p['face'][1:])
    values=np.rad2deg(np.arccos(np.clip(np.sum(d[:-1]*d[1:],axis=1)[good],-1,1)))
    return dict(face_transitions=int(good.sum()),world_turn_quantiles=quantiles(values))

def main():
    p=protocol();check_assets();refs,targets,_,_=load_assets();inputs=load(UNIT/'INPUT_LOCK.json')['files']
    for path,h in inputs.items():assert sha(path)==h,path
    for path,h in load(UNIT/'BUILD_LOCK.json')['files'].items():assert sha(UNIT/path)==h,path
    for relative,h in load(UNIT/'SOURCE_LOCK.json')['snapshots'].items():assert sha(UNIT/'source_snapshot'/relative)==h
    moved=npz(UNIT/'asset/CARRIER.npz');protection=npz(CBASE/'asset/DENOISE.npz')
    np.testing.assert_array_equal(targets[0]['vertices'][protection['protected']],refs[0]['vertices'][protection['protected']])
    vd=np.linalg.norm(targets[0]['vertices']-refs[0]['vertices'],axis=1);assert (vd<=protection['cap']+1e-12).all()
    assert sha(UNIT/'asset/CARRIER.npz')==sha(CBASE/'asset/CARRIER.npz')
    original={r['parent_stroke_id']:r for r in load(BASE/'asset/SEEDS_AND_STOPS.json')}
    records=load(UNIT/'asset/D_SEEDS_AND_STOPS.json');assert len(records)==len(original)==380
    info={};max_error=0.;new_ids=set();all_turns={}
    for part,ref,target,label in zip(('old','added'),refs,targets,(1,2)):
        paths={arm:npz(UNIT/'asset'/(arm+'_'+part+'.npz')) for arm in PATH_ARMS}
        for arm in ('A','B'):assert sha(UNIT/'asset'/(arm+'_'+part+'.npz'))==sha(BASE/'asset'/(arm+'_'+part+'.npz'))
        d=paths['D'];g=npz(UNIT/'asset'/('GENERATION_C_'+part+'.npz'))
        for k in d:
            if k!='points':np.testing.assert_array_equal(d[k],g[k])
        assert not new_ids&set(d['stroke_id']);new_ids.update(map(int,d['stroke_id']))
        errors=[]
        for q,m in ((d,ref),(g,target)):
            triangles=m['vertices'][m['faces'][q['face']]]
            expected=sum(q['bary'][:,:,k,None]*triangles[:,None,k,:] for k in range(3))
            error=float(np.abs(expected-q['points']).max());max_error=max(max_error,error);errors.append(error)
            np.testing.assert_allclose(q['points'],expected,atol=1e-12,rtol=0)
            assert (moved['partitions'][q['face']]==label).all()
        rows=[r for r in records if r['partition']==part];tangent_error=0.
        for r in rows:
            old=original[r['parent_stroke_id']];face=r['seed_face']
            assert r['requested_length']==old['requested_length'] and face==old['seed_face']
            np.testing.assert_array_equal(r['seed_bary'],old['seed_bary'])
            tri=ref['tri'][face];edges=(tri[1:]-tri[0]).T
            uv=np.linalg.lstsq(edges,np.array(old['initial_tangent']),rcond=None)[0]
            ct=target['tri'][face];expected=uv[0]*(ct[1]-ct[0])+uv[1]*(ct[2]-ct[0]);expected/=np.linalg.norm(expected)
            err=float(np.linalg.norm(expected-r['initial_tangent_generation']));tangent_error=max(err,tangent_error);assert err<1e-9
            ix=d['stroke_id']==r['stroke_id'];assert int(ix.sum())==r['segments']
            assert (d['parent_stroke_id'][ix]==r['parent_stroke_id']).all()
            for q,key in ((g,'generation_length'),(d,'pulled_length')):
                length=float(np.linalg.norm(q['points'][ix,1]-q['points'][ix,0],axis=1).sum());assert abs(length-r[key])<1e-10
            assert r['minus_length']<=r['requested_length']/2+1e-10 and r['plus_length']<=r['requested_length']/2+1e-10
        info[part]=dict(seeds=len(rows),new_paths=len(np.unique(d['stroke_id'])),segments=len(d['face']),max_anchor_error=max(errors),max_independent_tangent_error=tangent_error,
            empty_records=sum(r['empty'] for r in rows),requested_length=sum(r['requested_length'] for r in rows),generation_length=sum(r['generation_length'] for r in rows),pulled_length=sum(r['pulled_length'] for r in rows))
        for arm,q in paths.items():
            for sid in np.unique(q['stroke_id']):
                x=q['points'][q['stroke_id']==sid];np.testing.assert_allclose(x[:-1,1],x[1:,0],atol=1e-8,rtol=0)
            all_turns[arm+'_'+part]=turns(q)
    assert not new_ids&set(original)
    links=npz(PACKAGE/'SOURCE_LINK.npz');binding=npz(PACKAGE/'SOURCE_BINDING.npz')
    for q in (links,binding):np.testing.assert_array_equal(q['source_index'],np.arange(310475))
    assert binding['unknown'].sum()==195279
    far=[];absolute=[];effects=[];pngs=0;composition_error=0.;scales=load(UNIT/'BUILD_MATCH.json')['scales'];fragment=[];interactions=[]
    for v in p['views']:
        if v['kind']=='build' or (v['kind']=='arc' and v['camera']['view']=='orbit_241_24_5.3'):continue
        view=v['camera']['view'];folder=UNIT/v['kind']/view;f=npz(folder/'FRAME.npz');ref=npz(v['cache']);prior=npz(prior_frame(v));target=f['regions']==4
        near=ndimage.binary_dilation(target,iterations=2);masks={'other':(f['regions']>0)&~near,'background':(f['regions']==0)&~near}
        for k in ('source','paper','support','regions','old_regions'):np.testing.assert_array_equal(f[k],ref[k])
        for arm,key in [('A','A'),('B','B')]:
            for suffix in ('_preS','_linked_natural','_ungated_natural'):np.testing.assert_array_equal(f[arm+suffix],prior[key+suffix])
        for arm in ARMS:
            path,mode=arm.split('_');raw=f[path+'_preS']*(f['support'] if mode=='linked' else 1.)
            for match in ('natural','matched'):
                alpha=np.clip(raw*(scales[arm] if match=='matched' else 1.),0,1)
                expected=f['paper']*(1-alpha[:,:,None])+.03*alpha[:,:,None];key=arm+'_'+match
                err=float(np.abs(expected-f[key]).max());composition_error=max(composition_error,err)
                np.testing.assert_allclose(expected,f[key],atol=2e-7,rtol=0)
                d=np.abs(f['source']-f[key]).sum(2)
                absolute.append(dict(view=view,arm=key,**{n:dict(L1=float(d[m].sum(dtype=float)),pixels=int(m.sum()),max=float(d[m].max()) if m.any() else 0.) for n,m in masks.items()}))
        for link in ('linked','ungated'):
            for mode in ('natural','matched'):
                key=link+'_'+mode
                for a,b in PAIRS:
                    d=np.abs(f[a+'_'+key]-f[b+'_'+key]).sum(2)
                    far.append(dict(view=view,pair=a+'_'+b,mode=key,**{n:dict(L1=float(d[m].sum(dtype=float)),max=float(d[m].max()) if m.any() else 0.,nonzero=int((d[m]>0).sum()),above_1_255=int((d[m]>1/255).sum())) for n,m in masks.items()}))
                    effects.append(dict(view=view,pair=a+'_'+b,mode=key,target_pixels=int(target.sum()),target_L1=float(d[target].sum(dtype=float)),changed_pixels=int((d[target]>0).sum()),above_005_fraction=float((d[target]>=.05).mean())))
        fragment.append(dict(view=view,columns=['covered','accepted','region_rejected','depth_rejected'],partitions=['old','added'],**{arm:f[arm+'_fragment_diagnostics'] for arm in PATH_ARMS}))
        for file in folder.glob('*.png'):
            key=file.stem;expected=None
            if key in f:expected=f[key]
            elif key.endswith('_ink') and key[:-4]+'_alpha' in f:expected=1-f[key[:-4]+'_alpha']
            elif key.endswith('_preS_ink'):expected=1-f[key[:-4]]
            if expected is None:continue
            if expected.ndim==2:expected=np.repeat(expected[:,:,None],3,axis=2)
            with Image.open(file) as im:im.load();np.testing.assert_array_equal(np.array(im.convert('RGB')),np.uint8(np.clip(expected,0,1)*255+.5))
            pngs+=1
    decoded=0
    for file in UNIT.rglob('*.png'):
        with Image.open(file) as im:im.load()
        decoded+=1
    js(UNIT/'FAR_READBACK.json',far);js(UNIT/'FAR_ABSOLUTE.json',absolute);js(UNIT/'VISIBLE_INTERVENTION.json',effects);js(UNIT/'FRAGMENT_READBACK.json',fragment)
    js(UNIT/'GEOMETRY_READBACK.json',dict(partitions=info,face_transition_turns=all_turns,scope='Fixed seeds integrated on O/C; every displayed path embedded on O. Generation C retained independently.'))
    result=dict(status='pass',input_files_checked=len(inputs),new_D_paths=len(new_ids),max_independent_anchor_error=max_error,pngs_checked=pngs,all_png_fully_decoded=decoded,composition_error=composition_error,original_rows=310475,source_weights_and_rows_hash_fixed=True)
    js(UNIT/'AUDIT.json',result);print(json.dumps(result),flush=True)

if __name__=='__main__':main()
