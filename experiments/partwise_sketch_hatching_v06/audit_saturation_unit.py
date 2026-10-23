"""Read back frozen inputs, render evidence and two actual null controls."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,js,sha,now
import argparse,json
from pathlib import Path
import numpy as np
from scipy import ndimage
from run_saturation_unit import protocol,locked,source,selection,cache,match,fresh,ARMS,OLD,render_paper
from run_hybrid import read_npz,array_hashes,png
from hybrid import edit_metrics,paper_copy
from appearance_completion import apply_fixed_ink,paper_residual
from link_renderer import Renderer,validate_trace
import base_model as base

def reconstruct(a,c,tr,strength,paper):
    sid=tr['sample_index'];ids=tr['source_index'];w=tr['weight'];n=len(tr['xy'])
    mass=np.bincount(sid,w,minlength=n);colors=base.source_colors(a,c)
    color=colors[ids]*(1-strength[ids,None])+np.asarray(paper)*strength[ids,None]
    out=np.repeat((1-mass[:,None]),3,axis=1)
    for j in range(3):out[:,j]+=np.bincount(sid,w*color[:,j],minlength=n)
    return out

def audit():
    p=protocol();m=match();a=source(p);before=array_hashes(a);sel=selection(p)
    for f,h in p['inputs'].items():assert sha(f)==h,f
    oldsel=read_npz(locked(p,OLD/'SELECTION.npz'));b=read_npz(locked(p,OLD/'SOURCE_BINDING.npz'))
    np.testing.assert_array_equal(sel['source_index'],np.arange(310475))
    np.testing.assert_array_equal(sel['weighted_strength'],oldsel['completed_strength'])
    np.testing.assert_array_equal(sel['saturated_strength'],(oldsel['completed_strength']>0).astype(float))
    np.testing.assert_array_equal(sel['ink_strength'],oldsel['original_strength'])
    assert int((sel['saturated_strength']>0).sum())==41058 and int(b['unknown'].sum())==195279
    for name,h in json.loads((UNIT/'BUILD_LOCK.json').read_text())['files'].items():assert sha(UNIT/name)==h,name
    checks=[];records=[];budgets={k:0. for k in ARMS}
    for v in p['views']:
        c=v['camera'];ref=cache(p,v)
        if v['kind']=='build':
            f=read_npz(UNIT/'build_match'/(c['view']+'.npz'));g=read_npz(UNIT/'build_match'/(c['view']+'_matched.npz'))
            np.testing.assert_array_equal(f['alpha'],ref['new_raw_alpha'])
            for arm in ARMS:budgets[arm]+=float(np.abs(g[arm+'_matched_paper']-ref['source']).sum(dtype=float))
            continue
        folder=UNIT/v['kind']/c['view'];done=json.loads((folder/'COMPLETED.json').read_text())
        for name,h in done['files'].items():assert sha(folder/name)==h,name
        f=read_npz(folder/'FRAME.npz');e=json.loads((folder/'EVALUATION.json').read_text());tr=read_npz(locked(p,v['trace']))
        np.testing.assert_array_equal(f['source'],ref['source']);np.testing.assert_array_equal(f['alpha'],ref['new_raw_alpha'])
        np.testing.assert_array_equal(f['support'],ref['new_support']);np.testing.assert_array_equal(f['regions'],ref['regions'])
        np.testing.assert_array_equal(f['weighted_raw_paper'],ref['new_paper']);np.testing.assert_array_equal(f['weighted_raw'],ref['new_raw'])
        tc=validate_trace(a,c,tr['xy'],dict(rgb=f['source'],alpha=f['source_alpha']),tr);xx,yy=tr['xy'].T;target=f['regions']==4
        assert int(target[yy,xx].sum())==int(target.sum())
        support=np.bincount(tr['sample_index'],tr['weight']*sel['ink_strength'][tr['source_index']],minlength=len(xx))
        np.testing.assert_allclose(support,f['support'][yy,xx],rtol=0,atol=1e-6)
        for arm in ARMS:
            for mode,scale in [('raw',1.),('matched',m['scales'][arm])]:
                key=arm+'_'+mode;paper=f[key+'_paper'];im=apply_fixed_ink(paper,f['alpha'])
                np.testing.assert_array_equal(im,f[key])
                np.testing.assert_allclose(reconstruct(a,c,tr,sel[arm+'_strength']*scale,p['paper']),paper[yy,xx],rtol=0,atol=1e-6)
                assert edit_metrics(f['source'],paper,f['regions'])==e['metrics'][key+'_paper']
                assert edit_metrics(f['source'],im,f['regions'])==e['metrics'][key]
                assert edit_metrics(paper,im,f['regions'])==e['ink'][key]
                assert paper_residual(paper,f['regions'],p['paper'])==e['paper_residual'][key]
        if v['kind']=='dev':
            d=read_npz(UNIT/'decomposition'/(c['view']+'.npz'))
            np.testing.assert_allclose(d['licensed_unreplaced']+d['unlicensed']+d['background']+p['paper'],f['weighted_raw_paper'][yy,xx],rtol=0,atol=1e-6)
            np.testing.assert_allclose(d['unlicensed']+d['background']+p['paper'],f['saturated_raw_paper'][yy,xx],rtol=0,atol=1e-6)
        near=ndimage.binary_dilation(target,iterations=2);far=~near
        delta=np.abs(f['saturated_raw']-f['weighted_raw']).sum(2)
        farcheck=dict(max_new_raw_L1=float(delta[far].max()),new_visible_pixels=int((delta[far]>1/255).sum()),
            new_far_sum=float(delta[far].sum(dtype=float)))
        checks.append(dict(kind=v['kind'],view=c['view'],original_ID_trace=tc,all_four_papers_reconstructed=True,
            fixed_alpha_and_old_output_exact=True,far=farcheck))
        records.append(dict(kind=v['kind'],view=c['view'],**{k:e[k] for k in ('metrics','ink','paper_residual','coverage','changes')},far_readback=farcheck))
        print('AUDIT',v['kind'],c['view'],flush=True)
    assert max(abs(x-m['budget'])/m['budget'] for x in budgets.values())<1e-5;assert before==array_hashes(a)==m['original_array_hashes']
    js(UNIT/'SUMMARY.json',dict(records=records,build=m))
    js(UNIT/'VALIDATION.json',dict(utc=now(),input_hashes_checked=len(p['inputs']),full_original_rows=True,same_permission_set=True,
        original_array_hashes=before,UNKNOWN_unchanged=195279,ink_rows_unchanged=21006,views=checks,matched_budget=budgets,scope=p['scope']))

def replay(out):
    p=protocol();m=match();sel=selection(p);a=source(p);before=array_hashes(a);out=fresh(out);r=Renderer(out/'build')
    v=next(v for v in p['views'] if v['kind']=='dev' and v['camera']['azimuth']==241 and v['camera']['elevation']==24);c=v['camera']
    ref=cache(p,v);saved=read_npz(UNIT/'dev'/c['view']/'FRAME.npz');xy=read_npz(locked(p,v['trace']))['xy']
    f,tr=r.render(a,c,xy,sel['ink_strength']);tc=validate_trace(a,c,xy,f,tr)
    np.testing.assert_array_equal(f['rgb'],saved['source']);np.testing.assert_array_equal(f['contribution'],saved['support'])
    arrays={};renders=1
    for arm in ARMS:
        for mode,scale in [('raw',1.),('matched',m['scales'][arm])]:
            key=arm+'_'+mode;paper=render_paper(r,a,c,sel[arm+'_strength']*scale,p);renders+=1
            np.testing.assert_array_equal(paper,saved[key+'_paper']);im=apply_fixed_ink(paper,saved['alpha'])
            np.testing.assert_array_equal(im,saved[key]);arrays[key]=im
    zero,_=r.render(paper_copy(a,c,np.zeros(310475),p['paper']),c,strength=np.zeros(310475));renders+=1
    np.testing.assert_array_equal(zero['rgb'],f['rgb']);assert not zero['contribution'].any()
    zeroalpha=ref['new_ink']*zero['contribution']
    inkzero=apply_fixed_ink(saved['saturated_raw_paper'],zeroalpha);np.testing.assert_array_equal(inkzero,saved['saturated_raw_paper'])
    allzero=apply_fixed_ink(zero['rgb'],zeroalpha);np.testing.assert_array_equal(allzero,saved['source'])
    assert before==array_hashes(a)
    np.savez_compressed(out/'REPLAY.npz',**arrays,zero_ink=inkzero,all_links_zero=allzero)
    png(out/'saturated_raw.png',arrays['saturated_raw']);png(out/'all_links_zero.png',allzero)
    js(out/'REPLAY_CHECK.json',dict(utc=now(),camera=c,full_GS_renders=renders,all_four_papers_and_hybrids_exact=True,
        source_support_exact=True,zero_ink_equals_paper=True,all_links_zero_equals_original_GS=True,trace=tc,original_arrays_unchanged=True))
    print('REPLAY six full-GS renders exact, both null controls exact',flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['audit','replay']);ap.add_argument('--out',type=Path);args=ap.parse_args()
    if args.stage=='audit':audit()
    else:replay(args.out)
