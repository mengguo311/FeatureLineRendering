"""Readback and actual full-original-GS cold replay for unit010."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,js,sha,now
from pathlib import Path
import argparse,json
import numpy as np
from scipy import ndimage
from run_frame_unit import protocol,locked,original_asset,asset,match,fresh,measure,ARMS,OLD
from local_frame import fit_frame,frame_normals
from target_completion import render_pair
from hybrid import compose,paper_copy
from link_renderer import Renderer,validate_trace
from run_hybrid import read_npz,array_hashes,png
import base_model as base

def source(p):
    s=p['scene']['source'];a=base.load_source(locked(p,s['original_ply']),s['sha256'])
    a['source_index']=np.arange(len(a['means']),dtype=np.int64);assert len(a['means'])==310475;return a

def audit():
    p=protocol();m=match();a=source(p);before=array_hashes(a)
    for f,h in p['inputs'].items():assert sha(f)==h,f
    oldmesh,mesh,paths,added,meta=asset(p);sel=read_npz(UNIT/'asset/SOURCE_LINK.npz');oldsel=read_npz(locked(p,OLD/'SELECTION.npz'))
    np.testing.assert_array_equal(sel['source_index'],np.arange(310475))
    np.testing.assert_array_equal(sel['paper_strength'],oldsel['completed_strength']);np.testing.assert_array_equal(sel['ink_strength'],oldsel['original_strength'])
    assert int(read_npz(locked(p,OLD/'SOURCE_BINDING.npz'))['unknown'].sum())==195279
    ids=read_npz(UNIT/'asset/BUILD_FACES.npz')['face_ids'];frame=json.loads((UNIT/'asset/FRAME.json').read_text())
    assert fit_frame(mesh,ids)==frame
    normals=frame_normals(frame['basis'],[35.,95.])
    for part in (paths,added):
        np.testing.assert_allclose(part['points'],np.einsum('nij,njk->nik',part['bary'],mesh['tri'][part['face']]),rtol=0,atol=1e-10)
        for layer,spacing in [(0,.06),(1,.075)]:
            points=part['points'][part['layer_id']==layer];levels=points@normals[layer]/spacing-.1732050807568877
            np.testing.assert_allclose(levels,np.rint(levels),rtol=0,atol=1e-10)
    for name,h in json.loads((UNIT/'BUILD_LOCK.json').read_text())['files'].items():assert sha(UNIT/name)==h,name
    checks=[];records=[];budgets={k:0. for k in ARMS}
    for v in p['views']:
        c=v['camera'];ref=read_npz(locked(p,v['cache']))
        path=UNIT/'build_match'/(c['view']+'.npz') if v['kind']=='build' else UNIT/v['kind']/c['view']/'FRAME.npz'
        f=read_npz(path)
        for key,oldkey in [('source','source'),('paper','new_paper'),('support','new_support'),('xz_raw','new_raw'),('xz_raw_alpha','new_raw_alpha'),('regions','regions')]:
            np.testing.assert_array_equal(f[key],ref[oldkey])
        for arm in ARMS:
            for mode,scale in [('raw',1.),('matched',m['scales'][arm])]:
                im,alpha=compose(f['paper'],f[arm+'_ink'],f['support'],True,scale,p['ink_color'])
                if arm+'_'+mode in f:
                    np.testing.assert_array_equal(im,f[arm+'_'+mode]);np.testing.assert_array_equal(alpha,f[arm+'_'+mode+'_alpha'])
                if v['kind']=='build' and mode=='matched':budgets[arm]+=float(np.abs(im-f['paper'])[f['regions']==4].sum(dtype=float))
        if v['kind']=='build':continue
        folder=path.parent;done=json.loads((folder/'COMPLETED.json').read_text())
        for name,h in done['files'].items():assert sha(folder/name)==h,name
        e=json.loads((folder/'EVALUATION.json').read_text());measured=measure(f)
        for key,value in measured.items():assert value==e[key],key
        tr=read_npz(locked(p,v['trace']));tc=validate_trace(a,c,tr['xy'],dict(rgb=f['source'],alpha=f['source_alpha']),tr)
        sid=tr['sample_index'];ids=tr['source_index'];w=tr['weight'];xx,yy=tr['xy'].T;count=len(xx)
        support=np.bincount(sid,w*sel['ink_strength'][ids],minlength=count)
        np.testing.assert_allclose(support,f['support'][yy,xx],rtol=0,atol=1e-6)
        mass=np.bincount(sid,w,minlength=count);colors=base.source_colors(a,c);s=sel['paper_strength'][ids]
        colors=colors[ids]*(1-s[:,None])+np.asarray(p['paper'])*s[:,None]
        paper=np.repeat(1-mass[:,None],3,axis=1)
        for j in range(3):paper[:,j]+=np.bincount(sid,w*colors[:,j],minlength=count)
        np.testing.assert_allclose(paper,f['paper'][yy,xx],rtol=0,atol=1e-6)
        target=f['regions']==4;assert int(target[yy,xx].sum())==int(target.sum())
        far=~ndimage.binary_dilation(target,iterations=2);delta=np.abs(f['local_raw']-f['xz_raw']).sum(2)
        farcheck=dict(max_new_raw_L1=float(delta[far].max()),new_visible_pixels=int((delta[far]>1/255).sum()),new_far_sum=float(delta[far].sum(dtype=float)))
        checks.append(dict(kind=v['kind'],view=c['view'],trace=tc,original_ID_support_and_paper_reconstructed=True,legacy_exact=True,far=farcheck))
        records.append(dict(kind=v['kind'],view=c['view'],**measured,far_readback=farcheck))
        print('AUDIT',v['kind'],c['view'],flush=True)
    assert max(abs(v-m['budget'])/m['budget'] for v in budgets.values())<1e-5;assert before==array_hashes(a)
    js(UNIT/'SUMMARY.json',dict(records=records,build=m,asset=json.loads((UNIT/'asset/ASSET.json').read_text())))
    js(UNIT/'VALIDATION.json',dict(utc=now(),inputs_checked=len(p['inputs']),original_array_hashes=before,
        source_count=310475,UNKNOWN_unchanged=195279,paper_rows_unchanged=41058,ink_rows_unchanged=21006,views=checks,
        budget_readback=budgets,anchors_and_slice_levels_verified=True,frame_recomputed=True,scope=p['scope']))

def replay(out):
    p=protocol();m=match();a=source(p);before=array_hashes(a);out=fresh(out);r=Renderer(out/'build')
    sel=read_npz(UNIT/'asset/SOURCE_LINK.npz');v=next(v for v in p['views'] if v['kind']=='dev' and v['camera']['azimuth']==241 and v['camera']['elevation']==24)
    c=v['camera'];saved=read_npz(UNIT/'dev'/c['view']/'FRAME.npz');xy=read_npz(locked(p,v['trace']))['xy']
    f,tr=r.render(a,c,xy,sel['ink_strength']);tc=validate_trace(a,c,xy,f,tr)
    np.testing.assert_array_equal(f['rgb'],saved['source']);np.testing.assert_array_equal(f['contribution'],saved['support'])
    paper,_=r.render(paper_copy(a,c,sel['paper_strength'],p['paper']),c);np.testing.assert_array_equal(paper['rgb'],saved['paper'])
    oldmesh,mesh,paths,added,meta=asset(p);local,_=render_pair(oldmesh,mesh,paths,added,meta,c)
    np.testing.assert_array_equal(local['new'],saved['local_ink'])
    _,_,old,oldadded,_=original_asset(p);legacy,_=render_pair(oldmesh,mesh,old,oldadded,meta,c)
    np.testing.assert_array_equal(legacy['new'],saved['xz_ink'])
    arrays={}
    for arm,ink in [('xz',legacy['new']),('local',local['new'])]:
        for mode,scale in [('raw',1.),('matched',m['scales'][arm])]:
            key=arm+'_'+mode;im,alpha=compose(paper['rgb'],ink,f['contribution'],True,scale,p['ink_color'])
            np.testing.assert_array_equal(im,saved[key]);np.testing.assert_array_equal(alpha,saved[key+'_alpha']);arrays[key]=im
    zero,_=r.render(paper_copy(a,c,np.zeros(310475),p['paper']),c,strength=np.zeros(310475))
    np.testing.assert_array_equal(zero['rgb'],f['rgb']);assert not zero['contribution'].any()
    im,_=compose(paper['rgb'],local['new'],zero['contribution'],True);np.testing.assert_array_equal(im,paper['rgb'])
    allzero,_=compose(zero['rgb'],local['new'],zero['contribution'],True);np.testing.assert_array_equal(allzero,f['rgb'])
    assert before==array_hashes(a)
    np.savez_compressed(out/'REPLAY.npz',**arrays,zero_ink=im,all_links_zero=allzero)
    png(out/'local_raw.png',arrays['local_raw']);png(out/'all_links_zero.png',allzero)
    js(out/'REPLAY_CHECK.json',dict(utc=now(),camera=c,full_GS_renders=3,proxy_paths_rerendered=True,
        source_and_support_exact=True,all_four_hybrids_exact=True,zero_ink_equals_paper=True,all_links_zero_equals_original_GS=True,original_arrays_unchanged=True,trace=tc))
    print('REPLAY three full GS renders; both path variants and null controls exact',flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['audit','replay']);ap.add_argument('--out',type=Path);args=ap.parse_args()
    if args.stage=='audit':audit()
    else:replay(args.out)
