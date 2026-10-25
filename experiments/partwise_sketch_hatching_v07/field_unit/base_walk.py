"""Fixed-seed straightest paths on the unchanged triangle carrier.

At a genuine shared edge, preserve the component along the edge and unfold
the perpendicular component into the adjacent triangle. No spatial KNN,
normal smoothing, hole filling, per-view fitting, or carrier modification.
"""
import runtime
import numpy as np

def adjacency(mesh):
    edges={}
    for face,vertices in enumerate(mesh['faces']):
        for j in range(3):
            edge=tuple(sorted(int(vertices[k]) for k in range(3) if k!=j))
            edges.setdefault(edge,[]).append(face)
    return edges

def bary_derivative(triangle,direction):
    a=triangle[1]-triangle[0]; b=triangle[2]-triangle[0]
    aa,ab,bb=np.dot(a,a),np.dot(a,b),np.dot(b,b)
    determinant=aa*bb-ab*ab
    if determinant<=1e-24: return None
    ad,bd=np.dot(a,direction),np.dot(b,direction)
    u=(bb*ad-ab*bd)/determinant; v=(aa*bd-ab*ad)/determinant
    return np.array([-u-v,u,v])

def walk(mesh,face,bary,direction,length,allowed=None,edges=None):
    """One direction from a face/bary seed, with explicit early-stop reasons."""
    if allowed is None: allowed=np.ones(len(mesh['faces']),bool)
    if edges is None: edges=adjacency(mesh)
    face=int(face); bary=np.asarray(bary,float).copy(); direction=np.asarray(direction,float).copy()
    if not allowed[face] or not np.isfinite(bary).all() or (bary<-1e-9).any() or abs(bary.sum()-1)>1e-9: raise ValueError('invalid seed')
    if length<0 or not np.isfinite(length): raise ValueError('invalid length')
    direction-=np.dot(direction,mesh['normals'][face])*mesh['normals'][face]
    norm=np.linalg.norm(direction)
    if norm<1e-12: raise ValueError('degenerate tangent')
    direction/=norm
    points=[]; barys=[]; owners=[]; remaining=float(length); reason='step_limit'
    for step in range(10000):
        if remaining<=1e-11: reason='requested_length'; break
        tri=mesh['tri'][face]; db=bary_derivative(tri,direction)
        if db is None: reason='degenerate_face'; break
        exits=np.full(3,np.inf); outward=db<-1e-12
        exits[outward]=-bary[outward]/db[outward]
        exits[exits<-1e-9]=np.inf
        exits=np.maximum(exits,0.)
        edge_distance=float(exits.min())
        if not np.isfinite(edge_distance): reason='degenerate_exit'; break
        travel=min(remaining,edge_distance)
        end=bary+travel*db
        end[np.abs(end)<1e-10]=0.; end/=end.sum()
        if travel>1e-11:
            bb=np.stack([bary,end]); points.append(bb@tri); barys.append(bb); owners.append(face)
            remaining-=travel
        bary=end
        if remaining<=1e-11: reason='requested_length'; break
        crossed=np.flatnonzero(np.abs(exits-edge_distance)<1e-9)
        if len(crossed)!=1: reason='vertex_ambiguity'; break
        j=int(crossed[0]); old_ids=mesh['faces'][face]
        edge=tuple(sorted(int(old_ids[k]) for k in range(3) if k!=j))
        neighbors=edges[edge]
        if len(neighbors)!=2: reason='mesh_boundary' if len(neighbors)==1 else 'nonmanifold_edge'; break
        nxt=neighbors[0] if neighbors[1]==face else neighbors[1]
        if not allowed[nxt]: reason='authored_region_boundary'; break
        v0,v1=mesh['vertices'][list(edge)]; axis=v1-v0
        edge_norm=np.linalg.norm(axis)
        if edge_norm<1e-12: reason='degenerate_edge'; break
        axis/=edge_norm; next_ids=mesh['faces'][nxt]
        third=[int(k) for k in next_ids if k not in edge]
        if len(third)!=1: reason='duplicate_face'; break
        inward=mesh['vertices'][third[0]]-v0; inward-=np.dot(inward,axis)*axis
        inward_norm=np.linalg.norm(inward)
        if inward_norm<1e-12: reason='degenerate_face'; break
        inward/=inward_norm
        along=float(np.dot(direction,axis))
        perpendicular=float(np.linalg.norm(direction-along*axis))
        direction=along*axis+perpendicular*inward; direction/=np.linalg.norm(direction)
        next_bary=np.zeros(3)
        for vertex in edge: next_bary[np.flatnonzero(next_ids==vertex)[0]]=bary[np.flatnonzero(old_ids==vertex)[0]]
        bary=next_bary/next_bary.sum(); face=int(nxt)
    p=np.asarray(points,float).reshape(-1,2,3)
    return dict(points=p,bary=np.asarray(barys,float).reshape(-1,2,3),face=np.asarray(owners,np.int32),
                reason=reason,length=float(np.linalg.norm(p[:,1]-p[:,0],axis=1).sum()),steps=step+1)

def regenerate(mesh,old,allowed,id_offset=100_000_000_000):
    edges=adjacency(mesh); arrays={k:[] for k in ('points','bary','face','stroke_id','layer_id','visibility_mask','parent_stroke_id')}; records=[]
    for sid in np.unique(old['stroke_id']):
        ix=np.flatnonzero(old['stroke_id']==sid); p=old['points'][ix]
        if len(ix)>1 and not np.allclose(p[:-1,1],p[1:,0],atol=1e-8,rtol=0): raise ValueError('baseline stroke not an ordered connected chain')
        lengths=np.linalg.norm(p[:,1]-p[:,0],axis=1); total=float(lengths.sum())
        if total<=1e-12: raise ValueError('zero baseline stroke')
        cumulative=np.cumsum(lengths); mid=min(int(np.searchsorted(cumulative,total/2,side='right')),len(ix)-1)
        before=0. if mid==0 else cumulative[mid-1]; t=(total/2-before)/lengths[mid]
        seed_bary=(1-t)*old['bary'][ix[mid],0]+t*old['bary'][ix[mid],1]
        face=int(old['face'][ix[mid]]); tangent=(p[mid,1]-p[mid,0])/lengths[mid]
        minus=walk(mesh,face,seed_bary,-tangent,total/2,allowed,edges)
        plus=walk(mesh,face,seed_bary,tangent,total/2,allowed,edges)
        new={k:np.concatenate([minus[k][::-1,::-1] if k in ('points','bary') else minus[k][::-1],plus[k]]) for k in ('points','bary','face')}
        count=len(new['face'])
        layer=old.get('layer_id',np.zeros(len(old['face']),np.uint8))[ix]
        mask=old.get('visibility_mask',np.full(len(old['face']),1<<4,np.uint64))[ix]
        if len(np.unique(layer))!=1 or len(np.unique(mask))!=1: raise ValueError('nonuniform baseline stroke metadata')
        for key in ('points','bary','face'): arrays[key].append(new[key])
        for key,value,dtype in [('stroke_id',int(sid)+id_offset,np.int64),('layer_id',int(layer[0]),np.uint8),
                                ('visibility_mask',int(mask[0]),np.uint64),('parent_stroke_id',int(sid),np.int64)]:
            arrays[key].append(np.full(count,value,dtype))
        actual=minus['length']+plus['length']
        records.append(dict(parent_stroke_id=int(sid),stroke_id=int(sid)+id_offset,seed_face=face,seed_bary=seed_bary.tolist(),
            seed_point=(seed_bary@mesh['tri'][face]).tolist(),initial_tangent=tangent.tolist(),layer_id=int(layer[0]),
            requested_length=total,actual_length=actual,minus_stop=minus['reason'],plus_stop=plus['reason'],
            segments=count,minus_length=minus['length'],plus_length=plus['length']))
    result={k:np.concatenate(v) for k,v in arrays.items()}
    np.testing.assert_allclose(result['points'],np.einsum('nij,njk->nik',result['bary'],mesh['tri'][result['face']]),atol=1e-10,rtol=0)
    if (result['bary']<-1e-8).any() or not allowed[result['face']].all(): raise ValueError('walk escaped carrier or partition')
    return result,records
