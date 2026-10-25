"""A single bounded bilateral-normal/Jacobi carrier diagnostic, not truth geometry."""
import runtime
import numpy as np
from geometry import mesh_data

DEFAULTS=dict(crease_degrees=60.,normal_sigma_degrees=30.,vertex_iterations=3,
              relaxation=.5,relative_cap=.1,max_displacement=.002)

def denoise(mesh,partitions,config=None):
    cfg=dict(DEFAULTS if config is None else config)
    v=mesh['vertices'];faces=mesh['faces'];normals=mesh['normals'];tri=mesh['tri']
    labels=np.asarray(partitions);assert labels.shape==(len(faces),)
    edges={};incident=[[] for _ in v];neighbors=[set() for _ in v]
    for i,face in enumerate(faces):
        for vertex in face:incident[int(vertex)].append(i)
        for j,k in ((0,1),(1,2),(2,0)):
            a,b=sorted((int(face[j]),int(face[k])));edges.setdefault((a,b),[]).append(i)
            neighbors[a].add(b);neighbors[b].add(a)
    selected=np.zeros(len(v),bool);selected[np.unique(faces[labels>0])]=True
    protected=~selected;boundary=np.zeros(len(v),bool);sharp=np.zeros(len(v),bool)
    face_neighbors=[{i} for i in range(len(faces))]
    cosine=np.cos(np.deg2rad(cfg['crease_degrees']))
    for edge,fs in edges.items():
        if len(fs)!=2 or labels[fs[0]]<=0 or not (labels[fs]==labels[fs[0]]).all():
            boundary[list(edge)]=True;continue
        i,j=fs;dot=abs(float(normals[i]@normals[j]))
        if dot<cosine:sharp[list(edge)]=True;continue
        face_neighbors[i].add(j);face_neighbors[j].add(i)
    protected|=boundary|sharp
    areas=.5*np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1)
    degenerate=areas<=1e-14;protected[np.unique(faces[degenerate])]=True
    centers=tri.mean(1);filtered=normals.copy();sigma=np.deg2rad(cfg['normal_sigma_degrees'])
    for i in np.flatnonzero(labels>0):
        ids=np.array(sorted(face_neighbors[i]),int);dots=normals[ids]@normals[i]
        aligned=normals[ids]*np.where(dots<0,-1.,1.)[:,None]
        theta=np.arccos(np.clip(np.abs(dots),0,1))
        edge_lengths=np.linalg.norm(tri[i]-np.roll(tri[i],1,axis=0),axis=1)
        spatial=max(float(np.median(edge_lengths)),1e-12)
        w=areas[ids]*np.exp(-.5*(theta/sigma)**2-.5*np.sum((centers[ids]-centers[i])**2,axis=1)/spatial**2)
        total=(aligned*w[:,None]).sum(0);length=np.linalg.norm(total)
        if length>1e-14:filtered[i]=total/length
    caps=np.zeros(len(v))
    for i in np.flatnonzero(~protected):
        lengths=np.linalg.norm(v[sorted(neighbors[i])]-v[i],axis=1)
        caps[i]=min(cfg['max_displacement'],cfg['relative_cap']*float(np.median(lengths)))
    current=v.copy()
    for _ in range(cfg['vertex_iterations']):
        centers=current[faces].mean(1);proposal=current.copy()
        for i in np.flatnonzero(~protected):
            ids=np.array(incident[i]);n=filtered[ids];w=areas[ids]
            offsets=np.einsum('ij,ij->i',centers[ids]-current[i],n)
            delta=cfg['relaxation']*(w[:,None]*offsets[:,None]*n).sum(0)/w.sum()
            displacement=current[i]+delta-v[i];length=np.linalg.norm(displacement)
            if length>caps[i]:displacement*=caps[i]/length
            proposal[i]=v[i]+displacement
        current=proposal
    # Reject affected vertices rather than shrinking the whole experiment until a metric passes.
    rejected=np.zeros(len(v),bool)
    for _ in range(10):
        t=current[faces];cross=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0])
        bad=(np.einsum('ij,ij->i',cross,normals)<=0)&~degenerate
        if not bad.any():break
        ids=np.unique(faces[bad]);current[ids]=v[ids];rejected[ids]=True
    else:raise ValueError('could not preserve triangle orientation')
    result=mesh_data(current,faces.copy(),mesh['regions'].copy())
    displacement=np.linalg.norm(current-v,axis=1)
    assert (displacement<=caps+1e-12).all()
    np.testing.assert_array_equal(current[protected],v[protected])
    return result,dict(protected=protected,boundary=boundary,sharp=sharp,selected=selected,
        rejected_inversion=rejected,cap=caps,displacement=displacement,filtered_normals=filtered)
