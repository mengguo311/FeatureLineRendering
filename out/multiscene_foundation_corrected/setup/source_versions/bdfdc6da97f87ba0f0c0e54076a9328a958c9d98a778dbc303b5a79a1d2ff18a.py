"""Local image-evidence probes; no curve, field, or scene-specific optimization."""
import ctypes
import hashlib
from pathlib import Path
import cv2
import numpy as np
from scipy.ndimage import distance_transform_edt
from scipy.ndimage import map_coordinates
from scipy.optimize import linear_sum_assignment
from .foundation import project_jacobian


def axial_angle(a,b):
    a=np.asarray(a,float);b=np.asarray(b,float)
    denominator=np.linalg.norm(a,axis=-1)*np.linalg.norm(b,axis=-1)
    cosine=np.abs(np.sum(a*b,axis=-1))/np.maximum(denominator,1e-30)
    return np.degrees(np.arccos(np.clip(cosine,0,1)))


def image_hessian(J,normals):
    covectors=np.einsum('vij,vi->vj',np.asarray(J,float),np.asarray(normals,float))
    H=covectors.T@covectors
    eigenvalues,eigenvectors=np.linalg.eigh(H)
    return H,np.maximum(eigenvalues,0),eigenvectors[:,0]


def edge_field(rgb,cfg):
    params=cfg['detector'];gray=cv2.cvtColor(np.round(np.clip(rgb,0,1)*255).astype('u1'),cv2.COLOR_RGB2GRAY)
    gray=cv2.GaussianBlur(gray,(0,0),params['sigma'])
    edge=cv2.Canny(gray,*params['canny'],apertureSize=params['aperture'],L2gradient=params['L2gradient'])>0
    y,x=np.indices(edge.shape);e=edge.astype(float);k=params['tangent_window']
    def box(v):return cv2.boxFilter(v,-1,(k,k),normalize=False,borderType=cv2.BORDER_CONSTANT)
    count=box(e);denom=np.maximum(count,1);mx=box(x*e)/denom;my=box(y*e)/denom
    xx=box(x*x*e)/denom-mx*mx;yy=box(y*y*e)/denom-my*my;xy=box(x*y*e)/denom-mx*my
    gap=np.sqrt((xx-yy)**2+4*xy*xy);major=(xx+yy+gap)/2;minor=(xx+yy-gap)/2
    valid=edge&(count>=params['min_tangent_pixels'])&(major>0)&(minor<=major*params['tangent_eigen_ratio_max'])
    angle=.5*np.arctan2(2*xy,xx-yy);tangent=np.stack([np.cos(angle),np.sin(angle)],axis=2)
    tangent[~valid]=np.nan
    if edge.any():
        dt,nearest=distance_transform_edt(~edge,return_indices=True)
        direction=tangent[nearest[0],nearest[1]]
        nearest_uv=np.stack([nearest[1],nearest[0]],axis=2).astype(float)
    else:
        dt=np.full(edge.shape,np.inf);direction=np.full((*edge.shape,2),np.nan)
        nearest_uv=np.full((*edge.shape,2),np.nan)
    return dict(edge=edge,dt=dt,tangent=tangent,nearest_tangent=direction,
                nearest_uv=nearest_uv,domain=np.ones(edge.shape,bool))


def sample_queries(field,view,cfg,negative=False,foreground=None):
    mask=(field['dt']>=cfg['queries']['negative_min_dt'])&foreground if negative else field['edge']
    y,x=np.nonzero(mask);seed=cfg['queries']['seed'];grid=cfg['queries']['grid']
    candidates=[]
    for yy,xx in zip(y,x):
        digest=hashlib.sha256(f'{seed}:query:{view}:{yy}:{xx}'.encode()).hexdigest()
        candidates.append((digest,int(xx),int(yy)))
    candidates.sort();cells=set();result=[]
    maximum=cfg['queries']['negative_per_view'] if negative else cfg['queries']['max_per_view']
    for digest,xx,yy in candidates:
        cell=(xx//grid,yy//grid)
        if cell in cells:continue
        cells.add(cell);result.append(dict(query=digest,view=view,pixel=[xx,yy],negative=negative))
        if len(result)==maximum:break
    return result


def shift_field(field,view_number,cfg):
    d=cfg['controls']['shift_pixels'];dx=d*((view_number%3)-1);dy=d*(((view_number+1)%3)-1)
    result={k:np.roll(v,(dy,dx),axis=(0,1)) for k,v in field.items()}
    result['domain']=np.ones_like(field['domain'])
    result['domain'][:d]=False;result['domain'][-d:]=False
    result['domain'][:,:d]=False;result['domain'][:,-d:]=False
    return result


def _minima(values):
    minima=[];i=0
    while i<len(values):
        j=i
        while j+1<len(values) and values[j+1]==values[i]:j+=1
        left=values[i-1] if i else np.inf;right=values[j+1] if j+1<len(values) else np.inf
        if np.isfinite(values[i]) and values[i]<=left and values[i]<=right:
            minima.append((i,j))
        i=j+1
    return minima


def ray_profile(camera,pixel,box,delta,evaluate,cfg):
    K=np.asarray(camera['K'],float);c2w=np.linalg.inv(camera['w2c']);origin=c2w[:3,3]
    direction=c2w[:3,:3]@np.linalg.solve(K,[*pixel,1.]);direction/=np.linalg.norm(direction)
    near,far=0.,np.inf
    for axis in range(3):
        if abs(direction[axis])<1e-14:
            if not box[0][axis]<=origin[axis]<=box[1][axis]:
                return dict(depths=np.array([]),cost=np.array([]),modes=[],resolution_ok=True,origin=origin,direction=direction)
        else:
            a=(box[0][axis]-origin[axis])/direction[axis];b=(box[1][axis]-origin[axis])/direction[axis]
            near=max(near,min(a,b));far=min(far,max(a,b))
    if far<=near:return dict(depths=np.array([]),cost=np.array([]),modes=[],resolution_ok=True,origin=origin,direction=direction)
    p=cfg['probe'];count=min(p['ray_max_samples'],max(p['ray_min_samples'],int(np.ceil(2*(far-near)/delta))+1))
    depths=np.linspace(near,far,count);points=origin+depths[:,None]*direction
    values=np.asarray(evaluate(points),float);modes=[]
    for i,j in _minima(values):
        low,high=depths[max(0,i-1)],depths[min(count-1,j+1)]
        best_depth=float(depths[(i+j)//2]);best=float(values[(i+j)//2])
        plateau=[float(depths[i]),float(depths[j])]
        if i==j:
            for _ in range(p['refine_levels']):
                fine=np.linspace(low,high,p['refine_samples']);cost=np.asarray(evaluate(origin+fine[:,None]*direction))
                k=int(np.argmin(cost))
                if cost[k]<best:best_depth,best=float(fine[k]),float(cost[k])
                low,high=fine[max(0,k-1)],fine[min(len(fine)-1,k+1)]
        modes.append(dict(depth=best_depth,cost=best,plateau=plateau,bracket=[float(low),float(high)]))
    return dict(depths=depths,cost=values,modes=modes,resolution_ok=bool((far-near)/(count-1)<=delta*.5*(1+1e-10)),
                origin=origin,direction=direction)


class NativeLayers:
    def __init__(self,state,height,width):
        self.height,self.width=height,width
        library=Path(__file__).resolve().parents[1]/'out/multiscene_foundation/setup/layers.so'
        self.lib=ctypes.CDLL(str(library));fn=self.lib.multiscene_layers
        fn.argtypes=[ctypes.c_int,ctypes.c_int]+[ctypes.c_void_p]*10
        fn.restype=None
        arrays=[np.ascontiguousarray(state[k],dtype=d) for k,d in
                [('means2D','f4'),('conic','f4'),('depths','f4'),('point_list','u4'),('ranges','u4')]]
        counts=np.zeros(height*width,'i8')
        fn(height,width,*[a.ctypes.data for a in arrays],counts.ctypes.data,None,None,None,None)
        self.offsets=np.concatenate([[0],np.cumsum(counts)]).astype('i8')
        self.depth=np.empty(self.offsets[-1],'f4');self.weight=np.empty_like(self.depth);self.transmittance=np.empty_like(self.depth)
        fn(height,width,*[a.ctypes.data for a in arrays],counts.ctypes.data,self.offsets.ctypes.data,
           self.depth.ctypes.data,self.weight.ctypes.data,self.transmittance.ctypes.data)
        query=self.lib.multiscene_layer_query
        query.argtypes=[ctypes.c_int,ctypes.c_int]+[ctypes.c_void_p]*5+[ctypes.c_double]+[ctypes.c_void_p]*2
        query.restype=None

    def events(self,x,y):
        i=y*self.width+x;a,b=self.offsets[i:i+2]
        return dict(depth=self.depth[a:b],weight=self.weight[a:b],transmittance=self.transmittance[a:b])

    def query(self,uv,depth,delta):
        uv=np.asarray(uv,float);valid=np.isfinite(uv).all(1)
        pixels=np.rint(np.nan_to_num(uv)).astype('i8')
        valid&=(pixels[:,0]>=0)&(pixels[:,0]<self.width)&(pixels[:,1]>=0)&(pixels[:,1]<self.height)
        index=np.where(valid,pixels[:,1]*self.width+pixels[:,0],-1).astype('i8')
        depth=np.ascontiguousarray(depth,'f8');front=np.ones(len(index),'f8');support=np.zeros(len(index),'u1')
        self.lib.multiscene_layer_query(len(index),self.height*self.width,self.offsets.ctypes.data,
            self.depth.ctypes.data,self.transmittance.ctypes.data,index.ctypes.data,depth.ctypes.data,
            float(delta),front.ctypes.data,support.ctypes.data)
        return front,support.astype(bool)


def match_outputs(base,other,delta,cfg):
    distances=[];angles=[];g=cfg['gates']
    for query in sorted(set(str(r['query']) for r in base)):
        a=[r for r in base if str(r['query'])==query];b=[r for r in other if str(r['query'])==query]
        if not b:continue
        pa=np.array([r['point'] for r in a]);pb=np.array([r['point'] for r in b])
        ta=np.array([r['axis'] for r in a]);tb=np.array([r['axis'] for r in b])
        d=np.linalg.norm(pa[:,None]-pb[None],axis=2)/delta;angle=axial_angle(ta[:,None],tb[None])
        allowed=(d<=g['G3_distance_delta_max'])&(angle<=g['G3_angle_max'])
        cost=np.where(allowed,d+angle/20,1e12);left,right=linear_sum_assignment(cost)
        for i,j in zip(left,right):
            if allowed[i,j]:distances.append(float(d[i,j]));angles.append(float(angle[i,j]))
    n=len(distances);result=dict(base_count=len(base),other_count=len(other),matches=n,passed=False,
        forward=n/len(base) if base else 0.,backward=n/len(other) if other else 0.,
        count_change=abs(len(base)-len(other))/len(base) if base else None)
    if n:
        result.update(median_distance_delta=float(np.median(distances)),p90_distance_delta=float(np.quantile(distances,.9)),
            median_axis_degrees=float(np.median(angles)),p90_axis_degrees=float(np.quantile(angles,.9)))
        result['passed']=bool(min(result['forward'],result['backward'])>=g['G3_match_min']
            and result['count_change']<=g['G3_count_change_max']
            and result['median_distance_delta']<=g['G3_median_delta_max']
            and result['p90_distance_delta']<=g['G3_p90_delta_max']
            and result['median_axis_degrees']<=g['G3_median_angle_max']
            and result['p90_axis_degrees']<=g['G3_p90_angle_max'])
    return result


class ImageEvidence:
    def __init__(self,cameras,fields,layers,delta,cfg):
        self.cameras,self.fields,self.layers=cameras,fields,layers
        self.delta,self.cfg=delta,cfg
        self.views=list(fields)

    def observations(self,points):
        points=np.atleast_2d(points);records=[]
        for view in self.views:
            camera=self.cameras[view];field=self.fields[view];height,width=field['dt'].shape
            uv,z,J=project_jacobian(points,camera['K'],camera['w2c'])
            safe=np.nan_to_num(uv,nan=-1.,posinf=-1.,neginf=-1.)
            pixel=np.rint(safe).astype(int);x=np.clip(pixel[:,0],0,width-1);y=np.clip(pixel[:,1],0,height-1)
            inside=(z>0)&np.isfinite(uv).all(1)&(uv[:,0]>=0)&(uv[:,0]<=width-1)&(uv[:,1]>=0)&(uv[:,1]<=height-1)
            inside&=field['domain'][y,x]
            dt=map_coordinates(field['dt'],[safe[:,1],safe[:,0]],order=1,mode='constant',cval=6.)
            tangent=field['nearest_tangent'][y,x];normal=np.stack([-tangent[:,1],tangent[:,0]],axis=1)
            edge_uv=field['nearest_uv'][y,x]
            front=np.ones(len(points));support=np.ones(len(points),bool)
            if self.layers is not None:front,support=self.layers[view].query(uv,z,self.delta)
            visible=inside&(front>=self.cfg['native']['visible_transmittance_min'])
            classification=np.where(~inside,-2,np.where(front>=.8,1,np.where(front<=.1,-1,0)))
            records.append(dict(view=view,uv=uv,z=z,J=J,dt=dt,normal=normal,tangent=tangent,
                edge_uv=edge_uv,inside=inside,visible=visible,support=support,classification=classification))
        return records

    def cost(self,points):
        observations=self.observations(points);count=np.zeros(len(points),int);square=np.zeros(len(points))
        for o in observations:
            use=o['visible'];count+=use;square+=np.where(use,np.minimum(o['dt'],self.cfg['probe']['residual_clip'])**2,0)
        return np.where(count>=self.cfg['probe']['min_views'],np.sqrt(square/np.maximum(count,1)),np.inf)

    def mode(self,initial):
        p=self.cfg['probe'];point=np.array(initial,float);start=point.copy();reasons=[]
        original=np.array([o['classification'][0] for o in self.observations(point)])
        for _ in range(p['gauss_newton_steps']):
            observations=self.observations(point);valid=[o for o in observations if o['visible'][0] and np.isfinite(o['normal'][0]).all()]
            if len(valid)<p['min_views']:break
            J=np.array([o['J'][0] for o in valid]);normals=np.array([o['normal'][0] for o in valid])
            covectors=np.einsum('vij,vi->vj',J,normals)
            residual=np.array([np.dot(o['uv'][0]-o['edge_uv'][0],o['normal'][0]) for o in valid])
            step=-np.linalg.pinv(covectors)@residual
            length=np.linalg.norm(step);cap=self.delta*p['max_step_delta']
            if length>cap:step*=cap/length
            candidate=point+step;total=np.linalg.norm(candidate-start);cap=self.delta*p['max_displacement_delta']
            if total>cap:candidate=start+(candidate-start)*cap/total
            classes=np.array([o['classification'][0] for o in self.observations(candidate)])
            if not np.array_equal(classes,original):reasons.append('visibility_changed');break
            point=candidate
            if length<1e-8*self.delta:break
        observations=self.observations(point);visible=[o for o in observations if o['visible'][0]]
        valid=[o for o in visible if np.isfinite(o['normal'][0]).all()]
        if len(valid)<p['min_views']:
            return dict(point=point.tolist(),axis=[0.,0.,0.],reasons=reasons+['insufficient_views'],accepted=False,
                        rms=None,eigenvalues=None,uncertainty_delta=None,direction_evaluable=0)
        H,eigenvalues,axis=image_hessian(np.array([o['J'][0] for o in valid]),np.array([o['normal'][0] for o in valid]))
        rms=float(np.sqrt(np.mean([min(o['dt'][0],p['residual_clip'])**2 for o in visible])))
        centers=np.array([np.linalg.inv(self.cameras[o['view']]['w2c'])[:3,3] for o in valid]);rays=point-centers
        rays/=np.linalg.norm(rays,axis=1,keepdims=True)
        separation=float(np.degrees(np.arccos(np.clip((rays@rays.T).min(),-1,1))))
        l1,l2,l3=eigenvalues;uncertainty=np.sqrt(p['transverse_factor']/l2)/self.delta if l2>0 else np.inf
        if l2<=0 or l1/l2>p['lambda1_lambda2_max'] or l3/l2>p['lambda3_lambda2_max'] or uncertainty>p['uncertainty_delta_max']:
            reasons.append('degenerate_H_img')
        if separation<p['min_baseline_degrees']:reasons.append('insufficient_baseline')
        if rms>p['rms_max']:reasons.append('image_residual')
        errors=[];view_rows=[]
        for o in observations:
            projected=o['J'][0]@axis
            direction_ok=bool(o['visible'][0] and np.isfinite(o['tangent'][0]).all()
                              and np.linalg.norm(projected)*self.delta>=p['foreshortening_pixels'])
            angle=float(axial_angle(projected,o['tangent'][0])) if direction_ok else None
            if angle is not None:errors.append(angle)
            view_rows.append(dict(view=o['view'],visible=bool(o['visible'][0]),supported=bool(o['support'][0]),
                dt=float(o['dt'][0]),angle=angle,direction_evaluable=direction_ok))
        if len(errors)<p['min_views'] or np.median(errors)>p['angle_median_max']:reasons.append('direction_residual_or_foreshortening')
        if self.layers is not None and sum(o['support'][0] for o in visible)<p['min_views']:reasons.append('GS_support_conflict')
        return dict(point=point.tolist(),axis=axis.tolist(),reasons=reasons,accepted=not reasons,rms=rms,
            H_img=H.tolist(),eigenvalues=eigenvalues.tolist(),uncertainty_delta=float(uncertainty) if np.isfinite(uncertainty) else None,
            angle_median=float(np.median(errors)) if errors else None,baseline_degrees=separation,
            direction_evaluable=len(errors),views=view_rows,ray_point=start.tolist())


def infer_queries(queries,cameras,fields,layers,box,delta,cfg):
    evidence=ImageEvidence(cameras,fields,layers,delta,cfg);modes=[];profiles=[];resolution=True
    for query in queries:
        profile=ray_profile(cameras[query['view']],query['pixel'],box,delta,evidence.cost,cfg)
        profiles.append(dict(query=query['query'],**profile));resolution&=profile['resolution_ok']
        current=[]
        for mode in profile['modes']:
            point=profile['origin']+mode['depth']*profile['direction']
            result=evidence.mode(point);result.update(query=query['query'],view=query['view'],
                ray_depth=mode['depth'],profile_rms=mode['cost'],plateau=mode['plateau'])
            if not profile['resolution_ok']:result['reasons'].append('search_resolution')
            current.append(result)
        # Reject every locally convincing interpretation with a near-optimal,
        # transverse-separated alternative, even if that alternative fails H_img.
        for a in current:
            if a['rms'] is None:continue
            for b in current:
                if b is a or b['rms'] is None:continue
                difference=np.array(a['point'])-b['point'];axis=np.array(a['axis'])
                transverse=np.linalg.norm(difference-axis*np.dot(difference,axis))
                if abs(a['rms']-b['rms'])<=cfg['probe']['ambiguity_rms_gap'] and transverse>cfg['probe']['ambiguity_transverse_delta']*delta:
                    a['reasons'].append('multimodal');break
            direction=profile['direction'];axis=np.array(a['axis'])
            width=(a['plateau'][1]-a['plateau'][0])*np.linalg.norm(direction-axis*np.dot(direction,axis))
            if width>cfg['probe']['ambiguity_transverse_delta']*delta:a['reasons'].append('wide_plateau')
            a['reasons']=sorted(set(a['reasons']));a['accepted']=not a['reasons']
        modes.extend(current)
    accepted=[]
    for mode in sorted((m for m in modes if m['accepted']),key=lambda m:(str(m['query']),m['ray_depth'])):
        if not accepted or min(np.linalg.norm(np.array(mode['point'])-m['point']) for m in accepted)>=delta:
            accepted.append(mode)
    return dict(accepted=accepted,modes=modes,profiles=profiles,resolution_ok=bool(resolution),query_count=len(queries))
