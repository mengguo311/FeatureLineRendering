"""Frozen elevation H1; exact-camera source caches and unchanged final B0/U."""
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

PREV=UNIT.parent/'unit_003'
H1=UNIT.parent/'unit_002'
ASSET=UNIT/'inputs/assets/on'
from elevation import elevation_plan,validate_cache

def save(path,**values):
    path=runtime.output_guard(path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():raise FileExistsError(path)
    np.savez_compressed(path,**values)
def low(a):return a.reshape(384,2,384,2).mean((1,3))
def compose(paper,fixed,target,factor):
    ink=low(np.maximum(fixed,target*np.float32(factor)))
    return paper*(1-ink[:,:,None])+.03*ink[:,:,None],ink
def plan():return json.loads((UNIT/'CAMERAS.json').read_text())
def locks():
    for path,h in json.loads((UNIT/'INPUT_LOCK.json').read_text()).items():assert sha(UNIT/path)==h,('input',path)
    for path,h in json.loads((UNIT/'SOURCE_LOCK.json').read_text()).items():assert sha(Path(path))==h,('source',path)
    for path,h in json.loads((UNIT/'PROTOCOL_LOCK.json').read_text()).items():assert sha(UNIT/path)==h,('protocol',path)
def prepare():
    records=[]
    def copy(src,dest,expected=None):
        h=sha(src)
        if expected is not None:assert h==expected,str(src)
        runtime.output_guard(dest);dest.parent.mkdir(parents=True,exist_ok=True)
        if dest.exists():raise FileExistsError(dest)
        shutil.copyfile(src,dest);assert sha(dest)==h
        records.append(dict(source=str(src),destination=str(dest.relative_to(UNIT)),sha256=h))
    oldlock=json.loads((PREV/'INPUT_LOCK.json').read_text())
    for folder in ('assets/on','data/chair'):
        for src in sorted((PREV/'inputs'/folder).iterdir()):
            if src.is_file():copy(src,UNIT/src.relative_to(PREV),oldlock[str(src.relative_to(PREV))])
    hlock=json.loads((H1/'PROTOCOL_LOCK.json').read_text())
    for name,expected in [('CONFIG.json',hlock['config_sha256']),('RAW_FIELD.npz',hlock['field_sha256']),('BUILD_MATCH.json',None)]:copy(H1/name,UNIT/name,expected)
    rows=elevation_plan(json.loads((PREV/'CAMERAS.json').read_text()))
    for row in rows:
        src=PREV/'renders'/row['prior_key'];cache=UNIT/'inputs/cache'/row['key']
        copy(src/'COMMON.npz',cache/'COMMON.npz');copy(src/'METRICS.json',cache/'PREVIOUS_METRICS.json')
        trace=src/'TRACE.npz'
        if not trace.exists():trace=PREV/'inputs/cache'/row['prior_key']/'TRACE.npz'
        copy(trace,cache/'TRACE.npz')
        copy(src/'natural/U/FRAME.npz',cache/'REFERENCE_U.npz')
        if row['h1_reference']:
            for mode in ('natural','matched'):
                for arm in ('B0','B1'):copy(H1/'renders'/row['h1_reference']/mode/arm/'FRAME.npz',cache/f'{mode}_{arm}_REFERENCE.npz')
        prior=json.loads((cache/'PREVIOUS_METRICS.json').read_text())
        validate_cache(row['camera'],prior['camera'],npz(cache/'COMMON.npz'))
        row['cache']=str((cache/'COMMON.npz').relative_to(UNIT));row['cache_sha256']=sha(cache/'COMMON.npz')
    js(UNIT/'CAMERAS.json',rows);js(UNIT/'IMPORT.json',records)
    protocol=dict(schema='conditional_H1_elevation_unit004',frozen_utc=runtime.now(),decision_sha256=sha(UNIT/'DECISION.json'),
        question='Does the unit002 conditional temporal advantage survive elevation-induced compression and first-hit visibility transitions, or reverse?',
        arms=dict(B0='exact final unit002 deterministic2D projected raw field, fixed part anchor/basis/lattice; boundary-intersection repair retained',B1='unchanged original U persistent proxy surface paths'),
        cameras=rows,frames=13,directional_pairs=24,static_checks=2,playback_fps=8,
        config=json.loads((UNIT/'CONFIG.json').read_text()),matching=json.loads((UNIT/'BUILD_MATCH.json').read_text()),
        frozen_rules='No recalibration or per-view matching; single layer; 1px/AA2/.004 first-hit tolerance, original phase/spacing/length/gap/field; all169 structure ON',
        fixed='Original256690 rows/order/fullSH/geometry/covariance/opacity,UNKNOWN170281,seatS27873,mesh/rough labels,all original paths,paper.95,non-target layers',
        caches='All15 exact-camera source/paper/S arrays reused from unit003; inherited sparse traces copied. No fresh GS science render claimed. All15 B0 paths generated and both arms rasterized anew, native and AA proxy rays recomputed.',
        masks='Same unit002 first-hit region5 masks, fixed2px erosion necessary interior, no H2-guide exclusion; temporal uses exact native ray centers for both arms',
        temporal='All12 adjacent pairs both directions; actual own-ink common-pixel L1 and union-normalized L1, both-method centerline-to-actual-ink distances and absent ink, coverage and visible denominators; no LOD/trim',
        falsification=json.loads((UNIT/'DECISION.json').read_text())['falsification'],
        limits='One exposed Chair, unequal projected coverage and generator/seed/scaling differences. Not pure-anchor causality, semantic GT, best2D method or Gaussian superiority. No H2 parameter changes.',
        preserved_failures='H2 S high-angle coverage loss/D36of37 coverage loss/matchedFARnonzero; open return/holes/high rear zero/old dropouts143UNKNOWN and failed center-only B0',
        budget='CPU affinity2 threads1 CUDAempty serial; <=35min; no new science15:20 wrap15:45 hard16:00 JST')
    js(UNIT/'PROTOCOL.json',protocol)
    js(UNIT/'INPUT_LOCK.json',{str(p.relative_to(UNIT)):sha(p) for p in sorted((UNIT/'inputs').rglob('*')) if p.is_file()})
    js(UNIT/'SOURCE_LOCK.json',{str(p):sha(p) for root in (CODE,BASECODE) for p in sorted(root.iterdir()) if p.suffix in ('.py','.cpp') and p.name not in ('audit_h1.py','finish_h1.py','replay_h1.py')})
    js(UNIT/'PROTOCOL_LOCK.json',{n:sha(UNIT/n) for n in ('PROTOCOL.json','DECISION.json','CAMERAS.json','CONFIG.json','RAW_FIELD.npz','BUILD_MATCH.json')})
    print(json.dumps(dict(cameras=len(rows),frames=13,matching='unchanged',cache_scope='source/paper/S only; both arms rerender')),flush=True)

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
        from hybrid import region_strength
        self.mesh,self.paths,self.meta,self.link,self.binding=load_asset(ASSET)
        self.raw=npz(UNIT/'RAW_FIELD.npz')['raw'];self.cfg=json.loads((UNIT/'CONFIG.json').read_text())
        self.curve=npz(ASSET/'structure.npz');self.source=base.load_source((ASSET/self.link['source_file']).resolve(),self.link['source_sha256'])
        self.source['source_index']=np.arange(len(self.source['means']),dtype=np.int64);self.original=source_hashes(self.source)
        self.strength=region_strength(self.binding)
    def frame(self,row,key_override=None):
        from render import render,RenderCache
        from structure import raster_structure
        start=time.monotonic();c=row['camera'];dest=runtime.configure_output(UNIT/'renders'/(key_override or row['key']))
        cachepath=UNIT/row['cache'];cache=npz(cachepath);prior=json.loads((cachepath.parent/'PREVIOUS_METRICS.json').read_text())
        validate_cache(c,prior['camera'],cache);assert sha(cachepath)==row['cache_sha256']
        source=dict(rgb=cache['source'],contribution=cache['support']);paper=dict(rgb=cache['paper'])
        trace=npz(cachepath.parent/'TRACE.npz');xy=trace.pop('xy')
        proof=dict(cache_sha256=sha(cachepath),cache_source=str(PREV/'renders'/row['prior_key']/'COMMON.npz'),cold_original_GS=False)
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
        original_reference=npz(cachepath.parent/'REFERENCE_U.npz')
        np.testing.assert_array_equal(original,original_reference['hybrid'])
        np.testing.assert_array_equal(low(b1),original_reference['own_ink'])
        ref=dict(original_U_exact=True,unit003_key=row['prior_key'],unit002_reference=row['h1_reference'])
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
                if row['h1_reference']:
                    oldframe=npz(cachepath.parent/f'{mode}_{arm}_REFERENCE.npz')
                    for name,value in [('hybrid',img),('own_ink',own),('own_aa',aa[arm]*np.float32(factor)),('combined_ink',ink)]:np.testing.assert_array_equal(value,oldframe[name])
                    ref[f'{mode}_{arm}_unit002_exact']=True
                absolute=np.abs(img-source['rgb']).sum(2);delta=np.abs(img-original).sum(2);inc=np.abs(img-base).sum(2)
                metrics[mode][arm]=dict(factor=factor,target_rgb_effect=float(inc.sum()),own_ink_mass=float(own.sum()),whole_ink_mass=float(ink.sum()),
                    regions={k:dict(pixels=int(m.sum()),coverage_fraction=float((own[m]>1/255).mean()) if m.any() else None,own_ink_mass=float(own[m].sum()),absolute_source_L1=float(absolute[m].sum()),increment_vs_U_L1=float(delta[m].sum())) for k,m in masks.items()})
        proxy=1-low(np.maximum.reduce([data['contour'],structure,seat,b1]));png(dest/'conventional_B1.png',proxy)
        for k in ('source','paper'):png(dest/(k+'.png'),common[k])
        png(dest/'structure.png',1-common['structure'])
        save(dest/'CONVENTIONAL.npz',image=proxy,source_S_applied=np.array(False))
        assert source_hashes(self.source)==self.original
        record=dict(key=key_override or row['key'],camera=c,metrics=metrics,source_cache=proof,original_source_rows=len(self.strength),unknown_rows=int(self.binding['unknown'].sum()),selected_source_rows=int((self.strength>0).sum()),
            source_hashes=self.original,source_arrays_unchanged=True,cold_original_GS=False,structure=sd,reference=ref,seconds=time.monotonic()-start)
        js(dest/'METRICS.json',record);print(json.dumps(dict(key=row['key'],seconds=record['seconds'],B0_paths=len(paths),effects={a:effect(a,1) for a in aa})),flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','render']);p.add_argument('--keys',nargs='+');a=p.parse_args()
    if a.stage=='prepare':prepare();return
    locks();r=Runner();rows={r['key']:r for r in plan()}
    for key in a.keys:r.frame(rows[key])
    locks()
if __name__=='__main__':main()
