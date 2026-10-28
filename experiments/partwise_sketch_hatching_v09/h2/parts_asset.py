"""Two authored Chair regions: saved proxy edits and separate original-GS color controls."""
import runtime
from runtime import sha,js
from pathlib import Path
import argparse,hashlib,json,os,shutil,time
import numpy as np
from linked_asset import load_asset,npz,seal,validate_paths,source_hashes,png
from whole_asset import load_preset,render_whole
from hatching import generate_region,validate_style
from hybrid import region_strength,edit_metrics
from geometry import orbit_camera

def check_region(region):
    if type(region) is not int or region not in (4,5):raise ValueError('editable authored regions are 4 (seat) and 5 (upper back)')

def regenerate_paths(mesh,region,style,parent,existing_ids):
    check_region(region);validate_style(style)
    data,stats=generate_region(mesh,region,style)
    if not len(data['face']):raise ValueError('edited style has no proxy support')
    key=hashlib.sha256(json.dumps([parent,region,style],sort_keys=True).encode()).hexdigest()
    _,index=np.unique(data['stroke_id'],return_inverse=True)
    if index.max()>=1_000_000:raise ValueError('path identity namespace exceeded')
    data['stroke_id']=(int(key[:10],16)+1)*1_000_000+index.astype(np.int64)
    data['visibility_mask']=np.full(len(index),1<<region,np.uint64)
    data['layer_id']=np.zeros(len(index),np.uint8)
    if np.intersect1d(data['stroke_id'],existing_ids).size:raise ValueError('new path identity collision')
    validate_paths(mesh,data,region)
    return data,stats

def part_edit(asset,out,region,changes,prepare=False):
    check_region(region);asset=Path(asset).resolve();load_preset(asset)
    mesh,paths,meta,link,_=load_asset(asset)
    if set(changes)-{'angle','spacing','length'}:raise ValueError('supported edits: angle, spacing, length')
    if prepare and (region!=5 or changes):raise ValueError('prepare only regenerates region5 at its saved style')
    style={**meta['styles'][str(region)],**changes};validate_style(style)
    regenerate=prepare or any(style[k]!=meta['styles'][str(region)][k] for k in changes)
    parent=sha(asset/'FILES.json');new=None
    if regenerate:
        oldids=np.concatenate([p['stroke_id'] for p in paths.values()])
        new,stats=regenerate_paths(mesh,region,style,parent,oldids)
    out=runtime.configure_output(out)
    for f in asset.iterdir():
        if f.is_file() and f.name!='FILES.json':shutil.copy2(f,out/f.name)
    if regenerate:
        np.savez_compressed(out/f'region_{region}.npz',**new)
        meta['statistics'][str(region)]=stats
    meta['styles'][str(region)]=style
    meta['edit']=dict(region=region,changes=changes,regenerated=regenerate,preparation=prepare,parent_asset_sha256=parent,
        scope='Proxy direction/spacing/length control; source kernels and source-region weights unchanged. Generation includes path-count, boundary phase and length responses.')
    meta['linked_scope']='Whole-object fixed paper; seat region4 source-gated ink. Upper-back region5 proxy-only ink. Separate region-source control never certifies paths.'
    if prepare:
        meta['region5_preparation']=dict(historical_paths_sha256=sha(asset/'region_5.npz'),historical_paths=int(len(np.unique(paths[5]['stroke_id']))),
            historical_masks=np.unique(paths[5].get('visibility_mask',np.full(len(paths[5]['face']),32))).tolist(),new_mask=32,
            operation='Same saved -25-degree style regenerated with owner-only capsule support; not an angle-edit gain.')
    for field in ('source_file','binding_file'):link[field]=os.path.relpath((asset/link[field]).resolve(),out)
    meta['original']['original_ply']=link['source_file'];meta['selected_region']=region
    link['parent']=parent;link['editable_proxy_regions']=[4,5]
    link['path_source_certificate']='None transferred: unit004 sparse certificate remains attached to its original asset.'
    js(out/'asset.json',meta);js(out/'LINKED_ASSET.json',link);seal(out);load_preset(out)
    for r in paths:
        if r!=region or not regenerate:
            if sha(asset/f'region_{r}.npz')!=sha(out/f'region_{r}.npz'):raise AssertionError('non-target path file changed')
    return out

def source_strength(binding,region,mix):
    check_region(region)
    if isinstance(mix,bool) or not np.isfinite(mix) or not 0<=mix<=1:raise ValueError('mix must be finite in [0,1]')
    return region_strength(binding,region)*mix

def save_control(asset,out,region,mix,color):
    check_region(region);asset=Path(asset).resolve();_,_,_,link,b=load_asset(asset)
    color=np.asarray(color,float)
    if color.shape!=(3,) or not np.isfinite(color).all() or (color<0).any() or (color>1).any():raise ValueError('RGB must be three finite values in [0,1]')
    strength=source_strength(b,region,mix);out=runtime.configure_output(out)
    np.savez_compressed(out/'WEIGHTS.npz',source_index=b['source_index'],strength=strength)
    record=dict(schema='chair_original_region_color_v1',region=region,mix=float(mix),color=color.tolist(),source_count=link['source_count'],
        source_sha256=link['source_sha256'],binding_sha256=link['binding_sha256'],weights_sha256=sha(out/'WEIGHTS.npz'),
        selected_rows=int((strength>0).sum()),unknown_rows=int(b['unknown'].sum()),
        rule='mix * membership[:,region] where region_id==region and not UNKNOWN; complete original-row universe retained',
        scope='Saved original-GS evaluated-color override. Region evidence only, not per-path attachment or semantic probabilities. No selection by camera.')
    js(out/'CONTROL.json',record);load_control(asset,out)
    return out

def load_control(asset,control):
    control=Path(control);m=json.loads((control/'CONTROL.json').read_text())
    if m['schema']!='chair_original_region_color_v1' or sha(control/'WEIGHTS.npz')!=m['weights_sha256']:raise ValueError('control checksum/schema mismatch')
    _,_,_,link,b=load_asset(asset)
    for key in ('source_count','source_sha256','binding_sha256'):
        if m[key]!=link[key]:raise ValueError('source control identity mismatch')
    color=np.asarray(m['color'],float)
    if color.shape!=(3,) or not np.isfinite(color).all() or (color<0).any() or (color>1).any():raise ValueError('invalid control color')
    d=npz(control/'WEIGHTS.npz')
    np.testing.assert_array_equal(d['source_index'],b['source_index'])
    np.testing.assert_array_equal(d['strength'],source_strength(b,m['region'],m['mix']))
    return d,m

def control_query(asset,control,ids):
    d,m=load_control(asset,control);_,_,_,_,b=load_asset(asset)
    ids=np.asarray(ids,np.int64)
    if (ids<0).any() or (ids>=m['source_count']).any():raise ValueError('ID outside original row universe')
    return dict(control=m,rows=[dict(source_index=int(i),region_id=int(b['region_id'][i]),unknown=bool(b['unknown'][i]),
        membership=float(b['membership'][i,m['region']]),applied_strength=float(d['strength'][i])) for i in ids])

def render_control(asset,control,out,camera,reference=None):
    import base_model as base
    from link_renderer import Renderer,validate_trace
    from membership import evaluated_tint_copy
    from render import render,RenderCache
    started=time.monotonic();asset=Path(asset).resolve();weights,m=load_control(asset,control)
    mesh,paths,meta,link,b=load_asset(asset);out=runtime.configure_output(out)
    a=base.load_source((asset/link['source_file']).resolve(),link['source_sha256']);a['source_index']=np.arange(m['source_count'],dtype=np.int64)
    original=source_hashes(a);engine=Renderer(out/'build')
    # Fixed native-pixel lattice across the entire frame, including background;
    # no visible-region selection and no new path-support claim.
    xy=np.array([(x,y) for y in range(0,camera['height'],8) for x in range(0,camera['width'],8)],np.int32)
    source,trace=engine.render(a,camera,xy=xy,strength=weights['strength'])
    proof=validate_trace(a,camera,xy,source,trace)
    high,_=engine.render(evaluated_tint_copy(a,camera,weights['strength'],m['color']),camera)
    for key in ('alpha','median_camera_z','center_depth_proxy','expected_camera_z'):np.testing.assert_array_equal(source[key],high[key])
    ids=trace['source_index'];sid=trace['sample_index'];w=trace['weight'];colors=base.source_colors(a,camera)
    effect=w[:,None]*weights['strength'][ids,None]*(np.asarray(m['color'])-colors[ids])
    expected=np.stack([np.bincount(sid,effect[:,j],minlength=len(xy)) for j in range(3)],1)
    x,y=xy.T;err=float(np.max(np.abs(expected-(high['rgb']-source['rgb'])[y,x])));assert err<1e-6
    support=np.bincount(sid,w*weights['strength'][ids],minlength=len(xy))
    serr=float(np.max(np.abs(support-source['contribution'][y,x])));assert serr<1e-6
    proxy=render(mesh,paths,meta['styles'],camera,2,dict(contours_visible=True,contour_strength=1.),RenderCache())
    frames=dict(source=source['rgb'],highlight=high['rgb'],source_alpha=source['alpha'],source_depth=source['median_camera_z'],
        region_contribution=source['contribution'],regions=proxy['regions'])
    equal=None
    if reference is not None:
        old=npz(Path(reference)/'FRAME.npz');equal={k:bool(np.array_equal(v,old[k],equal_nan=True)) for k,v in frames.items()};assert all(equal.values())
    np.savez_compressed(out/'FRAME.npz',**frames);np.savez_compressed(out/'TRACE.npz',xy=xy,**trace)
    for key in ('source','highlight','region_contribution'):png(out/(key+'.png'),frames[key])
    assert original==source_hashes(a)
    record=dict(camera=camera,control=m,control_sha256=sha(Path(control)/'CONTROL.json'),source_array_hashes=original,
        source_arrays_unchanged=True,alpha_depth_unchanged=True,trace=proof,delta_reconstruction_error=err,support_error=serr,
        source_change=edit_metrics(frames['source'],frames['highlight'],frames['regions'],m['region']),
        sampled_exposed_selected_ids=int(len(np.unique(ids[weights['strength'][ids]>0]))),
        exposure_scope='Fixed 8-pixel lattice; selected kernel exposure here is sampled, not full-image visibility or path ownership',
        full_image_effect_mass=float(source['contribution'].sum()),cold_original_GS=True,reload_comparison=equal,seconds=time.monotonic()-started,
        files={f.name:sha(f) for f in out.iterdir() if f.is_file()})
    js(out/'RENDER_RECEIPT.json',record)
    print(json.dumps(dict(view=camera['view'],selected_rows=m['selected_rows'],delta_error=err,seconds=record['seconds'])),flush=True)

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    for name in ('prepare','edit','render','source-save','source-render','query'):
        q=sub.add_parser(name);q.add_argument('--asset',type=Path,required=True)
        if name!='query':q.add_argument('--out',type=Path,required=True)
        if name in ('edit','source-save'):q.add_argument('--region',type=int,choices=[4,5],required=True)
        if name=='edit':
            for key in ('angle','spacing','length'):q.add_argument('--'+key,type=float)
        if name=='source-save':
            q.add_argument('--mix',type=float,default=.5);q.add_argument('--color',type=float,nargs=3,default=[.02,.4,1.])
        if name in ('render','source-render'):
            q.add_argument('--camera',type=Path,required=True);q.add_argument('--reference',type=Path)
        if name in ('source-render','query'):q.add_argument('--control',type=Path,required=True)
        if name=='query':q.add_argument('--ids',type=int,nargs='+',required=True)
    a=p.parse_args()
    if a.command=='prepare':part_edit(a.asset,a.out,5,{},True)
    elif a.command=='edit':
        changes={k:getattr(a,k) for k in ('angle','spacing','length') if getattr(a,k) is not None}
        if not changes:p.error('provide angle, spacing or length')
        part_edit(a.asset,a.out,a.region,changes)
    elif a.command=='source-save':save_control(a.asset,a.out,a.region,a.mix,a.color)
    elif a.command=='query':print(json.dumps(control_query(a.asset,a.control,a.ids),indent=2))
    else:
        c=json.loads(a.camera.read_text())
        if a.command=='render':render_whole(a.asset,a.out,c,a.reference)
        else:render_control(a.asset,a.control,a.out,c,a.reference)
if __name__=='__main__':main()
