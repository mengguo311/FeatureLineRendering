"""Saved Chair region4 editor: original-GS paper plus source-gated proxy ink."""
import runtime
from runtime import sha,js
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import time
import numpy as np
from geometry import mesh_data,orbit_camera
from hatching import generate_region,validate_style
from membership import load_binding
from hybrid import region_strength,paper_copy,compose

SOURCE_SHA='13e4ecc9ffe9c5ae2a0656e2e5c56a737cfdc90a62ad04799db3c46b0b442f5d'
SAMPLES=[[x,y] for y in (160,192,224,256) for x in (128,160,192,224)]+[[0,0]]

def npz(path):
    with np.load(path,allow_pickle=False) as z:return {k:z[k] for k in z.files}

def seal(asset):
    js(asset/'FILES.json',{p.name:sha(p) for p in sorted(asset.iterdir()) if p.is_file() and p.name!='FILES.json'})

def validate_paths(mesh,paths,region):
    n=len(paths['face'])
    if n==0 or paths['points'].shape!=(n,2,3) or paths['bary'].shape!=(n,2,3):raise ValueError('invalid path shape')
    if not np.isfinite(paths['points']).all() or not np.isfinite(paths['bary']).all():raise ValueError('nonfinite paths')
    if (paths['face']<0).any() or (paths['face']>=len(mesh['faces'])).any():raise ValueError('bad face index')
    if not (mesh['regions'][paths['face']]==region).all():raise ValueError('path escaped region')
    if paths['bary'].min() < -1e-8 or paths['bary'].max()>1+1e-8:raise ValueError('bad barycentric range')
    np.testing.assert_allclose(paths['bary'].sum(-1),1.,atol=1e-8,rtol=0)
    np.testing.assert_allclose(paths['points'],np.einsum('nij,njk->nik',paths['bary'],mesh['tri'][paths['face']]),atol=1e-9,rtol=0)

def load_asset(asset):
    asset=Path(asset).resolve()
    for name,h in json.loads((asset/'FILES.json').read_text()).items():
        if Path(name).name!=name or sha(asset/name)!=h:raise ValueError('asset file mismatch: '+name)
    meta=json.loads((asset/'asset.json').read_text());link=json.loads((asset/'LINKED_ASSET.json').read_text())
    if link['schema']!='chair_linked_asset_v08' or link['source_sha256']!=SOURCE_SHA or link['source_count']!=256690:raise ValueError('source identity mismatch')
    if not np.isfinite(link['paper_effect']) or not 0<=link['paper_effect']<=1:raise ValueError('invalid paper effect')
    binding=(asset/link['binding_file']).resolve()
    if sha(binding)!=link['binding_sha256']:raise ValueError('binding hash mismatch')
    b,_=load_binding(binding,link['source_sha256'],link['source_count'])
    weights=npz(asset/'SOURCE_LINK.npz');s=region_strength(b)
    np.testing.assert_array_equal(weights['source_index'],np.arange(link['source_count']))
    for k in ('paper_strength','ink_strength'):np.testing.assert_array_equal(weights[k],s)
    np.testing.assert_array_equal(weights['unknown'],b['unknown'])
    raw=npz(asset/'mesh.npz');mesh=mesh_data(raw['vertices'],raw['faces'],raw['face_regions'])
    if sha(asset/'mesh.npz')!=meta['mesh_sha256']:raise ValueError('mesh hash mismatch')
    strokes={}
    for k in meta['regions']:
        r=int(k);validate_style(meta['styles'][k]);strokes[r]=npz(asset/f'region_{r}.npz');validate_paths(mesh,strokes[r],r)
    if link['visibility_policy']=='owner_only':np.testing.assert_array_equal(strokes[4]['visibility_mask'],16)
    return mesh,strokes,meta,link,b

def initialize(legacy,data,out):
    legacy=Path(legacy).resolve();data=Path(data).resolve();out=runtime.configure_output(out)
    for f in legacy.iterdir():
        if f.is_file():shutil.copy2(f,out/f.name)
    meta=json.loads((out/'asset.json').read_text());old=npz(out/'region_4.npz')
    masks=np.unique(old.get('visibility_mask',np.full(len(old['face']),16))).tolist()
    normalized={**old,'visibility_mask':np.full(len(old['face']),16,np.uint64)}
    np.savez_compressed(out/'region_4.npz',**normalized)
    binding=data/'SOURCE_BINDING.npz';b,_=load_binding(binding,SOURCE_SHA,256690);s=region_strength(b)
    np.savez_compressed(out/'SOURCE_LINK.npz',source_index=b['source_index'],paper_strength=s,ink_strength=s,unknown=b['unknown'])
    meta['original']['original_ply']=os.path.relpath(data/'source.ply',out)
    meta['original'].pop('input_directory',None)
    meta['linked_scope']='Only seat region4 is composited over full original GS. Other proxy region files are retained for future edits, not displayed here.'
    js(out/'asset.json',meta)
    link=dict(schema='chair_linked_asset_v08',source_file=os.path.relpath(data/'source.ply',out),source_sha256=SOURCE_SHA,source_count=256690,
        binding_file=os.path.relpath(binding,out),binding_sha256=sha(binding),unknown_rows=int(b['unknown'].sum()),
        paper_effect=1.,paper_color=[.95,.95,.95],ink_color=.03,region=4,active_regions=[4],visibility_policy='owner_only',
        identity_revision='historical geometry; visibility normalization only',parent=None,
        normalization=dict(historical_path_sha256=sha(legacy/'region_4.npz'),old_masks=masks,new_mask=16,geometry_and_stroke_ids_unchanged=True,
            scope='Common v08 baseline preparation. This cap clipping change is not a spacing-edit gain.'),
        scope='Original PLY zero-based rows; authored region evidence, not semantic probabilities. Regional alpha*T gating is not per-path ownership; proxy ink is not native Gaussian ink.')
    js(out/'LINKED_ASSET.json',link);seal(out);load_asset(out)
    return out

def edit_asset(asset,out,changes,paper_effect=None):
    asset=Path(asset).resolve();mesh,strokes,meta,link,_=load_asset(asset)
    if set(changes)-{'angle','spacing','length'}:raise ValueError('only angle, spacing, length supported for this region4 editor')
    style={**meta['styles']['4'],**changes};validate_style(style)
    effect=link['paper_effect'] if paper_effect is None else paper_effect
    if not np.isfinite(effect) or not 0<=effect<=1:raise ValueError('paper-effect must be finite in [0,1]')
    regenerate=any(style[k]!=meta['styles']['4'][k] for k in changes)
    out=runtime.configure_output(out)
    for f in asset.iterdir():
        if f.is_file() and f.name!='FILES.json':shutil.copy2(f,out/f.name)
    parent=sha(asset/'FILES.json')
    if regenerate:
        paths,stat=generate_region(mesh,4,style)
        if not len(paths['face']):raise ValueError('edited style has no surface support')
        key=hashlib.sha256(json.dumps([parent,style],sort_keys=True).encode()).hexdigest()
        namespace=(int(key[:10],16)+1)*1_000_000
        _,inverse=np.unique(paths['stroke_id'],return_inverse=True)
        if inverse.max()>=1_000_000:raise ValueError('path namespace overflow')
        paths['stroke_id']=namespace+inverse.astype(np.int64)
        paths['visibility_mask']=np.full(len(paths['face']),16,np.uint64)
        paths['layer_id']=np.zeros(len(paths['face']),np.uint8)
        if np.intersect1d(paths['stroke_id'],strokes[4]['stroke_id']).size:raise ValueError('identity collision')
        validate_paths(mesh,paths,4);np.savez_compressed(out/'region_4.npz',**paths)
        meta['statistics']['4']=stat;link['identity_revision']=key
    meta['styles']['4']=style
    meta['edit']=dict(region=4,changes=changes,paper_effect=effect,regenerated=regenerate,parent_asset_sha256=parent,
        scope='Region regeneration includes boundary-start arclength phase changes; no isolated sampling-quality claim.')
    for field in ('source_file','binding_file'):
        link[field]=os.path.relpath((asset/link[field]).resolve(),out)
    meta['original']['original_ply']=link['source_file']
    link.update(paper_effect=float(effect),parent=parent)
    js(out/'asset.json',meta);js(out/'LINKED_ASSET.json',link);seal(out);load_asset(out)
    return out

def source_hashes(a):
    return {k:hashlib.sha256(np.ascontiguousarray(a[k]).tobytes()).hexdigest() for k in ('means','covariance','precision','opacity','SH','source_index')}

def png(path,array):
    from PIL import Image
    a=np.asarray(array)
    if a.ndim==2:a=np.repeat(a[:,:,None],3,axis=2)
    Image.fromarray(np.uint8(np.clip(a,0,1)*255+.5)).save(runtime.output_guard(path))

def render_asset(asset,out,camera,reference=None,legacy=None):
    import base_model as base
    from link_renderer import Renderer,validate_trace
    from render import render as proxy_render
    started=time.monotonic();asset=Path(asset).resolve()
    mesh,paths,meta,link,b=load_asset(asset);out=runtime.configure_output(out)
    a=base.load_source((asset/link['source_file']).resolve(),link['source_sha256'])
    a['source_index']=np.arange(len(a['means']),dtype=np.int64)
    before=source_hashes(a);s=region_strength(b)
    xy=np.asarray(SAMPLES,np.int32)
    # Explicit non-default image size scales the fixed grid without selecting by output.
    xy=np.unique(np.clip(np.rint(xy*(camera['width']/384)),0,camera['width']-1).astype(np.int32),axis=0)
    renderer=Renderer(out/'build')
    source,trace=renderer.render(a,camera,xy=xy,strength=s)
    paper,_=renderer.render(paper_copy(a,camera,s*link['paper_effect'],link['paper_color']),camera)
    proof=validate_trace(a,camera,xy,source,trace)
    sid=trace['sample_index'];ids=trace['source_index'];w=trace['weight'];n=len(xy)
    support=np.bincount(sid,w*s[ids],minlength=n)
    color=base.source_colors(a,camera)
    delta=link['paper_effect']*s[ids,None]*(np.asarray(link['paper_color'])-color[ids])
    expected=np.stack([np.bincount(sid,w*delta[:,j],minlength=n) for j in range(3)],1)
    xx,yy=xy.T
    support_error=float(np.max(np.abs(support-source['contribution'][yy,xx])))
    delta_error=float(np.max(np.abs(expected-(paper['rgb']-source['rgb'])[yy,xx])))
    assert support_error<1e-6 and delta_error<1e-6,(support_error,delta_error)
    np.testing.assert_array_equal(source['alpha'],paper['alpha'])
    h=proxy_render(mesh,{4:paths[4]},meta['styles'],camera,2,meta.get('display'))
    hybrid,ink_alpha=compose(paper['rgb'],h['layers'][4],source['contribution'],True,ink_color=link['ink_color'])
    frames=dict(source=source['rgb'],paper=paper['rgb'],support=source['contribution'],source_alpha=source['alpha'],
        ink=h['layers'][4],linked_ink=ink_alpha,hybrid=hybrid,regions=h['regions'],proxy_depth=h['depth'])
    if legacy is not None:
        old=npz(Path(legacy)/'region_4.npz')
        oh=proxy_render(mesh,{4:old},meta['styles'],camera,2,meta.get('display'))
        historical,ha=compose(paper['rgb'],oh['layers'][4],source['contribution'],True,ink_color=link['ink_color'])
        frames.update(historical_hybrid=historical,historical_ink=oh['layers'][4],historical_linked_ink=ha)
    equal=None
    if reference is not None:
        ref=npz(Path(reference)/'FRAME.npz')
        equal={k:dict(array_equal=bool(np.array_equal(frames[k],v)),max_error=float(np.max(np.abs(frames[k].astype(float)-v.astype(float)))))
               for k,v in ref.items() if k!='proxy_depth'}
        # Depth contains infinities for background; exact equality is the meaningful check.
        equal['proxy_depth']=dict(array_equal=bool(np.array_equal(frames['proxy_depth'],ref['proxy_depth'])))
        assert all(v['array_equal'] for v in equal.values()),equal
    assert source_hashes(a)==before
    np.savez_compressed(out/'FRAME.npz',**frames)
    np.savez_compressed(out/'TRACE.npz',xy=xy,**trace)
    np.savez_compressed(out/'SOURCE_WITNESS.npz',xy=xy,expected_paper_delta=expected,reconstructed_support=support,
        target_pixel=h['regions'][yy,xx]==4,source_alpha=source['alpha'][yy,xx],selected_mass=support)
    for key in ('source','paper','hybrid','support'):png(out/(key+'.png'),frames[key])
    png(out/'ink.png',1-frames['ink']);png(out/'linked_ink.png',1-frames['linked_ink'])
    if legacy is not None:png(out/'historical_hybrid.png',frames['historical_hybrid'])
    receipt=dict(camera=camera,asset_manifest_sha256=sha(asset/'FILES.json'),source_sha256=link['source_sha256'],source_count=len(a['means']),
        source_array_hashes=before,source_arrays_unchanged=True,unknown_rows=int(b['unknown'].sum()),selected_rows=int((s>0).sum()),
        trace_validation=proof,support_reconstruction_max_error=support_error,paper_delta_reconstruction_max_error=delta_error,
        trace_samples=len(xy),target_samples=int((h['regions'][yy,xx]==4).sum()),unsupported_samples=int((support==0).sum()),
        original_source_ids_with_events=int(len(np.unique(ids))),scope=link['scope'],cold_original_GS=True,
        parameters=meta['styles']['4'],paper_effect=link['paper_effect'],paths_sha256=sha(asset/'region_4.npz'),
        reload_comparison=equal,seconds=time.monotonic()-started,actual_backend='CPU EWA fullSH3; proxy surface ink; no native CUDA certification',
        files={f.name:sha(f) for f in out.iterdir() if f.is_file()})
    js(out/'RENDER_RECEIPT.json',receipt)
    print(json.dumps(dict(out=str(out),seconds=receipt['seconds'],target_samples=receipt['target_samples'],reload_equal=equal is not None)),flush=True)

def query(asset,ids):
    _,_,_,link,b=load_asset(asset);s=region_strength(b);rows=[]
    for i in ids:
        if not 0<=i<link['source_count']:raise ValueError('source ID outside original row universe')
        rows.append(dict(source_index=i,region_id=int(b['region_id'][i]),unknown=bool(b['unknown'][i]),reason=str(b['reason'][i]),
            membership=b['membership'][i],exposure=float(b['exposure'][i]),distinct_views=int(b['distinct_views'][i]),
            paper_strength=float(s[i]*link['paper_effect']),ink_strength=float(s[i])))
    return dict(source_sha256=link['source_sha256'],source_count=link['source_count'],rows=rows,scope=link['scope'])

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    e=sub.add_parser('edit');e.add_argument('--asset',type=Path,required=True);e.add_argument('--out',type=Path,required=True)
    for k in ('angle','spacing','length','paper-effect'):e.add_argument('--'+k,type=float)
    r=sub.add_parser('render');r.add_argument('--asset',type=Path,required=True);r.add_argument('--out',type=Path,required=True)
    r.add_argument('--azimuth',type=float,default=61.);r.add_argument('--elevation',type=float,default=24.);r.add_argument('--distance',type=float,default=5.1);r.add_argument('--size',type=int,default=384)
    r.add_argument('--camera',type=Path);r.add_argument('--reference',type=Path);r.add_argument('--legacy',type=Path)
    q=sub.add_parser('query');q.add_argument('--asset',type=Path,required=True);q.add_argument('--ids',type=int,nargs='+',required=True)
    a=p.parse_args()
    if a.command=='edit':
        changes={k:getattr(a,k) for k in ('angle','spacing','length') if getattr(a,k) is not None}
        if not changes and a.paper_effect is None:p.error('supply an edit parameter')
        edit_asset(a.asset,a.out,changes,a.paper_effect);print(a.out)
    elif a.command=='query':print(json.dumps(query(a.asset,a.ids),indent=2,ensure_ascii=False,default=runtime.json_default))
    else:
        if not 64<=a.size<=1024 or not np.isfinite([a.azimuth,a.elevation,a.distance]).all() or a.distance<=0:p.error('invalid camera')
        c=json.loads(a.camera.read_text()) if a.camera else orbit_camera(a.azimuth,a.elevation,a.distance,a.size)
        render_asset(a.asset,a.out,c,a.reference,a.legacy)

if __name__=='__main__':main()
