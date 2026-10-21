"""NumPy projective TSDF recovery; uses unchanged saved qualified depths."""
import runtime
from runtime import js,sha,now,output_guard
from pathlib import Path
import json
import time
import argparse
import numpy as np
from skimage.measure import marching_cubes
import open3d as o3d
from plyfile import PlyData
from scipy.special import expit
from geometry import project,region_ids

def fuse(unit):
    unit=output_guard(unit);p=json.loads((unit/'PROTOCOL.json').read_text());out=unit/'proxy'
    if (out/'mesh.npz').exists():raise FileExistsError('frozen proxy exists')
    t=time.monotonic()
    raw=PlyData.read(p['original']['original_ply'])['vertex'].data
    xyz=np.column_stack([raw[k] for k in ('x','y','z')]);xyz=xyz[expit(raw['opacity'])>.5]
    bounds=np.array([xyz.min(0)-.06,xyz.max(0)+.06]);voxel=.012;trunc=.036
    shape=np.ceil((bounds[1]-bounds[0])/voxel).astype(int)+1
    grid=np.indices(shape,dtype=np.float32).reshape(3,-1).T*voxel+bounds[0]
    sums=np.zeros(len(grid),np.float32);weights=np.zeros(len(grid),np.uint16)
    for c in p['build_cameras']:
        with np.load(out/(c['view']+'.npz')) as f:z=f['qualified_depth']
        for start in range(0,len(grid),200000):
            points=grid[start:start+200000];uv,zz=project(points,c);xy=np.rint(uv).astype(int)
            inside=(zz>.2)&(xy>=0).all(1)&(xy[:,0]<c['width'])&(xy[:,1]<c['height'])
            ids=np.flatnonzero(inside);obs=z[xy[ids,1],xy[ids,0]];sdf=obs-zz[ids]
            good=(obs>0)&(sdf>=-trunc);ids=ids[good];values=np.minimum(1,sdf[good]/trunc)
            sums[start+ids]+=values;weights[start+ids]+=1
    tsdf=np.divide(sums,weights,out=np.ones_like(sums),where=weights>0).reshape(shape)
    observed=(weights>0).reshape(shape)
    vertices,faces,_,_=marching_cubes(tsdf,level=0,spacing=(voxel,)*3,mask=observed,allow_degenerate=False)
    vertices+=bounds[0]
    mesh=o3d.geometry.TriangleMesh(o3d.utility.Vector3dVector(vertices),o3d.utility.Vector3iVector(faces))
    raw_faces=len(faces);labels,counts,areas=mesh.cluster_connected_triangles();counts=np.asarray(counts)
    mesh.remove_triangles_by_mask(counts[np.asarray(labels)]<40);mesh.remove_unreferenced_vertices()
    before_simplify=len(mesh.triangles)
    if before_simplify>30000:mesh=mesh.simplify_quadric_decimation(30000)
    mesh.remove_degenerate_triangles();mesh.remove_unreferenced_vertices();mesh.compute_vertex_normals()
    vertices=np.asarray(mesh.vertices);faces=np.asarray(mesh.triangles)
    assert len(faces)>0 and np.isfinite(vertices).all()
    cuts=p.get('region_rule',{}).get('cuts',[-.35,.20])
    np.savez_compressed(out/'mesh.npz',vertices=vertices,faces=faces,face_regions=region_ids(vertices[faces].mean(1),cuts))
    o3d.io.write_triangle_mesh(str(out/'proxy.ply'),mesh)
    js(out/'PROXY.json',dict(utc=now(),source_model_sha256=p['original']['sha256'],geometry_source=p['geometry'],
        fusion_backend='NumPy projective TSDF + skimage marching cubes; Open3D cleanup/simplification',
        vertices=len(vertices),faces=len(faces),raw_faces=raw_faces,raw_components=len(counts),
        removed_small_component_faces=raw_faces-before_simplify,before_simplification_faces=before_simplify,
        voxel=voxel,truncation=trunc,grid_shape=shape.tolist(),observed_voxels=int(observed.sum()),
        bbox_min=vertices.min(0).tolist(),bbox_max=vertices.max(0).tolist(),original_center_crop=bounds.tolist(),
        seconds=time.monotonic()-t,mesh_sha256=sha(out/'mesh.npz'),region_provenance=p['region_provenance'],
        negatives='No independent geometry truth. Limited depth confidence and missing undersides; TSDF can bridge thin surfaces. No GT, old ink or primitive substitution.'))
    print(json.dumps(dict(faces=len(faces),vertices=len(vertices),seconds=time.monotonic()-t)),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--unit',required=True);fuse(Path(p.parse_args().unit))
