"""One anchor per connection component; global tangent trace-free tensor solve.

No per-face raw-field fidelity or parameter search. The relaxed tensor magnitude
is retained: a small objective obtained by magnitude collapse is not coherence.
"""
import runtime
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import splu
from scipy.sparse.csgraph import connected_components
from line_field import transport
from base_walk import adjacency

DEFAULTS=dict(crease_degrees=60.,degeneracy_epsilon=1e-12)

def tensor_bases(normals):
    axes=np.eye(3)[np.argmin(np.abs(normals),axis=1)]
    u=axes-np.sum(axes*normals,axis=1)[:,None]*normals
    u/=np.linalg.norm(u,axis=1,keepdims=True);v=np.cross(normals,u)
    return np.stack([(np.einsum('fi,fj->fij',u,u)-np.einsum('fi,fj->fij',v,v))/np.sqrt(2),
                     (np.einsum('fi,fj->fij',u,v)+np.einsum('fi,fj->fij',v,u))/np.sqrt(2)],axis=1)

def global_fields(mesh,partitions,cutting_normals,config=None):
    cfg=dict(DEFAULTS if config is None else config);eps=cfg['degeneracy_epsilon']
    n=np.asarray(mesh['normals']);labels=np.asarray(partitions);q=np.asarray(cutting_normals,float)
    selected=np.flatnonzero(labels>0)
    if not len(selected) or labels.shape!=(len(n),) or q.ndim!=2 or q.shape[1]!=3:raise ValueError('invalid field inputs')
    if not np.isfinite(n).all() or not np.isfinite(q).all():raise ValueError('nonfinite field inputs')
    if not np.allclose(np.linalg.norm(n[selected],axis=1),1.,atol=1e-12):raise ValueError('degenerate selected carrier normal')
    raw=np.cross(n[:,None,:],q[None,:,:]);sizes=np.linalg.norm(raw,axis=2)
    raw=np.divide(raw,sizes[:,:,None],out=np.zeros_like(raw),where=sizes[:,:,None]>eps)
    # A degenerate raw anchor has no authorized alternative orientation.
    if (sizes[selected]<=eps).any():raise ValueError('raw selected guide degeneracy; no angle substitution')
    tri=mesh['tri'];area=.5*np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1)
    bases=tensor_bases(n);pairs=[];excluded=[];trans=[];cosine=np.cos(np.deg2rad(cfg['crease_degrees']))
    for edge,fs in adjacency(mesh).items():
        if len(fs)!=2:continue
        i,j=fs
        if labels[i]<=0 or labels[i]!=labels[j]:continue
        if abs(float(n[i]@n[j]))<cosine:excluded.append((i,j));continue
        try:T=transport(mesh,i,j,edge)
        except ValueError:continue
        pairs.append((i,j));trans.append(T)
    pairs=np.asarray(pairs,np.int32).reshape(-1,2);excluded=np.asarray(excluded,np.int32).reshape(-1,2)
    trans=np.asarray(trans,float).reshape(-1,3,3)
    local=np.full(len(n),-1,int);local[selected]=np.arange(len(selected));pp=local[pairs]
    graph=sparse.coo_matrix((np.ones(2*len(pp)),(np.r_[pp[:,0],pp[:,1]],np.r_[pp[:,1],pp[:,0]])),shape=(len(selected),len(selected))).tocsr()
    count,components=connected_components(graph,directed=False)
    anchors=np.array([min(selected[components==c],key=lambda i:(-area[i],int(i))) for c in range(count)],np.int32)
    # Orthonormal Frobenius tensor coordinates. R maps neighbor j to i,
    # including reflection when local normal winding is reversed.
    if len(pairs):
        moved=trans[:,None,:,:]@bases[pairs[:,1]]@trans[:,None,:,:].transpose(0,1,3,2)
        connection=np.einsum('eaij,ebij->eab',bases[pairs[:,0]],moved)
        np.testing.assert_allclose(connection@connection.transpose(0,2,1),np.broadcast_to(np.eye(2),connection.shape),atol=1e-10)
    else:connection=np.empty((0,2,2))
    weights=(area[pairs[:,0]]+area[pairs[:,1]])/2
    rows=[];cols=[];values=[]
    for (i,j),R,w in zip(pp,connection,weights):
        for a in range(2):
            rows.extend([2*i+a,2*j+a]);cols.extend([2*i+a,2*j+a]);values.extend([w,w])
            for b in range(2):
                rows.extend([2*i+a,2*j+b]);cols.extend([2*j+b,2*i+a]);values.extend([-w*R[a,b],-w*R[a,b]])
    matrix=sparse.coo_matrix((values,(rows,cols)),shape=(2*len(selected),2*len(selected))).tocsr()
    raw_tensor=np.einsum('fli,flj->flij',raw,raw)-.5*(np.eye(3)[None,None,:,:]-np.einsum('fi,fj->fij',n,n)[:,None,:,:])
    raw_coeff=np.einsum('faij,flij->fal',bases,raw_tensor)
    coeff=np.zeros((2*len(selected),len(q)))
    fixed=(2*local[anchors,None]+np.arange(2)).reshape(-1);free=np.setdiff1d(np.arange(len(coeff)),fixed)
    coeff[fixed]=raw_coeff[anchors].reshape(-1,len(q))
    if len(free):
        rhs=-(matrix[free][:,fixed]@coeff[fixed])
        coeff[free]=splu(matrix[free][:,free].tocsc()).solve(rhs)
    if not np.isfinite(coeff).all():raise ValueError('nonfinite global tensor solve')
    residual=matrix@coeff;free_residual=float(np.abs(residual[free]).max()) if len(free) else 0.
    coeff=coeff.reshape(len(selected),2,len(q));tensor=np.einsum('fal,faij->flij',coeff,bases[selected])
    eig,vec=np.linalg.eigh(tensor);directions=vec[:,:,:,-1]
    amplitude=np.sqrt(2)*np.linalg.norm(coeff,axis=1);fallback=amplitude<=eps
    directions[fallback]=raw[selected][fallback]
    result=raw.copy();result[selected]=directions
    # Tangency and unit norm checks include all selected faces after fallback.
    np.testing.assert_allclose(np.sum(result[selected]*n[selected,None,:],axis=2),0.,atol=1e-10)
    np.testing.assert_allclose(np.linalg.norm(result[selected],axis=2),1.,atol=1e-10)
    def normalized_energy(field,edge_pairs):
        vals=[];ww=[]
        for i,j in edge_pairs:
            edge=tuple(sorted(set(mesh['faces'][i])&set(mesh['faces'][j])))
            T=transport(mesh,int(i),int(j),edge)
            dot=np.sum(field[i]*(field[j]@T.T),axis=1)
            vals.append(1-np.clip(dot*dot,0,1));ww.append((area[i]+area[j])/2)
        return np.average(vals,axis=0,weights=ww).tolist() if vals else [0.]*len(q)
    e0=normalized_energy(raw,pairs);eh=normalized_energy(result,pairs)
    excluded0=normalized_energy(raw,excluded);excludedh=normalized_energy(result,excluded)
    diff=coeff[pp[:,0]]-np.einsum('eab,ebl->eal',connection,coeff[pp[:,1]])
    relaxed=np.sum(weights[:,None]*np.sum(diff*diff,axis=1),axis=0)
    change=np.rad2deg(np.arccos(np.clip(np.abs(np.sum(raw[selected]*result[selected],axis=2)),0,1)))
    diagnostic=dict(config=cfg,components=int(count),anchor_faces=anchors.tolist(),selected_faces=len(selected),graph_pairs=len(pairs),excluded_sharp_pairs=len(excluded),
        free_residual_max=free_residual,relaxed_tensor_objective=relaxed.tolist(),normalized_graph_energy_F0=float(np.mean(e0)),normalized_graph_energy_H=float(np.mean(eh)),
        normalized_graph_energy_by_layer_F0=e0,normalized_graph_energy_by_layer_H=eh,normalized_excluded_energy_F0=excluded0,normalized_excluded_energy_H=excludedh,
        amplitude_quantiles=np.quantile(amplitude,[0,.01,.1,.5,.9,1]).tolist(),fallback_selected_face_layers=int(fallback.sum()),
        fallback_faces_by_layer=[selected[fallback[:,k]].tolist() for k in range(len(q))],selected_change_degrees_quantiles=np.quantile(change,[.5,.9,.95,1]).tolist(),
        scope='One fixed F0 anchor per unchanged transport component. Global relaxed trace-free tangent tensor solve; no dense raw fidelity. Normalized-field energy and amplitude reported separately; no true-surface or global smoothness guarantee across excluded edges.')
    saved=dict(selected_faces=selected,component=components,anchors=anchors,graph_pairs=pairs,excluded_pairs=excluded,
        connection=connection,weights=weights,tensor_basis=bases[selected],tensor_coeff=coeff,raw_tensor_coeff=raw_coeff[selected],amplitude=amplitude,fallback=fallback)
    return raw,result,diagnostic,saved
