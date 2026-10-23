"""Add visible authored faces; retain original source rows and old stroke arrays."""
import runtime
import numpy as np
from hatching import generate_layers, layer_ids, visibility_masks
from render import _coverage

def visible_additions(face_image,face_regions,polygon,scale=2):
    face=np.asarray(face_image);labels=np.asarray(face_regions);poly=np.asarray(polygon,float)
    if face.ndim!=2 or poly.ndim!=2 or poly.shape[1]!=2 or len(poly)<3 or not np.isfinite(poly).all():
        raise ValueError('finite polygon and first-hit face image required')
    yy,xx=np.mgrid[:face.shape[0],:face.shape[1]];x=(xx+.5)/scale;y=(yy+.5)/scale
    inside=np.zeros(face.shape,bool)
    for a,b in zip(poly,np.roll(poly,-1,axis=0)):
        if a[1]==b[1]:continue
        inside ^= ((a[1]>y)!=(b[1]>y)) & (x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0])
    hit=face[inside & (face>=0)]
    return np.unique(hit[labels[hit]==3]).astype(np.int32)

def remap_regions(trace,face_regions):
    face=np.asarray(trace['proxy_face']);labels=np.asarray(face_regions)
    if face.ndim!=1 or (face>=len(labels)).any() or (face < -1).any():raise ValueError('invalid proxy face IDs')
    out=np.zeros(len(face),np.int32);good=face>=0;out[good]=labels[face[good]]
    return out

def extend_paths(mesh,old,added_faces,style):
    ids=np.unique(np.asarray(added_faces,np.int32))
    if len(ids)==0:return {k:v.copy() for k,v in old.items()},{k:v[:0].copy() for k,v in old.items()}
    if (ids<0).any() or (ids>=len(mesh['faces'])).any() or (mesh['regions'][ids]!=3).any():
        raise ValueError('only previously unselected upper-region faces can be added')
    labels=np.ones(len(mesh['faces']),np.int32);labels[ids]=4
    new,_=generate_layers(dict(mesh,regions=labels),4,style)
    new['stroke_id']=new['stroke_id']-new['stroke_id'].min()+old['stroke_id'].max()+1
    if 'visibility_mask' in old:new['visibility_mask']=visibility_masks(new,4)
    if 'layer_id' in old:new['layer_id']=layer_ids(new)
    if set(new)!=set(old):raise ValueError('new and old path field contract differs')
    return {k:np.concatenate([old[k],new[k]]) for k in old},new

def render_pair(old_mesh,new_mesh,old,added,meta,camera):
    a=_coverage(old_mesh,{4:old},meta['styles'],camera,2)
    high=np.maximum.reduce(list(a['coverage'][4].values())).astype(np.float32)*meta['styles']['4'].get('ink_strength',.8)
    if len(added['points']):
        b=_coverage(new_mesh,{4:added},meta['styles'],camera,2)
        new_high=np.maximum.reduce(list(b['coverage'][4].values())).astype(np.float32)*meta['styles']['4'].get('ink_strength',.8)
    else:b=a;new_high=np.zeros_like(high)
    low=lambda x:x.reshape(camera['height'],2,camera['width'],2).mean((1,3))
    return dict(old=low(high),new=low(np.maximum(high,new_high))),dict(old_regions=a['regions'],regions=b['regions'],
        depth=b['depth'],proxy=b['proxy'],added_ink=low(new_high),old_hi=high,added_hi=new_high)
