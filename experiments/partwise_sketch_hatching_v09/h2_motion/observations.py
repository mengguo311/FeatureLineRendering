"""Fixed parent-interval samples and actual same-ID ink observations.

Trim boundaries split quadrature cells exactly. Planned removal is never a
temporal dropout. D has its own pre-stop path domain, not U's displaced points.
"""
import runtime
import numpy as np
from scipy import ndimage
from geometry import project

THRESHOLD=1/255
def interval_samples(paths,trim,step=.005):
    removed={r['parent_segment']:r['removed_t'] for r in trim.get('intervals',[])}
    values={k:[] for k in ('point','face','bary','parent','segment','t','weight','planned')}
    for i,(p,b,f,sid) in enumerate(zip(paths['points'],paths['bary'],paths['face'],paths['stroke_id'])):
        ll=float(np.linalg.norm(p[1]-p[0]));rr=removed.get(i,[])
        cuts=sorted(set([0.,1.]+[float(t) for interval in rr for t in interval]))
        for lo,hi in zip(cuts[:-1],cuts[1:]):
            if hi-lo<1e-12:continue
            planned=any(l<=(lo+hi)/2<=h for l,h in rr)
            n=max(1,int(np.ceil(ll*(hi-lo)/step)));tt=lo+(np.arange(n)+.5)/n*(hi-lo)
            for t in tt:
                for k,v in dict(point=(1-t)*p[0]+t*p[1],face=int(f),bary=(1-t)*b[0]+t*b[1],parent=int(sid),segment=i,t=t,weight=ll*(hi-lo)/n,planned=planned).items():values[k].append(v)
    return {k:np.asarray(v,dtype=(bool if k=='planned' else np.int64 if k in ('face','parent','segment') else float)) for k,v in values.items()}

def make_scene(mesh):
    import open3d as o3d
    scene=o3d.t.geometry.RaycastingScene(nthreads=1)
    scene.add_triangles(o3d.core.Tensor(mesh['vertices'].astype(np.float32)),o3d.core.Tensor(mesh['faces'].astype(np.uint32)))
    return scene

def observe(mesh,samples,camera,tracked,increment,strength,scene=None):
    import open3d as o3d
    points=samples['point'];uv,z=project(points,camera)
    E=np.asarray(camera['extrinsic']);origin=-np.linalg.inv(E[:3,:3])@E[:3,3]
    scene=make_scene(mesh) if scene is None else scene
    rays=np.c_[np.broadcast_to(origin,points.shape),(points-origin)/z[:,None]].astype(np.float32)
    hit=scene.cast_rays(o3d.core.Tensor(rays),nthreads=1)
    depth=hit['t_hit'].numpy();faces=hit['primitive_ids'].numpy();valid=faces<len(mesh['faces'])
    owner=np.zeros(len(points),bool);owner[valid]=mesh['regions'][faces[valid]]==5
    inside=(z>.2)&(uv[:,0]>=0)&(uv[:,0]<camera['width'])&(uv[:,1]>=0)&(uv[:,1]<camera['height'])
    visible=inside&owner&(abs(depth-z)<=.004)
    own=np.zeros(len(points));aa=(uv+.5)*2-.5
    for sid in np.unique(samples['parent']):
        selected=samples['parent']==sid;layer=tracked.get(f'5:{int(sid)}')
        if layer is not None:
            own[selected]=ndimage.map_coordinates(layer.astype(np.float32),[aa[selected,1],aa[selected,0]],order=1,mode='constant',cval=0)*strength
    inc=ndimage.map_coordinates(increment,[uv[:,1],uv[:,0]],order=1,mode='constant',cval=0)
    return dict(visible=visible,inside=inside,depth_rejected=inside&~visible,own=own,increment=inc,uv=uv,depth=z)

def frame_summary(samples,obs):
    w=samples['weight'];v=obs['visible'];p=samples['planned'];ink=obs['own']>THRESHOLD
    retained=v&~p
    return dict(raw_parent_length=float(w.sum()),planned_trim_length=float(w[p].sum()),retained_length=float(w[~p].sum()),
        raw_proxy_visible_length=float(w[v].sum()),planned_visible_length=float(w[v&p].sum()),retained_proxy_visible_length=float(w[retained].sum()),
        retained_visible_without_same_id_ink_length=float(w[retained&~ink].sum()),retained_visible_with_same_id_ink_length=float(w[retained&ink].sum()),
        retained_own_present_no_composite_increment_length=float(w[retained&ink&(obs['increment']<=THRESHOLD)].sum()),
        sample_count=len(w),retained_visible_sample_count=int(retained.sum()))

def transition(samples,a,b):
    w=samples['weight'];r=~samples['planned'];joint=r&a['visible']&b['visible']
    ai=a['own']>THRESHOLD;bi=b['own']>THRESHOLD
    drop=joint&ai&~bi;reappear=joint&~ai&bi
    cancel=joint&ai&bi&(a['increment']>THRESHOLD)&(b['increment']<=THRESHOLD)
    result=dict(joint_retained_visible_length=float(w[joint].sum()),joint_retained_visible_samples=int(joint.sum()),
        source_own_joint_length=float(w[joint&ai].sum()),destination_own_joint_length=float(w[joint&bi].sum()),
        proper_visibility_exit_length=float(w[r&a['visible']&~b['visible']].sum()),proper_visibility_entry_length=float(w[r&~a['visible']&b['visible']].sum()))
    for name,mask in [('own_dropout',drop),('own_reappearance',reappear),('composite_cancellation',cancel)]:
        result[name+'_count']=int(mask.sum());result[name+'_length']=float(w[mask].sum());result[name+'_sample_indices']=np.flatnonzero(mask).tolist()
    return result
