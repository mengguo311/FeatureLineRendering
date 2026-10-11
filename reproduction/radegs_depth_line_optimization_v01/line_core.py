"""Depth-only CPU lines; all thresholds have explicit geometric/algorithmic roles."""
import numpy as np
import cv2
from skimage.morphology import thin

PARAMETERS = dict(sigmas=[2.,4.],alpha_min=.5,distance_floor=.25,
                  distance_scale=.35,anchor_percentile=30,low=.014,high=.04,
                  min_size=12,confidence_support_min=.85,mv_reference_count=6,
                  mv_relative_tolerance=.006,mv_unknown=.8,mv_floor=.25,
                  focus_center="49 optical axes least squares",focus_radius="median of 3 fixed-view central60pct radial p95",
                  focus_floor=.05,focus_half_weight_radius=1.,image_border_guard_pixels=19,fragment_rule="crossing-number junction paths")

def soft_distance(z, valid):
    w=np.zeros_like(z,dtype=np.float64)
    if not valid.any():return w
    anchor=float(np.percentile(z[valid],30))
    t=np.maximum(z[valid]/anchor-1,0)/.35
    w[valid]=.25+.75/(1+t*t)
    return w

def normalized_inverse(z, valid, sigma):
    # Normalize by actual valid sample mass; a missing sample never becomes depth 0.
    q=np.zeros_like(z,dtype=np.float64);np.divide(1,z,out=q,where=valid)
    den=cv2.GaussianBlur(valid.astype(np.float64),(0,0),sigma,borderType=cv2.BORDER_REFLECT_101)
    num=cv2.GaussianBlur(q,(0,0),sigma,borderType=cv2.BORDER_REFLECT_101)
    return np.divide(num,den,out=np.zeros_like(num),where=den>1e-12),den

def normal_response(q,cam):
    h,w=q.shape;y,x=np.indices(q.shape,dtype=np.float64)
    dx=cv2.Sobel(q,cv2.CV_64F,1,0,ksize=3,scale=1/8)
    dy=cv2.Sobel(q,cv2.CV_64F,0,1,ksize=3,scale=1/8)
    n=np.stack([cam['fx']*dx,cam['fy']*dy,q-(x-(w-1)/2)*dx-(y-(h-1)/2)*dy],-1)
    n/=np.maximum(np.linalg.norm(n,axis=-1,keepdims=True),1e-12)
    nx=cv2.Sobel(n,cv2.CV_64F,1,0,ksize=3,scale=1/8)
    ny=cv2.Sobel(n,cv2.CV_64F,0,1,ksize=3,scale=1/8)
    a=np.sum(nx*nx,-1);b=np.sum(ny*ny,-1);c=np.sum(nx*ny,-1)
    response=np.sqrt(a+b)
    direction=.5*np.arctan2(2*c,a-b)
    return response,direction

def features(z,alpha,cam):
    z=np.asarray(z,dtype=np.float64);alpha=np.asarray(alpha)
    valid=np.isfinite(z)&(z>0)&np.isfinite(alpha)&(alpha>=.5)
    q2,c2=normalized_inverse(z,valid,2.);q4,c4=normalized_inverse(z,valid,4.)
    r2,d2=normal_response(q2,cam);r4,d4=normal_response(q4,cam)
    # Consistent peaks survive; fine-only oscillations do not create strong seeds.
    response=np.minimum(r2,1.6*r4)
    stability=np.where(r2<1e-10,1.,np.minimum(1.,1.8*r4/np.maximum(r2,1e-12)))
    support=cv2.erode(valid.astype(np.uint8),np.ones((3,3),np.uint8),borderType=cv2.BORDER_CONSTANT,borderValue=0)>0
    support &= (c2>=.85)&(c4>=.85)
    # Only at the image frame: radius 4*sigma_max=16 + two Sobel radii + NMS=19.
    # Reflected padding is not observed geometry. Internal alpha boundaries retain
    # normalized valid-sample fitting; this is NOT a 19px erosion of every mask.
    halo=19
    support[:halo]=False;support[-halo:]=False;support[:,:halo]=False;support[:,-halo:]=False
    confidence=c2*c4*stability;confidence[~valid]=0
    response[~support]=0
    return dict(response=response,direction=d2,confidence=confidence,valid=valid,support=support,
                distance_weight=soft_distance(z,valid),fine_response=r2,coarse_response=r4)

def trace(response,direction,valid,confidence,low=.014,high=.04,min_size=12):
    h,w=response.shape;y,x=np.indices((h,w),dtype=np.float32)
    ux=np.cos(direction).astype(np.float32);uy=np.sin(direction).astype(np.float32)
    r=response.astype(np.float32)
    plus=cv2.remap(r,x+ux,y+uy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
    minus=cv2.remap(r,x-ux,y-uy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
    ridge=(r>=plus)&(r>=minus)&(r>=low)&valid
    ridge=thin(ridge)
    # Split only actual skeleton branch points, not every 8-neighbor corner.
    ring=[np.roll(ridge,(dy,dx),(0,1)) for dy,dx in [(-1,0),(-1,1),(0,1),(1,1),(1,0),(1,-1),(0,-1),(-1,-1)]]
    crossing=sum((ring[i]!=ring[(i+1)%8]).astype(np.uint8) for i in range(8))//2
    junction=ridge&(crossing>=3)
    junction_neighborhood=cv2.dilate(junction.astype(np.uint8),np.ones((3,3),np.uint8)).astype(bool)
    paths=ridge&~junction_neighborhood
    count,labels,stats,_=cv2.connectedComponentsWithStats(paths.astype(np.uint8),connectivity=8)
    output=np.zeros_like(ridge)
    for i in range(1,count):
        if stats[i,cv2.CC_STAT_AREA]<min_size:continue
        yy,xx=np.where(labels==i)
        # Whole existing fragment decision: confidence changes do not cut individual pixels.
        weighted=response[yy,xx]*confidence[yy,xx]
        if np.percentile(weighted,90)>=high and weighted.mean()>=low*1.5:
            output[yy,xx]=True
    # Restore original junction pixels touching accepted paths; never draw new pixels.
    adjacent=cv2.dilate(output.astype(np.uint8),np.ones((5,5),np.uint8)).astype(bool)
    output |= ridge&junction_neighborhood&adjacent
    return output

def optimize(z,alpha,cam,mv=None):
    f=features(z,alpha,cam)
    conf=f['confidence']*f['distance_weight']
    if mv is not None:conf=conf*mv
    f['selection_weight']=conf
    f['lines']=trace(f['response'],f['direction'],f['support'],conf)
    return f

def camera_center(cam):
    E=np.asarray(cam['extrinsic'],dtype=np.float64)
    return -E[:3,:3].T@E[:3,3]

def visibility_confidence(z,valid,cam,refs):
    h,w=z.shape;y,x=np.indices(z.shape,dtype=np.float64)
    z=np.where(valid,z,0)
    xyz=np.stack([(x-(w-1)/2)*z/cam['fx'],(y-(h-1)/2)*z/cam['fy'],z],-1)
    E=np.asarray(cam['extrinsic']);world=(xyz-E[:3,3])@E[:3,:3]
    total=np.zeros((h,w),dtype=np.float64);count=np.zeros((h,w),np.uint8)
    occluded=np.zeros_like(count)
    for rz,rv,rc in refs:
        R=np.asarray(rc['extrinsic']);p=world@R[:3,:3].T+R[:3,3]
        zz=p[:,:,2];safe=np.maximum(zz,1e-12)
        u=np.rint(p[:,:,0]/safe*rc['fx']+(rc['width']-1)/2).astype(np.int64)
        v=np.rint(p[:,:,1]/safe*rc['fy']+(rc['height']-1)/2).astype(np.int64)
        inside=valid&(zz>0)&(u>=1)&(u<rc['width']-1)&(v>=1)&(v<rc['height']-1)
        u=np.clip(u,0,rc['width']-1);v=np.clip(v,0,rc['height']-1)
        # 3x3 interval tolerates subpixel reprojection at depth discontinuities.
        rmin=cv2.erode(np.where(rv,rz,1e10).astype(np.float64),np.ones((3,3),np.uint8))
        rmax=cv2.dilate(np.where(rv,rz,-1e10).astype(np.float64),np.ones((3,3),np.uint8))
        rvalid=cv2.erode(rv.astype(np.uint8),np.ones((3,3),np.uint8)).astype(bool)
        lo=rmin[v,u];hi=rmax[v,u];tol=.006*np.maximum(zz,1e-12)
        seen=inside&rvalid[v,u];hidden=seen&(zz>hi+tol)
        obs=seen&~hidden
        residual=np.maximum(lo-zz,0)/np.maximum(tol,1e-12)
        agreement=np.exp(-.5*np.minimum(residual,30)**2)
        total+=np.where(obs,agreement,0);count+=obs;occluded+=hidden
    avg=np.divide(total,count,out=np.full_like(total,.8),where=count>0)
    weight=np.where(count>0,.25+.75*avg,.8);weight[~valid]=0
    return dict(weight=weight,observations=count,occluded=occluded,agreement=avg)

def focus_center(cams):
    A=np.zeros((3,3));b=np.zeros(3)
    for cam in cams:
        E=np.asarray(cam['extrinsic'],dtype=np.float64);d=E[2,:3];d=d/np.linalg.norm(d)
        P=np.eye(3)-np.outer(d,d);A+=P;b+=P@camera_center(cam)
    if np.linalg.cond(A)>1e6:raise ValueError('camera optical axes do not constrain a focus center')
    return np.linalg.solve(A,b)

def world_points(z,cam):
    h,w=z.shape;y,x=np.indices(z.shape,dtype=np.float64)
    xyz=np.stack([(x-(w-1)/2)*z/cam['fx'],(y-(h-1)/2)*z/cam['fy'],z],-1)
    E=np.asarray(cam['extrinsic']);return (xyz-E[:3,3])@E[:3,:3]

def focus_weight(z,cam,center,radius):
    if not np.isfinite(radius) or radius<=0:raise ValueError('invalid focus radius')
    good=np.isfinite(z)&(z>0)
    xyz=world_points(np.where(good,z,0),cam)
    r=np.linalg.norm(xyz-np.asarray(center),axis=-1)/radius
    weight=.05+.95*np.exp(-np.log(2)*np.minimum(r,20)**4)
    weight[~good]=0
    return weight
