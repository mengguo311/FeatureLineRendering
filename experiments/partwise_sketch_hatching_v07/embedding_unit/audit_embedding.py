"""Independent material-coordinate, image and failure readback; no regeneration."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,sha,js
import json
from pathlib import Path
import numpy as np
from scipy import ndimage
from PIL import Image
from run_embedding import protocol,check_assets,npz,load_assets,BASE,PACKAGE,PATH_ARMS,ARMS

def load(p):return json.loads(Path(p).read_text())
def quantiles(v):return np.quantile(v,[.5,.9,.95,1]).tolist() if len(v) else []
def turns(p):
    d=p['points'][:,1]-p['points'][:,0];d/=np.linalg.norm(d,axis=1)[:,None]
    good=(p['stroke_id'][:-1]==p['stroke_id'][1:])&(p['face'][:-1]!=p['face'][1:])
    values=np.rad2deg(np.arccos(np.clip(np.sum(d[:-1]*d[1:],axis=1)[good],-1,1)))
    return dict(face_transitions=int(good.sum()),world_turn_quantiles=quantiles(values))

def crossing_angles(a,t):
    result=[];dirs=[]
    for p in (a,t):
        d=p['points'][:,1]-p['points'][:,0];d/=np.linalg.norm(d,axis=1)[:,None];dirs.append(d)
    for face in np.unique(a['face']):
        ixs=[np.flatnonzero((a['face']==face)&(a['layer_id']==k)) for k in (0,1)]
        for i in ixs[0]:
            for j in ixs[1]:
                x=a['bary'][i,:,1:];y=a['bary'][j,:,1:]
                matrix=np.column_stack((x[1]-x[0],-(y[1]-y[0])))
                if abs(np.linalg.det(matrix))<=1e-14:continue
                uv=np.linalg.solve(matrix,y[0]-x[0])
                if (uv>=-1e-10).all() and (uv<=1+1e-10).all():
                    result.append(dict(face=int(face),segment0=int(i),segment1=int(j),material_intersection=uv.tolist(),
                        A_degrees=float(np.rad2deg(np.arccos(np.clip(abs(dirs[0][i]@dirs[0][j]),0,1)))),
                        T_degrees=float(np.rad2deg(np.arccos(np.clip(abs(dirs[1][i]@dirs[1][j]),0,1))))))
    return dict(face_segment_intersection_pairs=len(result),A_quantiles=quantiles([r['A_degrees'] for r in result]),
        T_quantiles=quantiles([r['T_degrees'] for r in result]),max_angle_change=max([abs(r['T_degrees']-r['A_degrees']) for r in result],default=0.),
        records=result,scope='Actual two-layer segment intersections in unchanged face/bary coordinates; shared-edge endpoint pairs may be duplicated, not a perceptual score.')

def main():
    p=protocol();check_assets();refs,targets,_,meta=load_assets()
    inputs=load(UNIT/'INPUT_LOCK.json')['files']
    for path,h in inputs.items():assert sha(path)==h,path
    for path,h in load(UNIT/'BUILD_LOCK.json')['files'].items():assert sha(UNIT/path)==h,path
    moved=npz(UNIT/'asset/CARRIER.npz');protection=npz(Path(moved_path())/'DENOISE.npz')
    np.testing.assert_array_equal(targets[0]['vertices'][protection['protected']],refs[0]['vertices'][protection['protected']])
    vertex_displacement=np.linalg.norm(targets[0]['vertices']-refs[0]['vertices'],axis=1)
    assert (vertex_displacement<=protection['cap']+1e-12).all()
    info={};max_error=0.;new_ids=set();guards=[];crossings={};all_turns={}
    for part,ref,target,label in zip(('old','added'),refs,targets,(1,2)):
        a=npz(UNIT/'asset'/('A_'+part+'.npz'));t=npz(UNIT/'asset'/('T_'+part+'.npz'))
        assert sha(UNIT/'asset'/('A_'+part+'.npz'))==sha(BASE/'asset'/('A_'+part+'.npz'))
        assert set(a)==set(t)
        for k in a:
            if k not in ('points','stroke_id'):np.testing.assert_array_equal(a[k],t[k])
        assert len(np.unique(a['stroke_id']))==len(np.unique(t['stroke_id']))
        assert not new_ids&set(t['stroke_id']);new_ids.update(map(int,t['stroke_id']))
        records=load(UNIT/'asset'/(part+'_MIGRATION.json'))
        for r in records:
            old=a['stroke_id']==r['immediate_H_parent_id'];new=t['stroke_id']==r['stroke_id'];np.testing.assert_array_equal(old,new)
        # Independent coordinate-wise sum rather than the producer's einsum.
        triangles=target['vertices'][target['faces'][t['face']]]
        expected=sum(t['bary'][:,:,k,None]*triangles[:,None,k,:] for k in range(3))
        error=float(np.abs(expected-t['points']).max());max_error=max(max_error,error)
        np.testing.assert_allclose(t['points'],expected,atol=1e-12,rtol=0)
        assert (moved['partitions'][t['face']]==label).all()
        displacement=np.linalg.norm(t['points']-a['points'],axis=2)
        assert (displacement<=vertex_displacement[target['faces'][t['face']]].max(1)[:,None]+1e-12).all()
        for q in (a,t):
            for sid in np.unique(q['stroke_id']):
                x=q['points'][q['stroke_id']==sid];np.testing.assert_allclose(x[:-1,1],x[1:,0],atol=1e-8,rtol=0)
        stops=load(UNIT/'asset'/('A_'+part+'_INHERITED_STOPS.json'))
        assert sha(UNIT/'asset'/('A_'+part+'_INHERITED_STOPS.json'))==sha(BASE/'asset'/('A_'+part+'_SEEDS.json'))
        guards.extend(dict(part=part,record=r) for r in stops if r['minus_stop']=='zero_step_cycle' or r['plus_stop']=='zero_step_cycle')
        info[part]=dict(paths=len(records),segments=len(a['face']),moved_paths=sum(r['moved'] for r in records),
            endpoint_displacement_quantiles=quantiles(displacement.ravel()),max_anchor_error=error)
        crossings[part]=crossing_angles(a,t)
        for arm,q in [('A',a),('T',t)]:all_turns[arm+'_'+part]=turns(q)
    assert len(new_ids)==380 and len(guards)==1
    links=npz(PACKAGE/'SOURCE_LINK.npz');binding=npz(PACKAGE/'SOURCE_BINDING.npz')
    np.testing.assert_array_equal(links['source_index'],np.arange(310475));np.testing.assert_array_equal(binding['source_index'],np.arange(310475))
    assert binding['unknown'].sum()==195279
    far=[];effects=[];pngs=0;composition_error=0.;scales=load(UNIT/'BUILD_MATCH.json')['scales'];fragment=[]
    for v in p['views']:
        if v['kind']=='build' or (v['kind']=='arc' and v['camera']['view']=='orbit_241_24_5.3'):continue
        folder=UNIT/v['kind']/v['camera']['view'];f=npz(folder/'FRAME.npz');ref=npz(v['cache']);target=f['regions']==4
        near=ndimage.binary_dilation(target,iterations=2);masks={'other':(f['regions']>0)&~near,'background':(f['regions']==0)&~near}
        for k in ('source','paper','support','regions','old_regions'):np.testing.assert_array_equal(f[k],ref[k])
        prior=npz(BASE/v['kind']/v['camera']['view']/'FRAME.npz')
        for key in ('A_preS','A_linked_natural','A_ungated_natural'):np.testing.assert_array_equal(f[key],prior[key])
        for arm in ARMS:
            path,mode=arm.split('_');raw=f[path+'_preS']*(f['support'] if mode=='linked' else 1.)
            for match in ('natural','matched'):
                alpha=np.clip(raw*(scales[arm] if match=='matched' else 1.),0,1)
                expected=f['paper']*(1-alpha[:,:,None])+.03*alpha[:,:,None];key=arm+'_'+match
                err=float(np.abs(expected-f[key]).max());composition_error=max(composition_error,err)
                np.testing.assert_allclose(expected,f[key],atol=2e-7,rtol=0)
        for link in ('linked','ungated'):
            for mode in ('natural','matched'):
                key=link+'_'+mode;d=np.abs(f['A_'+key]-f['T_'+key]).sum(2)
                far.append(dict(view=v['camera']['view'],mode=key,**{n:dict(L1=float(d[m].sum(dtype=float)),max=float(d[m].max()) if m.any() else 0.,nonzero=int((d[m]>0).sum()),above_1_255=int((d[m]>1/255).sum())) for n,m in masks.items()}))
                effects.append(dict(view=v['camera']['view'],mode=key,target_pixels=int(target.sum()),target_L1=float(d[target].sum(dtype=float)),changed_pixels=int((d[target]>0).sum()),above_005_fraction=float((d[target]>=.05).mean())))
        fragment.append(dict(view=v['camera']['view'],columns=['covered','accepted','region_rejected','depth_rejected'],partitions=['old','added'],A=f['A_fragment_diagnostics'],T=f['T_fragment_diagnostics']))
        for file in folder.glob('*.png'):
            key=file.stem;expected=None
            if key in f:expected=f[key]
            elif key.endswith('_ink') and key[:-4]+'_alpha' in f:expected=1-f[key[:-4]+'_alpha']
            elif key.endswith('_preS_ink'):expected=1-f[key[:-4]]
            if expected is None:continue
            if key.endswith('_preS') and 'layer' in key:expected=1-expected
            if expected.ndim==2:expected=np.repeat(expected[:,:,None],3,axis=2)
            with Image.open(file) as im:im.load();np.testing.assert_array_equal(np.array(im.convert('RGB')),np.uint8(np.clip(expected,0,1)*255+.5))
            pngs+=1
    decoded=0
    for file in UNIT.rglob('*.png'):
        with Image.open(file) as im:im.load()
        decoded+=1
    js(UNIT/'FAR_READBACK.json',far);js(UNIT/'VISIBLE_INTERVENTION.json',effects);js(UNIT/'FRAGMENT_READBACK.json',fragment)
    js(UNIT/'GEOMETRY_READBACK.json',dict(partitions=info,face_transition_turns=all_turns,crossing_angles=crossings,inherited_guard_records=guards,
        scope='No new integration; old failure preserved. Changed lengths/angles are embedding effects, not new estimated fields.'))
    result=dict(status='pass',input_files_checked=len(inputs),paths=380,max_independent_anchor_error=max_error,pngs_checked=pngs,all_png_fully_decoded=decoded,
        composition_error=composition_error,inherited_zero_step_cycles=len(guards),original_rows=310475,source_weights_and_rows_hash_fixed=True)
    js(UNIT/'AUDIT.json',result);print(json.dumps(result),flush=True)

def moved_path():return UNIT.parent/'unit_002/asset'
if __name__=='__main__':main()
