"""Independent finite-plane coverage truth and unchanged legacy primitive adapter.

All coordinates are optical camera coordinates. This module is a diagnostic;
it does not implement or select a replacement renderer.
"""
import round005_common as common
import numpy as np
from scipy import ndimage
from PIL import Image
import core
import stage_attribution as stages
EPS = 1e-9


def camera(protocol):
    p = protocol['camera']; scale = p['supersample']; size = p['resolution']*scale
    return {'size':size, 'focal':p['focal_output_px']*scale,
            'center':np.array(p['center_high_px']), 'R':np.eye(3),
            't':np.zeros(3), 'eye':np.zeros(3)}


def plane_depth(uv, plane, c):
    """Closed-form plane/ray intersection, clipped to finite projected patch."""
    uv = np.asarray(uv, float)
    rayxy = (uv-c['center'])/c['focal']
    den = 1-plane['sx']*rayxy[...,0]-plane['sy']*rayxy[...,1]
    z = np.divide(plane['z0'], den, out=np.full(den.shape, np.inf), where=den>EPS)
    x0,y0,x1,y1 = plane['bounds']
    inside = (uv[...,0]>=x0-EPS)&(uv[...,0]<=x1+EPS)&(uv[...,1]>=y0-EPS)&(uv[...,1]<=y1+EPS)
    return np.where(inside&(z>0),z,np.inf)


def first_hit(uv, planes, c):
    best = np.full(np.asarray(uv).shape[:-1],np.inf)
    owner = np.zeros(best.shape,np.int16)
    for p in planes:
        z = plane_depth(uv,p,c); take = z<best
        best[take] = z[take]; owner[take] = p['id']
    return best,owner


def points_on_plane(uv, plane, c):
    uv = np.asarray(uv,float); z = plane_depth(uv,plane,c)
    assert np.isfinite(z).all()
    return np.concatenate(((uv-c['center'])/c['focal'],np.ones((*uv.shape[:-1],1))),axis=-1)*z[...,None]


def make_mesh(planes, c):
    vertices=[];faces=[];parts=[]
    for p in planes:
        x0,y0,x1,y1=p['bounds']
        q=np.array([[x0,y0],[x1,y0],[x1,y1],[x0,y1]])
        start=len(vertices);vertices.extend(points_on_plane(q,p,c))
        faces.extend([[start,start+1,start+2],[start,start+2,start+3]])
        parts.extend([p['id'],p['id']])
    return core.finalize_mesh(vertices,faces,parts)


def ribbon_coverage(uv, ends, width):
    """Centered vertical rectangle with butt caps. Closed sampled boundary."""
    uv=np.asarray(uv,float);ends=np.asarray(ends,float)
    assert abs(ends[0,0]-ends[1,0])<EPS
    lo,hi=sorted(ends[:,1]);center=ends[0,0]
    return (abs(uv[...,0]-center)<=width/2+EPS)&(uv[...,1]>=lo-EPS)&(uv[...,1]<=hi+EPS)


def aa_centers(size, scale):
    # PIL resize maps output center (j+.5) to input center (j+.5)*scale.
    # Input geometric sample index is the latter minus .5.
    return (np.arange(size)+.5)*scale-.5


def rectangle_edge_distance(uv, bounds):
    x0,y0,x1,y1=bounds;uv=np.asarray(uv,float)
    x,y=uv[...,0],uv[...,1]
    dx=np.maximum(np.maximum(x0-x,x-x1),0)
    dy=np.maximum(np.maximum(y0-y,y-y1),0)
    outside=np.hypot(dx,dy)
    inside=np.minimum.reduce([x-x0,x1-x,y-y0,y1-y])
    return np.where((dx==0)&(dy==0),inside,outside)


def down(ink, scale=2):
    h,w=ink.shape
    q=np.uint8(np.clip(ink,0,1)*255)
    return np.asarray(Image.fromarray(q).resize((w//scale,h//scale),Image.Resampling.LANCZOS))


def coverage_counts(ink, visible, hidden):
    support=ink>0; nv=int(visible.sum());nh=int(hidden.sum())
    retained=int((support&visible).sum());leaked=int((support&hidden).sum())
    return {'visible_sites':nv,'visible_retained_sites':retained,
            'visible_missing_sites':nv-retained,'visible_retained_fraction':retained/nv if nv else None,
            'hidden_sites':nh,'hidden_ink_sites':leaked,
            'hidden_ink_fraction':leaked/nh if nh else None,
            'hidden_ink_sum':float(ink[hidden].sum())}


def _maxfinite(a,b):
    assert np.array_equal(np.isfinite(a),np.isfinite(b))
    good=np.isfinite(a)
    return float(np.max(abs(a[good]-b[good]))) if good.any() else 0.


def run_case(protocol, scene, phase):
    c=camera(protocol);size=c['size'];scale=protocol['camera']['supersample']
    g=protocol['geometry'];pp=protocol['primitive'];ink=pp['ink'];tol=pp['depth_tolerance_world']
    rear={k:scene[k] for k in ('z0','sx','sy')}
    rear.update(bounds=[scale*x for x in g['rear_patch_output_bounds_xyxy']],id=1)
    planes=[rear]
    if scene['occluder']:
        z0,sx,sy=g['front_plane']
        planes.append({'z0':z0,'sx':sx,'sy':sy,'bounds':[scale*x for x in g['front_patch_output_bounds_xyxy']],'id':2})
    ends=scale*np.array([[32+phase,12+phase],[32+phase,52+phase]])
    path=points_on_plane(ends,rear,c)
    mesh=make_mesh(planes,c);depth,parts=core.raster_surface(mesh,c)
    yy,xx=np.mgrid[:size,:size];grid=np.stack((xx,yy),axis=-1)
    oracle_depth,oracle_owner=first_hit(grid,planes,c)
    own_depth=plane_depth(grid,rear,c)
    own_exists=np.isfinite(own_depth)
    owner_visible=own_exists&(oracle_owner==1)
    # Owner identity is equivalent here to depth equality: no coincident planes.
    depth_equal=np.zeros(depth.shape,bool)
    valid=np.isfinite(own_depth)&np.isfinite(oracle_depth)
    depth_equal[valid]=abs(own_depth[valid]-oracle_depth[valid])<=EPS
    assert np.array_equal(depth_equal,owner_visible)
    owner_hidden=own_exists&~owner_visible
    foot=ribbon_coverage(grid,ends,pp['screen_width_px']*scale)&own_exists
    visible=foot&owner_visible;hidden=foot&owner_hidden
    points=core.dense_path(path,c,pp['dense_step_high_px'])
    uv,z=core.project(points,c);pixel=np.rint(uv).astype(int)
    exact_depth,exact_owner=first_hit(uv,planes,c)
    rounded_depth,rounded_owner=first_hit(pixel,planes,c)
    rounded_own=plane_depth(pixel,rear,c)
    inside=(z>0)&(pixel[:,0]>=0)&(pixel[:,0]<size)&(pixel[:,1]>=0)&(pixel[:,1]<size)
    accepted=core.visible_points(points,c,depth,tol)
    accepted &= parts[pixel[:,1],pixel[:,0]]>0
    expected_zpass=inside&(z<=rounded_depth+tol)&(rounded_owner>0)
    assert np.array_equal(accepted,expected_zpass)
    exact_visible=abs(z-exact_depth)<=EPS
    rounded_visible=(rounded_owner==1)&np.isfinite(rounded_own)
    pre=np.zeros(depth.shape);raw=np.zeros(depth.shape)
    np.maximum.at(pre,(pixel[inside,1],pixel[inside,0]),ink)
    np.maximum.at(raw,(pixel[accepted,1],pixel[accepted,0]),ink)
    width=ndimage.maximum_filter(raw,size=pp['high_width_filter_size'])
    clipped=width.copy();clipped[parts==0]=0
    pre_width=ndimage.maximum_filter(pre,size=pp['high_width_filter_size']);pre_width[parts==0]=0
    final=down(clipped,scale);reference=visible.astype(float)*ink;ref_final=down(reference,scale)
    # Read-only inherited stage implementation and crop adapter must reproduce bytes.
    old=stages.layer_stages(raw,parts,scale,pp['high_width_filter_size'])
    np.testing.assert_array_equal(old['clipped'],clipped);np.testing.assert_array_equal(old['downsample'],final)
    x0,y0,small,_=stages.ta.layer_crop(pixel[accepted],ink,parts,scale,pp['high_width_filter_size'])
    assembled=np.zeros(final.shape,np.uint8)
    assembled[y0:y0+small.shape[0],x0:x0+small.shape[1]]=small
    np.testing.assert_array_equal(assembled,final)
    reverse=core.finalize_mesh(mesh['vertices'],mesh['faces'][::-1],mesh['parts'][::-1])
    reversed_depth,reversed_parts=core.raster_surface(reverse,c)
    ray_depth,ray_owner,_=stages.exact_mesh_rays(mesh,c,grid.reshape(-1,2))
    depth_error=_maxfinite(depth,oracle_depth)
    ray_error=_maxfinite(ray_depth.reshape(depth.shape),oracle_depth)
    order_error=_maxfinite(reversed_depth,depth)
    roundtrip,_=core.project(path,c)
    checks={'raster_depth_max_error':depth_error,'triangle_ray_max_error':ray_error,
            'reverse_depth_max_error':order_error,'projection_max_error':float(abs(roundtrip-ends).max()),
            'raster_owner_equal':bool(np.array_equal(parts,oracle_owner)),
            'triangle_owner_equal':bool(np.array_equal(ray_owner.reshape(parts.shape),oracle_owner)),
            'reverse_owner_equal':bool(np.array_equal(reversed_parts,parts)),
            'adapter_stage_equal':True,'adapter_crop_equal':True}
    checks['oracle_valid']=all(checks[k] for k in ('raster_owner_equal','triangle_owner_equal','reverse_owner_equal')) and max(depth_error,ray_error,order_error,checks['projection_max_error'])<=EPS
    occl_edge=np.zeros(depth.shape,bool)
    if scene['occluder']:
        occl_edge=rectangle_edge_distance(grid,planes[1]['bounds'])<=4+EPS
    ribbon_bounds=[ends[0,0]-1,min(ends[:,1]),ends[0,0]+1,max(ends[:,1])]
    general_edge=(rectangle_edge_distance(grid,ribbon_bounds)<=4+EPS)|(rectangle_edge_distance(grid,rear['bounds'])<=4+EPS)|occl_edge
    core_hidden=foot&owner_hidden&(yy>=28*scale)&(yy<=36*scale)
    visible_control=foot&owner_visible&(yy>=16*scale)&(yy<=20*scale)
    main=coverage_counts(clipped,visible,hidden)
    main.update(all_hidden_owner_ink_sites=int(((clipped>0)&owner_hidden).sum()),
                all_hidden_owner_ink_sum=float(clipped[owner_hidden].sum()),
                hidden_raw_deposit_sites=int(((raw>0)&owner_hidden).sum()),
                hidden_width_added_sites=int(((width>0)&(raw==0)&owner_hidden).sum()),
                extra_visible_footprint_sites=int(((clipped>0)&owner_visible&~foot).sum()),
                all_actual_ink_sites=int((clipped>0).sum()),
                all_reference_ink_sites=int(visible.sum()),
                matched_candidate_visible_sites=int(((pre_width>0)&owner_visible).sum()),
                matched_candidate_visible_missing_sites=int(((pre_width>0)&owner_visible&(clipped==0)).sum()),
                ribbon_edge_sites=int((foot&general_edge).sum()),
                ribbon_nonedge_sites=int((foot&~general_edge).sum()))
    regions={name:coverage_counts(clipped,visible&m,hidden&m) for name,m in
             [('occlusion_edge',occl_edge),('away_from_occlusion_edge',~occl_edge),('all_edge',general_edge)]}
    point_metrics={'dense_count':len(points),'accepted_count':int(accepted.sum()),
                   'exact_visible_count':int(exact_visible.sum()),
                   'rounded_owner_visible_count':int(rounded_visible.sum()),
                   'rejected_rounded_visible_count':int((~accepted&rounded_visible).sum()),
                   'exact_visible_rounded_hidden_count':int((exact_visible&~rounded_visible).sum()),
                   'rejected_rounded_hidden_count':int((~accepted&~rounded_visible).sum()),
                   'accepted_rounded_hidden_count':int((accepted&~rounded_visible).sum()),
                   'point_minus_rounded_own_depth_min':float((z-rounded_own).min()),
                   'point_minus_rounded_own_depth_max':float((z-rounded_own).max())}
    low=aa_centers(protocol['camera']['resolution'],scale)
    ly,lx=np.meshgrid(low,low,indexing='ij');lowgrid=np.stack((lx,ly),axis=-1)
    _,lowowner=first_hit(lowgrid,planes,c)
    aa_edge=np.zeros(final.shape,bool)
    if scene['occluder']:aa_edge=rectangle_edge_distance(lowgrid,planes[1]['bounds'])<=4+EPS
    aa_deep_hidden=(lowowner==2)&~aa_edge
    a=final.astype(float)/255.;b=ref_final.astype(float)/255.
    def aa_stats(mask):
        denom=float(b[mask].sum())
        return {'pixels':int(mask.sum()),'actual_ink_sum':float(a[mask].sum()),'reference_ink_sum':denom,
                'L1_ink_sum':float(abs(a[mask]-b[mask]).sum()),
                'excess_ink_sum':float(np.maximum(a[mask]-b[mask],0).sum()),
                'retained_reference_ink_fraction':float(np.minimum(a[mask],b[mask]).sum())/denom if denom else None,
                'actual_nonzero_pixels':int((a[mask]>0).sum()),'reference_nonzero_pixels':int((b[mask]>0).sum())}
    aa={'all':aa_stats(np.ones(final.shape,bool)),'occlusion_edge':aa_stats(aa_edge),
        'deep_occluder':aa_stats(aa_deep_hidden),'center_mapping':'2*j+0.5 high-res sample coordinates'}
    controls={'visible_control_sites':int(visible_control.sum()),
              'visible_control_actual_sites':int(((clipped>0)&visible_control).sum()),
              'hidden_control_sites':int(core_hidden.sum()),
              'hidden_control_raw_sites':int(((raw>0)&core_hidden).sum()),
              'hidden_control_width_sites':int(((clipped>0)&core_hidden).sum()),
              'clear_hidden_depth_gap_min':float((own_depth[core_hidden]-oracle_depth[core_hidden]).min()) if core_hidden.any() else None}
    controls['known_control_pass']=bool(visible_control.any())
    if scene['id']=='flat': controls['known_control_pass'] &= bool(accepted.all() and controls['visible_control_actual_sites']>0)
    if scene['occluder']:
        controls['known_control_pass'] &= bool(core_hidden.any() and controls['hidden_control_raw_sites']==0 and controls['hidden_control_width_sites']==0 and controls['clear_hidden_depth_gap_min']>.5)
    metrics={'scene':scene['id'],'phase_output_px':phase,'high':main,'regions':regions,
             'points':point_metrics,'AA':aa,'checks':checks,'controls':controls}
    arrays={'grid_uv':grid,'mesh_depth':depth,'mesh_owner':parts,'oracle_depth':oracle_depth,
            'oracle_owner':oracle_owner,'own_depth':own_depth,'footprint':foot,'oracle_visible':visible,
            'oracle_hidden':hidden,'owner_visible':owner_visible,'owner_hidden':owner_hidden,
            'pre_z':pre,'accepted_raw':raw,'width':width,'clipped':clipped,'pre_z_width':pre_width,
            'reference_ink':reference,'final_uint8':final,'reference_final_uint8':ref_final,
            'occlusion_edge':occl_edge,'all_edge':general_edge,'clear_hidden':core_hidden,
            'clear_visible':visible_control,'AA_edge':aa_edge,'AA_deep_hidden':aa_deep_hidden,'AA_owner':lowowner,
            'point_xyz':points,'point_uv':uv,'point_z':z,'point_pixel':pixel,
            'point_exact_depth':exact_depth,'point_exact_owner':exact_owner,
            'point_rounded_depth':rounded_depth,'point_rounded_owner':rounded_owner,
            'point_rounded_own_depth':rounded_own,'point_exact_visible':exact_visible,
            'point_rounded_visible':rounded_visible,'point_accepted':accepted,
            'stroke_endpoints':path,'projected_endpoints':ends,'plane_vertices':mesh['vertices'],
            'plane_faces':mesh['faces'],'plane_parts':mesh['parts']}
    return metrics,arrays
