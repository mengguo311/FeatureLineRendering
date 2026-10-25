"""Anchored unoriented face fields and one common intrinsic triangle walker.

F0 is exactly the tangent to the original slicing planes. F1 diffuses tangent
dyads through genuine shared edges, with a fixed raw-field fidelity term.
No geometry, labels, seeds, visibility or per-camera inputs are optimized.
"""
import runtime
import numpy as np
from base_walk import adjacency, bary_derivative

DEFAULTS=dict(iterations=8,neighbor_weight=.5,crease_degrees=60.)

def transport(mesh,i,j,edge):
    """Linear tangent transport j -> i, independent of triangle winding."""
    v=mesh['vertices'];a,b=v[list(edge)];axis=b-a;axis/=np.linalg.norm(axis)
    inward=[]
    for face in (i,j):
        other=[int(k) for k in mesh['faces'][face] if k not in edge]
        if len(other)!=1:raise ValueError('invalid shared edge')
        u=v[other[0]]-a;u-=np.dot(u,axis)*axis
        if np.linalg.norm(u)<1e-12:raise ValueError('degenerate face')
        inward.append(u/np.linalg.norm(u))
    return np.outer(axis,axis)-np.outer(inward[0],inward[1])

def fields(mesh,partitions,cutting_normals,config=None):
    cfg=dict(DEFAULTS if config is None else config);labels=np.asarray(partitions)
    q=np.asarray(cutting_normals,float);n=mesh['normals'];raw=np.cross(n[:,None,:],q[None,:,:])
    lengths=np.linalg.norm(raw,axis=2);valid=lengths>1e-12
    raw=np.divide(raw,lengths[:,:,None],out=np.zeros_like(raw),where=valid[:,:,None])
    pairs=[];matrices=[];sharp=0
    for edge,fs in adjacency(mesh).items():
        if len(fs)!=2:continue
        i,j=fs
        if labels[i]<=0 or labels[i]!=labels[j]:continue
        if abs(float(n[i]@n[j]))<np.cos(np.deg2rad(cfg['crease_degrees'])):sharp+=1;continue
        try:T=transport(mesh,i,j,edge)
        except ValueError:continue
        pairs.append((i,j));matrices.append(T)
    pairs=np.asarray(pairs,int).reshape(-1,2);T=np.asarray(matrices,float).reshape(-1,3,3)
    areas=.5*np.linalg.norm(np.cross(mesh['tri'][:,1]-mesh['tri'][:,0],mesh['tri'][:,2]-mesh['tri'][:,0]),axis=1)
    result=raw.copy();diagnostics=[];energies=[]
    for layer in range(len(q)):
        ok=valid[pairs].all(1)[:,layer] if len(pairs) else np.zeros(0,bool)
        pp=pairs[ok];tt=T[ok];i=pp[:,0];j=pp[:,1]
        initial=np.einsum('ni,nj->nij',raw[:,layer],raw[:,layer]);dyads=initial.copy()
        degree=np.zeros(len(n));np.add.at(degree,i,areas[j]);np.add.at(degree,j,areas[i]);active=degree>0
        for _ in range(cfg['iterations']):
            summed=np.zeros_like(dyads)
            jt=tt@dyads[j]@tt.transpose(0,2,1);it=tt.transpose(0,2,1)@dyads[i]@tt
            np.add.at(summed,i,jt*areas[j,None,None]);np.add.at(summed,j,it*areas[i,None,None])
            dyads[active]=(1-cfg['neighbor_weight'])*initial[active]+cfg['neighbor_weight']*summed[active]/degree[active,None,None]
        ids=np.flatnonzero(active);eig,vec=np.linalg.eigh(dyads[ids]);direction=vec[:,:,-1]
        gap=eig[:,-1]-eig[:,-2];ambiguous=gap<=1e-12
        direction[ambiguous]=raw[ids[ambiguous],layer]
        result[ids,layer]=direction
        def energy(values):
            if not len(i):return 0.
            transported=np.einsum('nij,nj->ni',tt,values[j]);dot=np.sum(values[i]*transported,axis=1)
            return float(np.average(1-np.clip(dot*dot,0,1),weights=(areas[i]+areas[j])/2))
        energies.append([energy(raw[:,layer]),energy(result[:,layer])])
        diagnostics.append(dict(layer=layer,active_faces=len(ids),degenerate_selected_faces=int(((labels>0)&~valid[:,layer]).sum()),
                                ambiguous_fallbacks=int(ambiguous.sum()),raw_energy=energies[-1][0],regularized_energy=energies[-1][1]))
    change=np.rad2deg(np.arccos(np.clip(np.abs(np.sum(raw*result,axis=2)),0,1)))
    selected=labels>0
    return raw,result,dict(config=cfg,edge_pairs=len(pairs),cross_partition_pairs=0,sharp_pairs_excluded=sharp,
        raw_connection_energy=float(np.mean(np.array(energies)[:,0])),regularized_connection_energy=float(np.mean(np.array(energies)[:,1])),
        layers=diagnostics,selected_change_degrees_quantiles=np.quantile(change[selected],[.5,.9,.95,1]).tolist(),
        scope='Area-weighted connection energy on smoothing graph only; sharp excluded edges are not new walker stops; no true-surface claim.')

def walk_field(mesh,face,bary,direction,length,allowed,field,edges=None):
    if edges is None:edges=adjacency(mesh)
    face=int(face);bary=np.asarray(bary,float).copy();direction=np.asarray(direction,float).copy()
    if not allowed[face] or (bary<-1e-9).any() or abs(bary.sum()-1)>1e-9:raise ValueError('invalid seed')
    if length<0 or not np.isfinite(length):raise ValueError('invalid length')
    direction-=np.dot(direction,mesh['normals'][face])*mesh['normals'][face]
    if np.linalg.norm(direction)<1e-12:raise ValueError('degenerate seed tangent')
    direction/=np.linalg.norm(direction)
    points=[];barys=[];owners=[];remaining=float(length);reason='step_limit';zero_steps=0;reversals=0
    for step in range(10000):
        if remaining<=1e-11:reason='requested_length';break
        tri=mesh['tri'][face];db=bary_derivative(tri,direction)
        if db is None:reason='degenerate_face';break
        exits=np.full(3,np.inf);out=db<-1e-12;exits[out]=-bary[out]/db[out];exits[exits<-1e-9]=np.inf;exits=np.maximum(exits,0.)
        distance=float(exits.min())
        if not np.isfinite(distance):reason='degenerate_exit';break
        travel=min(remaining,distance);end=bary+travel*db;end[np.abs(end)<1e-10]=0.;end/=end.sum()
        if travel>1e-11:
            bb=np.stack([bary,end]);points.append(bb@tri);barys.append(bb);owners.append(face);remaining-=travel;zero_steps=0
        else:
            zero_steps+=1
            if zero_steps>3:reason='zero_step_cycle';break
        bary=end
        if remaining<=1e-11:reason='requested_length';break
        crossed=np.flatnonzero(np.abs(exits-distance)<1e-9)
        if len(crossed)!=1:reason='vertex_ambiguity';break
        opposite=int(crossed[0]);old_ids=mesh['faces'][face];edge=tuple(sorted(int(old_ids[k]) for k in range(3) if k!=opposite));fs=edges[edge]
        if len(fs)!=2:reason='mesh_boundary' if len(fs)==1 else 'nonmanifold_edge';break
        nxt=fs[0] if fs[1]==face else fs[1]
        if not allowed[nxt]:reason='authored_region_boundary';break
        ids=mesh['faces'][nxt];third=[k for k in range(3) if int(ids[k]) not in edge]
        if len(third)!=1:reason='duplicate_face';break
        candidate=field[nxt].copy();norm=np.linalg.norm(candidate)
        if norm<1e-12:reason='field_degeneracy';break
        candidate/=norm;derivative=bary_derivative(mesh['tri'][nxt],candidate)
        if derivative is None:reason='degenerate_face';break
        if abs(derivative[third[0]])<1e-12:reason='field_edge_tangency';break
        # The line has no sign. Enter the neighbor; do not invent a gap bridge.
        if derivative[third[0]]<0:candidate=-candidate
        previous=transport(mesh,nxt,face,edge)@direction
        if np.dot(previous,candidate)<0:reversals+=1
        next_bary=np.zeros(3)
        for vertex in edge:next_bary[np.flatnonzero(ids==vertex)[0]]=bary[np.flatnonzero(old_ids==vertex)[0]]
        bary=next_bary/next_bary.sum();face=int(nxt);direction=candidate
    p=np.asarray(points,float).reshape(-1,2,3)
    return dict(points=p,bary=np.asarray(barys,float).reshape(-1,2,3),face=np.asarray(owners,np.int32),reason=reason,
                length=float(np.linalg.norm(p[:,1]-p[:,0],axis=1).sum()),steps=step+1,obtuse_edge_transitions=reversals)

def regenerate(mesh,old,allowed,field,id_offset):
    edges=adjacency(mesh);arrays={k:[] for k in ('points','bary','face','stroke_id','layer_id','visibility_mask','parent_stroke_id')};records=[]
    for sid in np.unique(old['stroke_id']):
        ix=np.flatnonzero(old['stroke_id']==sid);p=old['points'][ix];lengths=np.linalg.norm(p[:,1]-p[:,0],axis=1);total=float(lengths.sum())
        if len(ix)>1:np.testing.assert_allclose(p[:-1,1],p[1:,0],atol=1e-8,rtol=0)
        cumulative=np.cumsum(lengths);mid=min(int(np.searchsorted(cumulative,total/2,side='right')),len(ix)-1)
        before=0. if mid==0 else cumulative[mid-1];t=(total/2-before)/lengths[mid]
        seed=(1-t)*old['bary'][ix[mid],0]+t*old['bary'][ix[mid],1];face=int(old['face'][ix[mid]])
        layer=int(old.get('layer_id',np.zeros(len(old['face']),np.uint8))[ix[mid]])
        reference=(p[mid,1]-p[mid,0])/lengths[mid];initial=field[face,layer].copy()
        if np.dot(initial,reference)<0:initial=-initial
        minus=walk_field(mesh,face,seed,-initial,total/2,allowed,field[:,layer],edges)
        plus=walk_field(mesh,face,seed,initial,total/2,allowed,field[:,layer],edges)
        new={k:np.concatenate([minus[k][::-1,::-1] if k in ('points','bary') else minus[k][::-1],plus[k]]) for k in ('points','bary','face')}
        count=len(new['face']);mask=int(old.get('visibility_mask',np.full(len(old['face']),1<<4,np.uint64))[ix[mid]])
        for key in ('points','bary','face'):arrays[key].append(new[key])
        for key,value,dtype in [('stroke_id',int(sid)+id_offset,np.int64),('layer_id',layer,np.uint8),('visibility_mask',mask,np.uint64),('parent_stroke_id',int(sid),np.int64)]:arrays[key].append(np.full(count,value,dtype))
        records.append(dict(parent_stroke_id=int(sid),stroke_id=int(sid)+id_offset,seed_face=face,seed_bary=seed.tolist(),
            seed_point=(seed@mesh['tri'][face]).tolist(),initial_tangent=initial.tolist(),initial_change_degrees=float(np.rad2deg(np.arccos(np.clip(abs(initial@reference),0,1)))),
            layer_id=layer,requested_length=total,actual_length=minus['length']+plus['length'],minus_stop=minus['reason'],plus_stop=plus['reason'],
            segments=count,obtuse_edge_transitions=minus['obtuse_edge_transitions']+plus['obtuse_edge_transitions']))
    result={k:np.concatenate(v) for k,v in arrays.items()}
    np.testing.assert_allclose(result['points'],np.einsum('nij,njk->nik',result['bary'],mesh['tri'][result['face']]),atol=1e-10,rtol=0)
    if (result['bary']<-1e-8).any() or not allowed[result['face']].all():raise ValueError('escaped carrier or authored partition')
    return result,records
