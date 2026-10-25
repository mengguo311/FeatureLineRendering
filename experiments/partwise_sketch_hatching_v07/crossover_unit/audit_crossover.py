"""Independent saved-layout, coordinate, composition and whole-frame readback."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,sha,js
import json
from pathlib import Path
import numpy as np
from scipy import ndimage
from PIL import Image
from run_crossover import protocol,check_assets,npz,load_assets,BASE,PACKAGE,PATH_ARMS,ARMS,PAIRS,prior_frame

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
    moved=npz(UNIT/'asset/CARRIER.npz');protection=npz(BASE/'asset/DENOISE.npz')
    np.testing.assert_array_equal(targets[0]['vertices'][protection['protected']],refs[0]['vertices'][protection['protected']])
    vd=np.linalg.norm(targets[0]['vertices']-refs[0]['vertices'],axis=1);assert (vd<=protection['cap']+1e-12).all()
    info={};max_error=0.;new_ids=set();all_turns={}
    for part,ref,target,label in zip(('old','added'),refs,targets,(1,2)):
        paths={arm:npz(UNIT/'asset'/(arm+'_'+part+'.npz')) for arm in PATH_ARMS}
        for arm,key in [('OO','A'),('CC','C')]:assert sha(UNIT/'asset'/(arm+'_'+part+'.npz'))==sha(BASE/'asset'/(key+'_'+part+'.npz'))
        for source,dest,carrier in [('OO','OC',target),('CC','CO',ref)]:
            a,t=paths[source],paths[dest]
            assert set(a)==set(t)
            for k in a:
                if k not in ('points','stroke_id'):np.testing.assert_array_equal(a[k],t[k])
            records=load(UNIT/'asset'/(dest+'_'+part+'_MIGRATION.json'))
            assert len(records)==len(np.unique(a['stroke_id']))
            assert not new_ids&set(t['stroke_id']);new_ids.update(map(int,t['stroke_id']))
            for r in records:np.testing.assert_array_equal(a['stroke_id']==r['immediate_saved_layout_id'],t['stroke_id']==r['stroke_id'])
            triangles=carrier['vertices'][carrier['faces'][t['face']]]
            expected=sum(t['bary'][:,:,k,None]*triangles[:,None,k,:] for k in range(3))
            error=float(np.abs(expected-t['points']).max());max_error=max(max_error,error)
            np.testing.assert_allclose(t['points'],expected,atol=1e-12,rtol=0)
            assert (moved['partitions'][t['face']]==label).all()
            displacement=np.linalg.norm(t['points']-a['points'],axis=2)
            assert (displacement<=vd[carrier['faces'][t['face']]].max(1)[:,None]+1e-12).all()
            info[dest+'_'+part]=dict(paths=len(records),segments=len(a['face']),moved_paths=sum(r['moved'] for r in records),endpoint_displacement_quantiles=quantiles(displacement.ravel()),max_anchor_error=error)
        for arm,q in paths.items():
            for sid in np.unique(q['stroke_id']):
                x=q['points'][q['stroke_id']==sid];np.testing.assert_allclose(x[:-1,1],x[1:,0],atol=1e-8,rtol=0)
            all_turns[arm+'_'+part]=turns(q)
    assert len(new_ids)==756
    links=npz(PACKAGE/'SOURCE_LINK.npz');binding=npz(PACKAGE/'SOURCE_BINDING.npz')
    for q in (links,binding):np.testing.assert_array_equal(q['source_index'],np.arange(310475))
    assert binding['unknown'].sum()==195279
    far=[];absolute=[];effects=[];pngs=0;composition_error=0.;scales=load(UNIT/'BUILD_MATCH.json')['scales'];fragment=[];interactions=[]
    for v in p['views']:
        if v['kind']=='build' or (v['kind']=='arc' and v['camera']['view']=='orbit_241_24_5.3'):continue
        view=v['camera']['view'];folder=UNIT/v['kind']/view;f=npz(folder/'FRAME.npz');ref=npz(v['cache']);prior=npz(prior_frame(v));target=f['regions']==4
        near=ndimage.binary_dilation(target,iterations=2);masks={'other':(f['regions']>0)&~near,'background':(f['regions']==0)&~near}
        for k in ('source','paper','support','regions','old_regions'):np.testing.assert_array_equal(f[k],ref[k])
        for arm,key in [('OO','A'),('CC','C')]:
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
                # Signed pixel difference-in-differences; natural is primary since
                # independent matching scales add another global intensity effect.
                dd=(f['CC_'+key]-f['CO_'+key])-(f['OC_'+key]-f['OO_'+key])
                interactions.append(dict(view=view,mode=key,target_signed_RGB_sum=dd[target].sum(0,dtype=float),target_absolute_RGB_sum=float(np.abs(dd[target]).sum(dtype=float)),scope='Descriptive pixel interaction; matched scales confound intensity; not a perceptual score.'))
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
    js(UNIT/'FAR_READBACK.json',far);js(UNIT/'FAR_ABSOLUTE.json',absolute);js(UNIT/'VISIBLE_INTERVENTION.json',effects);js(UNIT/'FRAGMENT_READBACK.json',fragment);js(UNIT/'PIXEL_INTERACTION.json',interactions)
    js(UNIT/'GEOMETRY_READBACK.json',dict(partitions=info,face_transition_turns=all_turns,scope='Material layout and embedding crossed. No cross-family pairing, new fields or denoising.'))
    result=dict(status='pass',input_files_checked=len(inputs),new_cross_paths=len(new_ids),max_independent_anchor_error=max_error,pngs_checked=pngs,all_png_fully_decoded=decoded,composition_error=composition_error,original_rows=310475,source_weights_and_rows_hash_fixed=True)
    js(UNIT/'AUDIT.json',result);print(json.dumps(result),flush=True)

if __name__=='__main__':main()
