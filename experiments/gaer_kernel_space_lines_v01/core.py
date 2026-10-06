"""Camera-free original-kernel graph; projection is a separate post-hoc function."""
import ast
import json
import struct
from pathlib import Path
import numpy as np
from scipy.spatial.distance import cdist

PARAMETERS=dict(k=12,baseline_neighbors=2,linearity_min=.45,alignment_cos=float(np.cos(np.pi/4)),distance_factor=3.,radius_factor=.12,tube_sides=8)
REASONS={1:'zero_length',2:'local_distance_gate',4:'not_baseline_top2',8:'low_endpoint_linearity',16:'endpoint_direction_mismatch',32:'not_mutual_knn',64:'not_mutual_halfaxis_choice'}

def project(xyz,camera):
    p=np.asarray(xyz,dtype=np.float64)
    m=np.asarray(camera['w2c'],dtype=np.float64)
    q=p@m[:3,:3].T+m[:3,3]
    fx=camera['width']/(2*np.tan(camera['FoVx']/2));fy=camera['height']/(2*np.tan(camera['FoVy']/2))
    with np.errstate(divide='ignore',invalid='ignore'):
        uv=q[:,:2]/q[:,2,None]*[fx,fy]+[(camera['width']-1)/2,(camera['height']-1)/2]
    return uv,q[:,2]

def selected_rows(model_xyz,source_ids):
    arrays=[np.asarray(a,dtype=np.int64) for a in source_ids]
    if len(arrays)!=2 or any(a.ndim!=1 or np.any(a<0) or np.any(a>=len(model_xyz)) for a in arrays):
        raise ValueError('exactly two valid original-ID source arrays required')
    ids=np.unique(np.concatenate(arrays))
    mask=np.isin(ids,arrays[0]).astype(np.uint8)+2*np.isin(ids,arrays[1]).astype(np.uint8)
    return ids,np.asarray(model_xyz)[ids].copy(),mask

def build_graph(xyz,ids):
    original=np.asarray(xyz).copy();p=np.asarray(xyz,dtype=np.float64);ids=np.asarray(ids,dtype=np.int64)
    n=len(p)
    if p.shape!=(n,3) or len(ids)!=n or n<2 or len(np.unique(ids))!=n or not np.isfinite(p).all():
        raise ValueError('finite original rows with unique IDs required')
    eps=max(float(np.linalg.norm(np.ptp(p,axis=0)))*1e-12,1e-15)
    d=cdist(p,p);np.fill_diagonal(d,np.inf)
    k=min(PARAMETERS['k'],n-1)
    neighbors=np.array([np.lexsort((ids,row))[:k] for row in d],dtype=np.int32)
    ranks=np.full((n,n),-1,dtype=np.int16)
    ranks[np.arange(n)[:,None],neighbors]=np.arange(k)
    nz=np.where(d>eps,d,np.inf)
    scale=nz.min(1);scale[~np.isfinite(scale)]=eps
    tangent=np.zeros((n,3));eigenvalues=np.zeros((n,3))
    for i in range(n):
        local=p[np.r_[i,neighbors[i]]];local=local-local.mean(0)
        vals,vecs=np.linalg.eigh(local.T@local/len(local))
        eigenvalues[i]=np.maximum(vals[::-1],0)
        t=vecs[:,-1];t*=1 if t[np.argmax(np.abs(t))]>=0 else -1
        tangent[i]=t
    linearity=(eigenvalues[:,0]-eigenvalues[:,1])/np.maximum(eigenvalues[:,0],eps**2)
    raw=np.column_stack([np.repeat(np.arange(n),k),neighbors.ravel()]);raw.sort(1)
    pairs=np.unique(raw,axis=0);a,b=pairs.T
    delta=p[b]-p[a];distance=np.linalg.norm(delta,axis=1)
    unit=delta/np.maximum(distance[:,None],eps)
    signed_a=np.einsum('ij,ij->i',tangent[a],unit)
    signed_b=-np.einsum('ij,ij->i',tangent[b],unit)
    align_a=np.abs(signed_a);align_b=np.abs(signed_b)
    gate=PARAMETERS['distance_factor']*np.minimum(scale[a],scale[b])
    shared=np.zeros(len(pairs),dtype=np.uint16)
    shared[distance<=eps]|=1;shared[distance>gate]|=2
    reason_A=shared.copy()
    top2=((ranks[a,b]>=0)&(ranks[a,b]<2))|((ranks[b,a]>=0)&(ranks[b,a]<2))
    reason_A[~top2]|=4
    base=shared.copy()
    base[(linearity[a]<PARAMETERS['linearity_min'])|(linearity[b]<PARAMETERS['linearity_min'])]|=8
    base[(align_a<PARAMETERS['alignment_cos'])|(align_b<PARAMETERS['alignment_cos'])]|=16
    base[(ranks[a,b]<0)|(ranks[b,a]<0)]|=32
    # Each endpoint nominates at most one shortest admissible edge per half axis.
    choices=np.full((n,2),-1,dtype=np.int64)
    eligible=np.flatnonzero(base==0)
    order=eligible[np.lexsort((ids[b[eligible]],ids[a[eligible]],distance[eligible]))]
    for e in order:
        for node,signed in [(a[e],signed_a[e]),(b[e],signed_b[e])]:
            half=int(signed>=0)
            if choices[node,half]<0:choices[node,half]=e
    mutual=np.array([e in choices[u] and e in choices[v] for e,(u,v) in enumerate(pairs)])
    reason_B=base.copy();reason_B[~mutual]|=64
    return dict(xyz=original,ids=ids,neighbors=neighbors,local_scale=scale,tangent=tangent,eigenvalues=eigenvalues,linearity=linearity,
                candidate_pairs=pairs,distance=distance,distance_limit=gate,alignment=np.column_stack([align_a,align_b]),
                endpoint_knn_rank=np.column_stack([ranks[a,b],ranks[b,a]]),reason_A=reason_A,reason_B=reason_B,choices=choices,
                A=pairs[reason_A==0],B=pairs[reason_B==0],radius=float(PARAMETERS['radius_factor']*np.median(scale)),eps=eps)

def _reuse_functions():
    source=Path(__file__).resolve().parents[1]/'gaer_fixed_contour_asset_v01'/'core.py'
    tree=ast.parse(source.read_text())
    # Execute only the already tested geometry serializers; no legacy import/run.
    chosen=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in {'tube_mesh','glb_bytes'}]
    scope=dict(np=np,json=json,struct=struct)
    exec(compile(ast.Module(body=chosen,type_ignores=[]),str(source),'exec'),scope)
    return scope['tube_mesh'],scope['glb_bytes']

def _encode_glb(doc,binary=b''):
    jb=json.dumps(doc,separators=(',',':')).encode();jb+=b' '*((-len(jb))%4)
    binary+=b'\0'*((-len(binary))%4)
    chunks=struct.pack('<II',len(jb),0x4e4f534a)+jb
    if binary:chunks+=struct.pack('<II',len(binary),0x004e4942)+binary
    return struct.pack('<III',0x46546c67,2,12+len(chunks))+chunks

def mesh_and_glb(xyz,edges,radius):
    edges=np.asarray(edges,dtype=np.int64).reshape(-1,2)
    if not len(edges):
        return np.empty((0,3),np.float32),np.empty((0,3),np.int32),_encode_glb(dict(asset={'version':'2.0','generator':'GAER kernel-space candidate graph'},scene=0,scenes=[{'nodes':[]}],nodes=[],extras={'empty_result':True,'fixed_geometry':True,'physical_edge_certified':False}))
    tube,glb=_reuse_functions()
    vertices,faces=tube([np.asarray(xyz)[pair] for pair in edges],radius,8)
    data=glb(vertices,faces)
    # Retain numerical serializer; give the new asset its accurate candidate label.
    _,_,doc=parse_glb(data)
    doc['asset']['generator']='GAER original-kernel-space candidate graph; tube/glb numerical functions reused'
    doc['nodes'][0]['name']='fixed_original_kernel_candidate_tubes'
    doc['extras']['physical_edge_certified']=False
    return vertices,faces,_encode_glb(doc,vertices.astype('<f4').tobytes()+faces.astype('<u4').tobytes())

def parse_glb(data):
    # Independent accessor/chunk reader, without trimesh or exporter helpers.
    if len(data)<20:raise ValueError('short GLB')
    magic,version,total=struct.unpack_from('<III',data)
    if magic!=0x46546c67 or version!=2 or total!=len(data):raise ValueError('GLB header/length mismatch')
    pos=12;doc=None;binary=b''
    while pos<len(data):
        size,kind=struct.unpack_from('<II',data,pos);pos+=8
        if pos+size>len(data):raise ValueError('truncated chunk')
        chunk=data[pos:pos+size];pos+=size
        if kind==0x4e4f534a:doc=json.loads(chunk)
        elif kind==0x004e4942:binary=chunk
    if doc is None:raise ValueError('missing JSON')
    if not doc.get('meshes'):return np.empty((0,3),np.float32),np.empty((0,3),np.int32),doc
    def read(index):
        acc=doc['accessors'][index];view=doc['bufferViews'][acc['bufferView']]
        dtype={5126:'<f4',5125:'<u4'}[acc['componentType']];width={'VEC3':3,'SCALAR':1}[acc['type']]
        offset=view.get('byteOffset',0)+acc.get('byteOffset',0);count=acc['count']*width
        return np.frombuffer(binary,dtype=dtype,count=count,offset=offset).copy().reshape(-1,width)
    primitive=doc['meshes'][0]['primitives'][0]
    return read(primitive['attributes']['POSITION']),read(primitive['indices']).reshape(-1,3),doc
