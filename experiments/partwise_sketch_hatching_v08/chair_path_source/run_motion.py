"""Render frozen saved Chair assets on a saved finite trajectory, in bounded batches."""
import runtime
from runtime import js,sha
from pathlib import Path
import argparse,json,time
import numpy as np
from linked_asset import load_asset,source_hashes,png,npz,SAMPLES
from whole_asset import load_preset,compose_whole
from motion import load_trajectory,observe

class MotionRenderer:
    def __init__(self,asset,build,samples):
        import base_model as base
        import open3d as o3d
        from link_renderer import Renderer
        from hybrid import region_strength
        self.asset=Path(asset).resolve();self.preset=load_preset(self.asset)
        self.mesh,self.paths,self.meta,self.link,self.binding=load_asset(self.asset)
        self.source=base.load_source((self.asset/self.link['source_file']).resolve(),self.link['source_sha256'])
        self.source['source_index']=np.arange(len(self.source['means']),dtype=np.int64)
        self.original=source_hashes(self.source);self.s=region_strength(self.binding)
        self.engine=Renderer(build);self.samples=samples
        self.scene=o3d.t.geometry.RaycastingScene(nthreads=1)
        self.scene.add_triangles(o3d.core.Tensor(self.mesh['vertices'].astype(np.float32)),o3d.core.Tensor(self.mesh['faces'].astype(np.uint32)))

    def frame(self,c,out,reference=None,observe_paths=True):
        from hybrid import paper_copy,edit_metrics
        from link_renderer import validate_trace
        from render import render,RenderCache
        started=time.monotonic();out=runtime.configure_output(out)
        xy=np.asarray(SAMPLES,np.int32)
        source,trace=self.engine.render(self.source,c,xy=xy,strength=self.s)
        paper,_=self.engine.render(paper_copy(self.source,c,np.ones(len(self.s)),self.preset['paper_color']),c)
        np.testing.assert_array_equal(source['alpha'],paper['alpha'])
        proof=validate_trace(self.source,c,xy,source,trace)
        support=np.bincount(trace['sample_index'],trace['weight']*self.s[trace['source_index']],minlength=len(xy))
        assert np.max(np.abs(support-source['contribution'][xy[:,1],xy[:,0]]))<1e-6
        assert np.max(np.abs(paper['rgb']-(1-.05*source['alpha'][:,:,None])))<1e-6
        cache=RenderCache(track_ids=self.samples['selected_paths'] if observe_paths else ())
        proxy=render(self.mesh,self.paths,self.meta['styles'],c,2,dict(contours_visible=True,contour_strength=1.),cache)
        data=cache.value
        if data is None:raise RuntimeError('bounded AA cache exceeded')
        layers={r:np.maximum.reduce([v.astype(np.float32)*self.meta['styles'][str(r)].get('ink_strength',.8) for v in values.values()]) for r,values in data['coverage'].items()}
        result=compose_whole(paper['rgb'],layers,data['contour'],source['contribution'],2)
        np.testing.assert_allclose(1-result['ungated_ink'],proxy['image'],atol=1e-7,rtol=0)
        frames=dict(source=source['rgb'],source_alpha=source['alpha'],paper=paper['rgb'],support=source['contribution'],
            proxy=proxy['image'],proxy_depth=proxy['depth'],regions=proxy['regions'],**result)
        reference_equal=None
        if reference is not None:
            old=npz(reference);assert set(old)==set(frames)
            reference_equal={k:bool(np.array_equal(v,old[k])) for k,v in frames.items()}
            assert all(reference_equal.values()),reference_equal
        np.savez_compressed(out/'FRAME.npz',**frames)
        np.savez_compressed(out/'TRACE.npz',xy=xy,**trace)
        for key in ('source','paper','support','hybrid','proxy'):png(out/(key+'.png'),frames[key])
        for key in ('combined_ink','seat_ink','seat_linked_ink','other_ink','contour'):png(out/(key+'.png'),1-frames[key])
        obs_summary=None
        if observe_paths:
            obs=observe(self.mesh,self.samples,c,data,source['contribution'],self.meta['styles'],self.scene)
            np.savez_compressed(out/'OBSERVATIONS.npz',**obs)
            obs_summary=dict(status_counts={str(k):int(v) for k,v in zip(*np.unique(obs['status'],return_counts=True))},
                visible_without_own_pre=int(((obs['status']=='visible')&(obs['pre']<=1/255)).sum()),
                visible_without_own_post=int(((obs['status']=='visible')&(obs['post']<=1/255)).sum()))
        target=proxy['regions']==4;obj=proxy['regions']>0
        metrics=dict(global_absolute_difference=edit_metrics(frames['source'],frames['hybrid'],frames['regions']),
            object_pixels=int(obj.sum()),seat_pixels=int(target.sum()),ink_alpha_mass=float(frames['combined_ink'].sum()),
            seat_ink_coverage=float((frames['seat_linked_ink'][target]>1/255).mean()) if target.any() else None,
            object_ink_coverage=float((frames['combined_ink'][obj]>1/255).mean()) if obj.any() else None)
        assert source_hashes(self.source)==self.original
        receipt=dict(camera=c,asset_manifest_sha256=sha(self.asset/'FILES.json'),source_array_hashes=self.original,
            source_count=len(self.s),selected_rows=int((self.s>0).sum()),unknown_rows=int(self.binding['unknown'].sum()),
            source_arrays_unchanged=True,path_hashes={str(r):sha(self.asset/f'region_{r}.npz') for r in self.paths},
            trace_validation=proof,reference_equal=reference_equal,bounds=proxy['bounds'],observations=obs_summary,
            metrics=metrics,seconds=time.monotonic()-started,actual_backend='CPU original GS recomputed at this camera; fixed proxy ink; regional S only',
            cold_original_GS=True,files={f.name:sha(f) for f in out.iterdir() if f.is_file()})
        js(out/'RENDER_RECEIPT.json',receipt)
        print(json.dumps(dict(frame=str(out),seconds=receipt['seconds'],observations=obs_summary)),flush=True)
        return receipt

def verify_unit(unit):
    lock=json.loads((unit/'PROTOCOL_LOCK.json').read_text());assert sha(unit/'PROTOCOL.json')==lock['sha256']
    protocol=json.loads((unit/'PROTOCOL.json').read_text());assert sha(unit/'DECISION.json')==protocol['decision_sha256']
    for p,h in json.loads((unit/'INPUT_LOCK.json').read_text()).items():assert sha(p)==h,p
    for name,h in json.loads((unit/'SOURCE_LOCK.json').read_text())['files'].items():assert sha(Path(__file__).parent/name)==h,name

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--unit',type=Path);p.add_argument('--asset',type=Path);p.add_argument('--trajectory',type=Path)
    p.add_argument('--samples',type=Path);p.add_argument('--out',type=Path);p.add_argument('--sequence',choices=['orbit','zoom'],required=True)
    p.add_argument('--start',type=int,required=True);p.add_argument('--stop',type=int,required=True)
    a=p.parse_args()
    if a.unit:
        unit=a.unit.resolve();verify_unit(unit);asset=unit/'delivery/assets/whole_spacing'
        plan=load_trajectory(unit/'delivery/TRAJECTORY.json');samples=json.loads((unit/'delivery/SAMPLES.json').read_text());out=unit/'renders'
    else:
        if not all((a.asset,a.trajectory,a.samples,a.out)):p.error('provide --unit or asset/trajectory/samples/out')
        unit=None;asset=a.asset;plan=load_trajectory(a.trajectory);samples=json.loads(a.samples.read_text());out=runtime.output_guard(a.out)
    rows=plan[a.sequence]
    if not 0<=a.start<a.stop<=len(rows):p.error('invalid frame range')
    renderer=MotionRenderer(asset,out/'build',samples)
    for row in rows[a.start:a.stop]:
        index=row['index'];dest=out/a.sequence/f'{index:03d}'
        # Zoom is symmetric; the return uses verified completed same-camera results.
        reuse=(out/'orbit/060') if a.sequence=='zoom' and index in (0,20) else ((out/'zoom'/f'{20-index:03d}') if a.sequence=='zoom' and index>10 else None)
        if reuse is not None:
            receipt=json.loads((reuse/'RENDER_RECEIPT.json').read_text())
            assert receipt['camera']==row['camera']
            for name,h in receipt['files'].items():assert sha(reuse/name)==h
            dest=runtime.configure_output(dest)
            js(dest/'REUSE.json',dict(source=str(reuse.relative_to(out)),camera=row['camera'],receipt_sha256=sha(reuse/'RENDER_RECEIPT.json'),reason='identical frozen camera and asset; no interpolation'))
            print('Verified same-camera reuse',a.sequence,index,flush=True);continue
        ref=None
        if unit is not None and a.sequence=='orbit' and index in (0,60):ref=unit/'inputs/reference'/row['camera']['view']/'whole_spacing/FRAME.npz'
        renderer.frame(row['camera'],dest,reference=ref)
    if unit is not None:verify_unit(unit)
if __name__=='__main__':main()
