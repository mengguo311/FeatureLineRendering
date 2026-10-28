"""Read back every saved policy PNG/APNG and original-index trace, no tuning."""
import runtime
from runtime import ROOT as UNIT,js,sha
import json
import numpy as np
from PIL import Image
from linked_asset import npz,load_asset,source_hashes
from run_motion import locks,ASSET,ARMS
from analyze_motion import panel

def check_png(path,val):
    if val.ndim==2:val=np.repeat(val[:,:,None],3,axis=2)
    with Image.open(path) as im:np.testing.assert_array_equal(np.array(im.convert('RGB')),np.uint8(np.clip(val,0,1)*255+.5))
def main():
    locks();rows=json.loads((UNIT/'CAMERAS.json').read_text());pngs=0;proof=[];far_nonzero=[]
    import base_model as base
    from hybrid import region_strength
    mesh,paths,meta,link,binding=load_asset(ASSET)
    source=base.load_source((ASSET/link['source_file']).resolve(),link['source_sha256']);source['source_index']=np.arange(len(source['means']),dtype=np.int64)
    identity=source_hashes(source);strength=region_strength(binding)
    for row in rows:
        key=row['key'];dest=UNIT/'renders'/key;common=npz(dest/'COMMON.npz');metric=json.loads((dest/'METRICS.json').read_text())
        assert metric['camera']==row['camera'];assert all(metric['reference_checks'].values())
        original=npz(dest/'natural/U/FRAME.npz')['hybrid']
        for mode in ('natural','matched'):
            for arm in ARMS:
                out=dest/mode/arm;f=npz(out/'FRAME.npz')
                check_png(out/'hybrid.png',f['hybrid']);check_png(out/'own_ink.png',1-f['own_ink']);pngs+=2
                for name in ('far_other','far_background'):
                    mask=common['mask_'+name]
                    delta=float(np.abs(f['hybrid']-original).sum(2)[mask].sum())
                    assert delta==metric['metrics'][mode][arm]['regions'][name]['increment_vs_U_L1']
                    if delta:far_nonzero.append(dict(key=key,mode=mode,arm=arm,region=name,absolute_increment_L1=delta))
        for name in ('source','paper'):check_png(dest/(name+'.png'),common[name]);pngs+=1
        for name in ('structure','guide'):check_png(dest/(name+'.png'),1-common[name]);pngs+=1
        tracepath=dest/'TRACE.npz' if metric['source']['cold_original_GS'] else UNIT/f'inputs/cache/{key}/TRACE.npz'
        if tracepath.exists():
            t=npz(tracepath);sid=t['sample_index'];ids=t['source_index'];w=t['weight'];xy=t['xy'];n=len(xy)
            assert (ids>=0).all() and (ids<len(strength)).all();assert np.array_equal(w,t['alpha']*t['T'])
            mass=np.bincount(sid,w,minlength=n);colors=base.source_colors(source,row['camera']);rgb=np.ones((n,3))*(1-mass[:,None])
            for j in range(3):rgb[:,j]+=np.bincount(sid,w*colors[ids,j],minlength=n)
            support=np.bincount(sid,w*strength[ids],minlength=n)
            re=float(np.max(abs(rgb-common['source'][xy[:,1],xy[:,0]])));se=float(np.max(abs(support-common['support'][xy[:,1],xy[:,0]])))
            assert re<1e-6 and se<1e-6
            errors=[]
            for s in range(n):
                ix=np.flatnonzero(sid==s);T=1.
                for j in ix:errors.append(abs(T-t['T'][j]));T*=1-t['alpha'][j]
            te=max(errors,default=0.);assert te<1e-12
            proof.append(dict(key=key,events=len(w),rgb_error=re,S_error=se,T_chain_error=te,cold_GS=metric['source']['cold_original_GS']))
    assert source_hashes(source)==identity
    media={}
    for mode in ('natural','matched'):
        path=UNIT/'media'/f'{mode}_orbit.png'
        with Image.open(path) as movie:
            assert movie.n_frames==37
            for i in range(37):
                movie.seek(i);np.testing.assert_array_equal(np.array(movie.convert('RGB')),np.array(panel(f'{i:03d}',mode)))
            media[mode]=dict(frames=37,all_decoded=True,exact_full_object_panels=True,sha256=sha(path))
    # Verify conventional control composition independently at difficult checkpoints.
    from render import render,RenderCache
    from structure import raster_structure
    from run_motion import low
    conventional=0
    for key in ('BUILD','024','036'):
        row=next(r for r in rows if r['key']==key);c=row['camera'];curve=npz(ASSET/'structure.npz');st,_=raster_structure(mesh,curve,c,2)
        for a in ARMS:
            p=npz(UNIT/f'frozen/paths/{a}.npz');rc=RenderCache();render(mesh,{4:paths[4],5:p},meta['styles'],c,2,dict(contours_visible=True,contour_strength=1.),rc)
            d=rc.value;seat=np.maximum.reduce(list(d['coverage'][4].values())).astype(np.float32)*np.float32(.35)
            target=np.maximum.reduce(list(d['coverage'][5].values())).astype(np.float32)*np.float32(.45)
            check_png(UNIT/f'renders/{key}/conventional_{a}.png',1-low(np.maximum.reduce([d['contour'],st,seat,target])));conventional+=1
    # Existing failed wrappers are never replaced by this audit's success.
    receipts={p.stem:json.loads(p.read_text())['child_returncode'] for p in sorted((UNIT/'logs').glob('*.json')) if not p.name.endswith('.start.json')}
    locks()
    js(UNIT/'READBACK.json',dict(utc=runtime.now(),science_cameras=len(rows),policy_pngs_and_common_pngs_checked=pngs,conventional_checkpoints_pngs=conventional,media=media,
        source_identity=identity,original_rows=len(strength),unknown_rows=int(binding['unknown'].sum()),seat_support_rows=int((strength>0).sum()),
        trace_checks=proof,trace_scope='38 camera sparse accepted original-row events; FRONT cache has no trace imported and is not counted. Not native CUDA parity or path ownership.',
        actual_child_receipts_snapshot=receipts,far_nonzero=far_nonzero,zero_far_every_arm_gate='FAILED for3 matched frame030 cases, retained unchanged; audit checks fidelity, not scientific success',
        interrupted005_preserved=json.loads((UNIT/'INTERRUPTION_005.json').read_text()),
        source_input_protocol_decision_unchanged=True,parent_verification='pending independent parent read'))
    print(json.dumps(dict(pngs=pngs,conventional=conventional,trace_cameras=len(proof),events=sum(p['events'] for p in proof),rgb_max=max(p['rgb_error'] for p in proof),S_max=max(p['S_error'] for p in proof),media=media)),flush=True)
if __name__=='__main__':main()
