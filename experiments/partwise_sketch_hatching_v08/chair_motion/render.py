"""CPU proxy depth + fixed surface capsules + independent view contours."""
import runtime
import hashlib
import json
import numpy as np
from scipy import ndimage
from geometry import project, ray_surface
from display_settings import validate_display
from hatching import layer_ids,validate_style,visibility_masks

class RenderCache:
    """One transient coverage entry; never a serialized asset dependency.

    Content hashes catch in-place changes and fresh loads equally. Only ink
    strength and display are excluded: they are composed at the original
    supersample resolution. Width/cross/path/geometry/label/camera changes miss.
    """
    def __init__(self,max_bytes=128*2**20,track_ids=()):
        self.track_ids=tuple(track_ids)
        self.max_bytes=max_bytes;self.hits=0;self.builds=0;self.last_hit=False
        self.clear()

    def clear(self):
        self.key=None;self.value=None;self.bytes=0

    def get(self,mesh,strokes,styles,camera,supersample):
        h=hashlib.sha256()
        def arrays(values):
            for name,value in sorted(values.items()):
                a=np.ascontiguousarray(value)
                h.update(json.dumps([name,a.dtype.str,a.shape]).encode())
                h.update(memoryview(a).cast('B'))
        arrays(mesh)
        for region,paths in sorted(strokes.items()):
            h.update(str(region).encode());arrays(paths)
        # The HTML form sends explicit defaults even for legacy metadata.
        fixed_styles={k:{n:v for n,v in {'cross_enabled':False,'cross_angle':60.,'cross_spacing':.06,**s}.items()
                         if n!='ink_strength'} for k,s in styles.items()}
        h.update(json.dumps([fixed_styles,camera,supersample],sort_keys=True,allow_nan=False).encode())
        key=h.digest();self.last_hit=key==self.key and self.value is not None
        if self.last_hit:
            self.hits+=1;return self.value
        self.clear()
        result=_coverage(mesh,strokes,styles,camera,supersample,self.track_ids);self.builds+=1
        def size(x):
            if isinstance(x,np.ndarray):return x.nbytes
            if isinstance(x,dict):return sum(size(v) for v in x.values())
            return 0
        size_bytes=size(result)
        if size_bytes<=self.max_bytes:self.key=key;self.value=result;self.bytes=size_bytes
        return result

    def info(self):
        return dict(hit=self.last_hit,hits=self.hits,builds=self.builds,bytes=self.bytes,max_bytes=self.max_bytes)

def _coverage(mesh,strokes,styles,camera,supersample,track_ids=()):
    """Visibility and capsule rasterization, independent of ink strength."""
    depth,face_image,regions,c=ray_surface(mesh,camera,supersample)
    region_bits=np.left_shift(np.uint64(1),regions.astype(np.uint64))
    size=c['width'];scale=supersample
    E=np.asarray(c['extrinsic']);R=E[:3,:3]
    nc=mesh['normals']@np.linalg.inv(R)
    pc=mesh['tri'][:,0]@R.T+E[:3,3]
    plane=np.einsum('ij,ij->i',nc,pc)
    coverage={};diag={};tracked={key:np.zeros((size,size),bool) for key in track_ids}
    for region,paths in strokes.items():
        subink={int(k):np.zeros((size,size),bool) for k in np.unique(layer_ids(paths))}
        accepted=0;covered_count=0;behind=0
        width=styles[str(region)]['width']*scale
        for points,face,layer,support,stroke_id in zip(paths['points'],paths['face'],layer_ids(paths),visibility_masks(paths,region),paths['stroke_id']):
            if layer==1 and not styles[str(region)].get('cross_enabled',False):continue
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
            support_bits=region_bits[lo[1]:hi[1]+1,lo[0]:hi[0]+1]
            visible=covered & np.isfinite(dd) & ((support_bits & support)!=0)
            difference=np.full_like(dd,np.inf)
            np.subtract(zz,dd,out=difference,where=np.isfinite(zz)&np.isfinite(dd))
            visible &= np.abs(difference)<=.004
            target=subink[int(layer)][lo[1]:hi[1]+1,lo[0]:hi[0]+1]
            target[visible]=True
            key=f'{region}:{int(stroke_id)}'
            if key in tracked:tracked[key][lo[1]:hi[1]+1,lo[0]:hi[0]+1][visible]=True
            accepted+=int(visible.sum());covered_count+=int(covered.sum())
        coverage[region]=subink
        diag[str(region)]=dict(accepted_fragments=accepted,covered_fragments=covered_count,
                               behind_segments=behind)
    hit=np.isfinite(depth)
    contour=hit & ~ndimage.binary_erosion(hit,iterations=scale)
    # Occlusion depth discontinuities only; texture/region edges are not structure.
    for axis in (0,1):
        other=np.roll(depth,1,axis=axis);both=hit & np.isfinite(other)
        difference=np.zeros_like(depth)
        np.subtract(depth,other,out=difference,where=both)
        contour |= both & (np.abs(difference)>.035)
    contour=contour.astype(np.float32)*.85
    low=lambda x:x.reshape(camera['height'],scale,camera['width'],scale).mean((1,3))
    n=np.zeros((*face_image.shape,3));n[hit]=mesh['normals'][face_image[hit]]
    light=np.array([-.4,-.6,.7]);light/=np.linalg.norm(light)
    shade=np.ones_like(depth);shade[hit]=.6+.35*np.abs(n[hit]@light)
    from colorsys import hsv_to_rgb
    palette=np.array([[1,1,1],[.24,.49,.77],[.9,.58,.19],[.29,.69,.48],[.80,.32,.58]]+
                     [hsv_to_rgb((i*.61803398875)%1,.55,.80) for i in range(5,33)])
    color=palette[regions].reshape(camera['height'],scale,camera['width'],scale,3).mean((1,3))
    uv,z=project(mesh['vertices'],camera)
    bounds=dict(all_vertices_in_front=bool((z>.2).all()),xmin=float(uv[:,0].min()),xmax=float(uv[:,0].max()),
                ymin=float(uv[:,1].min()),ymax=float(uv[:,1].max()))
    bounds['all_proxy_vertices_inside']=bool((z>.2).all() and (uv>=0).all() and (uv[:,0]<camera['width']).all() and (uv[:,1]<camera['height']).all())
    return dict(coverage=coverage,diagnostics=diag,tracked=tracked,contour=contour,proxy=low(shade),region_rgb=color,
                regions=regions[scale//2::scale,scale//2::scale].copy(),depth=depth[scale//2::scale,scale//2::scale].copy(),bounds=bounds)

def render(mesh,strokes,styles,camera,supersample=2,display=None,cache=None):
    display=validate_display(display)
    for style in styles.values():validate_style(style)
    data=(_coverage(mesh,strokes,styles,camera,supersample) if cache is None
          else cache.get(mesh,strokes,styles,camera,supersample))
    scale=supersample;layers={};style_layers={};diag={}
    low=lambda x:x.reshape(camera['height'],scale,camera['width'],scale).mean((1,3))
    for region,coverage in data['coverage'].items():
        strength=styles[str(region)].get('ink_strength',.80)
        subink={}
        for k,mask in coverage.items():
            ink=np.zeros(mask.shape,np.float32);ink[mask]=strength;subink[k]=ink
        ink=np.maximum.reduce(list(subink.values()));layers[region]=ink
        if 'layer_id' in strokes[region]:style_layers.update({f'{region}_{k}':v for k,v in subink.items()})
        diag[str(region)]=dict(data['diagnostics'][str(region)],ink_strength=float(strength),
            ink_mass=float(ink.sum()/scale**2),style_layer_ink_mass={str(k):float(v.sum()/scale**2) for k,v in subink.items()})
    contour=data['contour'].copy()
    contour*=display['contour_strength'] if display['contours_visible'] else 0.
    hatch=np.maximum.reduce(list(layers.values()));combined=1-np.maximum(hatch,contour)
    # Returned arrays cannot mutate the stored coverage or auxiliary rasters.
    return dict(image=low(combined),hatch=low(hatch),contour=low(contour),
        **{k:data[k].copy() for k in ('proxy','region_rgb','regions','depth')},bounds=dict(data['bounds']),
        layers={r:low(v) for r,v in layers.items()},style_layers={k:low(v) for k,v in style_layers.items()},diagnostics=diag)
