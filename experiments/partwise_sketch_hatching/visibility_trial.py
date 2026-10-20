"""Independent analytic evaluator for the separate visibility-only plane candidate."""
import round006_common as c
import numpy as np
from scipy import ndimage
import core
import coverage_fixture as oracle
import visibility_primitive as candidate


def depth_check(actual,truth):
    valid=np.isfinite(actual)&np.isfinite(truth)
    return {'finite_masks_equal':bool(np.array_equal(np.isfinite(actual),np.isfinite(truth))),
            'max_abs_error':float(abs(actual[valid]-truth[valid]).max()) if valid.any() else None,
            'common_finite_count':int(valid.sum())}


def stats(high,reference,visible,hidden,unsupported,footprint):
    support=high>0;nv=int(visible.sum());nh=int(hidden.sum())
    return {'visible_denominator':nv,'visible_retained':int((support&visible).sum()),
            'visible_recall':float((support&visible).sum()/nv) if nv else None,
            'visible_missing':int((visible&~support).sum()),'hidden_denominator':nh,
            'hidden_ink_sites':int((support&hidden).sum()),'hidden_ink_sum':float(high[hidden].sum()),
            'unsupported_owner_ink_sites':int((support&unsupported).sum()),
            'unsupported_owner_ink_sum':float(high[unsupported].sum()),
            'outside_footprint_ink_sites':int((support&~footprint).sum()),
            'reference_ink_sum':float(reference.sum()),'actual_ink_sum':float(high.sum()),
            'exact_reference_equal':bool(np.array_equal(high,reference))}


def evaluate_case(protocol,spec,split):
    cam=oracle.camera(protocol);scale=protocol['camera']['supersample'];size=cam['size'];pp=protocol['primitive']
    planes=[]
    for p in [spec['rear'],spec['front']]:
        if p is not None:planes.append(dict(p,bounds=[scale*b for b in p['bounds']]))
    rear=planes[0];ends=scale*np.array(spec['endpoints_output']);path=oracle.points_on_plane(ends,rear,cam)
    mesh=oracle.make_mesh(planes,cam)
    # Candidate receives finite triangles/path/camera only. Analytic coefficients stay here.
    result=candidate.render(mesh,[0,1],path,cam,pp['ink'],scale,pp['high_width_filter_size'],pp['dense_step_high_px'],pp['depth_tolerance_world'])
    yy,xx=np.mgrid[:size,:size];grid=np.stack((xx,yy),axis=-1)
    scene_z,scene_id=oracle.first_hit(grid,planes,cam);own_z=oracle.plane_depth(grid,rear,cam)
    finite=np.isfinite(own_z)&np.isfinite(scene_z);owner_visible=np.zeros(own_z.shape,bool)
    owner_visible[finite]=abs(own_z[finite]-scene_z[finite])<=oracle.EPS
    owner_hidden=finite&~owner_visible;unsupported=~np.isfinite(own_z)
    # Independent inherited footprint construction; never use candidate acceptance.
    points=core.dense_path(path,cam,pp['dense_step_high_px']);uv,z=core.project(points,cam);pix=np.rint(uv).astype(int)
    inside=(z>0)&(pix[:,0]>=0)&(pix[:,0]<size)&(pix[:,1]>=0)&(pix[:,1]<size)
    pre=np.zeros(scene_z.shape);np.maximum.at(pre,(pix[inside,1],pix[inside,0]),pp['ink'])
    expanded=ndimage.maximum_filter(pre,size=pp['high_width_filter_size']);foot=expanded>0
    visible=foot&owner_visible;hidden=foot&owner_hidden
    reference=expanded*owner_visible;ref_final=oracle.down(reference,scale)
    ribbon=oracle.ribbon_coverage(grid,ends,pp['screen_width_px']*scale)&np.isfinite(own_z)
    center_ref=ribbon*owner_visible*pp['ink'];center_final=oracle.down(center_ref,scale)
    # Historical primitive retained as control, from unchanged helpers.
    depth,parts=core.raster_surface(mesh,cam)
    accepted=core.visible_points(points,cam,depth,pp['depth_tolerance_world'])
    accepted[inside]&=parts[pix[inside,1],pix[inside,0]]>0
    accepted&=inside;raw=np.zeros(scene_z.shape)
    np.maximum.at(raw,(pix[accepted,1],pix[accepted,0]),pp['ink'])
    old_high=ndimage.maximum_filter(raw,size=pp['high_width_filter_size']);old_high[parts==0]=0
    old_final=oracle.down(old_high,scale)
    # Reverse both scene submission and owner face IDs; should not alter output.
    rev=core.finalize_mesh(mesh['vertices'],mesh['faces'][::-1],mesh['parts'][::-1])
    reverse=candidate.render(rev,[len(mesh['faces'])-1,len(mesh['faces'])-2],path,cam,pp['ink'],scale,pp['high_width_filter_size'],pp['dense_step_high_px'],pp['depth_tolerance_world'])
    dc=depth_check(result['scene_depth'],scene_z)
    oc=depth_check(result['owner_depth'][foot],own_z[foot])
    checks={'scene_depth':dc,'owner_depth':oc,'scene_owner_equal':bool(np.array_equal(result['scene_owner'],scene_id)),
            'pre_z_exact':bool(np.array_equal(result['pre_z'],pre)),
            'expanded_footprint_exact':bool(np.array_equal(result['footprint'],expanded)),
            'reverse_high_exact':bool(np.array_equal(result['high'],reverse['high'])),
            'reverse_final_exact':bool(np.array_equal(result['final_uint8'],reverse['final_uint8'])),
            'reverse_scene_depth':depth_check(reverse['scene_depth'],scene_z),
            'positive_finite_accepted':bool(np.all(np.isfinite(result['owner_depth'][result['gate']]) & np.isfinite(result['scene_depth'][result['gate']]) & (result['owner_depth'][result['gate']]>0)&(result['scene_depth'][result['gate']]>0))),
            'final_exact_matched_reference':bool(np.array_equal(result['final_uint8'],ref_final))}
    high=stats(result['high'],reference,visible,owner_hidden,unsupported,foot)
    legacy=stats(old_high,reference,visible,owner_hidden,unsupported,foot)
    owner_edge=oracle.rectangle_edge_distance(grid,rear['bounds'])<=4+oracle.EPS
    occ_edge=np.zeros(foot.shape,bool)
    if len(planes)>1:occ_edge=oracle.rectangle_edge_distance(grid,planes[1]['bounds'])<=4+oracle.EPS
    regions={name:stats(result['high']*m,reference*m,visible&m,owner_hidden&m,unsupported&m,foot) for name,m in [('occlusion_edge',occ_edge),('away_from_occlusion_edge',~occ_edge),('owner_edge',owner_edge)]}
    positive=visible&(yy<20*scale)
    controls={'positive_visible_sites':int(positive.sum()),'positive_ink_sites':int(((result['high']>0)&positive).sum()),
              'hidden_footprint_sites':int(hidden.sum()),'hidden_gap_min':float((own_z[hidden]-scene_z[hidden]).min()) if hidden.any() else None,
              'unsupported_foreground_footprint_sites':int((foot&unsupported&np.isfinite(scene_z)).sum()),
              'unsupported_background_footprint_sites':int((foot&unsupported&~np.isfinite(scene_z)).sum())}
    # For thin lines all support can lie in edge bands; no samples are excluded.
    low=oracle.aa_centers(protocol['camera']['resolution'],scale);ly,lx=np.meshgrid(low,low,indexing='ij');lowgrid=np.stack((lx,ly),axis=-1)
    lowz,lowid=oracle.first_hit(lowgrid,planes,cam);lowown=oracle.plane_depth(lowgrid,rear,cam)
    lowedge=np.zeros(ref_final.shape,bool)
    if len(planes)>1:lowedge=oracle.rectangle_edge_distance(lowgrid,planes[1]['bounds'])<=4+oracle.EPS
    lowhidden=np.isfinite(lowown)&(lowid==2)
    def aa_stats(mask):
        a=result['final_uint8'][mask]/255.;b=ref_final[mask]/255.;old=old_final[mask]/255.
        return {'pixels':int(mask.sum()),'candidate_ink_sum':float(a.sum()),'matched_reference_ink_sum':float(b.sum()),
                'legacy_ink_sum':float(old.sum()),'candidate_nonzero':int((a>0).sum()),'reference_nonzero':int((b>0).sum()),
                'candidate_L1':float(abs(a-b).sum()),'legacy_L1':float(abs(old-b).sum())}
    aa={name:aa_stats(mask) for name,mask in [('all',np.ones(ref_final.shape,bool)),('occlusion_edge',lowedge),('deep_occluder',lowhidden&~lowedge),('background',lowid==0),('unsupported_owner',~np.isfinite(lowown))]}
    centered={'visible_sites':int((ribbon&owner_visible).sum()),
              'visible_recall':float(((result['high']>0)&ribbon&owner_visible).sum()/(ribbon&owner_visible).sum()) if (ribbon&owner_visible).any() else None,
              'extra_visible_sites':int(((result['high']>0)&owner_visible&~ribbon).sum()),
              'support_symmetric_difference':int(np.count_nonzero((result['high']>0)!=(center_ref>0))),
              'final_L1_ink_sum':float(abs(result['final_uint8']/255.-center_final/255.).sum())}
    oracle_ok=all(d['finite_masks_equal'] and d['max_abs_error'] is not None and d['max_abs_error']<=oracle.EPS for d in [dc,oc,checks['reverse_scene_depth']]) and checks['scene_owner_equal']
    control_ok=controls['positive_visible_sites']>0 and controls['positive_ink_sites']==controls['positive_visible_sites']
    if spec['family'].startswith('overlap'):control_ok &= hidden.any() and controls['hidden_gap_min']>.5
    if spec['family']=='owner_side_foreground':control_ok &= controls['unsupported_foreground_footprint_sites']>0
    if spec['family']=='owner_end_background':control_ok &= controls['unsupported_background_footprint_sites']>0
    gates={'oracle_valid':bool(oracle_ok),'known_controls':bool(control_ok),'nonempty_visible':high['visible_denominator']>0,
           'matched_recall_one':high['visible_recall']==1.,'zero_hidden_ink':high['hidden_ink_sites']==0,
           'zero_unsupported_ink':high['unsupported_owner_ink_sites']==0,
           'zero_outside_footprint':high['outside_footprint_ink_sites']==0,
           'high_exact_reference':high['exact_reference_equal'],
           **{k:checks[k] for k in ['pre_z_exact','expanded_footprint_exact','reverse_high_exact','reverse_final_exact','positive_finite_accepted','final_exact_matched_reference']}}
    m={'case_id':spec['id'],'split':split,'family':spec['family'],'phase_output_px':spec['phase_output_px'],
       'high':high,'legacy':legacy,'controls':controls,'checks':checks,'regions':regions,'AA':aa,'centered':centered,'gates':gates,'case_go':all(gates.values())}
    arrays={**{'candidate_'+k:v for k,v in result.items()},'oracle_scene_depth':scene_z,'oracle_scene_id':scene_id,'oracle_owner_depth':own_z,
            'reference_pre_z':pre,'reference_expanded':expanded,'matched_visible':visible,'matched_hidden':hidden,'owner_hidden':owner_hidden,
            'owner_unsupported':unsupported,'matched_reference':reference,'matched_final_uint8':ref_final,
            'centered_ribbon':ribbon,'centered_reference':center_ref,'centered_final_uint8':center_final,
            'legacy_raw':raw,'legacy_high':old_high,'legacy_final_uint8':old_final,'legacy_point_accepted':accepted,
            'occlusion_edge':occ_edge,'owner_edge':owner_edge,'AA_scene_id':lowid,'AA_occlusion_edge':lowedge,'AA_deep_hidden':lowhidden&~lowedge,
            'mesh_vertices':mesh['vertices'],'mesh_faces':mesh['faces'],'mesh_parts':mesh['parts'],'stroke_path':path,'projected_endpoints':ends}
    return m,arrays
