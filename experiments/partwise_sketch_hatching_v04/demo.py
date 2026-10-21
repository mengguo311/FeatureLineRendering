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
from hatching import generate_region,validate_style
from render import render

def load_asset(path):
    path=Path(path);meta=json.loads((path/'asset.json').read_text())
    if sha(path/'mesh.npz')!=meta['mesh_sha256']:raise ValueError('proxy checksum mismatch')
    with np.load(path/'mesh.npz') as d:mesh=mesh_data(d['vertices'],d['faces'],d.get('face_regions'))
    strokes={}
    for region in (1,2,3):
        with np.load(path/f'region_{region}.npz') as d:strokes[region]={k:d[k] for k in d.files}
        s=strokes[region]
        if not len(s['points']) or not np.isfinite(s['points']).all():raise ValueError('empty or invalid region paths')
        if ((s['face']<0)|(s['face']>=len(mesh['faces']))).any():raise ValueError('bad face anchor')
        if not np.all(mesh['regions'][s['face']]==region):raise ValueError('region ownership mismatch')
        reconstructed=np.einsum('nij,njk->nik',s['bary'],mesh['tri'][s['face']])
        if np.max(np.abs(reconstructed-s['points']))>1e-9:raise ValueError('anchor mismatch')
    return mesh,strokes,meta

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
        data,stat=generate_region(mesh,region,p['styles'][str(region)])
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
    mesh,strokes,meta=load_asset(asset);output=new_output(output)
    for p in Path(asset).iterdir():
        if p.is_file():shutil.copy2(p,output/p.name)
    old_style=dict(meta['styles'][str(region)])
    style=dict(old_style);style.update(changes);validate_style(style)
    geometry_changed=any(style[k]!=old_style[k] for k in ('angle','spacing','length'))
    if geometry_changed:
        data,stat=generate_region(mesh,region,style)
        np.savez_compressed(output/f'region_{region}.npz',**data);meta['statistics'][str(region)]=stat
    meta['styles'][str(region)]=style
    meta['edit']=dict(region=region,changes=changes,geometry_changed=geometry_changed,
                       target_path_revision='regenerated' if geometry_changed else 'unchanged',
                       parent_asset_sha256=sha(Path(asset)/'asset.json'),utc=now())
    js(output/'asset.json',meta)
    print(json.dumps(dict(asset=str(output),edit=meta['edit'])),flush=True)

def save_frame(output,name,mesh,strokes,meta,c):
    t=time.monotonic();r=render(mesh,strokes,meta['styles'],c)
    for key in ('image','hatch','contour','proxy','region_rgb'):
        Image.fromarray(np.uint8(np.clip(r[key],0,1)*255+.5)).save(output/f'{name}_{key}.png')
    arrays={k:r[k] for k in ('image','hatch','contour','regions','depth')}
    arrays.update({f'layer_{k}':v for k,v in r['layers'].items()})
    np.savez_compressed(output/f'{name}_arrays.npz',**arrays)
    record=dict(camera=c,seconds=time.monotonic()-t,diagnostics=r['diagnostics'],bounds=r['bounds'],
                nonwhite_pixels=int((r['image']<.99).sum()))
    js(output/f'{name}.json',record);print(json.dumps(dict(frame=name,**record)),flush=True)
    return record

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['build','create','edit','render'])
    p.add_argument('--scene',default='chair');p.add_argument('--unit',type=Path);p.add_argument('--asset',type=Path)
    p.add_argument('--output',required=True,type=Path);p.add_argument('--region','--part',type=int,choices=[1,2,3])
    for name in ('angle','spacing','length','width'):p.add_argument('--'+name,type=float)
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
    elif a.command=='edit':
        if not a.asset or not a.region:p.error('edit requires --asset and --region')
        changes={k:getattr(a,k) for k in ('angle','spacing','length','width') if getattr(a,k) is not None}
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
