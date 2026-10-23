"""Independent contour-owner readback, original-ID reconstruction, cold GS replay."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,sha,js,now
import argparse
import json
import numpy as np
from scipy import ndimage
from run_contour_unit import protocol,locked,asset,saved_asset,match,cache,fresh,ARMS
from run_hybrid import read_npz,array_hashes,panel
from hybrid import compose,paper_copy,edit_metrics,region_strength
from membership import load_binding
from link_renderer import Renderer,validate_trace
from run_completion_unit import reconstruct_trace
import base_model as base


def load_source(p):
    s=p['scene'];a=base.load_source(locked(p,s['source']['original_ply']),s['source']['sha256'])
    a['source_index']=np.arange(len(a['means']),dtype=np.int64);assert len(a['means'])==310475
    b,_=load_binding(locked(p,s['binding']),s['source']['sha256'],310475)
    return a,b


def independent_contour_check(raster):
    depth=raster['depth_hi'];regions=raster['regions_hi'];hit=np.isfinite(depth)
    # Manhattan distance gives the two-pixel inside band, independent of erosion.
    distance=ndimage.distance_transform_cdt(np.pad(hit,1),metric='taxicab')[1:-1,1:-1]
    silhouette=hit&(distance<=2)&(regions==4)
    np.testing.assert_array_equal(silhouette,raster['silhouette_hi'])
    expected=np.zeros(hit.shape,bool);h,w=hit.shape
    # Each target pixel asks whether it is the foreground owner of any neighbor.
    for y,x in np.argwhere(hit&(regions==4)):
        z=depth[y,x]
        for dy,dx in ((-1,0),(1,0),(0,-1),(0,1)):
            yy,xx=y+dy,x+dx
            if 0<=yy<h and 0<=xx<w and np.isfinite(depth[yy,xx]):
                other=depth[yy,xx]
                if z<other and abs(z-other)>.035:expected[y,x]=True;break
    np.testing.assert_array_equal(expected,raster['occlusion_hi'])
    np.testing.assert_array_equal(raster['contour_hi'],(silhouette|expected).astype(np.float32)*.85)
    assert not raster['contour_hi'][regions!=4].any()
    return dict(silhouette_subpixels=int(silhouette.sum()),occlusion_subpixels=int(expected.sum()),
        union_subpixels=int((silhouette|expected).sum()),foreground_owner_verified=True,nonwrapping_neighbors=True)


def audit():
    p=protocol();m=match();mesh,paths,meta=asset(p);link=saved_asset();a,b=load_source(p);before=array_hashes(a)
    for f,h in p['input_hashes'].items():assert sha(f)==h,f
    np.testing.assert_array_equal(link['source_index'],a['source_index'])
    np.testing.assert_array_equal(link['original_strength'],region_strength(b))
    for k in ('unknown','region_id','conflict'):np.testing.assert_array_equal(link[k+'_unchanged'],b[k])
    sel=read_npz(locked(p,p['source_selection']));np.testing.assert_array_equal(link['completed_strength'],sel['completed_strength'])
    saved=read_npz(UNIT/'asset/PATHS.npz')
    for key in paths:np.testing.assert_array_equal(paths[key],saved[key])
    budgets={k:0. for k in ARMS}
    for v in (v for v in p['views'] if v['kind']=='build'):
        f=read_npz(UNIT/'build_match'/(v['camera']['view']+'.npz'));target=f['regions']==4
        for arm in ARMS:
            im,_=compose(f['paper'],f[arm+'_ink'],f['support'],True,m['scales'][arm],p['ink_color'])
            budgets[arm]+=float(np.abs(im-f['paper'])[target].sum(dtype=float))
    assert m['scales']['hatch']==1. and max(abs(x-m['budget'])/m['budget'] for x in budgets.values())<1e-5
    records=[];checks=[]
    for v in (v for v in p['views'] if v['kind']!='build'):
        c=v['camera'];root=UNIT/v['kind']/c['view'];completion=json.loads((root/'COMPLETED.json').read_text())
        for name,h in completion['files'].items():assert sha(root/name)==h,name
        f=read_npz(root/'FRAME.npz');raster=read_npz(root/'RASTER.npz');e=json.loads((root/'EVALUATION.json').read_text());old=cache(p,v)
        for name in ('source','paper','support','regions'):np.testing.assert_array_equal(f[name],old[name])
        np.testing.assert_array_equal(f['hatch_raw'],old['old_hybrid']);np.testing.assert_array_equal(f['hatch_raw_alpha'],old['old_alpha'])
        contour_check=independent_contour_check(raster)
        low=lambda x:x.reshape(c['height'],2,c['width'],2).mean((1,3))
        np.testing.assert_array_equal(f['hatch_ink'],low(raster['hatch_hi']))
        np.testing.assert_array_equal(f['outlined_ink'],low(np.maximum(raster['hatch_hi'],raster['contour_hi'])))
        np.testing.assert_array_equal(f['contour_ink'],low(raster['contour_hi']))
        np.testing.assert_array_equal(f['contour_alpha'],f['contour_ink']*f['support'])
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
                    far_background_L1=mm['far_background']['raw_L1_sum'],far_ink_L1=e['ink'][key]['far_visible_ink_L1'])
        for mode in ('raw','matched'):
            assert edit_metrics(f['hatch_raw'],f['outlined_'+mode],f['regions'])==e['changes'][mode]
        records.append(dict(kind=v['kind'],view=c['view'],target_pixels=int(target.sum()),interior_pixels=int(inner.sum()),
            arms=rows,support=e['support'],changes=e['changes'],contour=e['contour'],contour_audit=contour_check))
        checks.append(dict(kind=v['kind'],view=c['view'],hatch_exact=True,trace_events=len(mass),source_paper_S_from_original_rows=True,contour_owner_exact=True))
        print('AUDIT',v['kind'],c['view'],'owners, original-ID linkage and output consistent',flush=True)
    assert before==array_hashes(a)
    js(UNIT/'SUMMARY.json',dict(records=records,build=m))
    js(UNIT/'VALIDATION.json',dict(utc=now(),input_hashes_checked=len(p['input_hashes']),full_original_row_identity=True,
        M1_and_paper_permissions_unchanged=True,all_path_arrays_exact=True,all_contour_owners_independently_checked=True,
        actual_BUILD_ink_budget=budgets,views=checks,original_array_hashes=before,scope=p['scope']))


def replay(out):
    from linked_contours import render_contours
    p=protocol();m=match();mesh,paths,meta=asset(p);link=saved_asset()
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
    pair,hi=render_contours(mesh,paths,meta,c);arrays=dict(source=source['rgb'],paper=paper['rgb'],support=source['contribution'])
    checks={k:True for k in ('source','paper','support','source_alpha')}
    for arm in ARMS:
        np.testing.assert_array_equal(pair[arm],saved[arm+'_ink'])
        for mode,scale in [('raw',1.),('matched',m['scales'][arm])]:
            name=arm+'_'+mode;im,alpha=compose(paper['rgb'],pair[arm],source['contribution'],True,scale,p['ink_color'])
            np.testing.assert_array_equal(im,saved[name]);np.testing.assert_array_equal(alpha,saved[name+'_alpha'])
            checks[name]=True;arrays[name]=im
    null,na=compose(paper['rgb'],pair['outlined'],zero['contribution'],True,ink_color=p['ink_color'])
    np.testing.assert_array_equal(null,paper['rgb']);assert not na.any();arrays['zero_link_control']=null
    assert before==array_hashes(a)
    np.savez_compressed(out/'REPLAY.npz',**arrays);np.savez_compressed(out/'TRACE.npz',**tr,xy=xy)
    panel(out/'REPLAY.png',[arrays[k] for k in ('source','paper','zero_link_control','hatch_raw','outlined_raw','outlined_matched')],
        ['Actual original GS','Actual fixed GS paper','Actual zero-S control','Old linked hatch','Owned contour natural','Owned contour matched'],
        'Cold complete original-GS replay; original rows, opacity and full SH3 unchanged',columns=3)
    js(out/'REPLAY_CHECK.json',dict(utc=now(),camera=c,actual_complete_GS_renders=3,exact=checks,
        actual_zero_link_blank_ink=True,trace=trace_check,original_array_hashes=before,
        files={f.name:sha(f) for f in out.iterdir() if f.is_file()},scope=p['scope']))
    print('COLD_REPLAY',checks,'actual zero-link blank',flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['audit','replay']);ap.add_argument('--out',type=runtime.Path);args=ap.parse_args()
    if args.stage=='audit':audit()
    else:replay(args.out or UNIT/'cold_replay_001')
