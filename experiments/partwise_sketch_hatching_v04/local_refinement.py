"""Opt-in bounded local proxy revision, preserving saved non-target regions.

This changes an exploratory model-derived proxy, not the source GS model.
It supplies no new surface evidence and does not fill missing geometry.
"""
import runtime
from runtime import js, sha, now
from pathlib import Path
import argparse, json, shutil, time
import numpy as np
from demo import load_asset,new_output
from geometry import mesh_data
from hatching import generate_region,add_cross_layer,layer_ids
from refine_proxy import refine

def settings(config):
    expected={'iterations','positive_step','negative_step','max_displacement'}
    if not isinstance(config,dict) or set(config)!=expected:
        raise ValueError('local refinement requires exactly iterations/positive_step/negative_step/max_displacement; pinned regions are automatic')
    if type(config['iterations']) is not int or not 1<=config['iterations']<=30:
        raise ValueError('iterations must be an integer in [1,30]')
    result=dict(config)
    for key,lo,hi in [('positive_step',0.,1.),('negative_step',-1.,0.),('max_displacement',0.,.05)]:
        value=config[key]
        if type(value) not in (int,float) or not np.isfinite(value) or not lo<value<=hi or (key=='negative_step' and value==0):
            raise ValueError('invalid bounded refinement setting: '+key)
        result[key]=float(value)
    return result

def target_roughness(mesh,region):
    """Descriptive adjacent-normal angles, only true edges with two target faces."""
    edges={}
    for i,face in enumerate(mesh['faces']):
        for a,b in ((0,1),(1,2),(2,0)):
            edges.setdefault(tuple(sorted((int(face[a]),int(face[b])))),[]).append(i)
    pairs=np.asarray([p for p in edges.values() if len(p)==2 and np.all(mesh['regions'][p]==region)],dtype=int).reshape(-1,2)
    if not len(pairs):return dict(shared_target_edges=0,mean_angle_degrees=None,p95_angle_degrees=None)
    dot=np.clip(np.einsum('ij,ij->i',mesh['normals'][pairs[:,0]],mesh['normals'][pairs[:,1]]),-1,1)
    angles=np.rad2deg(np.arccos(dot))
    return dict(shared_target_edges=len(pairs),mean_angle_degrees=float(angles.mean()),
                median_angle_degrees=float(np.median(angles)),p95_angle_degrees=float(np.quantile(angles,.95)),
                scope='proxy adjacency diagnostic only; lower is imposed by smoothing and is not geometry accuracy')

def path_summary(paths):
    result={}
    for layer in np.unique(layer_ids(paths)):
        mask=layer_ids(paths)==layer
        lengths=np.linalg.norm(np.diff(paths['points'][mask],axis=1),axis=2).ravel()
        ids,inverse=np.unique(paths['stroke_id'][mask],return_inverse=True)
        totals=np.bincount(inverse,weights=lengths)
        result[str(int(layer))]=dict(paths=len(ids),segments=int(mask.sum()),length_world=float(lengths.sum()),
                                    median_path_length=float(np.median(totals)),max_path_length=float(totals.max()))
    return result

def refine_asset(asset,output,region,config):
    start=time.monotonic();config=settings(config);asset=Path(asset)
    mesh,paths,meta=load_asset(asset)
    if type(region) is not int or region not in paths:raise ValueError('unknown target region')
    others=sorted(set(paths)-{region});original=mesh['vertices'];faces=mesh['faces'];regions=mesh['regions']
    vertices,info=refine(original,faces,regions,dict(config,pinned_regions=others))
    if not info['moved_vertices']:raise ValueError('no movable target interior; no refinement produced')
    fixed=np.unique(faces[regions!=region])
    if not np.array_equal(vertices[fixed],original[fixed]):raise AssertionError('non-target geometry changed')
    new=mesh_data(vertices,faces,regions)
    n0=np.cross(mesh['tri'][:,1]-mesh['tri'][:,0],mesh['tri'][:,2]-mesh['tri'][:,0])
    n1=np.cross(new['tri'][:,1]-new['tri'][:,0],new['tri'][:,2]-new['tri'][:,0])
    guard=bool((np.einsum('ij,ij->i',n0,n1)>0).all() and
               (np.linalg.norm(n1,axis=1)>=.2*np.linalg.norm(n0,axis=1)).all())
    if not guard:raise AssertionError('oriented-area guard failed')
    style=meta['styles'][str(region)]
    target,stat=generate_region(new,region,style);regenerated=[0]
    # Disabled cross layers are cached editable geometry and must also be reanchored.
    if (layer_ids(paths[region])==1).any() or style.get('cross_enabled',False):
        target,cross=add_cross_layer(new,region,style,target)
        stat['cross_layer']=cross;regenerated.append(1)
    if not len(target['points']):raise ValueError('refined target has no hatch support')
    output=new_output(output)
    for file in asset.iterdir():
        if file.is_file():shutil.copy2(file,output/file.name)
    np.savez_compressed(output/'mesh.npz',vertices=vertices,faces=faces,face_regions=regions)
    np.savez_compressed(output/f'region_{region}.npz',**target)
    history=dict(operation='bounded_local_proxy_refinement',utc=now(),region=region,
        parent_asset_sha256=sha(asset/'asset.json'),parent_mesh_sha256=meta['mesh_sha256'],mesh_sha256=sha(output/'mesh.npz'),
        parameters=config,topology_and_labels_unchanged=True,non_target_vertices_exact=True,
        selection_policy='Saved selected face IDs and original selection history retained exactly; topology unchanged. The old screen-rectangle recipe records its original mesh, not a new selection on the refined surface.',
        path_policy='Only target paths regenerated on the revised surface; IDs require this mesh/path revision, not unchanged coordinates or original Gaussian indices.',
        regenerated_layers=regenerated,limitation='Exploratory smoothing, not independent surface evidence; no fill, weld, reconstruction accuracy or H5 claim.')
    meta['mesh_sha256']=history['mesh_sha256'];meta['statistics'][str(region)]=stat
    meta.setdefault('geometry_history',[]).append(history)
    meta['geometry']+='; opt-in bounded local proxy smoothing of region '+str(region)+' (no new surface evidence)'
    meta['refined_utc']=history['utc']
    js(output/'asset.json',meta)
    result=dict(**info,scene=meta['scene'],region=region,source_asset_sha256=history['parent_asset_sha256'],
        source_mesh_sha256=history['parent_mesh_sha256'],mesh_sha256=history['mesh_sha256'],original=meta['original'],
        non_target_vertices_exact=True,non_target_path_files_exact=all(sha(asset/f'region_{r}.npz')==sha(output/f'region_{r}.npz') for r in others),
        selection_files_exact=all(sha(asset/h['face_ids_file'])==sha(output/h['face_ids_file']) for h in meta.get('region_history',[])),
        oriented_area_guard_pass=guard,regenerated_layers=regenerated,
        displacement_bbox_fraction=float(info['displacement_max']/np.linalg.norm(np.ptp(original,axis=0))),
        target_roughness_before=target_roughness(mesh,region),target_roughness_after=target_roughness(new,region),
        target_paths_before=path_summary(paths[region]),target_paths_after=path_summary(target),
        seconds=time.monotonic()-start,limitation=history['limitation'])
    js(output/'LOCAL_REFINEMENT.json',result)
    load_asset(output)  # Validates barycentric attachment against the newly saved mesh.
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--asset',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    p.add_argument('--region','--part',required=True,type=int)
    p.add_argument('--iterations',type=int,default=10);p.add_argument('--max-displacement',type=float,default=.018)
    a=p.parse_args()
    result=refine_asset(a.asset,a.output,a.region,dict(iterations=a.iterations,positive_step=.5,negative_step=-.53,max_displacement=a.max_displacement))
    print(json.dumps(result),flush=True)

if __name__=='__main__':main()
