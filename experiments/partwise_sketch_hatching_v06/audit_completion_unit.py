"""Read back immutable selection, actual source renders and whole-object metrics."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,sha,js,now,output_guard
import argparse
import json
import numpy as np
from scipy import ndimage
from run_completion_unit import protocol,selection,match,load_scene,get_cache,reconstruct_trace,fresh
from run_hybrid import read_npz,array_hashes,png,panel
from appearance_completion import apply_fixed_ink
from hybrid import paper_copy,edit_metrics
from link_renderer import Renderer
import base_model as base


def audit():
    p=protocol();sel=selection();m=match();a,b=load_scene(p);before=array_hashes(a)
    for f,h in p['input_hashes'].items():assert sha(f)==h,f
    for lockname in ('SELECTION_LOCK.json','BUILD_LOCK.json'):
        lock=json.loads((UNIT/lockname).read_text())
        for f,h in lock['files'].items():assert sha(UNIT/f)==h,f
    pv=sel['per_view_mass'];total=pv[:,:,0].sum(0);inside=pv[:,:,1].sum(0);far=pv[:,:,3].sum(0)
    frac=np.divide(inside,total,out=np.zeros_like(total),where=total>0)
    farfrac=np.divide(far,total,out=np.ones_like(total),where=total>0)
    per=np.divide(pv[:,:,3],pv[:,:,0],out=np.zeros_like(pv[:,:,0]),where=pv[:,:,0]>0)
    expected=b['unknown']&~b['conflict']&(inside>=.02)&((pv[:,:,1]>=.002).sum(0)>=2)&(frac>=.7)&(farfrac<=.02)&(np.where(pv[:,:,0]>=.02,per,0).max(0)<=.05)
    np.testing.assert_array_equal(expected,sel['appearance_completion_strength']>0)
    np.testing.assert_array_equal(sel['completed_strength'],sel['original_strength']+expected)
    for field in ('unknown','region_id','conflict'):np.testing.assert_array_equal(sel[field+'_unchanged'],b[field])
    np.testing.assert_array_equal(sel['source_index'],np.arange(310475))
    for index,v in enumerate(p['build_views']):
        f=read_npz(UNIT/'footprints'/v['camera']['view']/'FOOTPRINT.npz')
        np.testing.assert_array_equal(f['mass'],pv[index])
        for category in range(3):assert abs(f['mass'][:,1+category].sum()-f['alpha'][f['category']==category].sum(dtype=float))<.001
    budget={arm:0. for arm in ('original','completed')}
    for v in p['build_views'][:4]:
        root=UNIT/'budget'/v['camera']['view'];raw=read_npz(root/'NATURAL.npz');matched=read_npz(root/'MATCHED.npz')
        for arm in budget:budget[arm]+=float(np.abs(matched[arm+'_paper']-raw['source']).sum(dtype=float))
    assert max(abs(x-m['budget'])/m['budget'] for x in budget.values())<1e-5
    records=[];checks=[]
    for v in p['views']:
        c=v['camera'];root=UNIT/v['kind']/c['view'];completion=json.loads((root/'COMPLETED.json').read_text())
        for name,h in completion['files'].items():assert sha(root/name)==h,name
        f=read_npz(root/'FRAME.npz');t=read_npz(root/'TRACE.npz');e=json.loads((root/'EVALUATION.json').read_text());cache=get_cache(p,v)
        for name,other in [('source','source'),('support','support'),('fixed_ink_alpha','legacy_raw_alpha'),('original_paper','paper'),('original_hybrid','legacy_raw')]:np.testing.assert_array_equal(f[name],cache[other])
        sid=t['sample_index'];ids=t['source_index'];w=t['weight'];xy=t['xy'];xx,yy=xy.T;n=len(xy)
        mass=np.bincount(sid,w,minlength=n)
        np.testing.assert_allclose(mass,f['alpha'][yy,xx],rtol=0,atol=1e-6)
        np.testing.assert_allclose(w,t['alpha']*t['T'],rtol=0,atol=1e-14)
        for name,strength in [('support',sel['original_strength']),('added_support',sel['appearance_completion_strength']),('completed_support',sel['completed_strength'])]:
            support=np.bincount(sid,w*strength[ids],minlength=n)
            np.testing.assert_allclose(support,f[name][yy,xx],rtol=0,atol=1e-6)
        assert np.max(f['completed_support']-f['alpha'])<2e-6
        source=reconstruct_trace(a,c,t,xy,np.zeros(310475),p['paper'])
        np.testing.assert_allclose(source,f['source'][yy,xx],rtol=0,atol=1e-6)
        target=f['regions']==4;inner=ndimage.binary_erosion(target,iterations=2);rows={}
        for arm in ('original','completed'):
            for mode in ('natural','matched'):
                key=arm if mode=='natural' else arm+'_matched';paper=f[key+'_paper'];hybrid=f[key+'_hybrid']
                np.testing.assert_array_equal(hybrid,apply_fixed_ink(paper,f['fixed_ink_alpha']))
                strength=sel[arm+'_strength']*(1 if mode=='natural' else m['scales'][arm])
                recon=reconstruct_trace(a,c,t,xy,strength,p['paper'])
                np.testing.assert_allclose(recon,paper[yy,xx],rtol=0,atol=1e-6)
                for suffix,img in [('paper',paper),('hybrid',hybrid)]:assert edit_metrics(f['source'],img,f['regions'])==e['metrics'][key+'_'+suffix]
                residual=np.abs(np.clip(paper,0,1)-np.array(p['paper'])).sum(2)
                for area,mask in [('target_full',target),('target_interior',inner)]:
                    assert abs(float(residual[mask].sum(dtype=float))-e['paper_residual'][key][area]['clipped_L1_sum'])<1e-9
                mm=e['metrics'][key+'_paper']
                rows[key]=dict(interior_residual_mean=e['paper_residual'][key]['target_interior']['clipped_L1_mean'],
                    near_paper_fraction=e['paper_residual'][key]['target_interior']['near_paper_fraction_0_15'],
                    target_edit_mean=mm['target_full']['clipped_L1_mean'],target_edit_sum=mm['target_full']['clipped_L1_sum'],
                    interior_changed_fraction=mm['target_interior']['useful_fraction_0_05'],
                    far_other_L1=mm['far_other']['raw_L1_sum'],far_background_L1=mm['far_background']['raw_L1_sum'],
                    far_fraction=mm['far_raw_fraction'])
        record=dict(kind=v['kind'],view=c['view'],target_pixels=int(target.sum()),interior_pixels=int(inner.sum()),
                    arms=rows,residual_reduction=e['residual_reduction'],support=e['support'])
        records.append(record);checks.append(dict(kind=v['kind'],view=c['view'],trace_events=len(w),source_and_four_papers_reconstructed=True,fixed_ink_exact=True))
        print('AUDIT',v['kind'],c['view'],'all source/ink/membership identities checked',flush=True)
    assert before==array_hashes(a)
    dev=[r for r in records if r['kind']=='dev'];weak=next(r for r in dev if r['view']=='orbit_241_24_5.3')
    screen=dict(dev_residual_passes=sum(r['residual_reduction']['natural']['target_interior']>=.2 for r in dev),
        weak_residual_pass=weak['residual_reduction']['natural']['target_interior']>=.2,
        natural_far_reference_passes=sum(r['arms']['completed']['far_fraction']<=.02 for r in dev),
        note='Numerical screen only; whole-object visual review still required, not an automatic success.')
    js(UNIT/'SUMMARY.json',dict(records=records,numerical_screen=screen,selection=json.loads((UNIT/'SELECTION.json').read_text())))
    js(UNIT/'VALIDATION.json',dict(utc=now(),input_hashes_checked=len(p['input_hashes']),selection_independently_rebuilt=True,
        M1_unchanged=True,full_original_row_identity=True,all_12_full_pixel_footprints_partition=True,
        actual_BUILD_source_effect_budget=budget,views=checks,original_array_hashes=before,scope=p['scope']))
    print('VALIDATED',screen,flush=True)


def replay(out):
    p=protocol();sel=selection();m=match();v=next(v for v in p['views'] if v['kind']=='dev' and v['camera']['view']=='orbit_241_24_5.3')
    folder=fresh(out);c=v['camera'];saved=read_npz(UNIT/'dev'/c['view']/'FRAME.npz');cache=get_cache(p,v)
    a,b=load_scene(p);before=array_hashes(a);r=Renderer(folder/'build');source,_=r.render(a,c,strength=sel['appearance_completion_strength'])
    checks={};arrays={}
    for name,value in [('source',source['rgb']),('alpha',source['alpha']),('added_support',source['contribution'])]:
        np.testing.assert_array_equal(value,saved[name]);checks[name]=True;arrays[name]=value
    for arm in ('original','completed'):
        for mode in ('natural','matched'):
            key=arm if mode=='natural' else arm+'_matched';strength=sel[arm+'_strength']*(1 if mode=='natural' else m['scales'][arm])
            f,_=r.render(paper_copy(a,c,strength,p['paper']),c);hybrid=apply_fixed_ink(f['rgb'],cache['legacy_raw_alpha'])
            for suffix,value in [('paper',f['rgb']),('hybrid',hybrid)]:
                name=key+'_'+suffix;np.testing.assert_array_equal(value,saved[name]);checks[name]=True;arrays[name]=value
    assert before==array_hashes(a)==m['original_array_hashes']
    np.savez_compressed(folder/'REPLAY.npz',**arrays)
    panel(folder/'REPLAY.png',[arrays[k] for k in ('source','original_paper','completed_paper','original_hybrid','completed_hybrid')],
          ['Actual source GS','Original paper','Completed paper','Original fixed ink','Completed fixed ink'],'Cold replay: actual complete GS renders; frozen original-row edits',columns=5)
    js(folder/'REPLAY_CHECK.json',dict(utc=now(),camera=c,actual_full_GS_renders=5,exact=checks,
        original_array_hashes=before,frame_sha256=sha(folder/'REPLAY.npz'),scope='Actual cold GS replay, not cached image composition alone.'))
    print('COLD_REPLAY',folder,checks,flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['audit','replay']);ap.add_argument('--out',type=runtime.Path);args=ap.parse_args()
    if args.stage=='audit':audit()
    else:replay(args.out or UNIT/'cold_replay_001')
