"""Frozen finite camera trajectory and descriptive own-stroke observations."""
import runtime
from runtime import js,sha
import json
from pathlib import Path
import numpy as np
from geometry import orbit_camera,project

def trajectory():
    out=dict(schema='chair_motion_v1',fps=12,scope='finite half orbit and dolly; not GS-unseen or physical temporal certification')
    for name,n in [('orbit',61),('zoom',21)]:
        rows=[]
        for i in range(n):
            a=float(61+3*i) if name=='orbit' else 241.
            d=5.1 if name=='orbit' else round(5.1-.06*min(i,20-i),2)
            rows.append(dict(index=i,time_seconds=i/12,azimuth=a,elevation=24.,distance=d,
                camera=orbit_camera(a,24.,d,384),exposure='previously_exposed' if (a in (61.,241.) and d==5.1) else 'reserved_at_unit003_freeze_not_certified_GS_unseen'))
        out[name]=rows
    return out

def save_trajectory(path,plan):
    if plan!=trajectory():raise ValueError('trajectory differs from frozen specification')
    js(path,plan)

def load_trajectory(path):
    plan=json.loads(Path(path).read_text())
    if plan!=trajectory():raise ValueError('trajectory differs from frozen specification')
    return plan

def select_samples(mesh,paths,counts=None):
    counts={4:6,5:3,1:3} if counts is None else counts
    chosen=[];anchors=[]
    for region,count in counts.items():
        p=paths[region];ids=np.unique(p['stroke_id'])
        if len(ids)<count:raise ValueError('insufficient paths for frozen sampling')
        rank=np.rint(np.linspace(0,len(ids)-1,count)).astype(int)
        for stroke in ids[rank]:
            key=f'{region}:{int(stroke)}';chosen.append(key)
            index=np.flatnonzero(p['stroke_id']==stroke)
            lengths=np.linalg.norm(p['points'][index,1]-p['points'][index,0],axis=1)
            total=float(lengths.sum());cumulative=np.cumsum(lengths)
            if total<=0:raise ValueError('zero-length selected path')
            for fraction in (.2,.5,.8):
                distance=fraction*total;j=min(int(np.searchsorted(cumulative,distance,side='right')),len(index)-1)
                previous=cumulative[j-1] if j else 0.;t=float((distance-previous)/lengths[j]);k=int(index[j])
                bary=(1-t)*p['bary'][k,0]+t*p['bary'][k,1]
                anchors.append(dict(key=key,region=region,stroke_id=int(stroke),fraction=fraction,segment_index=k,
                    face=int(p['face'][k]),bary=bary.tolist(),point=(bary@mesh['tri'][p['face'][k]]).tolist(),
                    visibility_mask=int(p.get('visibility_mask',np.full(len(p['face']),1<<region))[k])))
    return dict(selection='uniform ranks in sorted stable IDs; concatenated stored-segment arclength, gaps never interpolated',
        fractions=[.2,.5,.8],selected_paths=chosen,anchors=anchors,scope='Own proxy-stroke samples; no original-Gaussian per-path source certification')

def classify_visibility(in_frame,z,hit_z,region,masks):
    in_frame=np.asarray(in_frame);z=np.asarray(z);hit_z=np.asarray(hit_z);region=np.asarray(region)
    result=np.full(len(z),'visible',dtype='<U24')
    bits=np.left_shift(np.uint64(1),region.astype(np.uint64));label_ok=(bits&np.asarray(masks,np.uint64))!=0
    result[~label_ok]='label_rejected'
    delta=np.full(len(z),np.inf);np.subtract(z,hit_z,out=delta,where=np.isfinite(hit_z))
    result[np.abs(delta)>.004]='depth_rejected'
    result[~np.isfinite(hit_z)]='no_proxy_hit'
    result[~in_frame]='offscreen';result[z<=.2]='behind'
    return result

def transition_counts(a,b,ink_a,ink_b):
    a=np.asarray(a);b=np.asarray(b);joint=(a=='visible')&(b=='visible')
    on_a=np.asarray(ink_a)>1/255;on_b=np.asarray(ink_b)>1/255
    return dict(joint_visible=int(joint.sum()),visible_ink_dropouts=int((joint&on_a&~on_b).sum()),
        visible_ink_reappearances=int((joint&~on_a&on_b).sum()),
        occlusion_entries=int(((a=='visible')&(b=='depth_rejected')).sum()),
        occlusion_exits=int(((a=='depth_rejected')&(b=='visible')).sum()))

def observe(mesh,samples,camera,data,support,styles,scene):
    import open3d as o3d
    points=np.asarray([a['point'] for a in samples['anchors']]);uv,z=project(points,camera)
    E=np.asarray(camera['extrinsic']);R=E[:3,:3];origin=-np.linalg.inv(R)@E[:3,3]
    # Rays are normalized to camera z=1 so t_hit is camera-axis depth.
    local=np.column_stack(((uv[:,0]-camera['cx'])/camera['fx'],(uv[:,1]-camera['cy'])/camera['fy'],np.ones(len(z))))
    direction=local@np.linalg.inv(R).T
    rays=np.column_stack((np.broadcast_to(origin,direction.shape),direction)).astype(np.float32)
    result=scene.cast_rays(o3d.core.Tensor(rays),nthreads=1)
    depth=result['t_hit'].numpy().astype(float);faces=result['primitive_ids'].numpy().astype(np.int64)
    labels=np.zeros(len(z),np.int32);hit=np.isfinite(depth);labels[hit]=mesh['regions'][faces[hit]]
    size=camera['width'];inside=(uv[:,0]>=0)&(uv[:,1]>=0)&(uv[:,0]<=size-1)&(uv[:,1]<=size-1)
    status=classify_visibility(inside,z,depth,labels,[a['visibility_mask'] for a in samples['anchors']])
    low=lambda v:v.reshape(size,2,size,2).mean((1,3))
    own_pre=[];own_post=[]
    for key in samples['selected_paths']:
        region=int(key.split(':')[0]);mask=data['tracked'][key].astype(np.float32)*styles[str(region)].get('ink_strength',.8)
        own_pre.append(low(mask));own_post.append(low(mask)*support if region==4 else low(mask))
    own_pre=np.asarray(own_pre);own_post=np.asarray(own_post)
    # Bilinear sampling at projected material anchors; includes actual AA coverage,
    # never substitutes ink from neighboring strokes or contours.
    def sample(image,x,y):
        x=float(np.clip(x,0,size-1));y=float(np.clip(y,0,size-1));ix=int(np.floor(x));iy=int(np.floor(y))
        jx=min(ix+1,size-1);jy=min(iy+1,size-1);tx=x-ix;ty=y-iy
        return float((1-tx)*(1-ty)*image[iy,ix]+tx*(1-ty)*image[iy,jx]+(1-tx)*ty*image[jy,ix]+tx*ty*image[jy,jx])
    pre=[];post=[]
    for a,(x,y),valid in zip(samples['anchors'],uv,inside&(z>.2)):
        k=samples['selected_paths'].index(a['key'])
        pre.append(sample(own_pre[k],x,y) if valid else 0.);post.append(sample(own_post[k],x,y) if valid else 0.)
    return dict(uv=uv,z=z,hit_z=depth,hit_region=labels,status=status,pre=np.asarray(pre),post=np.asarray(post),
                own_pre=own_pre,own_post=own_post)
