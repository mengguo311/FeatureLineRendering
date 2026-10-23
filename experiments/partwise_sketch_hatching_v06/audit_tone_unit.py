"""Saved original-ID readback and an actual complete-GS cold replay."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,sha,js,now
import argparse
import json
import numpy as np
from scipy import ndimage
from run_tone_unit import protocol,locked,asset,saved_asset,match,cache,fresh
from run_hybrid import read_npz,array_hashes,panel
from hybrid import compose,paper_copy,edit_metrics,region_strength
from membership import load_binding
from stroke_tone import render_tones,ARMS
from link_renderer import Renderer,validate_trace
from run_completion_unit import reconstruct_trace
import base_model as base


def load_source(p):
    s=p['scene'];a=base.load_source(locked(p,s['source']['original_ply']),s['source']['sha256'])
    a['source_index']=np.arange(len(a['means']),dtype=np.int64);assert len(a['means'])==310475
    b,_=load_binding(locked(p,s['binding']),s['source']['sha256'],310475)
    return a,b


def audit():
    p=protocol();m=match();mesh,paths,meta=asset(p);w,link=saved_asset();a,b=load_source(p);before=array_hashes(a)
    for f,h in p['input_hashes'].items():assert sha(f)==h,f
    np.testing.assert_array_equal(link['source_index'],a['source_index'])
    np.testing.assert_array_equal(link['original_strength'],region_strength(b))
    for k in ('unknown','region_id','conflict'):np.testing.assert_array_equal(link[k+'_unchanged'],b[k])
    sel=read_npz(locked(p,p['source_selection']));np.testing.assert_array_equal(link['completed_strength'],sel['completed_strength'])
    saved=read_npz(UNIT/'asset/PATHS.npz')
    for key in paths:np.testing.assert_array_equal(paths[key],saved[key])
    # Independently accumulate scalar face responses, without stroke_tones.
    light=np.array(p['light'],float);light/=np.linalg.norm(light);recomputed=[]
    lookup={int(s):i for i,s in enumerate(w['stroke_id'])}
    for i,sid in enumerate(w['stroke_id']):
        ii=np.flatnonzero(paths['stroke_id']==sid);num=den=0.
        for j in ii:
            length=float(np.linalg.norm(paths['points'][j,1]-paths['points'][j,0]));n=mesh['normals'][paths['face'][j]]
            norm=float(np.linalg.norm(n));response=abs(float(n@light)/norm) if np.isfinite(n).all() and norm>1e-12 else 0.
            num+=length*min(1.,response);den+=length
        expected=1-.8*num/den if den>1e-12 else 1.;recomputed.append(expected)
        source_i=lookup[int(w['shuffle_source_stroke_id'][i])]
        assert w['layer_id'][i]==w['layer_id'][source_i]
        assert w['shuffled_tau'][i]==w['tone_tau'][source_i]
    np.testing.assert_allclose(recomputed,w['tone_tau'],rtol=0,atol=5e-15)
    for layer in np.unique(w['layer_id']):
        ii=w['layer_id']==layer
        np.testing.assert_array_equal(np.sort(w['shuffled_tau'][ii]),np.sort(w['tone_tau'][ii]))
    budgets={k:0. for k in ARMS}
    for v in (v for v in p['views'] if v['kind']=='build'):
        f=read_npz(UNIT/'build_match'/(v['camera']['view']+'.npz'));target=f['regions']==4
        for arm in ARMS:
            im,_=compose(f['paper'],f[arm+'_ink'],f['support'],True,m['scales'][arm],p['ink_color'])
            budgets[arm]+=float(np.abs(im-f['paper'])[target].sum(dtype=float))
    assert max(abs(x-m['budget'])/m['budget'] for x in budgets.values())<1e-5
    records=[];checks=[]
    for v in (v for v in p['views'] if v['kind']!='build'):
        c=v['camera'];root=UNIT/v['kind']/c['view'];completion=json.loads((root/'COMPLETED.json').read_text())
        for name,h in completion['files'].items():assert sha(root/name)==h,name
        f=read_npz(root/'FRAME.npz');e=json.loads((root/'EVALUATION.json').read_text());oldcache=cache(p,v)
        for name in ('source','paper','support','regions'):np.testing.assert_array_equal(f[name],oldcache[name])
        np.testing.assert_array_equal(f['constant_raw'],oldcache['old_hybrid']);np.testing.assert_array_equal(f['constant_raw_alpha'],oldcache['old_alpha'])
        tr=read_npz(locked(p,v['trace']));xy=tr['xy'];xx,yy=xy.T;ids=tr['source_index'];sid=tr['sample_index'];mass=tr['weight'];n=len(xy)
        np.testing.assert_allclose(mass,tr['alpha']*tr['T'],rtol=0,atol=1e-14)
        np.testing.assert_allclose(np.bincount(sid,mass,minlength=n),f['source_alpha'][yy,xx],rtol=0,atol=1e-6)
        sr=np.bincount(sid,mass*link['original_strength'][ids],minlength=n)
        np.testing.assert_allclose(sr,f['support'][yy,xx],rtol=0,atol=1e-6)
        for key,strength in [('paper',link['completed_strength']),('source',np.zeros(310475))]:
            recon=reconstruct_trace(a,c,tr,xy,strength,p['paper'])
            np.testing.assert_allclose(recon,f[key][yy,xx],rtol=0,atol=1e-6)
        target=f['regions']==4;inner=ndimage.binary_erosion(target,iterations=2);rows={}
        for arm in ARMS:
            for mode,scale in [('raw',1.),('matched',m['scales'][arm])]:
                key=arm+'_'+mode;im,alpha=compose(f['paper'],f[arm+'_ink'],f['support'],True,scale,p['ink_color'])
                np.testing.assert_array_equal(im,f[key]);np.testing.assert_array_equal(alpha,f[key+'_alpha'])
                assert edit_metrics(f['source'],im,f['regions'])==e['metrics'][key]
                assert edit_metrics(f['paper'],im,f['regions'])==e['ink_regions'][key]
                effect=np.abs(im-f['paper']).sum(2);mm=e['metrics'][key]
                rows[key]=dict(target_ink_L1=float(effect[target].sum(dtype=float)),interior_ink_L1=float(effect[inner].sum(dtype=float)),
                    visible_ink_pixels=int(((alpha>.05)&target).sum()),interior_ink_pixels=int(((alpha>.05)&inner).sum()),
                    target_ink_mean=float(effect[target].mean()),far_other_L1=mm['far_other']['raw_L1_sum'],
                    far_background_L1=mm['far_background']['raw_L1_sum'],far_ink_L1=e['ink'][key]['far_visible_ink_L1'],
                    components=e['shape'][key]['visible']['components'])
        for arm in ('tone','shuffled'):
            for mode in ('raw','matched'):
                key=arm+'_'+mode;assert edit_metrics(f['constant_'+mode],f[key],f['regions'])==e['changes'][key]
        records.append(dict(kind=v['kind'],view=c['view'],target_pixels=int(target.sum()),interior_pixels=int(inner.sum()),
            arms=rows,support=e['support'],changes=e['changes'],raster_diagnostics=e['raster_diagnostics']))
        checks.append(dict(kind=v['kind'],view=c['view'],constant_exact=True,trace_events=len(mass),source_paper_S_from_original_rows=True))
        print('AUDIT',v['kind'],c['view'],'original-ID linkage and images consistent',flush=True)
    assert before==array_hashes(a)
    js(UNIT/'SUMMARY.json',dict(records=records,weights=json.loads((UNIT/'asset/WEIGHTS.json').read_text()),build=m))
    js(UNIT/'VALIDATION.json',dict(utc=now(),input_hashes_checked=len(p['input_hashes']),full_original_row_identity=True,
        M1_and_paper_permissions_unchanged=True,all_path_arrays_exact=True,all_stroke_responses_independently_checked=True,
        layer_shuffle_multisets_exact=True,actual_BUILD_ink_budget=budgets,views=checks,original_array_hashes=before,scope=p['scope']))


def replay(out):
    p=protocol();m=match();mesh,paths,meta=asset(p);w,link=saved_asset()
    v=next(v for v in p['views'] if v['kind']=='dev' and v['camera']['view']=='orbit_241_24_5.3');c=v['camera']
    out=fresh(out);saved=read_npz(UNIT/'dev'/c['view']/'FRAME.npz');a,b=load_source(p);before=array_hashes(a)
    r=Renderer(out/'build');yy,xx=np.mgrid[:c['height'],:c['width']]
    select=(saved['regions']==4)|((xx%7==1)&(yy%7==1));xy=np.column_stack([xx[select],yy[select]])
    source,tr=r.render(a,c,xy,link['original_strength']);trace_check=validate_trace(a,c,xy,source,tr)
    paper,_=r.render(paper_copy(a,c,link['completed_strength'],p['paper']),c)
    zero,_=r.render(a,c,strength=np.zeros(310475))
    np.testing.assert_array_equal(source['rgb'],saved['source']);np.testing.assert_array_equal(source['contribution'],saved['support'])
    np.testing.assert_array_equal(paper['rgb'],saved['paper']);np.testing.assert_array_equal(source['alpha'],saved['source_alpha'])
    np.testing.assert_array_equal(zero['rgb'],source['rgb']);assert not zero['contribution'].any()
    pair,hi=render_tones(mesh,paths,meta,c,w);arrays=dict(source=source['rgb'],paper=paper['rgb'],support=source['contribution'])
    checks={k:True for k in ('source','paper','support','source_alpha')}
    for arm in ARMS:
        np.testing.assert_array_equal(pair[arm],saved[arm+'_ink'])
        for mode,scale in [('raw',1.),('matched',m['scales'][arm])]:
            name=arm+'_'+mode;im,alpha=compose(paper['rgb'],pair[arm],source['contribution'],True,scale,p['ink_color'])
            np.testing.assert_array_equal(im,saved[name]);np.testing.assert_array_equal(alpha,saved[name+'_alpha'])
            checks[name]=True;arrays[name]=im
    null,na=compose(paper['rgb'],pair['tone'],zero['contribution'],True,ink_color=p['ink_color'])
    np.testing.assert_array_equal(null,paper['rgb']);assert not na.any();arrays['zero_link_control']=null
    assert before==array_hashes(a)
    np.savez_compressed(out/'REPLAY.npz',**arrays);np.savez_compressed(out/'TRACE.npz',**tr,xy=xy)
    panel(out/'REPLAY.png',[arrays[k] for k in ('source','paper','zero_link_control','constant_matched','tone_matched','shuffled_matched')],
        ['Actual original GS','Actual fixed GS paper','Actual zero-S control','Constant matched','Surface tone matched','Shuffled matched'],
        'Cold complete original-GS replay; unchanged source rows and full SH3',columns=3)
    js(out/'REPLAY_CHECK.json',dict(utc=now(),camera=c,actual_complete_GS_renders=3,exact=checks,
        actual_zero_link_blank_ink=True,trace=trace_check,original_array_hashes=before,
        files={f.name:sha(f) for f in out.iterdir() if f.is_file()},scope=p['scope']))
    print('COLD_REPLAY',checks,'actual zero-link blank',flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['audit','replay']);ap.add_argument('--out',type=runtime.Path);args=ap.parse_args()
    if args.stage=='audit':audit()
    else:replay(args.out or UNIT/'cold_replay_001')
