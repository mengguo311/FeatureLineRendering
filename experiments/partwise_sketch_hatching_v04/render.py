"""CPU proxy depth + fixed surface capsules + independent view contours."""
import runtime
import numpy as np
from scipy import ndimage
from geometry import project, ray_surface

def render(mesh, strokes, styles, camera, supersample=2):
    depth,face_image,regions,c=ray_surface(mesh,camera,supersample)
    size=c['width'];scale=supersample
    E=np.asarray(c['extrinsic']);R=E[:3,:3]
    nc=mesh['normals']@np.linalg.inv(R)
    pc=mesh['tri'][:,0]@R.T+E[:3,3]
    plane=np.einsum('ij,ij->i',nc,pc)
    layers={};diag={}
    for region,paths in strokes.items():
        ink=np.zeros((size,size),np.float32);accepted=0;covered_count=0;behind=0
        width=styles[str(region)]['width']*scale
        for points,face in zip(paths['points'],paths['face']):
            uv,z=project(points,c)
            if (z<=.2).any():behind+=1;continue
            direction=uv[1]-uv[0];length2=float(direction@direction)
            if length2<1e-14:continue
            radius=width/2
            lo=np.maximum(0,np.ceil(np.min(uv,axis=0)-radius)).astype(int)
            hi=np.minimum(size-1,np.floor(np.max(uv,axis=0)+radius)).astype(int)
            if (hi<lo).any():continue
            yy,xx=np.mgrid[lo[1]:hi[1]+1,lo[0]:hi[0]+1]
            t=np.clip(((xx-uv[0,0])*direction[0]+(yy-uv[0,1])*direction[1])/length2,0,1)
            covered=(xx-uv[0,0]-t*direction[0])**2+(yy-uv[0,1]-t*direction[1])**2<=radius**2
            normal=nc[face]
            denominator=normal[0]*(xx-c['cx'])/c['fx']+normal[1]*(yy-c['cy'])/c['fy']+normal[2]
            zz=np.divide(plane[face],denominator,out=np.full_like(denominator,np.inf),where=np.abs(denominator)>1e-12)
            dd=depth[lo[1]:hi[1]+1,lo[0]:hi[0]+1]
            region_image=regions[lo[1]:hi[1]+1,lo[0]:hi[0]+1]
            visible=covered & np.isfinite(dd) & (region_image==region)
            difference=np.full_like(dd,np.inf)
            np.subtract(zz,dd,out=difference,where=np.isfinite(zz)&np.isfinite(dd))
            visible &= np.abs(difference)<=.004
            target=ink[lo[1]:hi[1]+1,lo[0]:hi[0]+1]
            target[visible]=.80
            accepted+=int(visible.sum());covered_count+=int(covered.sum())
        layers[region]=ink
        diag[str(region)]=dict(accepted_fragments=accepted,covered_fragments=covered_count,
                               behind_segments=behind,ink_mass=float(ink.sum()/scale**2))
    hit=np.isfinite(depth)
    contour=hit & ~ndimage.binary_erosion(hit,iterations=scale)
    # Occlusion depth discontinuities only; texture/region edges are not structure.
    for axis in (0,1):
        other=np.roll(depth,1,axis=axis);both=hit & np.isfinite(other)
        difference=np.zeros_like(depth)
        np.subtract(depth,other,out=difference,where=both)
        contour |= both & (np.abs(difference)>.035)
    contour=contour.astype(np.float32)*.85
    hatch=np.maximum.reduce(list(layers.values()))
    combined=1-np.maximum(hatch,contour)
    low=lambda x:x.reshape(camera['height'],scale,camera['width'],scale).mean((1,3))
    n=np.zeros((*face_image.shape,3));n[hit]=mesh['normals'][face_image[hit]]
    light=np.array([-.4,-.6,.7]);light/=np.linalg.norm(light)
    shade=np.ones_like(depth);shade[hit]=.6+.35*np.abs(n[hit]@light)
    palette=np.array([[1,1,1],[.24,.49,.77],[.9,.58,.19],[.29,.69,.48]])
    color=palette[regions].reshape(camera['height'],scale,camera['width'],scale,3).mean((1,3))
    uv,z=project(mesh['vertices'],camera)
    bounds=dict(all_vertices_in_front=bool((z>.2).all()),xmin=float(uv[:,0].min()),xmax=float(uv[:,0].max()),
                ymin=float(uv[:,1].min()),ymax=float(uv[:,1].max()))
    bounds['all_proxy_vertices_inside']=bool((z>.2).all() and (uv>=0).all() and (uv[:,0]<camera['width']).all() and (uv[:,1]<camera['height']).all())
    return dict(image=low(combined),hatch=low(hatch),contour=low(contour),proxy=low(shade),region_rgb=color,
                regions=regions[scale//2::scale,scale//2::scale],depth=depth[scale//2::scale,scale//2::scale],
                layers={region:low(v) for region,v in layers.items()},diagnostics=diag,bounds=bounds)
