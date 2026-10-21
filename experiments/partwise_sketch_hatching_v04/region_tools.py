"""Explicit manual face selections on an immutable proxy geometry.

A world AABB selects face centroids in ONE existing style region. All faces,
including hidden sides, are selected; this is not a screen brush or semantics.
The saved face IDs are authoritative and boxes are recorded as authoring history.
"""
import runtime
from runtime import js, sha, now
from pathlib import Path
import shutil
import numpy as np
from demo import load_asset, new_output
from geometry import mesh_data
from hatching import generate_region

def select_faces(mesh,bounds,source_region):
    b=np.asarray(bounds,float)
    if b.shape!=(6,) or not np.isfinite(b).all() or (b[:3]>=b[3:]).any():
        raise ValueError('box needs six finite bounds, with min < max on every axis')
    if source_region not in mesh['regions']:raise ValueError('unknown source region')
    centers=mesh['tri'].mean(1)
    mask=(mesh['regions']==source_region)&(centers>=b[:3]).all(1)&(centers<=b[3:]).all(1)
    ids=np.flatnonzero(mask).astype(np.int32)
    if not len(ids):raise ValueError('box selects no faces in the source region')
    if mask.sum()==(mesh['regions']==source_region).sum():
        raise ValueError('box must leave some faces in the source region')
    return ids

def selection_summary(mesh,bounds,source_region):
    ids=select_faces(mesh,bounds,source_region)
    return dict(face_count=len(ids),source_face_count=int((mesh['regions']==source_region).sum()),
                source_region=int(source_region),bounds=list(map(float,bounds)),
                centroid_min=mesh['tri'][ids].mean(1).min(0).tolist(),
                centroid_max=mesh['tri'][ids].mean(1).max(0).tolist(),
                rule='world box on face centroids; includes hidden surfaces')

def path_stats(data,region):
    return dict(region=region,segments=len(data['points']),paths=len(np.unique(data['stroke_id'])),
                length_world=float(np.linalg.norm(np.diff(data['points'],axis=1),axis=2).sum()),
                construction='retained original segments and IDs outside explicitly reassigned faces; paths may be shortened at new boundary')

def author_region(asset,output,bounds,source_region,name):
    mesh,strokes,meta=load_asset(asset)
    name=str(name).strip()
    if not 1<=len(name)<=80:raise ValueError('region name must have 1 to 80 characters')
    selected=select_faces(mesh,bounds,source_region)
    region=max(strokes)+1
    if region>32:raise ValueError('demo supports at most 32 region IDs')
    labels=mesh['regions'].copy();labels[selected]=region
    new_mesh=mesh_data(mesh['vertices'],mesh['faces'],labels)
    old=strokes[source_region];keep=~np.isin(old['face'],selected)
    if not keep.any():raise ValueError('selection would leave source region without any hatch paths')
    retained={k:v[keep] for k,v in old.items()}
    style=dict(meta['styles'][str(source_region)])
    # Plane choice must follow the source style, never a newly allocated ID.
    style.setdefault('plane','xz' if source_region==3 else 'xy')
    generated,stats=generate_region(new_mesh,region,style)
    if not len(generated['points']):raise ValueError('selected faces have no hatch support at this spacing')
    output=new_output(output)
    for p in Path(asset).iterdir():
        if p.is_file():shutil.copy2(p,output/p.name)
    np.savez_compressed(output/'mesh.npz',vertices=mesh['vertices'],faces=mesh['faces'],face_regions=labels)
    np.savez_compressed(output/f'region_{source_region}.npz',**retained)
    np.savez_compressed(output/f'region_{region}.npz',**generated)
    selection_file=f'selection_{region}.npz'
    np.savez_compressed(output/selection_file,face_ids=selected,previous_region=np.full(len(selected),source_region,np.int32))
    record=dict(utc=now(),operation='manual_box_split',new_region=region,name=name,
        source_region=source_region,bounds=list(map(float,bounds)),
        face_ids_file=selection_file,face_ids_sha256=sha(output/selection_file),
        selected_faces=len(selected),parent_asset_sha256=sha(Path(asset)/'asset.json'),
        parent_mesh_sha256=meta['mesh_sha256'],
        geometry='vertices and indexed faces unchanged; only face labels changed',
        retained_source_segments=int(keep.sum()),removed_source_segments=int((~keep).sum()),
        non_target_policy='all unselected segments retain points/bary/face/stroke_id exactly; other region files copied',
        provenance='authored world-space bounds on proxy face centroids, NOT automatic semantic segmentation')
    meta['version']=2;meta['regions'][str(region)]=name;meta['styles'][str(region)]=style
    meta['statistics'][str(source_region)]=path_stats(retained,source_region)
    meta['statistics'][str(region)]=stats
    meta.setdefault('region_history',[]).append(record)
    meta['region_provenance']='Authored height regions with saved manual world-box face selections; not learned semantic parts.'
    meta['mesh_sha256']=sha(output/'mesh.npz')
    js(output/'asset.json',meta)
    print(__import__('json').dumps(dict(asset=str(output),authoring=record)),flush=True)
    return record
