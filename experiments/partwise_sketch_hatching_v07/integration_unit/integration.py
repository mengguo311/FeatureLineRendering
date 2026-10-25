"""Integrate immutable material seeds on a selected carrier, then pull back to O.

The initial tangent is pushed by the triangle's affine differential. Requested
world arclength is the original seed budget, not a length remeasured on C.
The walker and all its boundary/degeneracy stops are inherited unchanged.
"""
import runtime
import numpy as np
from base_walk import walk, adjacency, bary_derivative

def transport_tangent(original, carrier, face, tangent):
    tangent=np.asarray(tangent,float)
    if np.array_equal(original['tri'][face],carrier['tri'][face]):return tangent.copy()
    db=bary_derivative(original['tri'][face],tangent)
    if db is None:raise ValueError('degenerate source seed face')
    mapped=db@carrier['tri'][face];norm=np.linalg.norm(mapped)
    if not np.isfinite(norm) or norm<1e-12:raise ValueError('degenerate mapped seed tangent')
    return mapped/norm

def integrate_saved(original,carrier,parents,seeds,allowed,id_offset=None):
    if not np.array_equal(original['faces'],carrier['faces']):raise ValueError('changed ordered topology')
    if not np.array_equal(original['regions'],carrier['regions']):raise ValueError('changed labels')
    if not np.isfinite(carrier['vertices']).all():raise ValueError('nonfinite carrier')
    expected=set(map(int,np.unique(parents['stroke_id'])))
    if expected!=set(int(r['parent_stroke_id']) for r in seeds) or len(seeds)!=len(expected):raise ValueError('seed inventory mismatch')
    edges=adjacency(carrier);arrays={k:[] for k in ('points','bary','face','stroke_id','layer_id','visibility_mask','parent_stroke_id')};records=[]
    for rank,r in enumerate(seeds):
        sid=int(r['parent_stroke_id']);ix=np.flatnonzero(parents['stroke_id']==sid)
        face=int(r['seed_face']);bary=np.asarray(r['seed_bary'],float);length=float(r['requested_length'])
        initial=transport_tangent(original,carrier,face,r['initial_tangent'])
        minus=walk(carrier,face,bary,-initial,length/2,allowed,edges)
        plus=walk(carrier,face,bary,initial,length/2,allowed,edges)
        new={k:np.concatenate([minus[k][::-1,::-1] if k in ('points','bary') else minus[k][::-1],plus[k]]) for k in ('points','bary','face')}
        count=len(new['face']);newid=int(r['stroke_id']) if id_offset is None else int(id_offset+rank)
        layer=parents.get('layer_id',np.zeros(len(parents['face']),np.uint8))[ix]
        masks=parents.get('visibility_mask',np.full(len(parents['face']),16,np.uint64))[ix]
        if len(np.unique(layer))!=1 or len(np.unique(masks))!=1:raise ValueError('nonuniform parent metadata')
        for k in ('points','bary','face'):arrays[k].append(new[k])
        for k,value,dtype in [('stroke_id',newid,np.int64),('layer_id',int(layer[0]),np.uint8),('visibility_mask',int(masks[0]),np.uint64),('parent_stroke_id',sid,np.int64)]:arrays[k].append(np.full(count,value,dtype))
        pulled=np.einsum('nij,njk->nik',new['bary'],original['tri'][new['face']])
        records.append(dict(parent_stroke_id=sid,stroke_id=newid,baseline_B_id=int(r['stroke_id']),seed_face=face,seed_bary=bary.tolist(),
            initial_tangent_original=r['initial_tangent'],initial_tangent_generation=initial.tolist(),requested_length=length,
            generation_length=minus['length']+plus['length'],pulled_length=float(np.linalg.norm(pulled[:,1]-pulled[:,0],axis=1).sum()),
            minus_stop=minus['reason'],plus_stop=plus['reason'],minus_length=minus['length'],plus_length=plus['length'],segments=count,
            empty=count==0,scope='Fixed material seed and original request; carrier differential and metric are part of intervention.'))
    generated={k:np.concatenate(v) for k,v in arrays.items()}
    if (generated['bary']<-1e-8).any() or not allowed[generated['face']].all():raise ValueError('escaped partition')
    np.testing.assert_allclose(generated['points'],np.einsum('nij,njk->nik',generated['bary'],carrier['tri'][generated['face']]),atol=1e-10,rtol=0)
    pulled={k:v.copy() for k,v in generated.items()}
    pulled['points']=np.einsum('nij,njk->nik',pulled['bary'],original['tri'][pulled['face']])
    return generated,pulled,records
