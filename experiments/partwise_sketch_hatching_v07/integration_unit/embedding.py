"""Move immutable material path coordinates to an already saved carrier.

No smoothing, field estimation, integration, path deletion or gap repair.
The correspondence is valid only for identical ordered triangles and labels.
"""
import runtime
import numpy as np

def migrate(paths, original, target, id_offset):
    if not np.array_equal(original['faces'],target['faces']):
        raise ValueError('ordered carrier topology changed')
    if not np.array_equal(original['regions'],target['regions']):
        raise ValueError('carrier labels changed')
    if original['vertices'].shape!=target['vertices'].shape:
        raise ValueError('carrier vertex correspondence changed')
    if not np.isfinite(target['vertices']).all():raise ValueError('nonfinite carrier')
    bary=paths['bary'];faces=paths['face']
    if (bary<-1e-8).any():raise ValueError('invalid barycentric anchor')
    np.testing.assert_allclose(bary.sum(2),1.,atol=1e-10,rtol=0)
    np.testing.assert_allclose(paths['points'],np.einsum('nij,njk->nik',bary,original['tri'][faces]),atol=1e-10,rtol=0)
    result={k:v.copy() for k,v in paths.items()}
    result['points']=np.einsum('nij,njk->nik',bary,target['tri'][faces])
    ids=np.unique(paths['stroke_id']);records=[]
    new_ids=id_offset+np.arange(len(ids),dtype=np.int64)
    if np.isin(new_ids,ids).any():raise ValueError('identity collision')
    for sid,new in zip(ids,new_ids):
        ix=np.flatnonzero(paths['stroke_id']==sid)
        result['stroke_id'][ix]=new
        for p in (paths,result):
            q=p['points'][ix]
            np.testing.assert_allclose(q[:-1,1],q[1:,0],atol=1e-8,rtol=0)
            if (np.linalg.norm(q[:,1]-q[:,0],axis=1)<=0).any():raise ValueError('collapsed segment; never delete')
        displacement=np.linalg.norm(result['points'][ix]-paths['points'][ix],axis=2)
        records.append(dict(stroke_id=int(new),immediate_H_parent_id=int(sid),
            original_parent_id=int(paths.get('parent_stroke_id',paths['stroke_id'])[ix[0]]),
            segments=len(ix),max_endpoint_displacement=float(displacement.max()),
            moved=bool((displacement>1e-12).any()),
            scope='Material face/bary migration; inherited stops are not a new successful walk.'))
    return result,records
