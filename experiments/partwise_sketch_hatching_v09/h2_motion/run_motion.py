"""Frozen U/S/D/sham camera trajectory. No path regeneration or policy tuning."""
import runtime
from runtime import ROOT as UNIT,CODE,BASECODE,js,sha
from pathlib import Path
import argparse,json,shutil,time
import numpy as np
from scipy import ndimage
from linked_asset import load_asset,npz,png,source_hashes,SAMPLES
from geometry import orbit_camera,ray_surface,project
from observations import interval_samples,make_scene,observe,frame_summary

PREV=UNIT.parent/'unit_002';H2=UNIT.parent/'unit_001'
ASSET=UNIT/'inputs/assets/on';ARMS=['U','S','D','sham']
def save(path,**v):
    path=runtime.output_guard(path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():raise FileExistsError(path)
    np.savez_compressed(path,**v)
def low(a):return a.reshape(384,2,384,2).mean((1,3))
def compose(paper,fixed,target,factor):
    ink=low(np.maximum(fixed,target*np.float32(factor)))
    return paper*(1-ink[:,:,None])+.03*ink[:,:,None],ink
def plan():
    old={r['key']:r['camera'] for r in json.loads((PREV/'CAMERAS.json').read_text())}
    rows=[dict(key='BUILD',camera=old['BUILD'],cache=str(PREV/'renders/BUILD/COMMON.npz'),cache_kind='unit002')]
    rows += [dict(key=f'{i:03d}',camera=old[f'{i:03d}'],cache=str(PREV/f'renders/{i:03d}/COMMON.npz'),cache_kind='unit002',index=i) for i in range(25)]
    for j in range(1,13):
        i=24+j;c=orbit_camera(241,24+3*j,5.1,384)
        rows.append(dict(key=f'{i:03d}',camera=c,index=i,cache=str(PREV/'renders/HIGH/COMMON.npz') if j==12 else None,cache_kind='unit002' if j==12 else 'cold_original_GS'))
    rows.append(dict(key='FRONT',camera=orbit_camera(61,24,5.1,384),cache=str(H2/'renders/orbit_61_24_5.1/natural/U/FRAME.npz'),cache_kind='unit001'))
    return rows
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
    derived=json.loads((H2/'DERIVED_LOCK.json').read_text())
    for rel,h in derived.items():copy(H2/rel,UNIT/'frozen'/rel,h)
    for name in ['PROTOCOL.json','BUILD_MATCH.json','HEADROOM.json','GENERATOR_CHECK.json','GEOMETRY.json','D_GENERATION.json','TRIM_S.json','TRIM_D.json','TRIM_sham.json']:
        copy(H2/name,UNIT/'frozen'/name)
    rows=plan()
    for row in rows:
        if row['cache']:
            src=Path(row['cache']);dest=UNIT/f'inputs/cache/{row["key"]}/FRAME.npz';copy(src,dest)
            row['cache_original']=str(src);row['cache']=str(dest.relative_to(UNIT));row['cache_sha256']=sha(dest)
            if row['cache_kind']=='unit002':
                copy(src.parent/'TRACE.npz',dest.parent/'TRACE.npz')
                copy(src.parent/'METRICS.json',dest.parent/'PREVIOUS_METRICS.json')
    mesh,original,meta,link,b=load_asset(ASSET)
    states={a:npz(UNIT/f'frozen/paths/{a}.npz') for a in ARMS}
    from association import crossings
    events=crossings(states['U'],npz(UNIT/'frozen/GUIDE.npz'))
    oldevents=json.loads((UNIT/'frozen/HEADROOM.json').read_text())['events']
    assert [(e['face'],e['parent_id']) for e in events]==[(e['face'],e['parent_id']) for e in oldevents]
    samples={}
    for a in ARMS:
        raw=npz(UNIT/'frozen/paths/D_before_stop.npz') if a=='D' else states['U']
        trim={} if a=='U' else json.loads((UNIT/f'frozen/TRIM_{a}.json').read_text())
        samples[a]=interval_samples(raw,trim)
        save(UNIT/f'samples/{a}.npz',**samples[a])
        target_length=np.linalg.norm(states[a]['points'][:,1]-states[a]['points'][:,0],axis=1).sum()
        assert abs(samples[a]['weight'][~samples[a]['planned']].sum()-target_length)<1e-9
    js(UNIT/'CAMERAS.json',rows);js(UNIT/'IMPORT.json',records)
    js(UNIT/'PROTOCOL.json',dict(schema='H2_frozen_association_motion_v09_unit003',frozen_utc=runtime.now(),decision_sha256=sha(UNIT/'DECISION.json'),
        question='Do frozen local association gains survive actual camera transitions without extra necessary-shape loss or same-parent ink dropouts?',
        cameras=rows,frames=37,static_checks=2,playback_fps=8,trajectory='25 frame196/36 to241/24 then12 increments at fixed241 up to60; continuous finite path, loop reset not360',
        frozen_H2_protocol_sha256=sha(UNIT/'frozen/PROTOCOL.json'),guide='Existing curve240807000001 author_edge0..9,52segments,region5, assistant-confirmed style interface only; not semantic boundary or GT; full169 structure identical ON',
        policies='Exact saved U/S/D/sham paths, D_before_stop and parent trim intervals; no regeneration or parameter changes; single original layer',
        matching='Natural plus exactly unit001 BUILD_MATCH factors on target hatch only, never per-camera matching',
        sample_rule='All pretrim segments split exactly at removed interval endpoints, each subinterval midpoint quadrature maximum world step .005, fixed before evaluation. Same-ID tracked AA ink, continuous proxy first-hit depth .004 and region5. U-on-S/U-on-sham sampled at identical retained parent locations. D own pretrim domain, not displaced U points.',
        masks='Same renderer first-hit region5; necessary interior fixed2px erosion minus dilation2 of visible selected guide; guide absent means NA boundary observation, not success; also report mask denominators',
        observables='Raw/pretrim/trim/retained lengths, visibility and same-ID ink, forward+reverse transitions, own dropout vs composite cancellation vs correct rejection, fixed guide-band ink, actual RGB effect, absolute FAR other/background; no LOD',
        fixed='Original256690 rows/order/fullSH/geometry/covariance/opacity,UNKNOWN170281,seatS27873,mesh/rough labels,all non-target paths,169structure segments,paper.95,width1,AA2,visibility.004',
        caches='28 exact same-camera saved source/paper/S caches frozen at import;11 new elevation cameras render originalGS anew. All39 cameras freshly rasterize all4 arms. No image interpolation.',
        limitations='One authored proxy-conditional Chair, exposed cameras; no automatic segmentation/physical GT/nativeCUDA parity/Gaussian superiority. Old holes/open return/high rear zero/structure3dropouts1reappearance/143UNKNOWN and unit002 failures retained.',
        budget='35min maximum execution, CPU affinity2 threads1 serial CUDAempty;15:20 no new units15:45 wrap16:00 hardstop'))
    js(UNIT/'INPUT_LOCK.json',{str(p.relative_to(UNIT)):sha(p) for root in (UNIT/'inputs',UNIT/'frozen',UNIT/'samples') for p in sorted(root.rglob('*')) if p.is_file()})
    js(UNIT/'SOURCE_LOCK.json',{str(p):sha(p) for root in (CODE,BASECODE) for p in sorted(root.iterdir()) if p.suffix in ('.py','.cpp') and p.name not in ('analyze_motion.py','audit_motion.py','finish_motion.py')})
    js(UNIT/'PROTOCOL_LOCK.json',{n:sha(UNIT/n) for n in ('DECISION.json','PROTOCOL.json','CAMERAS.json')})
    print(json.dumps(dict(cameras=len(rows),headroom_crossings=len(events),samples={a:len(s['weight']) for a,s in samples.items()})),flush=True)
def locks():
    for p,h in json.loads((UNIT/'INPUT_LOCK.json').read_text()).items():assert sha(UNIT/p)==h,p
    for p,h in json.loads((UNIT/'SOURCE_LOCK.json').read_text()).items():assert sha(p)==h,p
    for p,h in json.loads((UNIT/'PROTOCOL_LOCK.json').read_text()).items():assert sha(UNIT/p)==h,p

class Runner:
    def __init__(self):
        self.mesh,self.paths,self.meta,self.link,self.binding=load_asset(ASSET)
        self.states={a:npz(UNIT/f'frozen/paths/{a}.npz') for a in ARMS}
        self.samples={a:npz(UNIT/f'samples/{a}.npz') for a in ARMS}
        self.guide=npz(UNIT/'frozen/GUIDE.npz');self.curve=npz(ASSET/'structure.npz')
        self.factors=json.loads((UNIT/'frozen/BUILD_MATCH.json').read_text())['factors'];self.scene=make_scene(self.mesh)
        self.source=None
    def cold(self,c,dest):
        import base_model as base
        from link_renderer import Renderer,validate_trace
        from hybrid import region_strength,paper_copy
        if self.source is None:
            self.source=base.load_source((ASSET/self.link['source_file']).resolve(),self.link['source_sha256'])
            self.source['source_index']=np.arange(len(self.source['means']),dtype=np.int64)
            self.source_identity=source_hashes(self.source);self.strength=region_strength(self.binding);self.engine=Renderer(UNIT/'build')
        xy=np.asarray(SAMPLES,np.int32);s,t=self.engine.render(self.source,c,xy=xy,strength=self.strength)
        p,_=self.engine.render(paper_copy(self.source,c,np.ones(len(self.strength)),[.95]*3),c)
        np.testing.assert_array_equal(s['alpha'],p['alpha'])
        proof=validate_trace(self.source,c,xy,s,t)
        reconstructed=np.bincount(t['sample_index'],t['weight']*self.strength[t['source_index']],minlength=len(xy))
        err=float(np.max(abs(reconstructed-s['contribution'][xy[:,1],xy[:,0]])));assert err<1e-6
        assert source_hashes(self.source)==self.source_identity
        save(dest/'TRACE.npz',xy=xy,**t)
        return dict(source=s['rgb'],paper=p['rgb'],support=s['contribution']),dict(trace=proof,support_error=err,source_hashes=self.source_identity,original_rows=len(self.strength),unknown_rows=int(self.binding['unknown'].sum()),seat_support_rows=int((self.strength>0).sum()),source_arrays_unchanged=True)
    def frame(self,row,key_override=None):
        from render import render,RenderCache
        from structure import raster_structure
        start=time.monotonic();key=key_override or row['key'];c=row['camera'];dest=runtime.configure_output(UNIT/'renders'/key)
        if row['cache']:
            cache=npz(UNIT/row['cache']);proof=dict(cache_original=row['cache_original'],cache_sha256=sha(UNIT/row['cache']),cold_original_GS=False)
        else:cache,proof=self.cold(c,dest);proof['cold_original_GS']=True
        paper=cache['paper'];states=self.states;allobs={};aa={};metrics={m:{} for m in ('natural','matched')};fixed=None;shared=None;reference_checks={}
        for a in ARMS:
            ids=[f'5:{int(s)}' for s in np.unique(states[a]['stroke_id'])]
            rc=RenderCache(track_ids=ids)
            render(self.mesh,{4:self.paths[4],5:states[a]},self.meta['styles'],c,2,dict(contours_visible=True,contour_strength=1.),rc)
            data=rc.value
            if data is None:raise RuntimeError('tracked cache capacity')
            target=np.maximum.reduce(list(data['coverage'][5].values())).astype(np.float32)*np.float32(.45);aa[a]=target
            if fixed is None:
                st,sd=raster_structure(self.mesh,self.curve,c,2);g,gd=raster_structure(self.mesh,self.guide,c,2)
                seat=np.maximum.reduce(list(data['coverage'][4].values())).astype(np.float32)*np.float32(.35)
                seatlinked=seat*np.repeat(np.repeat(cache['support'],2,0),2,1)
                fixed=np.maximum.reduce([data['contour'],st,seatlinked]);base,_=compose(paper,fixed,target,0)
                ref,_=compose(paper,fixed,target,1)
                mask=data['regions']==5;near=ndimage.binary_dilation(mask,iterations=2);band=ndimage.binary_dilation(low(g)>0,iterations=2)
                masks=dict(target=mask,necessary_interior=ndimage.binary_erosion(mask,iterations=2)&~band,boundary_band=band,
                    far_other=(data['regions']>0)&~near,far_background=(data['regions']==0)&~near)
                shared=dict(source=cache['source'],paper=paper,support=cache['support'],structure=low(st),guide=low(g),contour=low(data['contour']),seat=low(seat),seat_linked=low(seatlinked),
                    regions=data['regions'],baseline=base,**{f'mask_{n}':v for n,v in masks.items()})
                # Independently rasterize the untouched original U, not just a stored equality claim.
                original_rc=RenderCache();render(self.mesh,{4:self.paths[4],5:self.paths[5]},self.meta['styles'],c,2,dict(contours_visible=True,contour_strength=1.),original_rc)
                original_aa=np.maximum.reduce(list(original_rc.value['coverage'][5].values())).astype(np.float32)*np.float32(.45)
                np.testing.assert_array_equal(target,original_aa);reference_checks['original_U_AA_exact']=True
                if row['cache_kind']=='unit002':
                    prevkey='HIGH' if row['key']=='036' else row['key'];old=npz(PREV/f'renders/{prevkey}/natural/B1/FRAME.npz')
                    np.testing.assert_array_equal(ref,old['hybrid']);reference_checks['unit002_B1_hybrid_exact']=True
                elif row['cache_kind']=='unit001':
                    np.testing.assert_array_equal(ref,cache['hybrid']);reference_checks['unit001_U_hybrid_exact']=True
            else:np.testing.assert_array_equal(data['regions'],shared['regions'])
            image_natural,_=compose(paper,fixed,target,1);increment=np.abs(image_natural-base).sum(2)
            ob=observe(self.mesh,self.samples[a],c,data['tracked'],increment,.45,self.scene)
            allobs.update({f'{a}_{k}':v for k,v in ob.items()})
            if a=='U':
                for sarm in ('S','sham'):
                    co=observe(self.mesh,self.samples[sarm],c,data['tracked'],increment,.45,self.scene)
                    allobs.update({f'U_on_{sarm}_{k}':v for k,v in co.items()})
            visibility=frame_summary(self.samples[a],ob)
            for mode in ('natural','matched'):
                factor=1. if mode=='natural' else self.factors[a];img,ink=compose(paper,fixed,target,factor);own=low(target*np.float32(factor))
                out=dest/mode/a;out.mkdir(parents=True)
                save(out/'FRAME.npz',hybrid=img,own_ink=own,combined_ink=ink)
                png(out/'hybrid.png',img);png(out/'own_ink.png',1-own)
                absolute=np.abs(img-cache['source']).sum(2);delta=np.abs(img-ref).sum(2);inc=np.abs(img-base).sum(2)
                metrics[mode][a]=dict(factor=factor,target_rgb_effect=float(inc.sum()),whole_ink_mass=float(ink.sum()),own_target_ink_mass=float(own.sum()),
                    regions={n:dict(pixels=int(m.sum()),coverage_fraction=float((own[m]>1/255).mean()) if m.any() else None,own_ink_mass=float(own[m].sum()),
                        absolute_source_L1=float(absolute[m].sum()),increment_vs_U_L1=float(delta[m].sum())) for n,m in masks.items()},
                    visibility_natural_strength=visibility)
                if row['key'] in ('BUILD','000','024','036','FRONT'):
                    old=npz(H2/f'renders/{c["view"]}/{mode}/{a}/FRAME.npz')
                    np.testing.assert_array_equal(img,old['hybrid']);np.testing.assert_array_equal(own,old['target_ink'])
                    reference_checks[f'{mode}_{a}_unit001_exact']=True
            conventional=1-low(np.maximum.reduce([data['contour'],st,seat,target]));png(dest/f'conventional_{a}.png',conventional)
            del rc,data
        save(dest/'COMMON.npz',**shared);save(dest/'OBSERVATIONS.npz',**allobs)
        for n in ('source','paper'):png(dest/f'{n}.png',shared[n])
        for n in ('structure','guide'):png(dest/f'{n}.png',1-shared[n])
        # Pixel-space interval diagnostic against projected pre-stop endpoints, never a GT claim.
        margin={}
        for a in ('S','D'):
            raw=npz(UNIT/f'frozen/paths/{"D_before_stop" if a=="D" else "U"}.npz');trim=json.loads((UNIT/f'frozen/TRIM_{a}.json').read_text())
            gaps=[]
            for rec in trim['intervals']:
                p=raw['points'][rec['parent_segment']]
                for l,h in rec['removed_t']:
                    uv,z=project(np.array([(1-l)*p[0]+l*p[1],(1-h)*p[0]+h*p[1]]),c)
                    if (z>.2).all():gaps.append(float(np.linalg.norm(uv[1]-uv[0])))
            margin[a]=dict(intrinsic_implementation_endpoint_error_max=trim['white_margin_endpoint_error_max'],projected_removed_segment_lengths_px=gaps,
                scope='Projected pieces of fixed removed intervals, may be occluded and split by faces; not contiguous visible gap or physical truth')
        record=dict(key=key,camera=c,policy_paths_rasterized=True,source=proof,reference_checks=reference_checks,metrics=metrics,structure=sd,guide=gd,
            boundary_observable=bool(shared['mask_boundary_band'].any()),boundary_status='OBSERVED' if shared['mask_boundary_band'].any() else 'NO_VISIBLE_GUIDE_NA',margin=margin,
            seconds=time.monotonic()-start)
        js(dest/'METRICS.json',record)
        print(json.dumps(dict(key=key,seconds=record['seconds'],cold=proof['cold_original_GS'],boundary_observable=record['boundary_observable'],
            interior={a:metrics['natural'][a]['regions']['necessary_interior']['coverage_fraction'] for a in ARMS})),flush=True)
def main():
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','render']);p.add_argument('--keys',nargs='+');p.add_argument('--replay-key');a=p.parse_args()
    if a.stage=='prepare':prepare();return
    locks();runner=Runner();rows={r['key']:r for r in json.loads((UNIT/'CAMERAS.json').read_text())}
    for key in a.keys:runner.frame(rows[key],a.replay_key)
    locks()
if __name__=='__main__':main()
