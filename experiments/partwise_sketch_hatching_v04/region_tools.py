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
from hatching import generate_layers,layer_ids

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
    selected=select_faces(mesh,bounds,source_region)
    return author_face_selection(asset,output,selected,source_region,name,dict(
        operation='manual_box_split',bounds=list(map(float,bounds)),
        provenance='authored world-space bounds on proxy face centroids, NOT automatic semantic segmentation'))

def author_face_selection(asset,output,selected,source_region,name,selection):
    """Relabel faces and transfer existing segments without reflowing hatching."""
    from hatching import visibility_masks
    mesh,strokes,meta=load_asset(asset)
    name=str(name).strip()
    if not 1<=len(name)<=80:raise ValueError('region name must have 1 to 80 characters')
    raw=np.asarray(selected)
    if (raw.ndim!=1 or not len(raw) or not np.isfinite(raw).all() or
        not ((raw==np.floor(raw))&(raw>=0)&(raw<len(mesh['faces']))).all()):
        raise ValueError('selection requires valid integer proxy face IDs')
    selected=np.unique(raw).astype(np.int32)
    if source_region not in strokes or not (mesh['regions'][selected]==source_region).all():
        raise ValueError('selected faces must belong to the source region')
    if len(selected)==int((mesh['regions']==source_region).sum()):
        raise ValueError('selection must leave some faces in the source region')
    region=max(strokes)+1
    if region>32:raise ValueError('demo supports at most 32 region IDs')
    labels=mesh['regions'].copy();labels[selected]=region
    new_mesh=mesh_data(mesh['vertices'],mesh['faces'],labels)
    old=strokes[source_region];keep=~np.isin(old['face'],selected)
    if not (keep&(layer_ids(old)==0)).any():raise ValueError('selection would leave source region without any base hatch paths')
    if meta['styles'][str(source_region)].get('cross_enabled',False) and not (keep&(layer_ids(old)==1)).any():
        raise ValueError('selection would leave source region without its enabled cross hatch paths')
    # Expand saved raster support wherever the split label previously appeared.
    # This includes earlier siblings after repeated splits. Geometry/IDs stay
    # unchanged; no visibility support is inferred from spatial proximity.
    support_updates={}
    for r,paths in strokes.items():
        masks=visibility_masks(paths,r)
        affected=(masks & np.uint64(1 << source_region))!=0
        if affected.any():
            masks=masks.copy();masks[affected] |= np.uint64(1 << region)
            support_updates[r]=dict(paths,visibility_mask=masks)
    old_with_support=support_updates[source_region]
    retained={k:v[keep] for k,v in old_with_support.items()}
    style=dict(meta['styles'][str(source_region)])
    # Plane choice must follow the source style, never a newly allocated ID.
    style.setdefault('plane','xz' if source_region==3 else 'xy')
    generated={k:v[~keep] for k,v in old_with_support.items()}
    if not len(generated['points']) or not (layer_ids(generated)==0).any():
        raise ValueError('selected faces have no existing base hatch support; choose a larger patch')
    if style.get('cross_enabled',False) and not (layer_ids(generated)==1).any():
        raise ValueError('selected faces have no existing cross hatch support; choose a larger patch')
    stats=path_stats(generated,region)
    stats['construction']='Transferred parent segments, original points/bary/face/stroke IDs and capsule support; no regeneration'
    if 'cross_layer' in meta['statistics'][str(source_region)]:
        stats['cross_layer']=path_stats({k:v[layer_ids(generated)==1] for k,v in generated.items()},region)
    output=new_output(output)
    for p in Path(asset).iterdir():
        if p.is_file():shutil.copy2(p,output/p.name)
    np.savez_compressed(output/'mesh.npz',vertices=mesh['vertices'],faces=mesh['faces'],face_regions=labels)
    np.savez_compressed(output/f'region_{source_region}.npz',**retained)
    np.savez_compressed(output/f'region_{region}.npz',**generated)
    for r,data in support_updates.items():
        if r!=source_region:np.savez_compressed(output/f'region_{r}.npz',**data)
    selection_file=f'selection_{region}.npz'
    np.savez_compressed(output/selection_file,face_ids=selected,previous_region=np.full(len(selected),source_region,np.int32),
                        parent_segment_index=np.flatnonzero(~keep),parent_stroke_id=old['stroke_id'][~keep],
                        parent_layer_id=layer_ids(old)[~keep])
    record=dict(selection,utc=now(),new_region=region,name=name,
        source_region=source_region,
        face_ids_file=selection_file,face_ids_sha256=sha(output/selection_file),
        selected_faces=len(selected),parent_asset_sha256=sha(Path(asset)/'asset.json'),
        parent_mesh_sha256=meta['mesh_sha256'],
        geometry='vertices and indexed faces unchanged; only face labels changed',
        retained_source_segments=int(keep.sum()),removed_source_segments=int((~keep).sum()),
        transferred_segments=int((~keep).sum()),paths_regenerated=False,
        capsule_support_updated_regions=sorted(support_updates),
        capsule_support='Explicit per-segment current-region bitset retains original depth-tested footprint across manual splits. New generated layers use owner-only support.',
        parent_identity='selection file maps each transferred segment to parent array index, stroke ID and direction layer; stroke IDs retained, no Gaussian IDs',
        non_target_policy='all unselected segments retain points/bary/face/stroke_id exactly; only inherited sibling capsule masks can expand; unrelated files copied',
        provenance=selection.get('provenance','manual proxy face selection, NOT automatic semantic segmentation'))
    meta['version']=max(4,meta.get('version',1));meta['regions'][str(region)]=name;meta['styles'][str(region)]=style
    meta['statistics'][str(source_region)]=path_stats(retained,source_region)
    meta['statistics'][str(region)]=stats
    meta.setdefault('region_history',[]).append(record)
    meta['region_provenance']='Authored height regions with saved manual proxy face selections; not learned semantic parts.'
    meta['mesh_sha256']=sha(output/'mesh.npz')
    from region_restore import save_origin
    save_origin(output,meta,region)
    js(output/'asset.json',meta)
    print(__import__('json').dumps(dict(asset=str(output),authoring=record)),flush=True)
    return record
