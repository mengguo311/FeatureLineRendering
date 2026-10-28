"""Frozen Chair H2: derive persistent policies, then render one real camera at a time."""
import runtime
from runtime import js,sha
from pathlib import Path
import argparse,json,time
import numpy as np
from scipy import ndimage
from linked_asset import load_asset,npz,png,validate_paths
from hatching import cutting_normal
from line_field import regenerate
from association import SurfaceGuide,trim_paths,guided_field,crossings,retain_intervals,excluded_intervals,segment_dist
from geometry import project

UNIT=Path('/mnt/hdd1/u00134/partwise_sketch_hatching_gaussian_link_v09/units/unit_001')
CODE=Path(__file__).resolve().parent
ASSET=UNIT/'inputs/assets/on'
VIEWS=['orbit_151_36_5.1','orbit_196_36_5.1','orbit_241_24_5.1','orbit_241_60_5.1','orbit_61_24_5.1']
ARMS=['U','S','D','sham']
WIDTH=.016875
RADIUS=.135
def length(p):return float(np.linalg.norm(p['points'][:,1]-p['points'][:,0],axis=1).sum())
def save(path,**values):
    runtime.output_guard(path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():raise FileExistsError(path)
    np.savez_compressed(path,**values)

def sham_paths(mesh,p,metric,trim):
    budgets={}
    for r in trim['intervals']:budgets[r['parent_id']]=budgets.get(r['parent_id'],0.)+r['removed_length']
    removed={};records=[]
    for sid,budget in sorted(budgets.items()):
        ids=np.flatnonzero(p['stroke_id']==sid);arc=0.;safe=[];maprows=[]
        for i in ids:
            seglen=np.linalg.norm(p['points'][i,1]-p['points'][i,0]);excluded=excluded_intervals(metric,int(p['face'][i]),p['points'][i],2*WIDTH)
            start=0.
            for l,h in excluded+[[1.,1.]]:
                if l-start>1e-10:
                    a,b=arc+start*seglen,arc+l*seglen
                    if safe and abs(a-safe[-1][1])<1e-9:safe[-1][1]=b
                    else:safe.append([a,b])
                start=h
            maprows.append((int(i),arc,float(seglen)));arc+=seglen
        remaining=budget;chosen=[]
        for a,b in sorted(safe,key=lambda x:(-(x[1]-x[0]),x[0])):
            take=min(remaining,b-a);mid=(a+b)/2
            if take>1e-12:chosen.append([mid-take/2,mid+take/2]);remaining-=take
            if remaining<1e-10:break
        for i,arc,ll in maprows:
            for a,b in chosen:
                lo=max(arc,a);hi=min(arc+ll,b)
                if hi-lo>1e-12:removed.setdefault(i,[]).append([(lo-arc)/ll,(hi-arc)/ll])
        records.append(dict(parent_id=sid,requested_trim=budget,shortfall=max(0.,remaining),removed_arclength=chosen))
    q,report=retain_intervals(mesh,p,removed);report.update(rule='Same affected parents, equal total removed length from center of longest safe arc runs >=2 margin widths from guide; deterministic, no image choice',allocation=records)
    return q,report

def derive():
    started=time.monotonic();mesh,paths,meta,link,b=load_asset(ASSET);guide=npz(UNIT/'GUIDE.npz')
    metric=SurfaceGuide(mesh,guide,mesh['regions']==5)
    normal=cutting_normal(5,meta['styles']['5']['angle'],meta['styles']['5']['plane'])
    raw=np.cross(mesh['normals'],normal);norm=np.linalg.norm(raw,axis=1)
    assert (norm[mesh['regions']==5]>1e-12).all()
    raw=np.divide(raw,norm[:,None],out=np.zeros_like(raw),where=norm[:,None]>1e-12)
    u,ur=regenerate(mesh,paths[5],mesh['regions']==5,raw[:,None,:],0)
    # Verify geometric support against each saved same-parent, same-face segment.
    errors=[];length_errors=[]
    for sid in np.unique(u['stroke_id']):
        new=u['stroke_id']==sid;old=paths[5]['stroke_id']==sid
        length_errors.append(abs(length({k:v[new] for k,v in u.items()})-length({k:v[old] for k,v in paths[5].items()})))
        for i in np.flatnonzero(new):
            ref=paths[5]['points'][old&(paths[5]['face']==u['face'][i])]
            if not len(ref):errors.append(float('inf'))
            else:errors.extend(segment_dist(u['points'][i],ref))
    fair=dict(max_same_parent_same_face_distance=float(max(errors)),max_parent_length_error=float(max(length_errors)),
        raw_length=length(paths[5]),common_U_length=length(u),stops={k:sum(r[k]!='requested_length' for r in ur) for k in ('minus_stop','plus_stop')},
        rule='Shared walker, saved midpoint seeds and saved parent lengths; saved lengths were already clipped by baseline labels, not untruncated requests',records=ur)
    js(UNIT/'GENERATOR_CHECK.json',fair)
    assert fair['max_same_parent_same_face_distance']<1e-8 and fair['max_parent_length_error']<1e-8,'Common U changed baseline; do not evaluate as association'
    dfield,field_report=guided_field(mesh,raw,metric,RADIUS,30.)
    field_change=field_report.pop('per_face_change');field_distance=field_report.pop('per_face_distance')
    d0,dr=regenerate(mesh,paths[5],mesh['regions']==5,dfield[:,None,:],0)
    for a,c in zip(ur,dr):
        for key in ('parent_stroke_id','seed_face','seed_bary','requested_length','layer_id'):assert a[key]==c[key],key
    s,sr=trim_paths(mesh,u,metric,WIDTH);d,dd=trim_paths(mesh,d0,metric,WIDTH);sh,shr=sham_paths(mesh,u,metric,sr)
    assert abs(sr['trimmed_length']-shr['trimmed_length'])<1e-8,'sham cannot match trim'
    arms=dict(U=u,S=s,D=d,sham=sh)
    summaries={}
    for name,p in arms.items():
        validate_paths(mesh,p,5);save(UNIT/f'paths/{name}.npz',**p)
        ev=crossings(p,guide)
        summaries[name]=dict(segments=len(p['face']),parent_paths=len(np.unique(p['stroke_id'])),length=length(p),same_face_crossings=len(ev),crossing_events=ev)
    save(UNIT/'paths/D_before_stop.npz',**d0)
    save(UNIT/'FIELDS.npz',raw=raw,guided=dfield,change_degrees=field_change,guide_distance_at_face_center=field_distance)
    js(UNIT/'D_GENERATION.json',dict(field=field_report,records=dr,pretrim_length=length(d0),stops={k:sum(r[k]!='requested_length' for r in dr) for k in ('minus_stop','plus_stop')}))
    for name,report in [('S',sr),('D',dd),('sham',shr)]:
        if name!='sham':
            errors=[]
            rawpaths=u if name=='S' else d0
            for rec in report['intervals']:
                i=rec['parent_segment'];p=rawpaths['points'][i]
                for l,h in rec['removed_t']:
                    for t in (l,h):
                        if 1e-9<t<1-1e-9:errors.append(abs(float(metric.distance(rec['face'],[(1-t)*p[0]+t*p[1]])[0])-WIDTH))
            report['white_margin_endpoint_error_max']=max(errors,default=0.)
        js(UNIT/f'TRIM_{name}.json',report)
    js(UNIT/'GEOMETRY.json',dict(arms=summaries,seconds=time.monotonic()-started,guide_role='Open upper authored style interface only; no label edits',direction=field_report,
        all_other_region_files_unchanged={str(r):sha(ASSET/f'region_{r}.npz') for r in (1,2,3,4)},layer_count=1,cross_layer_change='Not applicable: current saved Chair has one direction layer; no layer added or collapsed'))
    freeze()
    print(json.dumps(dict(arms={k:{kk:vv for kk,vv in v.items() if kk!='crossing_events'} for k,v in summaries.items()},generator={k:v for k,v in fair.items() if k!='records'},seconds=time.monotonic()-started)))

def freeze():
    protocol=dict(schema='chair_H2_static_association_v09',decision_sha256=sha(UNIT/'DECISION.json'),frozen_utc=runtime.now(),
        guide=dict(curve_id=240807000001,author_edges=list(range(10)),target_region=5,role='Assistant-confirmed style white-margin and local direction guide; not semantic boundary or GT',open=True,geometry_changes=False,
                   manual_author_seconds=103.964121,new_manual_geometry_points=0),
        policies=dict(U='Shared raw-field walker, all ordinary protections retained',S='U plus surface-aware bounded persistent interval trim',D='Same seeds/walker/style, local transported guide tangent then identical S trim',sham='Equal S trim length on same parents away from guide'),
        margin_half_width=WIDTH,direction_radius=RADIUS,max_direction_turn_degrees=30.,distance='5 equally spaced portals per genuine manifold shared edge plus exact finite same-face segments; intrinsic route upper bound, not exact geodesic',
        cameras=[json.loads((UNIT/f'inputs/cameras/{v}.json').read_text()) for v in VIEWS],build=VIEWS[0],all_views_previously_exposed=True,
        style=json.loads((ASSET/'asset.json').read_text())['styles'],active_regions=[4,5],structure='Identical full169 segments ON in every arm',aa=2,width_px=1,depth_tolerance=.004,evaluation_aa_band_px=2,
        matching='Natural plus one BUILD global factor per target hatch layer, attenuate to minimum natural target RGB effect among all four arms; actual post-structure-max RGB effect; freeze factors for all DEV',
        masks='Saved proxy region5 and fixed2px band, conditional author labels, no independent semantic GT; necessary interior excludes2px band around projected selected guide',
        caches='Hash-verified saved same-camera source/paper/S, no camera interpolation; freshly rasterized policy paths. One cold original-GS check camera.',
        preserved=['original256690 rows/order/fullSH/geometry/covariance/opacity','UNKNOWN170281','seat S27873 rows','all labels','all non-target paths','all169 structure segments','source paper .95'],
        limitations=['single object and exposed views','proxy-only upper-back and guide','source S regional, no current path ownership certificate','static result not temporal guarantee','old holes/open return/high-rear zero and143/UNKNOWN remain'])
    js(UNIT/'PROTOCOL.json',protocol)
    js(UNIT/'INPUT_LOCK.json',{str(p.relative_to(UNIT)):sha(p) for p in sorted((UNIT/'inputs').rglob('*')) if p.is_file()})
    js(UNIT/'SOURCE_LOCK.json',{p.name:sha(p) for p in sorted(CODE.iterdir()) if p.suffix in ('.py','.cpp')})
    js(UNIT/'DERIVED_LOCK.json',{str(p.relative_to(UNIT)):sha(p) for p in [UNIT/'GUIDE.npz',UNIT/'FIELDS.npz',*sorted((UNIT/'paths').glob('*.npz'))]})

def low(a):return a.reshape(384,2,384,2).mean((1,3))
def compose(paper,fixed,target,factor):
    ink=low(np.maximum(fixed,target*np.float32(factor)))
    return paper*(1-ink[:,:,None])+.03*ink[:,:,None],ink

def visible_length(mesh,p,c,target_aa):
    import open3d as o3d
    points=[];weights=[]
    for x in p['points']:
        ll=np.linalg.norm(x[1]-x[0]);n=max(1,int(np.ceil(ll/.005)));t=(np.arange(n)+.5)/n
        points.extend((1-t[:,None])*x[0]+t[:,None]*x[1]);weights.extend([ll/n]*n)
    points=np.asarray(points);weights=np.asarray(weights);uv,z=project(points,c)
    E=np.array(c['extrinsic']);origin=-np.linalg.inv(E[:3,:3])@E[:3,3]
    scene=o3d.t.geometry.RaycastingScene(nthreads=1)
    scene.add_triangles(o3d.core.Tensor(mesh['vertices'].astype(np.float32)),o3d.core.Tensor(mesh['faces'].astype(np.uint32)))
    hit=scene.cast_rays(o3d.core.Tensor(np.c_[np.broadcast_to(origin,points.shape),(points-origin)/z[:,None]].astype(np.float32)),nthreads=1)
    zz=hit['t_hit'].numpy();faces=hit['primitive_ids'].numpy();ok=faces<len(mesh['faces']);owner=np.zeros(len(points),bool);owner[ok]=mesh['regions'][faces[ok]]==5
    visible=ok&owner&(abs(zz-z)<=.004)&(uv[:,0]>=0)&(uv[:,0]<384)&(uv[:,1]>=0)&(uv[:,1]<384)
    aa=(uv+.5)*2-.5
    ink=ndimage.map_coordinates(target_aa,[aa[:,1],aa[:,0]],order=1,mode='constant',cval=0)
    return dict(saved_length=float(weights.sum()),proxy_visible_length=float(weights[visible].sum()),visible_own_ink_length=float(weights[visible&(ink>1/255)].sum()),
        proxy_visible_without_own_ink_length=float(weights[visible&(ink<=1/255)].sum()),sample_count=len(points),sample_step_max=.005,
        scope='Current retained-path own-ink samples; proxy first-hit conditional, not independent physical GT; compare lengths alongside raw parent length')

def render_view(view):
    start=time.monotonic();assert view in VIEWS
    for name,h in json.loads((UNIT/'SOURCE_LOCK.json').read_text()).items():assert sha(CODE/name)==h,('source_changed',name)
    mesh,paths,meta,link,b=load_asset(ASSET);c=json.loads((UNIT/f'inputs/cameras/{view}.json').read_text())
    cache=npz(UNIT/f'inputs/cache/{view}/FRAME.npz');guide=npz(UNIT/'GUIDE.npz');full=npz(ASSET/'structure.npz')
    from render import render,RenderCache
    from structure import raster_structure
    states={name:npz(UNIT/f'paths/{name}.npz') for name in ARMS};states['reference']=paths[5]
    aa={};fixed=None;shared=None
    for name,p in states.items():
        rc=RenderCache();render(mesh,{4:paths[4],5:p},meta['styles'],c,2,dict(contours_visible=True,contour_strength=1.),rc)
        data=rc.value
        target=np.maximum.reduce(list(data['coverage'][5].values())).astype(np.float32)*np.float32(meta['styles']['5']['ink_strength'])
        aa[name]=target
        if fixed is None:
            structure,sd=raster_structure(mesh,full,c,2);gink,_=raster_structure(mesh,guide,c,2)
            seat=np.maximum.reduce(list(data['coverage'][4].values())).astype(np.float32)*np.float32(meta['styles']['4']['ink_strength'])
            seat*=np.repeat(np.repeat(cache['support'],2,0),2,1)
            fixed=np.maximum.reduce([data['contour'],structure,seat]);shared=dict(structure=low(structure),guide=low(gink),contour=low(data['contour']),seat=low(seat),regions=data['regions'],depth=data['depth'])
        np.testing.assert_array_equal(data['regions'],cache['regions'])
    paper=cache['paper'];base,_=compose(paper,fixed,aa['U'],0.)
    ref,refink=compose(paper,fixed,aa['reference'],1.)
    # Same AA composition as immutable v08. Verify renderer import before policy comparison.
    np.testing.assert_array_equal(ref,cache['hybrid'])
    np.testing.assert_array_equal(aa['U'],aa['reference'])
    effect=lambda name,factor:float(np.abs(compose(paper,fixed,aa[name],factor)[0]-base).sum())
    if view==VIEWS[0]:
        natural={name:effect(name,1.) for name in ARMS};budget=min(natural.values());factors={}
        for name in ARMS:
            lo,hi=0.,1.
            for _ in range(35):
                mid=(lo+hi)/2
                if effect(name,mid)<budget:lo=mid
                else:hi=mid
            factors[name]=(lo+hi)/2
        js(UNIT/'BUILD_MATCH.json',dict(view=view,natural_target_rgb_effect=natural,target_budget=budget,factors=factors,achieved={name:effect(name,factors[name]) for name in ARMS},rule='One factor per target hatch layer; same factor every view; structure/seat/paper fixed'))
    factors=json.loads((UNIT/'BUILD_MATCH.json').read_text())['factors']
    target=shared['regions']==5;near=ndimage.binary_dilation(target,iterations=2);interior=ndimage.binary_erosion(target,iterations=2)
    guideband=ndimage.binary_dilation(shared['guide']>0,iterations=2);necessary=interior&~guideband
    far_other=(shared['regions']>0)&~near;far_bg=(shared['regions']==0)&~near
    masks=dict(target=target,necessary_interior=necessary,boundary_band=guideband,far_other=far_other,far_background=far_bg)
    metrics={};visibility={name:visible_length(mesh,states[name],c,aa[name]) for name in ARMS}
    for mode in ('natural','matched'):
        metrics[mode]={}
        for name in ARMS:
            factor=1. if mode=='natural' else factors[name];img,ink=compose(paper,fixed,aa[name],factor);own=low(aa[name]*np.float32(factor))
            out=UNIT/f'renders/{view}/{mode}/{name}';out.mkdir(parents=True,exist_ok=False)
            save(out/'FRAME.npz',hybrid=img,combined_ink=ink,target_ink=own,source=cache['source'],paper=paper,support=cache['support'],**shared)
            png(out/'hybrid.png',img);png(out/'target_ink.png',1-own);png(out/'structure.png',1-shared['structure'])
            png(out/'proxy.png',1-ink)
            original_delta=np.abs(img-cache['source']).sum(2);policy_delta=np.abs(img-ref).sum(2)
            inc=np.abs(img-base).sum(2)
            metrics[mode][name]=dict(factor=factor,target_rgb_effect=float(inc.sum()),whole_ink_mass=float(ink.sum()),own_target_ink_mass=float(own.sum()),
                regions={key:dict(pixels=int(mask.sum()),own_ink_mass=float(own[mask].sum()),own_ink_covered_pixels=int((own[mask]>1/255).sum()),
                    own_coverage_fraction=float(np.mean(own[mask]>1/255)) if mask.any() else None,
                    absolute_source_L1=float(original_delta[mask].sum()),policy_vs_original_U_L1=float(policy_delta[mask].sum()),target_increment_L1=float(inc[mask].sum())) for key,mask in masks.items()},
                visible_length=visibility[name])
    refout=UNIT/f'renders/{view}/reference';refout.mkdir()
    png(refout/'hybrid.png',ref);png(refout/'source.png',cache['source']);png(refout/'structure.png',1-shared['structure']);png(refout/'guide.png',1-shared['guide'])
    save(UNIT/f'renders/{view}/FIXED.npz',fixed_aa=fixed,reference_target_aa=aa['reference'],**{f'mask_{k}':v for k,v in masks.items()})
    js(UNIT/f'renders/{view}/METRICS.json',dict(view=view,camera=c,cache_sha256=sha(UNIT/f'inputs/cache/{view}/FRAME.npz'),
        reference_recovers_saved_hybrid_exact=True,common_U_target_AA_exact=True,source_rerendered=False,policy_paths_rasterized=True,metrics=metrics,seconds=time.monotonic()-start))
    print(json.dumps(dict(view=view,seconds=time.monotonic()-start,natural_effects={k:v['target_rgb_effect'] for k,v in metrics['natural'].items()})))

def main():
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['derive','render']);p.add_argument('--view',choices=VIEWS);a=p.parse_args()
    if a.stage=='derive':derive()
    else:render_view(a.view)
if __name__=='__main__':main()
