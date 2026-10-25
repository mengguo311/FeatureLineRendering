"""Restore the original two-line relation around a frozen primary line.

The facewise rotation is determined by F0 and H; there is no selected angle,
new global solve, or camera input. Only layer1 paths receive new identities.
"""
import runtime
import numpy as np
from line_field import regenerate

def restore_crossing(normals,baseline,transported,selected):
    n=np.asarray(normals);f=np.asarray(baseline);h=np.asarray(transported);sel=np.asarray(selected,bool)
    if f.shape!=h.shape or f.shape!=(len(n),2,3) or n.shape!=(len(n),3) or sel.shape!=(len(n),):
        raise ValueError('expected two tangent layers on the same carrier')
    if not np.isfinite(n[sel]).all() or not np.isfinite(f[sel]).all() or not np.isfinite(h[sel]).all():
        raise ValueError('nonfinite selected field')
    np.testing.assert_allclose(np.linalg.norm(n[sel],axis=1),1.,atol=1e-12,rtol=0)
    for field in (f,h):
        np.testing.assert_allclose(np.linalg.norm(field[sel],axis=2),1.,atol=1e-12,rtol=0)
        np.testing.assert_allclose(np.sum(field[sel]*n[sel,None,:],axis=2),0.,atol=1e-12,rtol=0)
    a=f[sel,0];b=f[sel,1];c=h[sel,0]
    cosine=np.sum(a*b,axis=1);sine=np.sum(n[sel]*np.cross(a,b),axis=1)
    j=h.copy()
    j[sel,1]=cosine[:,None]*c+sine[:,None]*np.cross(n[sel],c)
    return j

def replace_second_layer(mesh,original,h_paths,h_records,allowed,j_field,id_offset):
    if 'layer_id' not in original or 'layer_id' not in h_paths:raise ValueError('explicit two-layer assets required')
    old_second={k:v[original['layer_id']==1] for k,v in original.items()}
    second,records=regenerate(mesh,old_second,allowed,j_field,id_offset)
    primary=h_paths['layer_id']==0
    if set(second)!=set(h_paths):raise ValueError('path schemas differ')
    paths={k:np.concatenate([v[primary],second[k]]) for k,v in h_paths.items()}
    primary_ids=set(int(x) for x in h_paths['stroke_id'][primary]);second_ids=set(int(x) for x in second['stroke_id'])
    if primary_ids&second_ids:raise ValueError('new identities collide with frozen primary')
    return paths,[dict(r) for r in h_records if r['layer_id']==0]+records
