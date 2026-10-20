"""Independent piecewise analytic patch fixtures and attachment validation.

The unchanged candidate receives only mesh, explicit owner IDs, path and camera.
Truth uses plane equations and finite XY halfspaces, never candidate hits.
"""
import round007_common as common
import numpy as np
from scipy import ndimage
import core
import coverage_fixture as old_oracle
import visibility_primitive as candidate
from visibility_trial import depth_check, stats
EPS=1e-9


def xyz(xy, face):
    xy=np.asarray(xy,float)
    return np.concatenate((xy,(face['z0']+face['sx']*xy[...,0]+face['sy']*xy[...,1])[...,None]),axis=-1)


def margins(xy, triangle):
    """Signed distance to each independent XY triangle supporting line."""
    tri=np.asarray(triangle,float);p=np.asarray(xy,float)
    e0=tri[1]-tri[0];e1=tri[2]-tri[0]
    area=e0[0]*e1[1]-e0[1]*e1[0]
    if abs(area)<1e-12:raise ValueError('degenerate analytic triangle')
    result=[]
    for a,b in zip(tri,np.roll(tri,-1,axis=0)):
        edge=b-a;q=p-a
        result.append(np.sign(area)*(edge[0]*q[...,1]-edge[1]*q[...,0])/np.linalg.norm(edge))
    return np.stack(result,axis=-1)


def validate_attachment(path, segment_faces, faces, shared_edge, eps=EPS):
    path=np.asarray(path,float);edge=np.asarray(shared_edge,float)
    if path.ndim!=2 or path.shape[1]!=3 or len(path)<2 or len(segment_faces)!=len(path)-1 or not np.isfinite(path).all():
        raise ValueError('attachment path shape, identity or finite-coordinate failure')
    residuals=[];minimum=[];transitions=0
    for i,fi in enumerate(segment_faces):
        if fi<0 or fi>=len(faces):raise ValueError('attachment unknown segment face')
        f=faces[fi];ends=path[i:i+2]
        residual=abs(ends[:,2]-f['z0']-f['sx']*ends[:,0]-f['sy']*ends[:,1])
        domain=margins(ends[:,:2],f['xy'])
        if np.max(residual)>eps or np.min(domain)<-eps:raise ValueError('attachment segment endpoints violate declared finite plane')
        residuals.extend(residual.tolist());minimum.append(float(domain.min()))
        if i and segment_faces[i-1]!=fi:
            before=xyz(faces[segment_faces[i-1]]['xy'],faces[segment_faces[i-1]])
            after=xyz(f['xy'],f)
            common_vertices=[a for a in before if np.any(np.linalg.norm(after-a,axis=1)<=eps)]
            if len(common_vertices)!=2 or edge.shape!=(2,3) or not np.isfinite(edge).all():raise ValueError('shared edge not a genuine two-vertex intersection')
            if any(not np.any(np.linalg.norm(np.array(common_vertices)-a,axis=1)<=eps) for a in edge):raise ValueError('shared edge declaration differs from actual shared vertices')
            v=edge[1]-edge[0];length2=float(v@v)
            if length2<=eps**2:raise ValueError('shared edge degenerate')
            t=float((path[i]-edge[0])@v/length2)
            if t < -eps or t > 1+eps or np.linalg.norm(path[i]-(edge[0]+t*v))>eps:raise ValueError('shared edge waypoint missing')
            transitions+=1
    return {'valid':True,'segments':len(segment_faces),'face_transitions':transitions,'plane_residual_max':max(residuals),'domain_margin_min':min(minimum),'segment_faces':list(segment_faces)}


def camera(protocol, phase):
    c=old_oracle.camera(protocol);c['center']=c['center']+phase*protocol['camera']['supersample'];return c


def fixture(protocol,spec,negative=False):
    g=protocol['geometry'];domains=np.array(g['owner_xy_triangles'],float)
    if negative:domains[1,2]=spec['triangle1_apex_xy']
    faces=[{'z0':g['z0'],'sx':g['sx'],'sy':slope,'xy':domain.tolist(),'part_id':1} for slope,domain in zip(spec['slopes_y'],domains)]
    cam=camera(protocol,spec['phase_output_px']);vertices=[];indices=[];lookup={}
    for f in faces:
        ids=[]
        for v in xyz(f['xy'],f):
            key=tuple(v)
            if key not in lookup:lookup[key]=len(vertices);vertices.append(v)
            ids.append(lookup[key])
        indices.append(ids)
    path=np.stack([xyz(q,faces[0 if i==0 else 1]) for i,q in enumerate(spec['path_xy'])])
    parts=[1,1];extras=[]
    extra_name=spec.get('extra_scene')
    if extra_name:
        extra=dict(g[extra_name]);extra['bounds']=[x*protocol['camera']['supersample'] for x in extra['bounds_output_xyxy']];extras.append(extra)
        x0,y0,x1,y1=extra['bounds'];uv=np.array([[x0,y0],[x1,y0],[x1,y1],[x0,y1]])
        q=old_oracle.points_on_plane(uv,extra,cam);start=len(vertices);vertices.extend(q)
        indices.extend([[start,start+1,start+2],[start,start+2,start+3]]);parts.extend([extra['part_id']]*2)
    mesh=core.finalize_mesh(vertices,indices,parts)
    return cam,faces,extras,mesh,path


def analytic_depth(uv,face,cam):
    uv=np.asarray(uv,float)
    ray=np.concatenate(((uv-cam['center'])/cam['focal'],np.ones((*uv.shape[:-1],1))),axis=-1)@cam['R']
    n=np.array([-face['sx'],-face['sy'],1.]);den=ray@n
    z=np.divide(face['z0']-cam['eye']@n,den,out=np.full(den.shape,np.inf),where=abs(den)>1e-12)
    safe=np.where(np.isfinite(z),z,0.)
    world=cam['eye']+ray*safe[...,None]
    inside=np.min(margins(world[...,:2],face['xy']),axis=-1)>=-EPS
    return np.where(inside&np.isfinite(z)&(z>0),z,np.inf)


def truth(uv,faces,extras,cam):
    owner_depths=np.stack([analytic_depth(uv,f,cam) for f in faces])
    owner=np.min(owner_depths,axis=0);scene=owner.copy();part=np.where(np.isfinite(owner),1,0).astype(np.int32)
    component=np.where(np.isfinite(owner),1+np.argmin(owner_depths,axis=0),0).astype(np.int32)
    for extra in extras:
        z=old_oracle.plane_depth(uv,extra,cam);take=z<scene
        scene[take]=z[take];part[take]=extra['part_id'];component[take]=3 if extra['part_id']==2 else 4
    both=np.isfinite(owner_depths).all(axis=0);ambiguous=np.zeros(both.shape,bool)
    ambiguous[both]=abs(owner_depths[0,both]-owner_depths[1,both])>EPS
    visible=np.zeros(owner.shape,bool);finite=np.isfinite(owner)&np.isfinite(scene)
    visible[finite]=abs(owner[finite]-scene[finite])<=EPS
    return {'owner_faces_depth':owner_depths,'owner':owner,'scene':scene,'part':part,'component':component,'ambiguous':ambiguous,'visible':visible,'hidden':finite&~visible,'unsupported':~np.isfinite(owner)}


def raw_footprint(path,cam,pp):
    points=core.dense_path(path,cam,pp['dense_step_high_px']);uv,z=core.project(points,cam);pix=np.rint(uv).astype(int)
    inside=(z>0)&(pix[:,0]>=0)&(pix[:,0]<cam['size'])&(pix[:,1]>=0)&(pix[:,1]<cam['size'])
    pre=np.zeros((cam['size'],cam['size']));np.maximum.at(pre,(pix[inside,1],pix[inside,0]),pp['ink'])
    return pre,ndimage.maximum_filter(pre,size=pp['high_width_filter_size']),points,pix,inside


def centered_ribbon(grid,projected_path,width):
    answer=np.zeros(grid.shape[:-1],bool)
    for a,b in zip(projected_path[:-1],projected_path[1:]):
        v=b-a;q=grid-a;length2=float(v@v)
        t=(q@v)/length2;distance=abs(v[0]*q[...,1]-v[1]*q[...,0])/np.sqrt(length2)
        answer|=(t>=-EPS)&(t<=1+EPS)&(distance<=width/2+EPS)
    return answer


def render(mesh,path,cam,pp,scale,owners=(0,1)):
    return candidate.render(mesh,owners,path,cam,pp['ink'],scale,pp['high_width_filter_size'],pp['dense_step_high_px'],pp['depth_tolerance_world'])


def evaluate_case(protocol,spec):
    pp=protocol['primitive'];scale=protocol['camera']['supersample'];cam,faces,extras,mesh,path=fixture(protocol,spec)
    attachment=validate_attachment(path,spec['segment_owner_faces'],faces,protocol['geometry']['shared_edge_xyz'])
    yy,xx=np.mgrid[:cam['size'],:cam['size']];grid=np.stack((xx,yy),axis=-1)
    t=truth(grid,faces,extras,cam);pre,expanded,points,pix,inside=raw_footprint(path,cam,pp);foot=expanded>0
    result=render(mesh,path,cam,pp,scale)
    visible=foot&t['visible'];reference=expanded*t['visible'];ref_final=old_oracle.down(reference,scale)
    proj,_=core.project(path,cam);ribbon=centered_ribbon(grid,proj,pp['screen_width_px']*scale)&np.isfinite(t['owner'])
    center_ref=ribbon*t['visible']*pp['ink'];center_final=old_oracle.down(center_ref,scale)
    accepted=core.visible_points(points,cam,result['scene_depth'],pp['depth_tolerance_world']);accepted&=inside
    accepted[inside]&=result['scene_owner'][pix[inside,1],pix[inside,0]]>0
    legacy_pre=np.zeros(pre.shape);np.maximum.at(legacy_pre,(pix[accepted,1],pix[accepted,0]),pp['ink'])
    legacy=ndimage.maximum_filter(legacy_pre,size=pp['high_width_filter_size']);legacy[result['scene_owner']==0]=0;legacy_final=old_oracle.down(legacy,scale)
    revmesh=core.finalize_mesh(mesh['vertices'],mesh['faces'][::-1],mesh['parts'][::-1]);n=len(mesh['faces'])
    rev=render(revmesh,path,cam,pp,scale,[n-1,n-2]);ownerrev=render(mesh,path,cam,pp,scale,[1,0])
    dc=depth_check(result['scene_depth'],t['scene']);oc=depth_check(result['owner_depth'][foot],t['owner'][foot]);rc=depth_check(rev['scene_depth'],t['scene'])
    high=stats(result['high'],reference,visible,t['hidden'],t['unsupported'],foot);old=stats(legacy,reference,visible,t['hidden'],t['unsupported'],foot)
    hidden=foot&t['hidden'];unsupported_fg=foot&t['unsupported']&np.isfinite(t['scene']);unsupported_bg=foot&t['unsupported']&~np.isfinite(t['scene'])
    controls={'visible_sites':int(visible.sum()),'hidden_footprint_sites':int(hidden.sum()),'hidden_gap_min':float((t['owner'][hidden]-t['scene'][hidden]).min()) if hidden.any() else None,'unsupported_foreground_sites':int(unsupported_fg.sum()),'unsupported_background_sites':int(unsupported_bg.sum()),'samepart_unsupported_foreground_sites':int((unsupported_fg&(t['part']==1)).sum()),'ambiguous_owner_footprint_sites':int((foot&t['ambiguous']).sum()),'shared_edge_vertex_count':len(set(mesh['faces'][0])&set(mesh['faces'][1]))}
    checks={'scene_depth':dc,'owner_depth':oc,'reverse_scene_depth':rc,'scene_parts_equal':bool(np.array_equal(result['scene_owner'],t['part'])),'pre_z_exact':bool(np.array_equal(result['pre_z'],pre)),'expanded_exact':bool(np.array_equal(result['footprint'],expanded)),'reverse_scene_high_exact':bool(np.array_equal(result['high'],rev['high'])),'reverse_scene_final_exact':bool(np.array_equal(result['final_uint8'],rev['final_uint8'])),'reverse_owner_high_exact':bool(np.array_equal(result['high'],ownerrev['high'])),'reverse_owner_final_exact':bool(np.array_equal(result['final_uint8'],ownerrev['final_uint8'])),'final_matched_exact':bool(np.array_equal(result['final_uint8'],ref_final))}
    low=old_oracle.aa_centers(protocol['camera']['resolution'],scale);ly,lx=np.meshgrid(low,low,indexing='ij');lg=np.stack((lx,ly),axis=-1);lt=truth(lg,faces,extras,cam)
    edge=np.zeros(lt['scene'].shape,bool)
    if extras and spec['extra_scene']=='front':edge=old_oracle.rectangle_edge_distance(lg,extras[0]['bounds'])<=protocol['oracle']['edge_band_high_px']+EPS
    def aa(mask):
        act=result['final_uint8'][mask]/255.;ref=ref_final[mask]/255.
        return {'pixels':int(mask.sum()),'candidate_ink_sum':float(act.sum()),'reference_ink_sum':float(ref.sum()),'candidate_nonzero':int((act>0).sum()),'reference_nonzero':int((ref>0).sum()),'L1':float(abs(act-ref).sum())}
    aa_stats={k:aa(mask) for k,mask in [('all',np.ones(edge.shape,bool)),('background',~np.isfinite(lt['scene'])),('hidden',lt['hidden']),('unsupported',lt['unsupported']),('occlusion_edge',edge),('deep_hidden',lt['hidden']&~edge)]}
    center_visible=ribbon&t['visible'];centered={'visible_sites':int(center_visible.sum()),'visible_recall':float(((result['high']>0)&center_visible).sum()/center_visible.sum()),'support_symmetric_difference':int(np.count_nonzero((result['high']>0)!=(center_ref>0))),'final_L1':float(abs(result['final_uint8']/255.-center_final/255.).sum())}
    known=visible.any() and controls['shared_edge_vertex_count']==2 and attachment['face_transitions']==1
    if spec['family']=='valley_occluded':known &= hidden.any() and controls['hidden_gap_min']>protocol['oracle']['physical_hidden_gap_min_world']
    if spec['family']=='ridge_edge_background':known &= unsupported_bg.any()
    if spec['family']=='valley_edge_samepart':known &= controls['samepart_unsupported_foreground_sites']>0
    gates={'attachment_valid':attachment['valid'],'known_controls_nonempty':bool(known),'oracle_valid':all(x['finite_masks_equal'] and x['max_abs_error'] is not None and x['max_abs_error']<=EPS for x in [dc,oc,rc]) and checks['scene_parts_equal'],'ordinary_owner_unambiguous':controls['ambiguous_owner_footprint_sites']==0,'matched_recall_one':high['visible_recall']==1.,'zero_hidden_ink':high['hidden_ink_sites']==0,'zero_unsupported_ink':high['unsupported_owner_ink_sites']==0,'zero_outside_footprint':high['outside_footprint_ink_sites']==0,'high_exact_reference':high['exact_reference_equal'],**{k:v for k,v in checks.items() if isinstance(v,bool)}}
    m={'case_id':spec['id'],'family':spec['family'],'phase_output_px':spec['phase_output_px'],'crease_angle_degrees':spec['crease_angle_degrees'],'attachment':attachment,'high':high,'legacy':old,'controls':controls,'checks':checks,'AA':aa_stats,'centered':centered,'gates':gates,'case_go':all(gates.values())}
    a={**{'candidate_'+k:v for k,v in result.items()},**{'oracle_'+k:v for k,v in t.items()},'reference_pre_z':pre,'reference_expanded':expanded,'matched_visible':visible,'matched_reference':reference,'matched_final_uint8':ref_final,'centered_ribbon':ribbon,'centered_reference':center_ref,'centered_final_uint8':center_final,'legacy_high':legacy,'legacy_final_uint8':legacy_final,'AA_component':lt['component'],'AA_hidden':lt['hidden'],'AA_unsupported':lt['unsupported'],'AA_edge':edge,'mesh_vertices':mesh['vertices'],'mesh_faces':mesh['faces'],'mesh_parts':mesh['parts'],'stroke_path':path,'projected_path':proj,'segment_owner_faces':np.array(spec['segment_owner_faces']),'reverse_scene_high':rev['high'],'reverse_scene_final_uint8':rev['final_uint8']}
    return m,a


def negative_controls(protocol):
    results=[]
    for spec in protocol['acceptance']['cases']:
        cam,faces,extras,mesh,path=fixture(protocol,spec)
        for fi in (0,1):
            try:validate_attachment(path[[0,2]],[fi],faces,protocol['geometry']['shared_edge_xyz'])
            except ValueError as ex:message=str(ex)
            else:message='NO_ERROR'
            results.append({'case_id':spec['id'],'declared_chord_face':fi,'error':message,'pass':message.startswith('attachment')})
    spec=protocol['negative_controls']['multidepth_connected'];cam,faces,extras,mesh,path=fixture(protocol,spec,True)
    attached=validate_attachment(path,spec['segment_owner_faces'],faces,protocol['geometry']['shared_edge_xyz'])
    yy,xx=np.mgrid[:cam['size'],:cam['size']];grid=np.stack((xx,yy),axis=-1);t=truth(grid,faces,extras,cam)
    pre,expanded,*_=raw_footprint(path,cam,protocol['primitive']);ambiguous=(expanded>0)&t['ambiguous']
    gap=abs(t['owner_faces_depth'][0,ambiguous]-t['owner_faces_depth'][1,ambiguous])
    try:render(mesh,path,cam,protocol['primitive'],protocol['camera']['supersample'])
    except ValueError as ex:message=str(ex)
    else:message='NO_ERROR'
    mult={'attachment':attached,'ambiguous_footprint_sites':int(ambiguous.sum()),'distinct_depth_gap_min':float(gap.min()) if len(gap) else None,'error':message,'pass':attached['valid'] and ambiguous.any().item() and 'ambiguous' in message}
    return {'invalid_chords':results,'connected_multidepth':mult,'all_pass':all(x['pass'] for x in results) and mult['pass']},{'multidepth_path':path,'multidepth_mesh_vertices':mesh['vertices'],'multidepth_mesh_faces':mesh['faces'],'multidepth_owner_faces_depth':t['owner_faces_depth'],'multidepth_pre_z':pre,'multidepth_expanded':expanded,'multidepth_ambiguous_footprint':ambiguous}
