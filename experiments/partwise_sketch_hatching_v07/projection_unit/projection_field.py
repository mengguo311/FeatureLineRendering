"""Two fixed macro-guide lifts on the SAME carrier; no fitting or diffusion.

P0 is the original plane-slicing tangent. P1 projects the corresponding
macro-plane tangent into each local tangent plane. Neither is surface truth.
"""
import runtime
import numpy as np

DEFAULTS=dict(degeneracy_epsilon=1e-12)

def projected_fields(mesh,partitions,cutting_normals,reference_normal,config=None):
    cfg=dict(DEFAULTS if config is None else config);eps=cfg['degeneracy_epsilon']
    n=np.asarray(mesh['normals'],float);q=np.asarray(cutting_normals,float)
    n0=np.asarray(reference_normal,float);labels=np.asarray(partitions)
    if n0.shape!=(3,) or q.ndim!=2 or q.shape[1]!=3 or labels.shape!=(len(n),):
        raise ValueError('invalid fixed guide dimensions')
    if not np.isfinite(n0).all() or np.linalg.norm(n0)<=eps or not np.isfinite(q).all():
        raise ValueError('invalid fixed guide')
    n0=n0/np.linalg.norm(n0)
    guide=np.cross(n0[None,:],q);size=np.linalg.norm(guide,axis=1)
    if (size<=eps).any():raise ValueError('macro guide degenerate; no alternative angle search')
    guide=guide/size[:,None]
    raw=np.cross(n[:,None,:],q[None,:,:]);length=np.linalg.norm(raw,axis=2)
    raw=np.divide(raw,length[:,:,None],out=np.zeros_like(raw),where=length[:,:,None]>eps)
    projected=guide[None,:,:]-np.einsum('fi,li->fl',n,guide)[:,:,None]*n[:,None,:]
    norm=np.linalg.norm(projected,axis=2);fallback=norm<=eps
    projected=np.divide(projected,norm[:,:,None],out=np.zeros_like(projected),where=~fallback[:,:,None])
    projected[fallback]=raw[fallback]
    selected=labels>0;tri=mesh['tri'];area=.5*np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1)
    change=np.rad2deg(np.arccos(np.clip(np.abs(np.sum(raw*projected,axis=2)),0,1)))
    layers=[]
    for layer in range(len(q)):
        mask=selected&fallback[:,layer]
        layers.append(dict(layer=layer,fallback_selected_faces=int(mask.sum()),fallback_face_ids=np.flatnonzero(mask).tolist(),
            fallback_selected_area=float(area[mask].sum()),fallback_area_fraction=float(area[mask].sum()/area[selected].sum()),
            raw_degenerate_selected_faces=int((selected&(length[:,layer]<=eps)).sum()),
            projected_norm_selected_quantiles=np.quantile(norm[selected,layer],[0,.1,.5,.9,1]).tolist()))
    diagnostic=dict(config=cfg,reference_normal=n0.tolist(),fixed_tangent_guides=guide.tolist(),
        selected_faces=int(selected.sum()),fallback_selected_face_layers=int(fallback[selected].sum()),layers=layers,
        selected_change_degrees_quantiles=np.quantile(change[selected],[.5,.9,.95,1]).tolist(),
        scope='Fixed macro guide projection only; no carrier edits, regularization, angle fitting or claim of globally coherent field. Degenerate projection falls back to same-face P0.')
    return raw,projected,diagnostic
