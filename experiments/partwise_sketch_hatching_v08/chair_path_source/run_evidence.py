"""One frozen camera per command; real full-source rendering and sparse path evidence."""
import runtime
from runtime import sha,js
from pathlib import Path
import argparse,json,time
import numpy as np
from linked_asset import npz,png,source_hashes
from whole_asset import compose_whole
from run_motion import MotionRenderer,verify_unit
from motion import observe
from geometry import project
from path_source import stencil,make_csr,select_highlights

def pixel_rays(renderer,xy,c):
    import open3d as o3d
    E=np.asarray(c['extrinsic']);R=E[:3,:3];origin=-np.linalg.solve(R,E[:3,3])
    local=np.column_stack(((xy[:,0]-c['cx'])/c['fx'],(xy[:,1]-c['cy'])/c['fy'],np.ones(len(xy))))
    direction=local@np.linalg.inv(R).T
    rays=np.column_stack((np.broadcast_to(origin,direction.shape),direction)).astype(np.float32)
    hit=renderer.scene.cast_rays(o3d.core.Tensor(rays),nthreads=1)
    depth=hit['t_hit'].numpy().astype(float);face=hit['primitive_ids'].numpy().astype(np.int64)
    region=np.zeros(len(xy),np.int32);valid=np.isfinite(depth);region[valid]=renderer.mesh['regions'][face[valid]]
    return depth,region

def run(unit,index):
    from render import render,RenderCache
    from hybrid import paper_copy,edit_metrics
    from link_renderer import validate_trace
    from membership import evaluated_tint_copy
    import base_model as base
    verify_unit(unit);start=time.monotonic();protocol=json.loads((unit/'PROTOCOL.json').read_text())
    samples=json.loads((unit/'delivery/SAMPLES.json').read_text());c=protocol['cameras'][index]
    asset=unit/'delivery/assets/whole_spacing';r=MotionRenderer(asset,unit/'renders/build',samples)
    out=runtime.configure_output(unit/'renders'/c['view']);support_root=unit/'delivery/support';support_root.mkdir(exist_ok=True)
    uv,z=project(np.asarray([a['point'] for a in samples['anchors']]),c)
    inside=(z>.2)&(uv[:,0]>=0)&(uv[:,1]>=0)&(uv[:,0]<=c['width']-1)&(uv[:,1]<=c['height']-1)
    xy,ro,rs,beta=stencil(uv,inside,c['width'],c['height'])
    if not len(xy):raise RuntimeError('no in-frame stencil: retain failure, do not substitute samples')
    source,trace=r.engine.render(r.source,c,xy=xy,strength=r.s)
    off,_=r.engine.render(r.source,c,strength=r.s)
    off_equal={k:bool(np.array_equal(v,off[k])) for k,v in source.items()};assert all(off_equal.values())
    proof=validate_trace(r.source,c,xy,source,trace);xx,yy=xy.T
    reconstructed=np.bincount(trace['sample_index'],trace['weight']*r.s[trace['source_index']],minlength=len(xy))
    support_error=float(np.max(np.abs(reconstructed-source['contribution'][yy,xx])));assert support_error<1e-6
    paper,_=r.engine.render(paper_copy(r.source,c,np.ones(len(r.s)),r.preset['paper_color']),c)
    np.testing.assert_array_equal(source['alpha'],paper['alpha'])
    assert np.max(np.abs(paper['rgb']-(1-.05*source['alpha'][:,:,None])))<1e-6
    cache=RenderCache(track_ids=samples['selected_paths'])
    proxy=render(r.mesh,r.paths,r.meta['styles'],c,2,dict(contours_visible=True,contour_strength=1.),cache)
    data=cache.value
    if data is None:raise RuntimeError('bounded own-coverage cache exceeded')
    layers={k:np.maximum.reduce([v.astype(np.float32)*r.meta['styles'][str(k)].get('ink_strength',.8) for v in vals.values()]) for k,vals in data['coverage'].items()}
    composed=compose_whole(paper['rgb'],layers,data['contour'],source['contribution'],2)
    np.testing.assert_allclose(1-composed['ungated_ink'],proxy['image'],atol=1e-7,rtol=0)
    frame=dict(source=source['rgb'],source_alpha=source['alpha'],paper=paper['rgb'],support=source['contribution'],
        proxy=proxy['image'],proxy_depth=proxy['depth'],regions=proxy['regions'],**composed)
    reference=npz(unit/'inputs/reference'/str(index)/'FRAME.npz')
    assert set(frame)==set(reference)
    equality={k:bool(np.array_equal(v,reference[k])) for k,v in frame.items()};assert all(equality.values()),equality
    obs=observe(r.mesh,samples,c,data,source['contribution'],r.meta['styles'],r.scene)
    pixel_depth,pixel_region=pixel_rays(r,xy,c)
    gates=protocol['eligibility']
    sample_ok=(pixel_region==4)&np.isfinite(pixel_depth)&(source['alpha'][yy,xx]>=gates['pixel_source_alpha_min'])
    sample_ok&=np.abs(source['median_camera_z'][yy,xx]-pixel_depth)<=gates['pixel_source_median_proxy_depth_tolerance']
    own=np.stack([obs['own_pre'][samples['selected_paths'].index(a['key']),yy,xx] for a in samples['anchors']])
    csr=make_csr(samples['anchors'],ro,rs,beta,trace,obs['status'],own,sample_ok,pixel_depth,r.s,gates['contributor_pixel_proxy_depth_tolerance'])
    own_post=[]
    for j in range(len(samples['anchors'])):
        lo,hi=csr['offsets'][j:j+2]
        own_post.append(np.sum(csr['pixel_weight'][lo:hi]*csr['own_ink'][lo:hi]*csr['weight'][lo:hi]*csr['region_strength'][lo:hi]))
    pre_error=float(np.max(np.abs(csr['own_pre']-obs['pre'])));post_error=float(np.max(np.abs(own_post-obs['post'])))
    assert pre_error<1e-6 and post_error<1e-6,(pre_error,post_error)
    csr.update(xy=xy,uv=uv,camera_z=z,pixel_proxy_depth=pixel_depth,pixel_proxy_region=pixel_region,
        pixel_sample_ok=sample_ok,own_post=np.asarray(own_post),observed_post=obs['post'],source_alpha=source['alpha'][yy,xx],
        source_support=source['contribution'][yy,xx])
    np.savez_compressed(out/'FRAME.npz',**frame);np.savez_compressed(out/'TRACE.npz',xy=xy,**trace)
    np.savez_compressed(out/'PATH_SUPPORT.npz',**csr);np.savez_compressed(out/'OBSERVATIONS.npz',**obs)
    np.savez_compressed(support_root/(c['view']+'.npz'),**csr)
    for key in ('source','paper','support','hybrid','proxy'):png(out/(key+'.png'),frame[key])
    for key in ('combined_ink','seat_ink','seat_linked_ink','other_ink','contour'):png(out/(key+'.png'),1-frame[key])
    strokes=[int(k.split(':')[1]) for k in samples['selected_paths']]
    if index==0:
        selected=select_highlights(csr,strokes,len(r.s))
        js(support_root/'HIGHLIGHTS.json',dict(asset_manifest_sha256=samples['asset_manifest_sha256'],source_sha256=r.link['source_sha256'],
            source_count=len(r.s),build_camera=c,build_support_sha256=sha(support_root/(c['view']+'.npz')),
            strength=protocol['highlight']['strength'],color=protocol['highlight']['color'],
            paths={str(k):v.tolist() for k,v in selected.items()},selection=protocol['highlight']['selection'],
            scope='Diagnostic source-kernel color selection from BUILD only; no physical ownership or local-control success claim'))
    saved=json.loads((support_root/'HIGHLIGHTS.json').read_text())
    assert saved['asset_manifest_sha256']==sha(asset/'FILES.json')
    assert saved['source_sha256']==r.link['source_sha256'] and saved['source_count']==len(r.s)
    colors=base.source_colors(r.source,c);highlights={};highlight_arrays={};tint=np.asarray(saved['color'])
    for k,stroke in enumerate(strokes):
        ids=np.asarray(saved['paths'][str(stroke)],np.int64)
        strength=np.zeros(len(r.s));strength[ids]=saved['strength']
        changed=evaluated_tint_copy(r.source,c,strength,tint)
        high,_=r.engine.render(changed,c)
        np.testing.assert_array_equal(source['alpha'],high['alpha'])
        for name in ('median_camera_z','center_depth_proxy','expected_camera_z'):np.testing.assert_array_equal(source[name],high[name])
        ev=trace['source_index'];delta=trace['weight'][:,None]*strength[ev,None]*(tint-colors[ev])
        pred=np.stack([np.bincount(trace['sample_index'],delta[:,j],minlength=len(xy)) for j in range(3)],1)
        delta_error=float(np.max(np.abs(pred-(high['rgb']-source['rgb'])[yy,xx])));assert delta_error<1e-6
        mask=obs['own_pre'][k]/r.meta['styles']['4'].get('ink_strength',.8)
        locate=frame['hybrid']*(1-mask[:,:,None])+np.array([.85,.03,.03])*mask[:,:,None]
        png(out/f'highlight_{stroke}.png',high['rgb']);png(out/f'path_{stroke}.png',locate)
        highlight_arrays[str(stroke)]=high['rgb']
        highlights[str(stroke)]=dict(selected_original_ids=len(ids),own_path_proxy_pixels=int((mask>0).sum()),
            delta_reconstruction_max_error=delta_error,source_change=edit_metrics(source['rgb'],high['rgb'],proxy['regions']),
            alpha_and_depth_unchanged=True)
    np.savez_compressed(out/'HIGHLIGHTS.npz',**highlight_arrays)
    assert source_hashes(r.source)==r.original
    states={str(k):int(v) for k,v in zip(*np.unique(csr['state'],return_counts=True))}
    summary=dict(camera=c,states=states,anchors=len(samples['anchors']),unique_trace_pixels=len(xy),trace_events=len(trace['weight']),
        csr_event_references=len(csr['weight']),eligible_event_references=int(csr['eligible'].sum()),
        eligible_mass=float(csr['eligible_mass'].sum()),raw_bilinear_mass=float(csr['weighted_mass'].sum()),
        own_pre_reconstruction_max_error=pre_error,own_post_reconstruction_max_error=post_error,
        trace_validation=proof,trace_off_equal=off_equal,support_error=support_error,baseline_arrays_equal=equality,
        highlight_manifest_sha256=sha(support_root/'HIGHLIGHTS.json'),highlights=highlights,
        global_hybrid_absolute=edit_metrics(frame['source'],frame['hybrid'],frame['regions']),
        source_arrays_unchanged=True,source_array_hashes=r.original,unknown_rows=int(r.binding['unknown'].sum()),selected_region_rows=int((r.s>0).sum()),
        seconds=time.monotonic()-start,cold_original_GS=True,reference_scope='Verified existing same-camera result; new whole scene and all highlight kernels actually rendered',
        files={f.name:sha(f) for f in out.iterdir() if f.is_file()})
    js(out/'RENDER_RECEIPT.json',summary)
    js(support_root/(c['view']+'.json'),dict(camera=c,csr_sha256=sha(support_root/(c['view']+'.npz')),asset_manifest_sha256=sha(asset/'FILES.json'),
        source_sha256=r.link['source_sha256'],states=states,scope='18 sparse anchors on6 fixed seat paths; raw full-T pixel evidence, not full-path physical certification'))
    verify_unit(unit)
    print(json.dumps(dict(view=c['view'],states=states,highlight_counts={k:v['selected_original_ids'] for k,v in highlights.items()},seconds=summary['seconds'])),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--unit',type=Path,required=True);p.add_argument('--camera-index',type=int,choices=[0,1,2],required=True)
    a=p.parse_args();run(a.unit,a.camera_index)
