"""Independent saved-result readback and actual full-GS cold replay."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,sha,js,now
import argparse
import json
import numpy as np
from scipy import ndimage
from run_gap_unit import protocol,locked,asset,new_asset,match,cache,fresh
from run_hybrid import read_npz,array_hashes,panel
from hybrid import compose,paper_copy,edit_metrics,region_strength
from membership import load_binding
from gap_completion import render_gap_pair
from link_renderer import Renderer,validate_trace
from run_completion_unit import reconstruct_trace
import base_model as base


def load_source(p):
    s=p['scene'];a=base.load_source(locked(p,s['source']['original_ply']),s['source']['sha256'])
    a['source_index']=np.arange(len(a['means']),dtype=np.int64)
    assert len(a['means'])==310475
    b,_=load_binding(locked(p,s['binding']),s['source']['sha256'],310475)
    return a,b


def audit():
    p=protocol();m=match();mesh,old,meta=asset(p);filled,gaps,link=new_asset();a,b=load_source(p)
    before=array_hashes(a)
    for f,h in p['input_hashes'].items():assert sha(f)==h,f
    np.testing.assert_array_equal(link['source_index'],a['source_index'])
    np.testing.assert_array_equal(link['original_strength'],region_strength(b))
    for k in ('unknown','region_id','conflict'):np.testing.assert_array_equal(link[k+'_unchanged'],b[k])
    sel=read_npz(locked(p,p['source_selection']))
    np.testing.assert_array_equal(link['completed_strength'],sel['completed_strength'])
    for k in old:np.testing.assert_array_equal(filled[k][:len(old['points'])],old[k])
    np.testing.assert_allclose(np.einsum('nij,njk->nik',gaps['bary'],mesh['tri'][gaps['face']]),gaps['points'],rtol=0,atol=1e-10)
    assert np.all(mesh['regions'][gaps['face']]==4)
    parents=[]
    for sid in np.unique(gaps['stroke_id']):
        ii=np.flatnonzero(gaps['stroke_id']==sid);left=int(gaps['left_stroke_id'][ii[0]]);right=int(gaps['right_stroke_id'][ii[0]])
        l=np.flatnonzero(old['stroke_id']==left)[-1];r=np.flatnonzero(old['stroke_id']==right)[0]
        np.testing.assert_allclose(gaps['points'][ii[0],0],old['points'][l,1],rtol=0,atol=1e-9)
        np.testing.assert_allclose(gaps['points'][ii[-1],1],old['points'][r,0],rtol=0,atol=1e-9)
        np.testing.assert_allclose(gaps['points'][ii[:-1],1],gaps['points'][ii[1:],0],rtol=0,atol=1e-9)
        assert abs(np.linalg.norm(gaps['points'][ii,1]-gaps['points'][ii,0],axis=1).sum()-.035)<1e-8
        assert np.all(gaps['layer_id'][ii]==old['layer_id'][l]) and old['layer_id'][l]==old['layer_id'][r]
        for fa,fb in zip(gaps['face'][ii[:-1]],gaps['face'][ii[1:]]):
            shared=set(mesh['faces'][fa])&set(mesh['faces'][fb]);assert len(shared)==2
            assert sum(shared.issubset(set(f)) for f in mesh['faces'][mesh['regions']==4])==2
        parents.append(dict(gap_id=int(sid),left=left,right=right,segments=len(ii)))
    budgets=dict(old=0.,filled=0.)
    for v in (v for v in p['views'] if v['kind']=='build'):
        f=read_npz(UNIT/'build_match'/(v['camera']['view']+'.npz'));target=f['regions']==4
        for arm in budgets:
            im,_=compose(f['paper'],f[arm+'_ink'],f['support'],True,m['scales'][arm],p['ink_color'])
            budgets[arm]+=float(np.abs(im-f['paper'])[target].sum(dtype=float))
    assert max(abs(x-m['budget'])/m['budget'] for x in budgets.values())<1e-5
    records=[];checks=[]
    for v in (v for v in p['views'] if v['kind']!='build'):
        c=v['camera'];root=UNIT/v['kind']/c['view'];completion=json.loads((root/'COMPLETED.json').read_text())
        for name,h in completion['files'].items():assert sha(root/name)==h,name
        f=read_npz(root/'FRAME.npz');e=json.loads((root/'EVALUATION.json').read_text());oldcache=cache(p,v)
        for name in ('source','paper','support','regions'):np.testing.assert_array_equal(f[name],oldcache[name])
        np.testing.assert_array_equal(f['old_raw'],oldcache['old_hybrid']);np.testing.assert_array_equal(f['old_raw_alpha'],oldcache['old_alpha'])
        tr=read_npz(locked(p,v['trace']));xy=tr['xy'];xx,yy=xy.T;ids=tr['source_index'];sid=tr['sample_index'];w=tr['weight'];n=len(xy)
        np.testing.assert_allclose(w,tr['alpha']*tr['T'],rtol=0,atol=1e-14)
        np.testing.assert_allclose(np.bincount(sid,w,minlength=n),f['source_alpha'][yy,xx],rtol=0,atol=1e-6)
        sr=np.bincount(sid,w*link['original_strength'][ids],minlength=n)
        np.testing.assert_allclose(sr,f['support'][yy,xx],rtol=0,atol=1e-6)
        recon=reconstruct_trace(a,c,tr,xy,link['completed_strength'],p['paper'])
        np.testing.assert_allclose(recon,f['paper'][yy,xx],rtol=0,atol=1e-6)
        recon=reconstruct_trace(a,c,tr,xy,np.zeros(310475),p['paper'])
        np.testing.assert_allclose(recon,f['source'][yy,xx],rtol=0,atol=1e-6)
        target=f['regions']==4;inner=ndimage.binary_erosion(target,iterations=2);rows={}
        for arm in ('old','filled'):
            for mode,scale in [('raw',1.),('matched',m['scales'][arm])]:
                key=arm+'_'+mode;im,alpha=compose(f['paper'],f[arm+'_ink'],f['support'],True,scale,p['ink_color'])
                np.testing.assert_array_equal(im,f[key]);np.testing.assert_array_equal(alpha,f[key+'_alpha'])
                assert edit_metrics(f['source'],im,f['regions'])==e['metrics'][key]
                effect=np.abs(im-f['paper']).sum(2);mm=e['metrics'][key]
                rows[key]=dict(target_ink_L1=float(effect[target].sum(dtype=float)),interior_ink_L1=float(effect[inner].sum(dtype=float)),
                    visible_ink_pixels=int(((alpha>.05)&target).sum()),target_ink_mean=float(effect[target].mean()),
                    interior_ink_pixels=int(((alpha>.05)&inner).sum()),
                    far_other_L1=mm['far_other']['raw_L1_sum'],far_background_L1=mm['far_background']['raw_L1_sum'],
                    far_ink_L1=e['ink'][key]['far_visible_ink_L1'],components=e['shape'][key]['visible']['components'])
        assert edit_metrics(f['old_raw'],f['filled_raw'],f['regions'])==e['changed_by_fill']
        assert np.min(f['increment_alpha'])>=-1e-7
        samples=read_npz(root/'GAP_SAMPLES.npz');weight=samples['length_weight'];vis=samples['status']==0
        assert abs(float(weight[vis].sum())-e['gap_support']['proxy_visible_length'])<1e-9
        for name,alpha in [('gap_before_S',samples['gap_only_alpha']),('gap_raw',samples['gap_only_alpha']*samples['support']),
                           ('gap_matched',samples['gap_only_alpha']*samples['support']*m['scales']['filled'])]:
            assert abs(float(weight[vis&(alpha>.05)].sum())-e['gap_support'][name]['visible_supported_length'])<1e-9
        records.append(dict(kind=v['kind'],view=c['view'],target_pixels=int(target.sum()),interior_pixels=int(inner.sum()),
            arms=rows,gap_support=e['gap_support'],changed_by_fill=e['changed_by_fill']))
        checks.append(dict(kind=v['kind'],view=c['view'],old_exact=True,trace_events=len(w),source_paper_S_from_original_rows=True))
        print('AUDIT',v['kind'],c['view'],'original-ID linkage and images consistent',flush=True)
    assert before==array_hashes(a)
    js(UNIT/'SUMMARY.json',dict(records=records,paths=json.loads((UNIT/'asset/PATHS.json').read_text()),build=m))
    js(UNIT/'VALIDATION.json',dict(utc=now(),input_hashes_checked=len(p['input_hashes']),full_original_row_identity=True,
        M1_and_paper_permissions_unchanged=True,old_path_prefix_exact=True,all_internal_gap_parents_checked=parents,
        actual_BUILD_ink_budget=budgets,views=checks,original_array_hashes=before,scope=p['scope']))


def replay(out):
    p=protocol();m=match();mesh,old,meta=asset(p);filled,gaps,link=new_asset()
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
    pair,hi=render_gap_pair(mesh,old,gaps,meta,c);arrays=dict(source=source['rgb'],paper=paper['rgb'],support=source['contribution'])
    checks={k:True for k in ('source','paper','support','source_alpha')}
    for arm in ('old','filled'):
        np.testing.assert_array_equal(pair[arm],saved[arm+'_ink'])
        for mode,scale in [('raw',1.),('matched',m['scales'][arm])]:
            name=arm+'_'+mode;im,alpha=compose(paper['rgb'],pair[arm],source['contribution'],True,scale,p['ink_color'])
            np.testing.assert_array_equal(im,saved[name]);np.testing.assert_array_equal(alpha,saved[name+'_alpha'])
            checks[name]=True;arrays[name]=im
    null,na=compose(paper['rgb'],pair['filled'],zero['contribution'],True,ink_color=p['ink_color'])
    np.testing.assert_array_equal(null,paper['rgb']);assert not na.any();arrays['zero_link_control']=null
    assert before==array_hashes(a)
    np.savez_compressed(out/'REPLAY.npz',**arrays);np.savez_compressed(out/'TRACE.npz',**tr,xy=xy)
    panel(out/'REPLAY.png',[arrays[k] for k in ('source','paper','old_matched','filled_matched','zero_link_control')],
        ['Actual original GS','Actual fixed GS paper','Old matched','Filled matched','Actual zero-S control'],
        'Cold original-GS replay; original row IDs and unchanged full SH3 source',columns=5)
    js(out/'REPLAY_CHECK.json',dict(utc=now(),camera=c,actual_complete_GS_renders=3,exact=checks,
        actual_zero_link_blank_ink=True,trace=trace_check,original_array_hashes=before,
        files={f.name:sha(f) for f in out.iterdir() if f.is_file()},scope=p['scope']))
    print('COLD_REPLAY',checks,'actual zero-link blank',flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['audit','replay']);ap.add_argument('--out',type=runtime.Path);args=ap.parse_args()
    if args.stage=='audit':audit()
    else:replay(args.out or UNIT/'cold_replay_001')
