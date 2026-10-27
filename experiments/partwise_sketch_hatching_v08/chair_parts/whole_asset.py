"""Fixed whole-Chair presentation; seat source responsibility remains optional evidence, not ownership."""
import runtime
from runtime import sha,js
from pathlib import Path
import argparse,json,os,shutil,time
import numpy as np
from linked_asset import load_asset,edit_asset,seal,npz,source_hashes,png,SAMPLES,query
from geometry import orbit_camera

PRESET=dict(schema='whole_chair_presentation_v1',paper_color=[.95,.95,.95],paper_scope='all_original_rows_render_time_only',
    active_regions=[1,2,3,4,5],source_gated_regions=[4],proxy_only_regions=[1,2,3,5],
    contours_visible=True,contour_strength=1.,ink_color=.03,supersample=2,
    composition='max union at AA2; native-pixel S replicated to its four subsamples; then area average',
    scope='System presentation capability, not a matched-budget mechanism comparison. Global appearance is not labeling; UNKNOWN stays UNKNOWN. No per-path original-ID certification.')

def validate_preset(preset):
    if preset!=PRESET:raise ValueError('only the frozen whole_chair_presentation_v1 preset is supported')
    return dict(preset)

def load_preset(asset):
    asset=Path(asset);_,_,_,link,_=load_asset(asset)
    if link['paper_effect']!=1.:raise ValueError('regional paper effect is inapplicable in this fixed global-paper mode')
    return validate_preset(json.loads((asset/'WHOLE_PRESET.json').read_text()))

def save_preset(asset,out,preset=None):
    preset=validate_preset(PRESET if preset is None else preset)
    asset=Path(asset).resolve();_,_,meta,link,_=load_asset(asset)
    if link['paper_effect']!=1.:raise ValueError('use a paper_effect=1 source asset; global paper is fixed')
    out=runtime.configure_output(out)
    for f in asset.iterdir():
        if f.is_file() and f.name!='FILES.json':shutil.copy2(f,out/f.name)
    for field in ('source_file','binding_file'):link[field]=os.path.relpath((asset/link[field]).resolve(),out)
    meta['original']['original_ply']=link['source_file']
    js(out/'asset.json',meta);js(out/'LINKED_ASSET.json',link);js(out/'WHOLE_PRESET.json',preset)
    seal(out);load_preset(out)
    return out

def edit_whole(asset,out,changes):
    load_preset(asset)
    if not changes:raise ValueError('provide angle, spacing or length')
    edit_asset(asset,out,changes);load_preset(out)
    return Path(out)

def compose_whole(paper,layers,contour,support,aa=2):
    paper=np.asarray(paper);support=np.asarray(support);contour=np.asarray(contour)
    h,w=support.shape
    if paper.shape!=(h,w,3) or contour.shape!=(h*aa,w*aa) or 4 not in layers:raise ValueError('invalid aligned layers')
    if not np.isfinite(support).all() or (support<0).any() or (support>1+1e-6).any():raise ValueError('invalid source support')
    values=[paper,contour,*layers.values()]
    if any(not np.isfinite(v).all() for v in values):raise ValueError('nonfinite layer')
    if any(np.asarray(v).shape!=contour.shape or np.min(v)<0 or np.max(v)>1+1e-6 for v in layers.values()):raise ValueError('invalid ink layer')
    low=lambda v:np.asarray(v).reshape(h,aa,w,aa).mean((1,3))
    up=np.repeat(np.repeat(np.clip(support,0,1),aa,0),aa,1)
    other=np.maximum.reduce([np.asarray(v) for r,v in layers.items() if r!=4]+[np.zeros_like(contour)])
    fixed=np.maximum(other,contour)
    seat=layers[4]*up
    combined=low(np.maximum(fixed,seat));ungated=low(np.maximum(fixed,layers[4]))
    hybrid=paper*(1-combined[:,:,None])+.03*combined[:,:,None]
    result=dict(hybrid=hybrid,combined_ink=combined,ungated_ink=ungated,other_ink=low(other),contour=low(contour),
                seat_ink=low(layers[4]),seat_linked_ink=low(seat))
    result.update({f'layer_{r}':low(v) for r,v in layers.items()})
    return result

def render_whole(asset,out,camera,reference=None):
    import base_model as base
    from link_renderer import Renderer,validate_trace
    from hybrid import paper_copy,region_strength
    from render import render,RenderCache
    start=time.monotonic();asset=Path(asset).resolve();preset=load_preset(asset)
    mesh,paths,meta,link,binding=load_asset(asset);out=runtime.configure_output(out)
    source_file=(asset/link['source_file']).resolve()
    a=base.load_source(source_file,link['source_sha256']);a['source_index']=np.arange(len(a['means']),dtype=np.int64)
    original=source_hashes(a);s=region_strength(binding)
    xy=np.asarray(SAMPLES,np.int32)
    xy=np.unique(np.clip(np.rint(xy*(camera['width']/384)),0,camera['width']-1).astype(np.int32),axis=0)
    engine=Renderer(out/'build')
    source,trace=engine.render(a,camera,xy=xy,strength=s)
    overridden=paper_copy(a,camera,np.ones(len(s)),preset['paper_color'])
    np.testing.assert_array_equal(overridden['colors'],np.broadcast_to(np.asarray(preset['paper_color']),overridden['colors'].shape))
    paper,_=engine.render(overridden,camera)
    np.testing.assert_array_equal(source['alpha'],paper['alpha'])
    paper_error=float(np.max(np.abs(paper['rgb']-(1-.05*source['alpha'][:,:,None]))))
    assert paper_error<1e-6
    trace_proof=validate_trace(a,camera,xy,source,trace)
    weights=trace['weight'];ids=trace['source_index'];sid=trace['sample_index']
    reconstructed=np.bincount(sid,weights*s[ids],minlength=len(xy));xx,yy=xy.T
    support_error=float(np.max(np.abs(reconstructed-source['contribution'][yy,xx])))
    assert support_error<1e-6
    cache=RenderCache();display=dict(contours_visible=True,contour_strength=1.)
    proxy=render(mesh,paths,meta['styles'],camera,2,display,cache)
    data=cache.value
    if data is None:raise RuntimeError('AA coverage exceeds bounded transient cache')
    layers={}
    for region,coverage in data['coverage'].items():
        strength=meta['styles'][str(region)].get('ink_strength',.80)
        layers[region]=np.maximum.reduce([v.astype(np.float32)*strength for v in coverage.values()])
    result=compose_whole(paper['rgb'],layers,data['contour'],source['contribution'],2)
    # Existing conventional renderer uses union before AA, with black ink on white.
    np.testing.assert_allclose(1-result['ungated_ink'],proxy['image'],atol=1e-7,rtol=0)
    frames=dict(source=source['rgb'],source_alpha=source['alpha'],paper=paper['rgb'],support=source['contribution'],
        proxy=proxy['image'],proxy_depth=proxy['depth'],regions=proxy['regions'],**result)
    assert source_hashes(a)==original
    comparison=None
    if reference is not None:
        prior=npz(Path(reference)/'FRAME.npz')
        assert set(prior)==set(frames)
        comparison={k:bool(np.array_equal(v,prior[k])) for k,v in frames.items()}
        assert all(comparison.values()),comparison
    np.savez_compressed(out/'FRAME.npz',**frames)
    np.savez_compressed(out/'TRACE.npz',xy=xy,**trace)
    for key in ('source','paper','hybrid','proxy','support'):png(out/(key+'.png'),frames[key])
    for key in ('combined_ink','other_ink','contour','seat_ink','seat_linked_ink'):png(out/(key+'.png'),1-frames[key])
    receipt=dict(camera=camera,preset=preset,asset_manifest_sha256=sha(asset/'FILES.json'),source_sha256=link['source_sha256'],
        source_count=len(s),source_array_hashes=original,source_arrays_unchanged=True,selected_rows=int((s>0).sum()),
        unknown_rows=int(binding['unknown'].sum()),global_override_rows=len(s),unknown_labels_unchanged=True,
        trace_validation=trace_proof,support_reconstruction_max_error=support_error,constant_paper_reconstruction_max_error=paper_error,
        regional_paper_effect_applied=False,parameters=meta['styles'],path_hashes={str(r):sha(asset/f'region_{r}.npz') for r in paths},
        actual_backend='CPU EWA original GS; fixed original kernels; proxy ink and proxy view contours',cold_original_GS=True,
        diagnostics=proxy['diagnostics'],bounds=proxy['bounds'],reload_comparison=comparison,seconds=time.monotonic()-start,
        files={f.name:sha(f) for f in out.iterdir() if f.is_file()})
    js(out/'RENDER_RECEIPT.json',receipt)
    print(json.dumps(dict(out=str(out),seconds=receipt['seconds'],reload_equal=comparison is not None)),flush=True)

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    s=sub.add_parser('preset');s.add_argument('--asset',type=Path,required=True);s.add_argument('--out',type=Path,required=True)
    e=sub.add_parser('edit');e.add_argument('--asset',type=Path,required=True);e.add_argument('--out',type=Path,required=True)
    for key in ('angle','spacing','length'):e.add_argument('--'+key,type=float)
    r=sub.add_parser('render');r.add_argument('--asset',type=Path,required=True);r.add_argument('--out',type=Path,required=True)
    r.add_argument('--camera',type=Path);r.add_argument('--reference',type=Path)
    r.add_argument('--azimuth',type=float,default=61.);r.add_argument('--elevation',type=float,default=24.);r.add_argument('--distance',type=float,default=5.1);r.add_argument('--size',type=int,default=384)
    q=sub.add_parser('query');q.add_argument('--asset',type=Path,required=True);q.add_argument('--ids',type=int,nargs='+',required=True)
    a=p.parse_args()
    if a.command=='preset':save_preset(a.asset,a.out)
    elif a.command=='edit':edit_whole(a.asset,a.out,{k:getattr(a,k) for k in ('angle','spacing','length') if getattr(a,k) is not None})
    elif a.command=='query':load_preset(a.asset);print(json.dumps(query(a.asset,a.ids),indent=2,default=runtime.json_default))
    else:
        if not 64<=a.size<=1024 or not np.isfinite([a.azimuth,a.elevation,a.distance]).all() or a.distance<=0:p.error('invalid camera')
        camera=json.loads(a.camera.read_text()) if a.camera else orbit_camera(a.azimuth,a.elevation,a.distance,a.size)
        if camera['width']!=camera['height']:p.error('square cameras required by inherited renderer')
        render_whole(a.asset,a.out,camera,a.reference)
if __name__=='__main__':main()
