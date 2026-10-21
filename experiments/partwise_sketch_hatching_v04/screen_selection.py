"""Manual selection of frontmost proxy faces, with saved image/camera provenance."""
import runtime
import numpy as np
from geometry import ray_surface

def visible_faces(mesh,camera,rectangle,source_region,allow_all=False):
    b=np.asarray(rectangle,float)
    width,height=camera['width'],camera['height']
    if (b.shape!=(4,) or not np.isfinite(b).all() or
        not (0<=b[0]<b[2]<=width and 0<=b[1]<b[3]<=height)):
        raise ValueError('rectangle must have finite increasing image-edge coordinates inside the image')
    if source_region not in mesh['regions']:raise ValueError('unknown source region')
    _,face,_,_=ray_surface(mesh,camera,2)
    # Image edge coordinates: displayed image [0,width] maps to pixel centers .5,1.5,...
    y,x=np.mgrid[:height*2,:width*2]
    inside=(x+.5>=b[0]*2)&(x+.5<b[2]*2)&(y+.5>=b[1]*2)&(y+.5<b[3]*2)
    hit=face[inside];hit=hit[hit>=0]
    ids=np.unique(hit[mesh['regions'][hit]==source_region]).astype(np.int32)
    if not len(ids):raise ValueError('rectangle has no visible faces in the source region')
    total=int((mesh['regions']==source_region).sum())
    if len(ids)==total and not allow_all:raise ValueError('selection must leave some faces in the source region')
    return ids,dict(face_count=len(ids),source_face_count=total,source_region=int(source_region),
        rectangle=b.tolist(),camera=camera,hidden_faces_selected=0,
        rule='frontmost 2x pixel-center ray hits only; selects whole triangles, which may extend beyond the rectangle; no hidden-face expansion')

def pick_region(mesh,camera,point):
    p=np.asarray(point,float)
    if (p.shape!=(2,) or not np.isfinite(p).all() or not
        (0<=p[0]<camera['width'] and 0<=p[1]<camera['height'])):
        raise ValueError('pick must lie inside the image')
    _,face,_,_=ray_surface(mesh,camera,2)
    fid=int(face[int(p[1]*2),int(p[0]*2)])
    if fid<0:raise ValueError('background: no visible proxy face here')
    return dict(face_id=fid,region=int(mesh['regions'][fid]),point=p.tolist(),
                rule='frontmost proxy face at the clicked 2x pixel-center ray')
