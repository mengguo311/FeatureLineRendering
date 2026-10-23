"""Read back saved original-ID evidence and cold-replay both null controls."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,js,sha,now
from pathlib import Path
import argparse,json
import numpy as np
from run_target_unit import protocol,locked,asset,source,selection,match,cache,fresh,spatial_metrics,ARMS,OLD,U4
from run_hybrid import read_npz,array_hashes,png
from membership import load_binding
from hybrid import compose,paper_copy,region_strength
from link_renderer import Renderer,validate_trace
from run_completion_unit import reconstruct_trace
from target_completion import render_pair
from appearance_completion import completion_selection

def audit():
    p=protocol();m=match();sel=selection();a=source(p);before=array_hashes(a)
    for f,h in p['input_hashes'].items():assert sha(f)==h,f
    oldmesh,newmesh,old,added,meta=asset(p);allpaths=read_npz(UNIT/'asset/PATHS.npz')
    for k in old:np.testing.assert_array_equal(allpaths[k][:len(old[k])],old[k])
    target=read_npz(UNIT/'asset/TARGET.npz');assert (oldmesh['regions'][target['added_faces']]==3).all()
    assert np.isin(added['face'],target['added_faces']).all();assert not np.isin(added['stroke_id'],old['stroke_id']).any()
    np.testing.assert_allclose(np.einsum('nij,njk->nik',allpaths['bary'],newmesh['tri'][allpaths['face']]),allpaths['points'],rtol=0,atol=1e-9)
    b,_=load_binding(UNIT/'SOURCE_BINDING.npz',p['scene']['source']['sha256'],310475)
    oldb,_=load_binding(locked(p,OLD/'results/lego/SOURCE_BINDING.npz'),p['scene']['source']['sha256'],310475)
    np.testing.assert_array_equal(sel['original_strength'],region_strength(b));np.testing.assert_array_equal(sel['old_ink_strength'],region_strength(oldb))
    for k in ('unknown','region_id','conflict'):np.testing.assert_array_equal(sel[k+'_unchanged'],b[k])
    pv=[];evidence=[]
    for i,e in enumerate(p['evidence']):
        tr=read_npz(locked(p,e['trace']));sid=tr['sample_index'];ids=tr['source_index'];faces=tr['proxy_face']
        labels=np.zeros(len(faces),np.int32);hit=faces>=0;labels[hit]=target['face_regions'][faces[hit]]
        good=tr['sample_eligible'][sid]&(labels[sid]>0)&np.isfinite(tr['depth'])&(np.abs(tr['depth']-tr['proxy_depth'][sid])<=p['membership']['contributor_proxy_z_tolerance'])
        lab=np.where(good,labels[sid],0);w=tr['weight']*tr['sampling_weight'][sid]
        score=np.bincount(ids*6+lab,w,minlength=310475*6).reshape(310475,6)
        np.testing.assert_array_equal(score,b['per_view_score'][i])
        fp=read_npz(UNIT/'footprints'/e['camera']['view']/'FOOTPRINT.npz');np.testing.assert_array_equal(fp['source_index'],np.arange(310475))
        np.testing.assert_allclose(fp['mass'][:,1:4].sum(1),fp['mass'][:,0],rtol=1e-12,atol=1e-10);pv.append(fp['mass'])
        evidence.append(dict(view=e['camera']['view'],M1_from_original_events_exact=True,full_footprint_partition=True))
    selected=completion_selection(np.stack(pv),b)
    for k in selected:np.testing.assert_array_equal(selected[k],sel[k])
    checks=[];records=[];budgets={k:0. for k in ARMS}
    for v in p['views']:
        c=v['camera'];kind=v['kind']
        if kind=='build':
            path=UNIT/'build_match'/(c['view']+'.npz');f=read_npz(path);mask=f['regions']==4
            for arm in ARMS:
                im,_=compose(f[arm+'_paper'],f[arm+'_ink'],f[arm+'_support'],True,m['scales'][arm],p['ink_color'])
                budgets[arm]+=float(np.abs(im-f[arm+'_paper'])[mask].sum(dtype=float))
            continue
        folder=UNIT/kind/c['view'];done=json.loads((folder/'COMPLETED.json').read_text())
        for name,h in done['files'].items():assert sha(folder/name)==h,name
        f=read_npz(folder/'FRAME.npz');tr=read_npz(folder/'TRACE.npz');e=json.loads((folder/'EVALUATION.json').read_text());ref=cache(p,v)
        np.testing.assert_array_equal(f['old_raw'],ref['hybrid']);np.testing.assert_array_equal(f['old_raw_alpha'],ref['alpha'])
        tc=validate_trace(a,c,tr['xy'],dict(rgb=f['source'],alpha=f['source_alpha']),tr)
        xx,yy=tr['xy'].T;ids=tr['source_index'];sid=tr['sample_index'];w=tr['weight'];n=len(xx)
        for arm,inkkey,paperkey in [('old','old_ink_strength','old_paper_strength'),('new','original_strength','completed_strength')]:
            sr=np.bincount(sid,w*sel[inkkey][ids],minlength=n)
            np.testing.assert_allclose(sr,f[arm+'_support'][yy,xx],rtol=0,atol=1e-6)
            recon=reconstruct_trace(a,c,tr,tr['xy'],sel[paperkey],p['paper'])
            np.testing.assert_allclose(recon,f[arm+'_paper'][yy,xx],rtol=0,atol=1e-6)
            for mode,scale in [('raw',1.),('matched',m['scales'][arm])]:
                key=arm+'_'+mode;im,alpha=compose(f[arm+'_paper'],f[arm+'_ink'],f[arm+'_support'],True,scale,p['ink_color'])
                np.testing.assert_array_equal(im,f[key]);np.testing.assert_array_equal(alpha,f[key+'_alpha'])
                assert spatial_metrics(f['source'],im,f['regions'],f['old_regions'])==e['metrics'][key]
                assert spatial_metrics(f[arm+'_paper'],im,f['regions'],f['old_regions'])==e['ink'][key]
        records.append(dict(kind=kind,view=c['view'],metrics=e['metrics'],ink=e['ink'],coverage=e['coverage'],support=e['support'],paper_residual=e['paper_residual'],changes=e['changes']))
        checks.append(dict(kind=kind,view=c['view'],original_ID_trace=tc,old_output_exact=True,paper_and_ink_link_reconstructed=True))
        print('AUDIT',kind,c['view'],flush=True)
    assert max(abs(x-m['budget'])/m['budget'] for x in budgets.values())<1e-5;assert before==array_hashes(a)
    js(UNIT/'SUMMARY.json',dict(records=records,build=m))
    js(UNIT/'VALIDATION.json',dict(utc=now(),input_hashes_checked=len(p['input_hashes']),original_array_hashes=before,
        full_original_rows=True,old_paths_exact=True,added_face_anchors_exact=True,old_inputs_unchanged=True,
        new_UNKNOWN_retained=True,evidence=evidence,views=checks,matched_ink_budget=budgets,scope=p['scope']))

def replay(out):
    p=protocol();m=match();sel=selection();a=source(p);before=array_hashes(a);out=fresh(out);r=Renderer(out/'build')
    # Front view sees the authored addition; weak rear view remains in full evaluation.
    v=next(v for v in p['views'] if v['kind']=='dev' and v['camera']['view']=='orbit_61_24_5.3');c=v['camera']
    saved=read_npz(UNIT/'dev'/c['view']/'FRAME.npz');mesh,newmesh,old,added,meta=asset(p)
    yy,xx=np.mgrid[:c['height'],:c['width']];mask=(saved['regions']==4)|((xx%7==1)&(yy%7==1));xy=np.column_stack([xx[mask],yy[mask]])
    f,tr=r.render(a,c,xy,sel['original_strength']);tc=validate_trace(a,c,xy,f,tr)
    paper,_=r.render(paper_copy(a,c,sel['completed_strength'],p['paper']),c)
    zero,_=r.render(paper_copy(a,c,np.zeros(310475),p['paper']),c,strength=np.zeros(310475))
    np.testing.assert_array_equal(f['rgb'],saved['source']);np.testing.assert_array_equal(f['contribution'],saved['new_support'])
    np.testing.assert_array_equal(paper['rgb'],saved['new_paper']);np.testing.assert_array_equal(zero['rgb'],f['rgb']);assert not zero['contribution'].any()
    pair,hi=render_pair(mesh,newmesh,old,added,meta,c)
    arrays=dict(source=f['rgb'],paper=paper['rgb'],support=f['contribution'])
    for mode,scale in [('raw',1.),('matched',m['scales']['new'])]:
        im,alpha=compose(paper['rgb'],pair['new'],f['contribution'],True,scale,p['ink_color'])
        np.testing.assert_array_equal(im,saved['new_'+mode]);np.testing.assert_array_equal(alpha,saved['new_'+mode+'_alpha']);arrays[mode]=im
    null,na=compose(paper['rgb'],pair['new'],zero['contribution'],True,ink_color=p['ink_color']);np.testing.assert_array_equal(null,paper['rgb']);assert not na.any()
    totalnull,na=compose(zero['rgb'],pair['new'],zero['contribution'],True,ink_color=p['ink_color']);np.testing.assert_array_equal(totalnull,saved['source'])
    assert before==array_hashes(a);np.savez_compressed(out/'REPLAY.npz',**arrays,zero_ink=null,all_links_zero=totalnull)
    png(out/'new_raw.png',arrays['raw']);png(out/'all_links_zero.png',totalnull)
    js(out/'REPLAY_CHECK.json',dict(utc=now(),camera=c,full_GS_renders=3,source_paper_support_exact=True,
        raw_and_matched_exact=True,zero_ink_equals_paper=True,all_links_zero_equals_original_GS=True,trace=tc,original_arrays_unchanged=True))
    print('REPLAY exact; zero ink and all-links-zero controls passed',flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['audit','replay']);ap.add_argument('--out',type=Path);args=ap.parse_args()
    if args.stage=='audit':audit()
    else:replay(args.out)
