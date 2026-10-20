"""Read-only diagnostic replay of frozen renderer stages; never a repair backend."""
import temporal_audit as ta  # CPU and thread controls before scientific imports.
import numpy as np
from scipy import ndimage
from PIL import Image

STAGE_NAMES = ['analytic_visible', 'dense_unrounded', 'rounded_pre_z',
               'accepted_deposition', 'width_foreground', 'isolated_AA',
               'combined_hatch', 'identified']
LOSS_NAMES = ['analytic_visibility_mismatch', 'dense_sampling_support_absent',
              'rounded_deposition_support_absent', 'mesh_z_test_local_rejection',
              'width_or_foreground_clip_loss', 'quantization_or_LANCZOS_support_loss',
              'combined_hatch_threshold_loss', 'identity_filter_loss']


def classify_stages(flags):
    flags = list(map(bool, flags))
    if flags[-1]:
        return 'supported'
    first = next(i for i, x in enumerate(flags) if not x)
    if any(flags[first+1:]):
        return 'unknown_or_mixed'
    return LOSS_NAMES[first]


def exact_mesh_rays(mesh, c, uv):
    """Moller-Trumbore first positive hit; rays parameterized by optical z.

    Triangle implementation is separate from the screen-space z-buffer.
    1e-9 barycentric tolerance only accommodates roundoff at shared edges.
    """
    ray = np.column_stack(((uv-c['center'])/c['focal'], np.ones(len(uv)))) @ c['R']
    best = np.full(len(uv), np.inf); part = np.zeros(len(uv), np.int16)
    face = np.full(len(uv), -1, np.int32)
    for i, tri in enumerate(mesh['tri']):
        e1, e2 = tri[1]-tri[0], tri[2]-tri[0]
        h = np.cross(ray, e2); det = h @ e1
        valid = abs(det) > 1e-12
        inv = np.divide(1., det, out=np.zeros(len(det)), where=valid)
        s = c['eye']-tri[0]; u = (h @ s)*inv
        q = np.cross(s, e1); v = (ray @ q)*inv
        t = np.dot(e2, q)*inv
        take = valid & (u >= -1e-9) & (v >= -1e-9) & (u+v <= 1+1e-9) & (t > 0) & (t < best)
        best[take] = t[take]; part[take] = mesh['parts'][i]; face[take] = i
    return best, part, face


def trace_points(points, c, depth, parts, tolerance, mesh, asset):
    uv, z = ta.core.project(points,c); pix = np.rint(uv).astype(int)
    inside = (z>0)&(pix[:,0]>=0)&(pix[:,0]<c['size'])&(pix[:,1]>=0)&(pix[:,1]<c['size'])
    pixel_depth = np.full(len(z), np.inf); pixel_part = np.zeros(len(z),np.int16)
    pixel_depth[inside] = depth[pix[inside,1],pix[inside,0]]
    pixel_part[inside] = parts[pix[inside,1],pix[inside,0]]
    zpass = ta.core.visible_points(points,c,depth,tolerance)
    np.testing.assert_array_equal(zpass,inside&(z<=pixel_depth+tolerance))
    exact, exactpart, exactface = exact_mesh_rays(mesh,c,uv)
    rounded, roundedpart, roundedface = exact_mesh_rays(mesh,c,pix)
    out = {'xyz':points,'uv':uv,'z':z,'pixel':pix,'inside':inside,
           'pixel_depth':pixel_depth,'pixel_part':pixel_part,'zpass':zpass,
           'accepted':zpass&(pixel_part>0),'exact_mesh_depth':exact,
           'exact_mesh_part':exactpart,'exact_mesh_face':exactface,
           'rounded_mesh_depth':rounded,'rounded_mesh_part':roundedpart,
           'rounded_mesh_face':roundedface}
    if asset is not None:
        az, ap = ta.analytic_rays(asset,c,uv)
        rz, rp = ta.analytic_rays(asset,c,pix)
        out.update(analytic_exact_depth=az,analytic_exact_part=ap,
                   analytic_rounded_depth=rz,analytic_rounded_part=rp)
    return out


def deposit(pixels, ink, shape):
    a=np.zeros(shape)
    if len(pixels): np.maximum.at(a,(pixels[:,1],pixels[:,0]),ink)
    return a


def layer_stages(raw, parts, scale, width):
    widened=ndimage.maximum_filter(raw,size=width)
    clipped=widened.copy();clipped[parts==0]=0
    quantized=np.uint8(np.clip(clipped,0,1)*255)
    h,w=quantized.shape
    down=np.asarray(Image.fromarray(quantized).resize((w//scale,h//scale),Image.Resampling.LANCZOS))
    return {'raw':raw,'width':widened,'clipped':clipped,'quantized':quantized,'downsample':down}


def full_image(hatch_high, structure):
    # Original structure pixels overwrite hatch (they do not alpha-composite).
    full=hatch_high.copy(); mask=np.isfinite(structure);full[mask]=structure[mask]
    return np.uint8((ta.downsample(1-full,2)/255.)*255.)


def replay_frame(mesh, strokes, cfg, params, selected):
    scale=cfg['renderer']['supersample'];size=cfg['renderer']['resolution'][0]
    width=max(1,round(cfg['strokes']['screen_width_px']*scale))
    tol=cfg['renderer']['visibility_tolerance_world']
    c=ta.core.camera(params['azimuth_deg'],params['elevation_deg'],params['distance'],size*scale,cfg['renderer']['focal_px']*scale)
    depth,parts=ta.core.raster_surface(mesh,c)
    raw=np.zeros(depth.shape);other=np.zeros(depth.shape)
    count=np.zeros((size,size),np.uint16); selected_data={}
    for i,s in enumerate(strokes):
        points=ta.core.dense_path(ta.core.anchor_points(mesh,s),c)
        uv,_=ta.core.project(points,c);pix=np.rint(uv).astype(int)
        visible=ta.core.visible_points(points,c,depth,tol)
        q=pix[visible];q=q[parts[q[:,1],q[:,0]]>0]
        if len(q):
            np.maximum.at(raw,(q[:,1],q[:,0]),s['ink'])
            if i not in selected: np.maximum.at(other,(q[:,1],q[:,0]),s['ink'])
        x0,y0,small,_=ta.layer_crop(q,s['ink'],parts,scale,width)
        count[y0:y0+small.shape[0],x0:x0+small.shape[1]]+=small>0
        if i in selected:
            trace=trace_points(points,c,depth,parts,tol,mesh,cfg['asset'])
            a=deposit(q,s['ink'],depth.shape)
            stages=layer_stages(a,parts,scale,width)
            fullsmall=np.zeros((size,size),np.uint8)
            fullsmall[y0:y0+small.shape[0],x0:x0+small.shape[1]]=small
            np.testing.assert_array_equal(stages['downsample'],fullsmall)
            pre=deposit(pix[trace['inside']],s['ink'],depth.shape)
            selected_data[i]={'trace':trace,'stages':stages,'pre_z':pre}
    combined=layer_stages(raw,parts,scale,width)
    structure=np.full(depth.shape,np.nan);structure[ta.core.contour_mask(parts)]=.92
    for profile in cfg['asset']['profiles_ry'].values():
        for r,y in profile:
            if r<.1: continue
            theta=np.linspace(0,2*np.pi,385)
            points=np.column_stack((r*np.cos(theta),np.full_like(theta,y),r*np.sin(theta)))
            points=ta.core.dense_path(points,c)
            uv,_=ta.core.project(points,c);pix=np.rint(uv).astype(int)
            q=pix[ta.core.visible_points(points,c,depth,tol)];q=q[parts[q[:,1],q[:,0]]>0]
            if len(q): structure[q[:,1],q[:,0]]=.85
    full=full_image(combined['clipped'],structure)
    for i,d in selected_data.items():
        omitted=other.copy()
        for j,od in selected_data.items():
            if j!=i: np.maximum(omitted,od['stages']['raw'],out=omitted)
        omitstages=layer_stages(omitted,parts,scale,width)
        omitfull=full_image(omitstages['clipped'],structure)
        isolated=d['stages']['downsample']
        before_id=(isolated/255.>.04)&(combined['downsample']/255.>.04)
        d.update(before_id=before_id,identified=before_id&(count==1),
                 hatch_leave_one_out_delta=abs(combined['downsample'].astype(np.int16)-omitstages['downsample'].astype(np.int16)),
                 full_leave_one_out_delta=abs(full.astype(np.int16)-omitfull.astype(np.int16)),
                 omitted_hatch=omitstages['downsample'],omitted_full=omitfull,
                 omitted_clipped=omitstages['clipped'])
    return {'c':c,'depth':depth,'parts':parts,'hatch':combined['downsample'],
            'count':count,'full':full,'selected':selected_data,'structure':structure}


def support_stats(uv, xy, radius=1.5):
    if len(xy)==0: return {'nearest_px':None,'within_radius':0,'supported':False}
    d=np.linalg.norm(xy-uv,axis=1)
    return {'nearest_px':float(d.min()),'within_radius':int((d<=radius).sum()),'supported':bool((d<=radius).any())}


def pixel_support(uv, array, threshold=0, scale=1):
    yy,xx=np.nonzero(array>threshold)
    return support_stats(uv,np.column_stack((xx,yy))/scale)


def record_stages(uv, analytic_visible, d, owner_part, scale=2):
    t=d['trace'];s=d['stages']
    stages={'analytic_visible':{'supported':bool(analytic_visible)},
            'dense_unrounded':support_stats(uv,t['uv'][t['inside']]/scale),
            'rounded_pre_z':pixel_support(uv,d['pre_z'],0,scale),
            'accepted_deposition':pixel_support(uv,s['raw'],0,scale),
            'width_foreground':pixel_support(uv,s['clipped'],0,scale),
            'isolated_AA':pixel_support(uv,s['downsample'],.04*255),
            'combined_hatch':pixel_support(uv,d['before_id']),
            'identified':pixel_support(uv,d['identified'])}
    extra={'zpass_before_foreground':support_stats(uv,t['pixel'][t['zpass']]/scale),
           'width_before_clip':pixel_support(uv,s['width'],0,scale),
           'quantized_before_resize':pixel_support(uv,s['quantized'],0,scale)}
    local=np.linalg.norm(t['uv']/scale-uv,axis=1)<=1.5
    local_round=np.linalg.norm(t['pixel']/scale-uv,axis=1)<=1.5
    exact_visible=(t['exact_mesh_part']==owner_part)&(abs(t['z']-t['exact_mesh_depth'])<=.006)
    analytic=(t['analytic_exact_part']==owner_part)&(abs(t['z']-t['analytic_exact_depth'])<=.006)
    rounded_analytic_reject=t['z']>t['analytic_rounded_depth']+.006
    rejected=local & t['inside'] & ~t['zpass']
    exgap=t['z']-t['exact_mesh_depth'];pixgap=t['z']-t['pixel_depth']
    def stats(a):
        a=a[np.isfinite(a)]
        return {'count':len(a),'min':float(a.min()) if len(a) else None,'max':float(a.max()) if len(a) else None}
    witnesses={'local_dense_count':int(local.sum()),'local_rounded_count':int(local_round.sum()),
               'local_zpass_count':int((local&t['zpass']).sum()),
               'local_accepted_count':int((local&t['accepted']).sum()),
               'local_rejected_count':int(rejected.sum()),
               'rejected_but_exact_mesh_visible':int((rejected&exact_visible).sum()),
               'rejected_but_analytic_visible':int((rejected&analytic).sum()),
               'rejected_and_rounded_analytic_rejects':int((rejected&rounded_analytic_reject).sum()),
               'rejected_exact_mesh_other_part':int((rejected&(t['exact_mesh_part']!=owner_part)).sum()),
               'rejected_exact_mesh_occluded_same_part':int((rejected&(t['exact_mesh_part']==owner_part)&(exgap>.006)).sum()),
               'rejected_point_minus_exact_mesh_depth':stats(exgap[rejected]),
               'rejected_point_minus_pixel_mesh_depth':stats(pixgap[rejected]),
               'rejected_rounded_mesh_minus_zbuffer_depth':stats((t['rounded_mesh_depth']-t['pixel_depth'])[rejected]),
               'all_local_dense_indices':np.flatnonzero(local).tolist(),
               'all_local_rounded_indices':np.flatnonzero(local_round).tolist()}
    influence={}
    for name in ['hatch','full']:
        delta=d[name+'_leave_one_out_delta']
        yy,xx=np.mgrid[:delta.shape[0],:delta.shape[1]]
        disk=(xx-uv[0])**2+(yy-uv[1])**2<=1.5**2
        influence[name]={'nonzero':pixel_support(uv,delta),
                         'above_0_04':pixel_support(uv,delta,.04*255),
                         'local_max_delta_uint8':int(delta[disk].max()) if disk.any() else 0,
                         'local_sum_abs_delta_uint8':int(delta[disk].sum())}
    flags=[stages[k]['supported'] for k in STAGE_NAMES]
    return {'stages':stages,'extra_stages':extra,'flags':flags,
            'loss_stage':classify_stages(flags),'witnesses':witnesses,'final_influence':influence}
