"""Persistent creation-time strokes for manually authored regions.

Restoration copies saved bytes; entering the original angle is still a normal
parameter edit. New snapshots bind the owner and all saved capsule support to
indexed geometry and per-face acceptance. Legacy snapshots keep their original
whole-mesh contract. Neither form restores old geometry or edits other regions.
"""
import runtime
from runtime import sha,js,now
from pathlib import Path
import copy,hashlib,json,re,shutil
import numpy as np
from hatching import validate_style,visibility_masks

DEPENDENCY_SCHEMA='region_support_v1'

def dependency(mesh,region,masks):
    """Camera-independent conservative dependency of saved capsule rendering.

    A capsule tests the label at every covered, depth-tested pixel. Hash the
    accepted *face sets* for each distinct saved mask, not just anchored faces
    or current visible pixels. Relabeling an excluded region remains harmless;
    relabeling even a distant accepted face invalidates this snapshot. Geometry
    of all accepted faces (including their shared vertices) is also protected.
    Other geometry remains current and can change occlusion on restoration.
    """
    h=hashlib.sha256()
    def array(name,value,dtype):
        a=np.ascontiguousarray(value,dtype=dtype)
        h.update(json.dumps([name,a.shape,a.dtype.str],separators=(',',':')).encode())
        h.update(a.tobytes())
    array('mesh_counts',[len(mesh['vertices']),len(mesh['faces'])],'<i8')
    array('owner_faces',np.flatnonzero(mesh['regions']==region),'<i8')
    bits=np.left_shift(np.uint64(1),mesh['regions'].astype(np.uint64))
    supported=np.zeros(len(bits),bool)
    for mask in masks:
        accepted=(bits & np.uint64(mask))!=0
        array('mask_'+str(mask),np.flatnonzero(accepted),'<i8')
        supported|=accepted
    faces=np.flatnonzero(supported);vertices=np.unique(mesh['faces'][faces])
    array('support_face_ids',faces,'<i8')
    array('support_faces',mesh['faces'][faces],'<i8')
    array('support_vertex_ids',vertices,'<i8')
    array('support_vertices',mesh['vertices'][vertices],'<f8')
    return dict(schema=DEPENDENCY_SCHEMA,masks=list(masks),sha256=h.hexdigest())

def validate_dependency(entry,region,paths):
    dep=entry.get('dependency')
    if dep is None:return
    if not isinstance(dep,dict) or set(dep)!= {'schema','masks','sha256'} or dep['schema']!=DEPENDENCY_SCHEMA:
        raise ValueError('invalid creation snapshot support schema')
    masks=dep['masks']
    if (not isinstance(masks,list) or not masks or len(masks)>32 or
        any(type(v) is not int or v<=0 or v>=(1<<33) or v&1 or not v&(1<<region) for v in masks) or
        masks!=sorted(set(masks)) or not re.fullmatch('[0-9a-f]{64}',str(dep['sha256']))):
        raise ValueError('invalid creation snapshot support metadata')
    if masks!=np.unique(visibility_masks(paths,region)).tolist():
        raise ValueError('creation snapshot support does not match saved paths')

def save_origin(asset,meta,region):
    from geometry import mesh_data
    asset=Path(asset);key=str(region);filename=f'origin_{region}.npz'
    shutil.copy2(asset/f'region_{region}.npz',asset/filename)
    with np.load(asset/'mesh.npz',allow_pickle=False) as z:mesh=mesh_data(z['vertices'],z['faces'],z['face_regions'])
    with np.load(asset/filename,allow_pickle=False) as z:paths={k:z[k] for k in z.files}
    masks=np.unique(visibility_masks(paths,region)).tolist()
    meta.setdefault('region_origins',{})[key]=dict(file=filename,sha256=sha(asset/filename),
        mesh_sha256=meta['mesh_sha256'],style=copy.deepcopy(meta['styles'][key]),
        statistics=copy.deepcopy(meta['statistics'][key]),created_utc=now(),
        dependency=dependency(mesh,region,masks),
        provenance='Exact creation-time manual-region paths and style, including inherited capsule support; no regeneration or Gaussian identities')
    meta['version']=max(6,meta.get('version',1))

def restore_status(meta,region,mesh=None):
    entry=meta.get('region_origins',{}).get(str(region))
    if entry is None:return dict(available=False,reason='No creation snapshot is saved for this region.')
    dep=entry.get('dependency')
    if dep is not None and mesh is not None:
        valid=dependency(mesh,region,dep['masks'])==dep
    else:
        valid=entry['mesh_sha256']==meta['mesh_sha256']
    if not valid:
        return dict(available=False,reason='Geometry or region boundaries changed in this snapshot’s support; its original strokes cannot be restored.')
    return dict(available=True,reason='Restore this region’s strokes and style from when it was created. Other regions and the view stay unchanged.')

def validate_origins(asset,mesh,meta):
    from demo import validate_paths
    origins=meta.get('region_origins',{})
    if not isinstance(origins,dict) or not set(origins)<=set(meta['regions']):raise ValueError('invalid creation snapshot regions')
    for key,entry in origins.items():
        if not isinstance(entry,dict) or entry.get('file')!=f'origin_{int(key)}.npz':raise ValueError('invalid creation snapshot filename')
        if not re.fullmatch('[0-9a-f]{64}',str(entry.get('mesh_sha256',''))):raise ValueError('invalid creation snapshot mesh checksum')
        filename=Path(asset)/entry['file']
        if not filename.is_file() or sha(filename)!=entry.get('sha256'):raise ValueError('creation snapshot checksum mismatch')
        validate_style(entry['style'])
        if not isinstance(entry.get('statistics'),dict):raise ValueError('invalid creation snapshot statistics')
        with np.load(filename,allow_pickle=False) as z:paths={k:z[k] for k in z.files}
        validate_dependency(entry,int(key),paths)
        # A stale origin remains archived, never a replacement for this mesh.
        # Imported archives size-check all NPZs before this loader is called.
        if restore_status(meta,int(key),mesh)['available']:
            validate_paths(mesh,paths,entry['style'],int(key),list(map(int,meta['regions'])))

def restore_region(asset,output,region):
    from demo import load_asset,new_output
    asset=Path(asset);mesh,_,meta=load_asset(asset)
    key=str(region)
    if key not in meta['regions']:raise ValueError('unknown region')
    status=restore_status(meta,region,mesh)
    if not status['available']:raise ValueError(status['reason'])
    entry=meta['region_origins'][key]
    output=new_output(output)
    for file in asset.iterdir():
        if file.is_file():shutil.copy2(file,output/file.name)
    shutil.copy2(asset/entry['file'],output/f'region_{region}.npz')
    meta['styles'][key]=copy.deepcopy(entry['style']);meta['statistics'][key]=copy.deepcopy(entry['statistics'])
    meta['edit']=dict(operation='restore_region_creation',region=int(region),utc=now(),
        parent_asset_sha256=sha(asset/'asset.json'),snapshot_sha256=entry['sha256'],
        geometry_changed=False,paths_regenerated=False,regenerated_layers=[],
        target_path_revision='exact creation-time bytes restored',scope='Only selected region paths, style and statistics restored; geometry, other regions, view and display retained')
    js(output/'asset.json',meta)
    return meta['edit']
