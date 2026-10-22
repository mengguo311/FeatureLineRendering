"""Runnable partwise NPR demo: create, edit, render, orbit and zoom saved assets."""
import runtime
from runtime import js,sha,output_guard,now
from pathlib import Path
import argparse
import json
import shutil
import time
import numpy as np
from PIL import Image
from geometry import mesh_data,orbit_camera,resize_camera
from hatching import generate_region,generate_layers,add_cross_layer,layer_ids,validate_style,visibility_masks
from render import render
from display_settings import validate_display

def load_asset(path):
    path=Path(path);meta=json.loads((path/'asset.json').read_text())
    validate_display(meta.get('display'))
    if sha(path/'mesh.npz')!=meta['mesh_sha256']:raise ValueError('proxy checksum mismatch')
    with np.load(path/'mesh.npz') as d:mesh=mesh_data(d['vertices'],d['faces'],d.get('face_regions'))
    strokes={}
    region_list=sorted(int(k) for k in meta['regions'])
    if set(region_list)!=set(np.unique(mesh['regions'])) or set(meta['styles'])!=set(meta['regions']):
        raise ValueError('saved region metadata and mesh labels disagree')
    for history in meta.get('region_history',[]):
        filename=history['face_ids_file']
        if Path(filename).name!=filename or sha(path/filename)!=history['face_ids_sha256']:
            raise ValueError('saved selection checksum mismatch')
    for region in region_list:
        validate_style(meta['styles'][str(region)])
        with np.load(path/f'region_{region}.npz') as d:strokes[region]={k:d[k] for k in d.files}
        validate_paths(mesh,strokes[region],meta['styles'][str(region)],region,region_list)
    from region_restore import validate_origins
    validate_origins(path,mesh,meta)
    return mesh,strokes,meta

def validate_paths(mesh,s,style,region,region_list):
    """Shared anchor/ownership contract for current and restorable saved paths."""
    n=len(s['points'])
    if (not n or s['points'].shape!=(n,2,3) or s['bary'].shape!=(n,2,3) or
        not np.isfinite(s['points']).all() or not np.isfinite(s['bary']).all()):raise ValueError('empty or invalid region paths')
    if s['face'].shape!=(n,) or s['face'].dtype.kind not in 'iu' or ((s['face']<0)|(s['face']>=len(mesh['faces']))).any():raise ValueError('bad face anchor')
    if s['stroke_id'].shape!=(n,) or s['stroke_id'].dtype.kind not in 'iu' or (s['stroke_id']<0).any():raise ValueError('invalid stroke IDs')
    if np.min(s['bary'])< -1e-8 or np.max(s['bary'])>1+1e-8 or not np.allclose(s['bary'].sum(-1),1,rtol=0,atol=1e-8):raise ValueError('invalid barycentric coordinates')
    if not np.all(mesh['regions'][s['face']]==region):raise ValueError('region ownership mismatch')
    if 'visibility_mask' in s:
        support=s['visibility_mask'];allowed=np.uint64(sum(1 << r for r in region_list))
        if support.shape!=(n,) or support.dtype.kind not in 'iu' or (support<0).any():raise ValueError('invalid capsule visibility masks')
        support=support.astype(np.uint64)
        if ((support & ~allowed)!=0).any() or ((support & np.uint64(1 << region))==0).any():raise ValueError('capsule visibility masks must include owner and only existing regions')
    reconstructed=np.einsum('nij,njk->nik',s['bary'],mesh['tri'][s['face']])
    if np.max(np.abs(reconstructed-s['points']))>1e-9:raise ValueError('anchor mismatch')
    ids=layer_ids(s)
    if ids.shape!=(n,) or not np.isin(ids,[0,1]).all() or not (ids==0).any():raise ValueError('invalid stroke layer IDs')
    if style.get('cross_enabled',False) and not (ids==1).any():raise ValueError('enabled cross layer is missing saved paths')
    if (ids==1).any() and np.intersect1d(s['stroke_id'][ids==0],s['stroke_id'][ids==1]).size:raise ValueError('stroke IDs overlap between layers')

def new_output(path):
    path=output_guard(path)
    if path.exists() and any(path.iterdir()):raise FileExistsError(f'output is not empty: {path}')
    path.mkdir(parents=True,exist_ok=True)
    return path

def create(unit,output,scene):
    p=json.loads((unit/'PROTOCOL.json').read_text())
    if p['scene']!=scene:raise ValueError('scene/protocol mismatch')
    output=new_output(output);shutil.copy2(unit/'proxy/mesh.npz',output/'mesh.npz')
    with np.load(output/'mesh.npz') as d:mesh=mesh_data(d['vertices'],d['faces'],d.get('face_regions'))
    stats={}
    for region in (1,2,3):
        data,stat=generate_layers(mesh,region,p['styles'][str(region)])
        np.savez_compressed(output/f'region_{region}.npz',**data);stats[str(region)]=stat
    meta=dict(scene=scene,created_utc=now(),version=1,styles=p['styles'],regions=p['regions'],
              region_provenance=p['region_provenance'],geometry=p['geometry'],original=p['original'],
              mesh_sha256=sha(output/'mesh.npz'),protocol_sha256=sha(unit/'PROTOCOL.json'),
              cameras=p['static_cameras'],orbit=p['orbit'],zoom=p['zoom'],statistics=stats,
              region_rule=p.get('region_rule',dict(axis='z',cuts=[-.35,.20])),
              viewer_camera=p.get('viewer_camera',dict(azimuth=17,elevation=20,distance=4.7)),
              identities='proxy face IDs and region/path IDs; none is an original Gaussian source index')
    js(output/'asset.json',meta)
    print(json.dumps(dict(asset=str(output),statistics=stats)),flush=True)

def edit(asset,output,region,changes):
    mesh,strokes,meta=load_asset(asset)
    if str(region) not in meta['styles']:raise ValueError('unknown region')
    old_style=dict(meta['styles'][str(region)])
    style=dict(old_style);style.update(changes);validate_style(style)
    geometry_changed=any(style.get(k)!=old_style.get(k) for k in ('angle','spacing','length','plane'))
    old=strokes[region];ids=layer_ids(old);cached_cross=bool((ids==1).any())
    cross_changed=any(style.get(k,default)!=old_style.get(k,default) for k,default in
                      [('angle',0.),('length',.22),('plane',None),('cross_angle',60.),('cross_spacing',.06)])
    regenerate_cross=(cached_cross and cross_changed) or (style.get('cross_enabled',False) and not cached_cross)
    regenerated=[];data=None;stat=dict(meta['statistics'][str(region)])
    if geometry_changed:
        base,stat=generate_region(mesh,region,style);regenerated.append(0)
        if not len(base['points']):raise ValueError('base layer has no proxy support at this spacing')
    else:base={k:v[ids==0] for k,v in old.items() if k!='layer_id'}
    if regenerate_cross:
        data,cross=add_cross_layer(mesh,region,style,base)
        stat['cross_layer']=cross;regenerated.append(1)
    elif geometry_changed:
        data=base
        if cached_cross:
            data={k:np.concatenate([base[k],old[k][ids==1]]) for k in base}
            if 'visibility_mask' in old:
                data['visibility_mask']=np.concatenate([visibility_masks(base,region),visibility_masks(old,region)[ids==1]])
            data['layer_id']=np.concatenate([np.zeros(len(base['points']),np.uint8),np.ones(int((ids==1).sum()),np.uint8)])
            stat['cross_layer']=meta['statistics'][str(region)].get('cross_layer',{})
    output=new_output(output)
    for p in Path(asset).iterdir():
        if p.is_file():shutil.copy2(p,output/p.name)
    if data is not None:
        np.savez_compressed(output/f'region_{region}.npz',**data);meta['statistics'][str(region)]=stat
    if cached_cross or regenerate_cross:
        meta['version']=max(3,meta.get('version',1))
        meta['layer_identity']='layer0=legacy base; layer1=optional cross; IDs disjoint, coordinates revisioned on angle/spacing/length edits; none are Gaussian IDs'
    meta['styles'][str(region)]=style
    meta['edit']=dict(region=region,changes=changes,geometry_changed=bool(regenerated),regenerated_layers=regenerated,
                       target_path_revision='regenerated layers '+str(regenerated) if regenerated else 'unchanged',
                       parent_asset_sha256=sha(Path(asset)/'asset.json'),utc=now())
    js(output/'asset.json',meta)
    print(json.dumps(dict(asset=str(output),edit=meta['edit'])),flush=True)

def set_display(asset,output,changes):
    """Copy an asset and save display only; all geometry/path bytes are retained."""
    _,_,meta=load_asset(asset)
    settings=validate_display(dict(validate_display(meta.get('display')),**changes))
    output=new_output(output)
    for p in Path(asset).iterdir():
        if p.is_file():shutil.copy2(p,output/p.name)
    meta['display']=settings
    meta['display_edit']=dict(changes=changes,parent_asset_sha256=sha(Path(asset)/'asset.json'),utc=now(),
                              geometry_changed=False,paths_regenerated=False)
    js(output/'asset.json',meta)

def save_frame(output,name,mesh,strokes,meta,c,cache=None):
    t=time.monotonic();r=render(mesh,strokes,meta['styles'],c,display=meta.get('display'),cache=cache)
    for key in ('image','hatch','contour','proxy','region_rgb'):
        Image.fromarray(np.uint8(np.clip(r[key],0,1)*255+.5)).save(output/f'{name}_{key}.png')
    arrays={k:r[k] for k in ('image','hatch','contour','regions','depth')}
    arrays.update({f'layer_{k}':v for k,v in r['layers'].items()})
    arrays.update({f'stroke_layer_{k}':v for k,v in r['style_layers'].items()})
    np.savez_compressed(output/f'{name}_arrays.npz',**arrays)
    record=dict(camera=c,display=validate_display(meta.get('display')),seconds=time.monotonic()-t,diagnostics=r['diagnostics'],bounds=r['bounds'],
                nonwhite_pixels=int((r['image']<.99).sum()))
    if cache is not None:record['render_cache']=cache.info()
    js(output/f'{name}.json',record);print(json.dumps(dict(frame=name,**record)),flush=True)
    return record

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['build','create','author','edit','restore','display','render'])
    p.add_argument('--scene',default='chair');p.add_argument('--unit',type=Path);p.add_argument('--asset',type=Path)
    p.add_argument('--output',required=True,type=Path);p.add_argument('--region','--part',type=int)
    p.add_argument('--bounds',type=float,nargs=6,metavar=('XMIN','YMIN','ZMIN','XMAX','YMAX','ZMAX'))
    p.add_argument('--screen-rect',type=float,nargs=4,metavar=('LEFT','TOP','RIGHT','BOTTOM'))
    p.add_argument('--selection-recipe',type=Path,help='Saved multi-view add/subtract rectangle recipe')
    p.add_argument('--name',default='Manual region')
    for name in ('angle','spacing','length','width'):p.add_argument('--'+name,type=float)
    p.add_argument('--ink-strength',type=float,help='Selected-region hatch darkness [0,1], default .80; paths stay fixed')
    p.add_argument('--cross',choices=['on','off']);p.add_argument('--cross-angle',type=float);p.add_argument('--cross-spacing',type=float)
    p.add_argument('--contour-strength',type=float)
    p.add_argument('--contours',choices=['on','off'])
    p.add_argument('--view');p.add_argument('--trajectory',choices=['static','orbit','zoom'])
    p.add_argument('--azimuth',type=float,default=47);p.add_argument('--elevation',type=float,default=25)
    p.add_argument('--distance',type=float,default=4.6);p.add_argument('--size',type=int,default=512)
    a=p.parse_args()
    if a.command=='build':
        if not a.unit:p.error('build requires --unit containing a frozen protocol')
        protocol=json.loads((a.unit/'PROTOCOL.json').read_text())
        if protocol['scene']!=a.scene:p.error('scene/protocol mismatch')
        output=new_output(a.output)
        shutil.copy2(a.unit/'PROTOCOL.json',output/'PROTOCOL.json')
        from build_proxy import build
        if 'refinement' in protocol:
            raw=output/'raw_source';raw.mkdir()
            shutil.copy2(a.unit/'PROTOCOL.json',raw/'PROTOCOL.json')
            build(raw)
            from refine_proxy import build as refine_build
            refine_build(output,source_mesh=raw/'proxy/mesh.npz')
        else:
            build(output)
        asset=output/'assets/baseline';create(output,asset,a.scene)
        mesh,strokes,meta=load_asset(asset)
        destination=output/'renders/first';destination.mkdir(parents=True)
        save_frame(destination,'frame_000',mesh,strokes,meta,resize_camera(meta['cameras'][0],a.size))
    elif a.command=='create':
        if not a.unit:p.error('create requires --unit')
        create(a.unit,a.output,a.scene)
    elif a.command=='author':
        if not a.asset or not a.region or sum(x is not None for x in (a.bounds,a.screen_rect,a.selection_recipe))!=1:
            p.error('author requires --asset, --region and exactly one of --bounds, --screen-rect or --selection-recipe')
        mesh,_,meta=load_asset(a.asset)
        if meta['scene']!=a.scene:p.error('scene/asset mismatch')
        from region_tools import author_region,author_face_selection
        if a.selection_recipe is not None:
            from selection_draft import replay_recipe
            recipe=json.loads(a.selection_recipe.read_text())
            if recipe['source_region']!=a.region:p.error('recipe/source region mismatch')
            draft=replay_recipe(mesh,meta['mesh_sha256'],recipe)
            author_face_selection(a.asset,a.output,draft.face_ids,a.region,a.name,draft.provenance())
        elif a.bounds is not None:author_region(a.asset,a.output,a.bounds,a.region,a.name)
        else:
            if not 64<=a.size<=1024:p.error('--size must be between 64 and 1024')
            from screen_selection import visible_faces
            c=orbit_camera(a.azimuth,a.elevation,a.distance,a.size)
            ids,summary=visible_faces(mesh,c,a.screen_rect,a.region)
            author_face_selection(a.asset,a.output,ids,a.region,a.name,dict(operation='manual_visible_rectangle',
                camera=c,rectangle=summary['rectangle'],rule=summary['rule'],
                provenance='manual visible proxy face selection; not semantic segmentation'))
    elif a.command=='display':
        if not a.asset:p.error('display requires --asset')
        meta=json.loads((a.asset/'asset.json').read_text())
        if meta['scene']!=a.scene:p.error('scene/asset mismatch')
        changes={}
        if a.contour_strength is not None:changes['contour_strength']=a.contour_strength
        if a.contours is not None:changes['contours_visible']=a.contours=='on'
        if not changes:p.error('display requires --contour-strength or --contours')
        set_display(a.asset,a.output,changes)
    elif a.command=='restore':
        if not a.asset or not a.region:p.error('restore requires --asset and --region')
        meta=json.loads((a.asset/'asset.json').read_text())
        if meta['scene']!=a.scene:p.error('scene/asset mismatch')
        from region_restore import restore_region
        print(json.dumps(restore_region(a.asset,a.output,a.region)))
    elif a.command=='edit':
        if not a.asset or not a.region:p.error('edit requires --asset and --region')
        meta=json.loads((a.asset/'asset.json').read_text())
        if meta['scene']!=a.scene:p.error('scene/asset mismatch')
        changes={k:getattr(a,k) for k in ('angle','spacing','length','width') if getattr(a,k) is not None}
        changes.update({k:getattr(a,k) for k in ('cross_angle','cross_spacing','ink_strength') if getattr(a,k) is not None})
        if a.cross is not None:changes['cross_enabled']=a.cross=='on'
        if not changes:p.error('edit requires at least one style change')
        edit(a.asset,a.output,a.region,changes)
    else:
        if not a.asset:p.error('render requires --asset')
        if not 64<=a.size<=1024:p.error('--size must be between 64 and 1024')
        mesh,strokes,meta=load_asset(a.asset)
        if meta['scene']!=a.scene:p.error('scene/asset mismatch')
        output=new_output(a.output)
        if a.trajectory:
            cameras=meta['cameras' if a.trajectory=='static' else a.trajectory]
        elif a.view:
            cameras=[c for c in meta['cameras'] if c['view']==a.view]
            if not cameras:raise ValueError('saved view not found')
        else:cameras=[orbit_camera(a.azimuth,a.elevation,a.distance,a.size)]
        records=[]
        for i,c in enumerate(cameras):
            c=resize_camera(c,a.size)
            records.append(save_frame(output,f'frame_{i:03d}',mesh,strokes,meta,c))
        js(output/'RENDER_RECEIPT.json',dict(utc=now(),asset_sha256=sha(a.asset/'asset.json'),scene=a.scene,
                                           frame_count=len(records),frames=records,cold_loaded=True))

if __name__=='__main__':main()
