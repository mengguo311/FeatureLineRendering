"""Finite current-asset orbit; structure remains independent of labels and seat S."""
import runtime
from runtime import js,sha
from pathlib import Path
import json,time,argparse
import numpy as np
from geometry import orbit_camera,project
from linked_asset import load_asset,source_hashes,npz,png,SAMPLES
from whole_asset import load_preset,compose_whole
from structure import load_structure,raster_structure,combine_structure

def trajectory():
    rows=[]
    for i in range(61):
        a=float(241-3*i)
        e=round(24+.8*i if i<=15 else (36. if i<=30 else 36-.4*(i-30)),8)
        rows.append(dict(index=i,time_seconds=i/12,azimuth=a,elevation=e,distance=5.1,
            camera=orbit_camera(a,e,5.1,384),exposure='previously_exposed_unit007' if i in (0,15,30,60) else 'reserved_for_current_asset_at_unit008_freeze; not certified GS-unseen'))
    return dict(schema='chair_structure_motion_v1',fps=12,frames=rows,
        scope='Finite piecewise linear camera path; fixed current style and world curves; no interpolation of images or real-time performance claim')

def select_curve_samples(curve):
    length=np.linalg.norm(curve['points'][:,1]-curve['points'][:,0],axis=1)
    total=float(length.sum());cumulative=np.cumsum(length);anchors=[]
    if total<=0:raise ValueError('empty curve')
    for i in range(64):
        fraction=(i+.5)/64;d=total*fraction;j=min(int(np.searchsorted(cumulative,d,side='right')),len(length)-1)
        t=(d-(cumulative[j-1] if j else 0))/length[j]
        anchors.append(dict(index=i,curve_id=int(curve['curve_id'][j]),fraction=fraction,segment=j,segment_t=float(t),
            face=int(curve['face'][j]),bary=((1-t)*curve['bary'][j,0]+t*curve['bary'][j,1]).tolist(),
            point=((1-t)*curve['points'][j,0]+t*curve['points'][j,1]).tolist(),world_weight=total/64))
    return dict(selection='64 equal stored-arclength midpoint samples; no bridge across gaps',anchors=anchors,
        scope='Same-proxy descriptive visibility only; no physical or original-Gaussian path certificate')

def compose_pair(paper,layers,contour,support,structure_aa):
    layers={r:(v if r in (4,5) else np.zeros_like(v)) for r,v in layers.items()}
    base=compose_whole(paper,layers,contour,support,2,[4,5]);h,w=support.shape
    low=lambda a:a.reshape(h,2,w,2).mean((1,3))
    up=np.repeat(np.repeat(np.clip(support,0,1),2,0),2,1)
    others=np.maximum.reduce([v for r,v in layers.items() if r!=4]+[contour])
    base_aa=np.maximum(others,layers[4]*up);ungated=np.maximum(others,layers[4])
    np.testing.assert_array_equal(low(base_aa),base['combined_ink'])
    pair=[]
    for enabled in (False,True):
        f=dict(base,base_hybrid=base['hybrid'].copy(),base_combined_ink=base['combined_ink'].copy(),
            base_proxy=low(1-ungated),structure_available=low(structure_aa))
        f.update(combine_structure(paper,base_aa,structure_aa,enabled))
        actual=structure_aa if enabled else np.zeros_like(structure_aa)
        f['ungated_ink']=low(np.maximum(ungated,actual));f['proxy']=low(1-np.maximum(ungated,actual))
        pair.append(f)
    return tuple(pair)

def observe_curve(mesh,samples,camera,own,increment,scene=None):
    import open3d as o3d
    if scene is None:
        scene=o3d.t.geometry.RaycastingScene(nthreads=1)
        scene.add_triangles(o3d.core.Tensor(mesh['vertices'].astype(np.float32)),o3d.core.Tensor(mesh['faces'].astype(np.uint32)))
    p=np.asarray([a['point'] for a in samples['anchors']]);uv,z=project(p,camera)
    E=np.asarray(camera['extrinsic']);R=E[:3,:3];origin=-np.linalg.inv(R)@E[:3,3]
    local=np.column_stack(((uv[:,0]-camera['cx'])/camera['fx'],(uv[:,1]-camera['cy'])/camera['fy'],np.ones(len(z))))
    direction=local@np.linalg.inv(R).T
    rays=np.column_stack((np.broadcast_to(origin,direction.shape),direction)).astype(np.float32)
    hit=scene.cast_rays(o3d.core.Tensor(rays),nthreads=1)['t_hit'].numpy().astype(float)
    w,h=camera['width'],camera['height'];inside=(uv[:,0]>=0)&(uv[:,0]<=w-1)&(uv[:,1]>=0)&(uv[:,1]<=h-1)
    delta=np.full(len(z),np.inf);np.subtract(z,hit,out=delta,where=np.isfinite(hit))
    status=np.full(len(z),'visible',dtype='<U24');status[np.abs(delta)>.004]='depth_rejected'
    status[~np.isfinite(hit)]='no_proxy_hit';status[~inside]='offscreen';status[z<=.2]='behind'
    def sample(a):
        out=[]
        for (x,y),valid in zip(uv,inside&(z>.2)):
            if not valid:out.append(0.);continue
            ix=int(np.floor(x));iy=int(np.floor(y));jx=min(ix+1,w-1);jy=min(iy+1,h-1);tx=x-ix;ty=y-iy
            out.append(float((1-tx)*(1-ty)*a[iy,ix]+tx*(1-ty)*a[iy,jx]+(1-tx)*ty*a[jy,ix]+tx*ty*a[jy,jx]))
        return np.asarray(out)
    return dict(uv=uv,z=z,hit_z=hit,status=status,own_ink=sample(own),increment=sample(np.abs(increment).sum(2)))

class MotionRenderer:
    def __init__(self,asset,build,samples):
        import base_model as base
        import open3d as o3d
        from link_renderer import Renderer
        from hybrid import region_strength
        self.asset=Path(asset).resolve();self.preset=load_preset(self.asset)
        if self.preset['active_regions']!=[4,5]:raise ValueError('unit008 requires the saved selective preset')
        self.mesh,self.paths,self.meta,self.link,self.binding=load_asset(self.asset)
        self.curve,self.config=load_structure(self.asset,self.mesh)
        if samples!=select_curve_samples(self.curve):raise ValueError('sample identity mismatch')
        self.samples=samples;self.source=base.load_source((self.asset/self.link['source_file']).resolve(),self.link['source_sha256'])
        self.source['source_index']=np.arange(len(self.source['means']),dtype=np.int64)
        self.original=source_hashes(self.source);self.s=region_strength(self.binding);self.engine=Renderer(build)
        self.scene=o3d.t.geometry.RaycastingScene(nthreads=1)
        self.scene.add_triangles(o3d.core.Tensor(self.mesh['vertices'].astype(np.float32)),o3d.core.Tensor(self.mesh['faces'].astype(np.uint32)))

    def frame(self,c,out,reference=None):
        from hybrid import paper_copy,edit_metrics
        from link_renderer import validate_trace
        from render import render,RenderCache
        started=time.monotonic();out=runtime.configure_output(out);xy=np.asarray(SAMPLES,np.int32)
        source,trace=self.engine.render(self.source,c,xy=xy,strength=self.s)
        paper,_=self.engine.render(paper_copy(self.source,c,np.ones(len(self.s)),self.preset['paper_color']),c)
        np.testing.assert_array_equal(source['alpha'],paper['alpha']);proof=validate_trace(self.source,c,xy,source,trace)
        support=np.bincount(trace['sample_index'],trace['weight']*self.s[trace['source_index']],minlength=len(xy))
        assert np.max(np.abs(support-source['contribution'][xy[:,1],xy[:,0]]))<1e-6
        effective={k:dict(v,ink_strength=(v.get('ink_strength',.8) if int(k) in (4,5) else 0.)) for k,v in self.meta['styles'].items()}
        cache=RenderCache();proxy=render(self.mesh,self.paths,effective,c,2,dict(contours_visible=True,contour_strength=1.),cache)
        data=cache.value
        if data is None:raise RuntimeError('AA cache exceeded')
        layers={r:np.maximum.reduce([v.astype(np.float32)*effective[str(r)]['ink_strength'] for v in values.values()]) for r,values in data['coverage'].items()}
        structure,diagnostics=raster_structure(self.mesh,self.curve,c,2)
        off,on=compose_pair(paper['rgb'],layers,data['contour'],source['contribution'],structure)
        common=dict(source=source['rgb'],source_alpha=source['alpha'],paper=paper['rgb'],support=source['contribution'],proxy_depth=proxy['depth'],regions=proxy['regions'])
        pair={'off':dict(common,**off),'on':dict(common,**on)};equal={}
        for arm,frames in pair.items():
            if reference is not None:
                old=npz(Path(reference)/arm/c['view']/'FRAME.npz');assert set(old)==set(frames)
                equal[arm]={k:bool(np.array_equal(v,old[k])) for k,v in frames.items()};assert all(equal[arm].values()),equal
            dest=out/arm;dest.mkdir();np.savez_compressed(dest/'FRAME.npz',**frames)
            for key in ('source','paper','support','hybrid','proxy'):png(dest/(key+'.png'),frames[key])
            for key in ('combined_ink','seat_linked_ink','contour','structure'):png(dest/(key+'.png'),1-frames[key])
        np.savez_compressed(out/'TRACE.npz',xy=xy,**trace)
        obs=observe_curve(self.mesh,self.samples,c,on['structure'],on['hybrid']-off['hybrid'],self.scene)
        np.savez_compressed(out/'OBSERVATIONS.npz',**obs)
        assert source_hashes(self.source)==self.original
        record=dict(camera=c,asset_manifest_sha256=sha(self.asset/'FILES.json'),source_count=len(self.s),unknown_rows=int(self.binding['unknown'].sum()),
            selected_source_rows=int((self.s>0).sum()),source_arrays_unchanged=True,source_hashes=self.original,
            path_hashes={str(r):sha(self.asset/f'region_{r}.npz') for r in self.paths},structure_sha256=sha(self.asset/'structure.npz'),
            structure=diagnostics,reference_equal=equal,trace_validation=proof,bounds=proxy['bounds'],
            off_absolute=edit_metrics(common['source'],off['hybrid'],common['regions']),on_absolute=edit_metrics(common['source'],on['hybrid'],common['regions']),
            increment_raw_L1=float(np.abs(on['hybrid']-off['hybrid']).sum()),ink_mass_off=float(off['combined_ink'].sum()),ink_mass_on=float(on['combined_ink'].sum()),
            observations=dict(visible=int((obs['status']=='visible').sum()),visible_without_own_ink=int(((obs['status']=='visible')&(obs['own_ink']<=1/255)).sum()),
                visible_own_ink_without_increment=int(((obs['status']=='visible')&(obs['own_ink']>1/255)&(obs['increment']<=1/255)).sum())),
            cold_original_GS=True,composition='One actual camera GS/proxy/structure evaluation; two saved switch states composed at AA2',
            seconds=time.monotonic()-started,files={str(f.relative_to(out)):sha(f) for f in out.rglob('*') if f.is_file()})
        js(out/'RENDER_RECEIPT.json',record);print(json.dumps(dict(frame=str(out),seconds=record['seconds'],observations=record['observations'])),flush=True)
        return record

def verify_unit(unit):
    protocol=json.loads((unit/'PROTOCOL.json').read_text());assert sha(unit/'PROTOCOL.json')==json.loads((unit/'PROTOCOL_LOCK.json').read_text())['sha256']
    assert sha(unit/'DECISION.json')==protocol['decision_sha256']
    for path,h in json.loads((unit/'INPUT_LOCK.json').read_text()).items():assert sha(Path(path))==h,path
    for name,h in json.loads((unit/'SOURCE_LOCK.json').read_text()).items():assert sha(Path(__file__).parent/name)==h,name

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--unit',type=Path);p.add_argument('--asset',type=Path)
    p.add_argument('--trajectory',type=Path);p.add_argument('--samples',type=Path);p.add_argument('--out',type=Path)
    p.add_argument('--start',type=int,required=True);p.add_argument('--stop',type=int,required=True);a=p.parse_args()
    if a.unit:
        unit=a.unit.resolve();verify_unit(unit);asset=unit/'delivery/assets/on';plan=json.loads((unit/'delivery/TRAJECTORY.json').read_text())
        samples=json.loads((unit/'delivery/SAMPLES.json').read_text());out=unit/'renders'
    else:
        if not all((a.asset,a.trajectory,a.samples,a.out)):p.error('unit or asset/trajectory/samples/out required')
        unit=None;asset=a.asset;plan=json.loads(a.trajectory.read_text());samples=json.loads(a.samples.read_text());out=runtime.output_guard(a.out)
    if plan!=trajectory():raise ValueError('trajectory changed')
    if not 0<=a.start<a.stop<=61:p.error('invalid frame range')
    engine=MotionRenderer(asset,out/'build',samples)
    for row in plan['frames'][a.start:a.stop]:
        ref=unit/'inputs/reference' if unit is not None and row['index'] in (0,15,30,60) else None
        engine.frame(row['camera'],out/f'{row["index"]:03d}',ref)
    if unit is not None:verify_unit(unit)
if __name__=='__main__':main()
