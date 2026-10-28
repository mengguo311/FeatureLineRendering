"""Bounded label-conditioned H1; original U versus deterministic 2D streamlines."""
import runtime
from runtime import ROOT as UNIT,js,sha,CODE,BASECODE
from pathlib import Path
import argparse,json,shutil,time
import numpy as np
from scipy import ndimage
from linked_asset import load_asset,npz,png,source_hashes,SAMPLES
from geometry import orbit_camera,ray_surface,project,backproject
from hatching import cutting_normal
from screen_hatch import projected_field,generate,raster
from temporal import sample

PREV=UNIT.parent/'unit_001'
ASSET=UNIT/'inputs/assets/on'
def save(path,**values):
    path=runtime.output_guard(path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():raise FileExistsError(path)
    np.savez_compressed(path,**values)
def low(a):return a.reshape(384,2,384,2).mean((1,3))
def compose(paper,fixed,target,factor):
    ink=low(np.maximum(fixed,target*np.float32(factor)))
    return paper*(1-ink[:,:,None])+.03*ink[:,:,None],ink
def plan():
    return [dict(key='BUILD',camera=orbit_camera(151,36,5.1,384),role='BUILD exposed')]+[
        dict(key=f'{i:03d}',camera=orbit_camera(196+45*i/24,36-12*i/24,5.1,384),role='predeclared H1 arc; not certified GS-unseen',index=i)
        for i in range(25)]+[dict(key='HIGH',camera=orbit_camera(241,60,5.1,384),role='static high-rear negative; outside arc')]
def locks():
    for path,h in json.loads((UNIT/'INPUT_LOCK.json').read_text()).items():assert sha(UNIT/path)==h,('input',path)
    for path,h in json.loads((UNIT/'SOURCE_LOCK.json').read_text()).items():assert sha(Path(path))==h,('source',path)
    lock=json.loads((UNIT/'PROTOCOL_LOCK.json').read_text())
    assert sha(UNIT/'PROTOCOL.json')==lock['sha256']
    assert sha(UNIT/'DECISION.json')==lock['decision_sha256']
def prepare():
    records=[];locked=json.loads((PREV/'INPUT_LOCK.json').read_text())
    for folder in ('assets/on','data/chair'):
        for src in sorted((PREV/'inputs'/folder).iterdir()):
            if not src.is_file():continue
            key=str(src.relative_to(PREV));assert sha(src)==locked[key],key
            dest=UNIT/key;dest.parent.mkdir(parents=True,exist_ok=True)
            if dest.exists():raise FileExistsError(dest)
            shutil.copyfile(src,dest);assert sha(dest)==locked[key]
            records.append(dict(source=str(src),destination=str(dest.relative_to(UNIT)),sha256=locked[key]))
    mesh,paths,meta,link,b=load_asset(ASSET);c=plan()[0]['camera']
    normal=cutting_normal(5,meta['styles']['5']['angle'],meta['styles']['5']['plane'])
    raw=np.cross(mesh['normals'],normal);raw/=np.maximum(np.linalg.norm(raw,axis=1)[:,None],1e-30)
    old=npz(PREV/'FIELDS.npz');np.testing.assert_array_equal(raw,old['raw'])
    depth,faces,regions,cc=ray_surface(mesh,c,1);target=regions==5
    y,x=np.nonzero(target);fid=faces[target];world=backproject(np.column_stack([x,y]),depth[target],c)
    E=np.array(c['extrinsic']);p=world@E[:3,:3].T+E[:3,3]
    def differential(v):
        v=v@E[:3,:3].T
        return np.column_stack([c['fx']*(v[:,0]*p[:,2]-p[:,0]*v[:,2])/p[:,2]**2,c['fy']*(v[:,1]*p[:,2]-p[:,1]*v[:,2])/p[:,2]**2])
    tangent=differential(raw[fid]);speed=np.linalg.norm(tangent,axis=1);unit=tangent/np.maximum(speed[:,None],1e-30)
    grad=normal-(mesh['normals'][fid]@normal)[:,None]*mesh['normals'][fid]
    transverse=differential(grad/np.maximum(np.sum(grad*grad,axis=1)[:,None],1e-20))
    projected_spacing=np.abs(transverse[:,0]*unit[:,1]-transverse[:,1]*unit[:,0])*.0675
    good=(speed>1e-4)&(projected_spacing>.2)&np.isfinite(projected_spacing)
    assert good.any()
    center=world.mean(0);chosen=int(np.argmin(np.linalg.norm(world-center,axis=1)))
    anchor=world[chosen];axis=raw[fid[chosen]]
    cfg=dict(spacing_px=float(np.median(projected_spacing[good])),length_px=float(np.median(speed[good])*.44),gap_px=float(np.median(speed[good])*.035),
        phase=[.1732050807568877,.3819660112501051],step_px=.5,depth_jump=.035,anchor_world=anchor.tolist(),basis_world=axis.tolist(),
        width_px=1.,aa=2,natural_strength=.45,degenerate_fallback='stop; no arbitrary direction',
        calibration='BUILD visible raw-field projection Jacobian medians; no candidate scan or image fitting',calibration_pixels=int(good.sum()),excluded_calibration_pixels=int((~good).sum()))
    save(UNIT/'RAW_FIELD.npz',raw=raw);js(UNIT/'CONFIG.json',cfg);js(UNIT/'CAMERAS.json',plan());js(UNIT/'IMPORT.json',records)
    protocol=dict(schema='conditional_H1_v09_unit002',frozen_utc=runtime.now(),decision_sha256=sha(UNIT/'DECISION.json'),
        question='With identical author labels/projected raw direction, does persistent surface hatching improve actual temporal output over deterministic image-space streamlines?',
        arms=dict(B0='per-view 2D integration on visible raw projected field; fixed phase lattice, one common projected part anchor/basis; no stroke 3D history',B1='unchanged original U persistent proxy paths'),
        config=cfg,cameras=plan(),matching='natural + one BUILD actual target RGB effect factor per arm, frozen for all evaluation cameras; no per-frame normalization',
        masks='same first-hit proxy region5; necessary interior fixed2px erosion; no new H2 margin; AA exact region clipping',
        temporal='Both directions, all native target pixels with depth/label/bilinear finite support correspondence at tolerance .004; actual own-ink L1/union/coverage plus each-method centerline-to-actual-ink; no U-only samples',
        fixed='original256690 rows/order/fullSH/geometry/covariance/opacity, UNKNOWN170281, seat S27873 rows, mesh/labels/all original paths, full169 structure segments ON, paper .95,1px/AA2/.004 visibility',
        conventional='actual raw seat ink without S, same B1 paths/structure/visibility; white background',
        source='All27 cameras render originalGS/paper/S anew; source loaded once per serial batch. Original U check cameras compared with hash-verified previous results; no image interpolation',
        limits='One Chair, author labels and proxy conditional; exposed cameras; no automatic segmentation, physical GT, Gaussian novelty, mature2D superiority or 360-degree claim',
        preserved_failures='H2 D coverage cost; open return/holes/high rear zero composite increment; old3 structure dropouts/1 reappearance,143/UNKNOWN and overlap receipts',
        resources='CPU affinity2,threads1,CUDA empty, serial batches; <=35minutes; no new science15:20/wrap15:45/hard16:00 JST')
    js(UNIT/'PROTOCOL.json',protocol)
    js(UNIT/'INPUT_LOCK.json',{str(p.relative_to(UNIT)):sha(p) for p in sorted((UNIT/'inputs').rglob('*')) if p.is_file()})
    js(UNIT/'SOURCE_LOCK.json',{str(p):sha(p) for root in (CODE,BASECODE) for p in sorted(root.iterdir()) if p.suffix in ('.py','.cpp') and p.name not in ('finish_h1.py','audit_h1.py')})
    js(UNIT/'PROTOCOL_LOCK.json',dict(sha256=sha(UNIT/'PROTOCOL.json'),decision_sha256=sha(UNIT/'DECISION.json'),config_sha256=sha(UNIT/'CONFIG.json'),field_sha256=sha(UNIT/'RAW_FIELD.npz')))
    print(json.dumps(dict(config=cfg,imported=len(records),cameras=len(plan()))),flush=True)

def centers_2d(paths):
    points=[];weights=[]
    for p in paths:
        for a,b in zip(p[:-1],p[1:]):
            ll=float(np.linalg.norm(b-a));n=max(1,int(np.ceil(ll/.5)));t=(np.arange(n)+.5)/n
            points.extend((1-t[:,None])*a+t[:,None]*b);weights.extend([ll/n]*n)
    return np.asarray(points).reshape(-1,2),np.asarray(weights)
def centers_3d(paths,c):
    pp=[];weights=[];zz=[]
    for p in paths['points']:
        uv,z=project(p,c)
        if not (z>.2).all():continue
        ll=float(np.linalg.norm(uv[1]-uv[0]));n=max(1,int(np.ceil(ll/.5)));t=(np.arange(n)+.5)/n
        pp.extend((1-t[:,None])*uv[0]+t[:,None]*uv[1]);weights.extend([ll/n]*n)
        zz.extend(1/((1-t)/z[0]+t/z[1]))
    return np.asarray(pp).reshape(-1,2),np.asarray(weights),np.asarray(zz)

class Runner:
    def __init__(self):
        import base_model as base
        from link_renderer import Renderer
        from hybrid import region_strength
        self.mesh,self.paths,self.meta,self.link,self.binding=load_asset(ASSET)
        self.raw=npz(UNIT/'RAW_FIELD.npz')['raw'];self.cfg=json.loads((UNIT/'CONFIG.json').read_text())
        self.curve=npz(ASSET/'structure.npz');self.source=base.load_source((ASSET/self.link['source_file']).resolve(),self.link['source_sha256'])
        self.source['source_index']=np.arange(len(self.source['means']),dtype=np.int64);self.original=source_hashes(self.source)
        self.strength=region_strength(self.binding);self.engine=Renderer(UNIT/'build')
    def frame(self,row):
        from hybrid import paper_copy
        from link_renderer import validate_trace
        from render import render,RenderCache
        from structure import raster_structure
        start=time.monotonic();c=row['camera'];dest=runtime.configure_output(UNIT/'renders'/row['key']);xy=np.asarray(SAMPLES,np.int32)
        source,trace=self.engine.render(self.source,c,xy=xy,strength=self.strength)
        paper,_=self.engine.render(paper_copy(self.source,c,np.ones(len(self.strength)),[.95]*3),c)
        proof=validate_trace(self.source,c,xy,source,trace);np.testing.assert_array_equal(source['alpha'],paper['alpha'])
        reconstructed=np.bincount(trace['sample_index'],trace['weight']*self.strength[trace['source_index']],minlength=len(xy))
        serr=float(np.max(np.abs(reconstructed-source['contribution'][xy[:,1],xy[:,0]])));assert serr<1e-6
        rc=RenderCache();render(self.mesh,{4:self.paths[4],5:self.paths[5]},self.meta['styles'],c,2,dict(contours_visible=True,contour_strength=1.),rc);data=rc.value
        structure,sd=raster_structure(self.mesh,self.curve,c,2)
        seat=np.maximum.reduce(list(data['coverage'][4].values())).astype(np.float32)*np.float32(.35)
        b1=np.maximum.reduce(list(data['coverage'][5].values())).astype(np.float32)*np.float32(.45)
        fixed=np.maximum.reduce([data['contour'],structure,seat*np.repeat(np.repeat(source['contribution'],2,0),2,1)])
        depthaa,facesaa,regionsaa,_=ray_surface(self.mesh,c,2)
        faces=facesaa[1::2,1::2];depth=depthaa[1::2,1::2];mask=regionsaa[1::2,1::2]==5
        # Coordinates correspond to native pixel centers, as does existing renderer's stored depth.
        # For the 2D field and temporal reference use exact native ray centers, shared by both arms.
        depth_native,faces_native,regions_native,_=ray_surface(self.mesh,c,1)
        native_mask=regions_native==5
        field,degenerate=projected_field(self.mesh,self.raw,depth_native,faces_native,c)
        anchor,z=project(np.array([self.cfg['anchor_world'],np.asarray(self.cfg['anchor_world'])+.01*np.asarray(self.cfg['basis_world'])]),c)
        axis=anchor[1]-anchor[0]
        if np.linalg.norm(axis)<1e-8:raise RuntimeError('frozen lattice axis projection degenerate')
        paths,gen=generate(field,native_mask,depth_native,anchor[0],axis,self.cfg)
        b0=raster(paths,np.ones_like(native_mask),1,2)&(regionsaa==5);b0=b0.astype(np.float32)*np.float32(.45)
        aa=dict(B0=b0,B1=b1);base,_=compose(paper['rgb'],fixed,b1,0.)
        effect=lambda arm,f:float(np.abs(compose(paper['rgb'],fixed,aa[arm],f)[0]-base).sum())
        original,_=compose(paper['rgb'],fixed,b1,1.)
        ref=None
        if row['key'] in ('BUILD','000','024','HIGH'):
            refpath=PREV/f'renders/{c["view"]}/natural/U/FRAME.npz'
            old=npz(refpath)
            for key,val in [('hybrid',original),('source',source['rgb']),('paper',paper['rgb']),('support',source['contribution'])]:np.testing.assert_array_equal(val,old[key])
            ref=dict(path=str(refpath),sha256=sha(refpath),source_paper_S_hybrid_exact=True)
        if row['key']=='BUILD':
            natural={arm:effect(arm,1) for arm in aa};budget=min(natural.values());factors={}
            for arm in aa:
                lo,hi=0.,1.
                for _ in range(35):
                    mid=(lo+hi)/2
                    if effect(arm,mid)<budget:lo=mid
                    else:hi=mid
                factors[arm]=(lo+hi)/2
            js(UNIT/'BUILD_MATCH.json',dict(natural=natural,budget=budget,factors=factors,achieved={k:effect(k,v) for k,v in factors.items()},frozen_utc=runtime.now()))
        factors=json.loads((UNIT/'BUILD_MATCH.json').read_text())['factors']
        near=ndimage.binary_dilation(mask,iterations=2);interior=ndimage.binary_erosion(mask,iterations=2)
        masks=dict(target=mask,necessary_interior=interior,far_other=(data['regions']>0)&~near,far_background=(data['regions']==0)&~near)
        common=dict(source=source['rgb'],paper=paper['rgb'],support=source['contribution'],structure=low(structure),contour=low(data['contour']),seat=low(seat),
            seat_linked=low(seat*np.repeat(np.repeat(source['contribution'],2,0),2,1)),regions=data['regions'],depth_native=depth_native,native_target=native_mask,baseline=base,
            **{f'mask_{k}':v for k,v in masks.items()})
        save(dest/'COMMON.npz',**common);save(dest/'TRACE.npz',xy=xy,**trace)
        uv0,w0=centers_2d(paths);uv1,w1,z1=centers_3d(self.paths[5],c)
        save(dest/'CENTERLINES.npz',B0_uv=uv0,B0_weight=w0,B1_uv=uv1,B1_weight=w1,B1_depth=z1)
        # Screen paths are saved as packed vertices/offsets; never as 3D attachments.
        offsets=np.cumsum([0]+[len(p) for p in paths]);save(dest/'B0_PATHS.npz',points=np.concatenate(paths) if paths else np.empty((0,2)),offsets=offsets)
        js(dest/'GENERATION.json',dict(gen,projected_degeneracies=degenerate,anchor_uv=anchor[0],basis_uv=axis/np.linalg.norm(axis)))
        metrics={}
        for mode in ('natural','matched'):
            metrics[mode]={}
            for arm in aa:
                factor=1. if mode=='natural' else factors[arm];img,ink=compose(paper['rgb'],fixed,aa[arm],factor);own=low(aa[arm]*np.float32(factor))
                out=dest/mode/arm;out.mkdir(parents=True);save(out/'FRAME.npz',hybrid=img,own_ink=own,own_aa=aa[arm]*np.float32(factor),combined_ink=ink)
                png(out/'hybrid.png',img);png(out/'own_ink.png',1-own)
                absolute=np.abs(img-source['rgb']).sum(2);delta=np.abs(img-original).sum(2);inc=np.abs(img-base).sum(2)
                metrics[mode][arm]=dict(factor=factor,target_rgb_effect=float(inc.sum()),own_ink_mass=float(own.sum()),whole_ink_mass=float(ink.sum()),
                    regions={k:dict(pixels=int(m.sum()),coverage_fraction=float((own[m]>1/255).mean()) if m.any() else None,own_ink_mass=float(own[m].sum()),absolute_source_L1=float(absolute[m].sum()),increment_vs_U_L1=float(delta[m].sum())) for k,m in masks.items()})
        proxy=1-low(np.maximum.reduce([data['contour'],structure,seat,b1]));png(dest/'conventional_B1.png',proxy)
        for k in ('source','paper'):png(dest/(k+'.png'),common[k])
        png(dest/'structure.png',1-common['structure'])
        save(dest/'CONVENTIONAL.npz',image=proxy,source_S_applied=np.array(False))
        assert source_hashes(self.source)==self.original
        record=dict(key=row['key'],camera=c,metrics=metrics,trace_validation=proof,support_error=serr,original_source_rows=len(self.strength),unknown_rows=int(self.binding['unknown'].sum()),selected_source_rows=int((self.strength>0).sum()),
            source_hashes=self.original,source_arrays_unchanged=True,cold_original_GS=True,structure=sd,reference=ref,seconds=time.monotonic()-start)
        js(dest/'METRICS.json',record);print(json.dumps(dict(key=row['key'],seconds=record['seconds'],B0_paths=len(paths),effects={a:effect(a,1) for a in aa})),flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','render']);p.add_argument('--keys',nargs='+');a=p.parse_args()
    if a.stage=='prepare':prepare();return
    locks();r=Runner();rows={r['key']:r for r in plan()}
    for key in a.keys:r.frame(rows[key])
    locks()
if __name__=='__main__':main()
