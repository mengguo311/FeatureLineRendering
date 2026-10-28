"""Read back frozen outputs, decode media, preserve actual execution history."""
import runtime
from runtime import ROOT as UNIT,js,sha
import json,shutil
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageSequence
from linked_asset import npz,load_asset,source_hashes
from run_h1 import locks,compose

def rgb(a):
    if a.ndim==2:a=np.repeat(a[:,:,None],3,axis=2)
    return np.uint8(np.clip(a,0,1)*255+.5)
def panel(items):
    out=Image.new('RGB',(384*len(items),410),'white');d=ImageDraw.Draw(out)
    for i,(label,path) in enumerate(items):
        im=Image.open(path);im.load();assert im.size==(384,384)
        out.paste(im,(384*i,26));d.text((384*i+5,5),label,fill='black')
    return out
def main():
    locks();rows=json.loads((UNIT/'CAMERAS.json').read_text());frames=[];checks=[]
    for record in json.loads((UNIT/'IMPORT.json').read_text()):assert sha(record['source'])==record['sha256']
    mesh,paths,meta,link,binding=load_asset(UNIT/'inputs/assets/on')
    import base_model as base
    a=base.load_source((UNIT/'inputs/assets/on'/link['source_file']).resolve(),link['source_sha256']);a['source_index']=np.arange(len(a['means']),dtype=np.int64)
    initial=source_hashes(a);strength=npz(UNIT/'inputs/assets/on/SOURCE_LINK.npz')['ink_strength']
    media=UNIT/'media';media.mkdir(exist_ok=True)
    pngs=0;maxrgb=0.;maxsupport=0.;maxT=0.;events=0
    for row in rows:
        dest=UNIT/'renders'/row['key'];c=npz(dest/'COMMON.npz');r=json.loads((dest/'METRICS.json').read_text());frames.append(r)
        assert r['source_hashes']==initial and r['source_arrays_unchanged'] and r['cold_original_GS']
        trace=npz(dest/'TRACE.npz');xy=trace['xy'];sid=trace['sample_index'];ids=trace['source_index'];weights=trace['weight'];colors=base.source_colors(a,row['camera'])
        expected=np.ones((len(xy),3))*(1-np.bincount(sid,weights,minlength=len(xy)))[:,None]
        for k in range(3):expected[:,k]+=np.bincount(sid,weights*colors[ids,k],minlength=len(xy))
        error=float(np.max(np.abs(expected-c['source'][xy[:,1],xy[:,0]])));assert error<1e-6;maxrgb=max(maxrgb,error)
        expected_s=np.bincount(sid,weights*strength[ids],minlength=len(xy));error_s=float(np.max(np.abs(expected_s-c['support'][xy[:,1],xy[:,0]])));assert error_s<1e-6;maxsupport=max(maxsupport,error_s)
        for s in range(len(xy)):
            ii=np.flatnonzero(sid==s);T=1.
            for j in ii:maxT=max(maxT,abs(T-trace['T'][j]));T*=1-trace['alpha'][j]
        events+=len(weights)
        natural={}
        for mode in ('natural','matched'):
            for arm in ('B0','B1'):
                out=dest/mode/arm;f=npz(out/'FRAME.npz')
                for name,array in [('hybrid',f['hybrid']),('own_ink',1-f['own_ink'])]:
                    im=Image.open(out/(name+'.png'));im.load();np.testing.assert_array_equal(np.asarray(im),rgb(array));pngs+=1
                np.testing.assert_array_equal(f['own_ink'],f['own_aa'].reshape(384,2,384,2).mean((1,3)))
                if mode=='natural':natural[arm]=f
                for k in ('far_other','far_background'):assert r['metrics'][mode][arm]['regions'][k]['increment_vs_U_L1']==0.
        conventional=npz(dest/'CONVENTIONAL.npz');assert not bool(conventional['source_S_applied'])
        np.testing.assert_array_equal(np.asarray(Image.open(dest/'conventional_B1.png')),rgb(conventional['image']));pngs+=1
        proxy_check=None
        if row['key'] in ('BUILD','000','024','HIGH'):
            from render import render,RenderCache
            from structure import raster_structure
            rc=RenderCache();render(mesh,{4:paths[4],5:paths[5]},meta['styles'],row['camera'],2,dict(contours_visible=True,contour_strength=1.),rc)
            structure,_=raster_structure(mesh,npz(UNIT/'inputs/assets/on/structure.npz'),row['camera'],2)
            seat=np.maximum.reduce(list(rc.value['coverage'][4].values())).astype(np.float32)*np.float32(.35)
            target=np.maximum.reduce(list(rc.value['coverage'][5].values())).astype(np.float32)*np.float32(.45)
            raw=np.maximum.reduce([rc.value['contour'],structure,seat,target]);expected_proxy=1-raw.reshape(384,2,384,2).mean((1,3))
            np.testing.assert_array_equal(expected_proxy,conventional['image']);proxy_check='Fresh proxy-AA re-render with raw seat/no S exactly equal'
        checks.append(dict(key=row['key'],source_trace_RGB_error=error,source_S_error=error_s,source_original_identity=True,all_arm_PNGs_equal=True,conventional_cold_check=proxy_check))
    assert maxT<1e-10;assert source_hashes(a)==initial
    keyrows=['BUILD','000','012','024','HIGH'];pans=[];layers=[]
    for key in keyrows:
        d=UNIT/'renders'/key
        pans.append(panel([(key+' | Original GS',d/'source.png'),(key+' | B0 2D natural',d/'natural/B0/hybrid.png'),(key+' | B1 3D natural',d/'natural/B1/hybrid.png'),
            (key+' | B0 BUILD matched',d/'matched/B0/hybrid.png'),(key+' | B1 BUILD matched',d/'matched/B1/hybrid.png'),(key+' | Conventional 3D, no S',d/'conventional_B1.png')]))
        layers.append(panel([(key+' | Fixed structure',d/'structure.png'),(key+' | B0 own hatch',d/'natural/B0/own_ink.png'),(key+' | B1 own hatch',d/'natural/B1/own_ink.png')]))
    def stack(pans,path):
        out=Image.new('RGB',(pans[0].width,sum(p.height for p in pans)),'white');y=0
        for p in pans:out.paste(p,(0,y));y+=p.height
        out.save(path)
    stack(pans,media/'KEYFRAMES.png');stack(layers,media/'WHOLE_LAYERS.png')
    videos={}
    for mode in ('natural','matched'):
        movie=[]
        for row in rows:
            if 'index' not in row:continue
            d=UNIT/'renders'/row['key'];key=row['key'];movie.append(panel([(key+' | B0 2D '+mode,d/mode/'B0/hybrid.png'),(key+' | B1 3D '+mode,d/mode/'B1/hybrid.png'),(key+' | Conventional 3D, no S',d/'conventional_B1.png')]))
        path=media/(mode+'_orbit.png');movie[0].save(path,save_all=True,append_images=movie[1:],duration=125,loop=0,disposal=0,blend=0)
        im=Image.open(path);assert im.n_frames==25
        for index,frame in enumerate(ImageSequence.Iterator(im)):np.testing.assert_array_equal(np.asarray(frame.convert('RGB')),np.asarray(movie[index]))
        videos[mode]=dict(frames=25,duration_ms_per_frame=125,all_frames_exact=True,scope='Finite arc, final-to-first is playback reset, not a continuous loop; 8fps playback is not rendering speed')
        contact=Image.new('RGB',(movie[0].width//2*5,205*5),'white')
        for i,p in enumerate(movie):contact.paste(p.resize((p.width//2,205)),((i%5)*(p.width//2),(i//5)*205))
        contact.save(media/(mode+'_ALL_FRAMES.png'))
    completed=[];missing=[]
    for p in sorted((UNIT/'logs').glob('*.start.json')):
        q=p.with_name(p.name.replace('.start.json','.json'))
        if not q.exists():missing.append(dict(start=p.name,final='MISSING',preserved_child_status=json.loads(p.read_text())['child_returncode']));continue
        r=json.loads(q.read_text());completed.append(r)
    finished=[r for r in completed if 'finished_utc' in r];finished.sort(key=lambda r:r['started_utc'])
    assert all(x['finished_utc']<=y['started_utc'] for x,y in zip(finished[:-1],finished[1:]))
    js(UNIT/'SUMMARY_METRICS.json',frames)
    js(UNIT/'READBACK.json',dict(utc=runtime.now(),frames=27,policy_PNGs_plus_conventional_checked=pngs,checks=checks,videos=videos,
        original_source_rows=len(a['means']),unknown_rows=int(binding['unknown'].sum()),source_S_rows=int((strength>0).sum()),accepted_trace_events=events,
        full_SH_RGB_max_error=maxrgb,S_max_error=maxsupport,T_chain_max_error=maxT,all_input_source_protocol_locks_unchanged=True,
        source_arrays_unchanged=True,completed_commands_serial=True,missing_final_receipts=missing,
        retained_BUILD_failure='failed_attempts/initial_center_only_baseline',parent_verification='pending independent parent read',
        scope='CPU EWA sampled original-row provenance; no native CUDA parity or upper-back Gaussian ownership; no independent perceptual preference test'))
    js(UNIT/'HANDOFF_ANALYSIS_SOURCE_LOCK.json',{p.name:sha(p) for p in runtime.CODE.glob('*.py')})
    print(json.dumps(dict(frames=27,PNGs=pngs,videos=videos,events=events,missing=missing)),flush=True)
if __name__=='__main__':main()
