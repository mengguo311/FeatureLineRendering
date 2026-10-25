"""Saved tensor stationarity, anchors, graph and actual path transition readback."""
import runtime
import numpy as np

def edge_transport(v,faces,i,j):
    edge=sorted(set(faces[i])&set(faces[j]));assert len(edge)==2
    a,b=v[edge];axis=b-a;axis/=np.linalg.norm(axis);inside=[]
    for f in (i,j):
        third=next(int(k) for k in faces[f] if k not in edge)
        t=v[third]-a;t-=axis*(axis@t);t/=np.linalg.norm(t);inside.append(t)
    return np.outer(axis,axis)-np.outer(inside[0],inside[1])

def audit_tensor(carrier,s,cfg):
    v=carrier['vertices'];f=carrier['faces'];tri=v[f]
    cross=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);area=.5*np.linalg.norm(cross,axis=1)
    n=cross/np.maximum(np.linalg.norm(cross,axis=1,keepdims=True),1e-30)
    labels=np.where(carrier['old_face_regions']==4,1,np.where(carrier['face_regions']==4,2,0))
    np.testing.assert_array_equal(s['partitions'],labels)
    selected=np.flatnonzero(labels>0);np.testing.assert_array_equal(s['selected_faces'],selected)
    edges={}
    for i,face in enumerate(f):
        for a,b in ((0,1),(1,2),(2,0)):edges.setdefault(tuple(sorted((int(face[a]),int(face[b])))),[]).append(i)
    graph=[];excluded=[];cosine=np.cos(np.deg2rad(cfg['crease_degrees']))
    for pair in edges.values():
        if len(pair)!=2:continue
        i,j=pair
        if labels[i]<=0 or labels[i]!=labels[j]:continue
        (excluded if abs(n[i]@n[j])<cosine else graph).append((i,j))
    assert set(graph)==set(map(tuple,s['graph_pairs']))
    assert set(excluded)==set(map(tuple,s['excluded_pairs']))
    parent={int(i):int(i) for i in selected}
    def root(i):
        while parent[i]!=i:i=parent[i]
        return i
    for i,j in graph:parent[root(j)]=root(i)
    groups={}
    for i in selected:groups.setdefault(root(int(i)),[]).append(int(i))
    anchors=sorted(min(g,key=lambda i:(-area[i],i)) for g in groups.values())
    assert anchors==sorted(s['anchors'].tolist())
    local={int(face):k for k,face in enumerate(selected)};basis=s['tensor_basis'];coeff=s['tensor_coeff']
    np.testing.assert_allclose(basis,basis.transpose(0,1,3,2),atol=1e-12)
    np.testing.assert_allclose(np.trace(basis,axis1=2,axis2=3),0.,atol=1e-12)
    np.testing.assert_allclose(np.einsum('faij,fj->fai',basis,n[selected]),0.,atol=1e-12)
    np.testing.assert_allclose(np.einsum('faij,fbij->fab',basis,basis),np.broadcast_to(np.eye(2),(len(selected),2,2)),atol=1e-12)
    tensor=np.einsum('fal,faij->flij',coeff,basis);gradient=np.zeros_like(tensor);objective=np.zeros(coeff.shape[2]);normenergy={key:[] for key in ('F0','H')}
    wsum=0.
    for i,j in graph:
        a,b=local[i],local[j];T=edge_transport(v,f,i,j);w=(area[i]+area[j])/2;wsum+=w
        diff=tensor[a]-T[None]@tensor[b]@T.T[None]
        objective+=w*np.sum(diff*diff,axis=(1,2));gradient[a]+=w*diff;gradient[b]-=w*(T.T[None]@diff@T[None])
        for key in normenergy:
            dot=np.sum(s[key][i]*(s[key][j]@T.T),axis=1);normenergy[key].append(w*(1-np.clip(dot*dot,0,1)))
    free=np.array([i for i in selected if i not in set(anchors)],int);free_indices=[local[int(i)] for i in free]
    residual=np.einsum('faij,flij->fal',basis[free_indices],gradient[free_indices])
    maxres=float(np.abs(residual).max()) if len(free) else 0.;assert maxres<1e-10
    anch_indices=[local[i] for i in anchors];a=s['F0'][anchors]
    rawQ=np.einsum('fli,flj->flij',a,a)-.5*(np.eye(3)[None,None]-np.einsum('fi,fj->fij',n[anchors],n[anchors])[:,None])
    np.testing.assert_allclose(tensor[anch_indices],rawQ,atol=1e-12)
    amplitude=np.sqrt(2)*np.linalg.norm(coeff,axis=1);np.testing.assert_allclose(amplitude,s['amplitude'],atol=1e-14)
    fallback=amplitude<=cfg['degeneracy_epsilon'];np.testing.assert_array_equal(fallback,s['fallback'])
    ev,evec=np.linalg.eigh(tensor);direction=evec[:,:,:,-1];direction[fallback]=s['F0'][selected][fallback]
    np.testing.assert_allclose(np.abs(np.sum(direction*s['H'][selected],axis=2)),1.,atol=1e-10)
    return dict(graph_pairs=len(graph),excluded_sharp_pairs=len(excluded),components=len(groups),anchor_faces=anchors,
        stationarity_residual_max=maxres,relaxed_objective=objective.tolist(),normalized_graph_energy={key:(np.sum(vals,axis=0)/wsum).tolist() for key,vals in normenergy.items()},
        amplitude_quantiles=np.quantile(amplitude,[0,.01,.1,.5,.9,1]).tolist(),fallback_selected_face_layers=int(fallback.sum()),anchors_exact=True,graph_exact=True)

def path_transitions(carrier,fields,load_paths):
    v=carrier['vertices'];faces=carrier['faces'];graph={tuple(sorted(x)) for x in fields['graph_pairs']}
    excluded={tuple(sorted(x)) for x in fields['excluded_pairs']};out={}
    for part in ('old','added'):
        for arm in ('F0','H'):
            p=load_paths(arm,part);groups={k:[] for k in ('graph','excluded_sharp','other')};world={k:[] for k in groups}
            for sid in np.unique(p['stroke_id']):
                ix=np.flatnonzero(p['stroke_id']==sid);xyz=p['points'][ix];ff=p['face'][ix]
                direction=xyz[:,1]-xyz[:,0];direction/=np.linalg.norm(direction,axis=1,keepdims=True)
                for k in range(len(ix)-1):
                    i,j=int(ff[k]),int(ff[k+1])
                    if i==j:continue
                    pair=tuple(sorted((i,j)));kind='graph' if pair in graph else 'excluded_sharp' if pair in excluded else 'other'
                    T=edge_transport(v,faces,j,i)
                    groups[kind].append(float(np.rad2deg(np.arccos(np.clip(direction[k+1]@(T@direction[k]),-1,1)))))
                    world[kind].append(float(np.rad2deg(np.arccos(np.clip(direction[k+1]@direction[k],-1,1)))))
            out[part+'_'+arm]={kind:dict(transitions=len(a),intrinsic_turn_quantiles=np.quantile(a,[.5,.9,.95,1]).tolist() if a else [],
                obtuse_transitions=int((np.asarray(a)>90).sum()),world_turn_quantiles=np.quantile(world[kind],[.5,.9,.95,1]).tolist() if a else []) for kind,a in groups.items()}
    return out
