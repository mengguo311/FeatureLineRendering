"""Unit012 delivery phases; all numerical work runs serially."""
import runtime
from runtime import OUTPUT_ROOT,js,sha,now
from pathlib import Path
import argparse,json,shutil,subprocess,sys,time
import numpy as np
from PIL import Image
from demo import load_asset,save_frame,new_output
from geometry import orbit_camera
from media import contact

UNIT=OUTPUT_ROOT/'units/unit_012'

def stage():
    previous=OUTPUT_ROOT/'units/unit_011/portable_demo';package=new_output(UNIT/'portable_demo')
    for f in ('run.sh','CATALOG.json','PORTABLE_DEMO.json'):
        shutil.copy2(previous/f,package/f)
    for scene in ('chair','lego','drums','ficus'):
        shutil.copytree(previous/'assets'/scene,package/'assets'/scene)
    metadata=json.loads((package/'PORTABLE_DEMO.json').read_text())
    metadata.update(source_unit='unit_012',created_utc=now(),presentation_exports='PNG / 12-frame orbit / 6-frame zoom, MP4 and verified FFV1, asset/camera replay')
    for key in ('experimental_asset','simplification_decision','previous_package_sha256'):metadata.pop(key,None)
    js(package/'PORTABLE_DEMO.json',metadata)
    refresh()
    (package/'requirements.txt').write_text('numpy\nscipy\nopen3d\nPillow\nimageio-ffmpeg\n')
    (UNIT/'build').mkdir();shutil.copy2(OUTPUT_ROOT/'units/unit_011/build/libsource.so',UNIT/'build/libsource.so')
    js(UNIT/'INPUT_LOCK.json',dict(protocol_sha256=sha(UNIT/'PROTOCOL.json'),assets={scene:{p.name:sha(p) for p in (package/'assets'/scene).iterdir() if p.is_file()} for scene in ('chair','lego','drums','ficus')},
        libsource_sha256=sha(UNIT/'build/libsource.so')))

def refresh():
    source=UNIT/'portable_demo/source';source.mkdir(exist_ok=True)
    for f in Path(__file__).parent.iterdir():
        if f.is_file():shutil.copy2(f,source/f.name)

def source_render(scene):
    import model_adapter
    p=json.loads((UNIT/'PROTOCOL.json').read_text());entry=p['scenes'][scene]
    model_adapter.LIB_PATH=UNIT/'build/libsource.so'
    model=model_adapter.load_source(entry['original']['original_ply'],entry['original']['sha256'])
    folder=new_output(UNIT/'source_model'/scene);camera=orbit_camera(**entry['camera']);start=time.monotonic()
    result=model_adapter.render_source(model,camera)
    Image.fromarray(np.uint8(np.clip(result['rgb'],0,1)*255+.5)).save(folder/'source_rgb.png')
    np.savez_compressed(folder/'source_arrays.npz',**result)
    js(folder/'RECEIPT.json',dict(original=entry['original'],original_gaussians=model['audit']['count'],camera=camera,
        seconds=time.monotonic()-start,adapter='CPU SH3 EWA of unchanged original checkpoint, not GPU equivalence or independent surface truth'))

def review_media():
    browser=UNIT/'browser';items=[];rows=[]
    for scene in ('chair','ficus'):
        state=json.loads((browser/(scene+'_EXPORT_STATE.json')).read_text())
        folder=browser/'session'/Path(state['images']['image'].removeprefix('/image/')).parent
        baseline=UNIT/'baseline'/scene;baseline.mkdir(parents=True)
        mesh,strokes,meta=load_asset(UNIT/'portable_demo/assets'/scene)
        # Baseline display is explicitly matched to the saved edited .35 display.
        meta['display']=state['display']
        save_frame(baseline,'frame_000',mesh,strokes,meta,orbit_camera(**state['camera']))
        items.append((scene.title()+' | original GS RGB',Image.open(UNIT/'source_model'/scene/'source_rgb.png')))
        for label,file in [('Proxy','frame_000_proxy.png'),('Authored regions','frame_000_region_rgb.png')]:items.append((label,Image.open(folder/file)))
        items.append(('Before | middle 95 deg',Image.open(baseline/'frame_000_image.png')))
        items.append(('Exported | middle 45 deg',Image.open(browser/(scene+'_image.png'))))
        with np.load(baseline/'frame_000_arrays.npz') as a,np.load(folder/'frame_000_arrays.npz') as b:
            for k in ('depth','regions','contour','layer_1','layer_3'):np.testing.assert_array_equal(a[k],b[k])
            delta=np.abs(a['image']-b['image']);target=a['regions']==2
            from scipy.ndimage import binary_dilation,binary_erosion
            band=binary_dilation(target,iterations=2)&~binary_erosion(target,iterations=2)
            other=(a['regions']>0)&~target&~band;bg=(a['regions']==0)&~band
            row=dict(scene=scene,target_L1=float(delta[target].sum()),total_L1=float(delta.sum()),
                far_other_L1=float(delta[other].sum()),background_L1=float(delta[bg].sum()),band_L1=float(delta[band].sum()),
                far_changed_yx=np.argwhere((other|bg)&(delta>0)).tolist(),non_target_layers_exact=True)
            assert row['target_L1']>0
        for k in (1,3):assert sha(UNIT/f'portable_demo/assets/{scene}/region_{k}.npz')==sha(Path(state['asset'])/f'region_{k}.npz')
        rows.append(row)
        for kind in ('orbit','zoom'):
            root=browser/(scene+'_'+kind)
            shutil.copy2(root/'contact_sheet.png',UNIT/'media'/(scene+'_'+kind+'_all_frames.png'))
            for suffix in ('mp4','mkv'):shutil.copy2(root/('animation.'+suffix),UNIT/'media'/(scene+'_'+kind+'.'+suffix))
    contact(UNIT/'media/source_proxy_regions_edit.png',items,cols=5,size=512,title='Actual source GS / proxy / authored regions / local edit / browser-exported PNG')
    js(UNIT/'metrics/LOCAL_EDIT.json',dict(frames=rows,scope='Shared proxy labels, fixed2px band; no independent semantic truth',non_target_paths_exact=True))

def replay_all():
    # Every browser ZIP is extracted to a new package-local path then replayed by
    # a new Python process using only that relocated bundle and packaged source.
    import zipfile
    package=UNIT/'portable_demo';reports=[]
    for scene in ('chair','ficus'):
        for kind in ('orbit','zoom'):
            bundle=package/'imports'/(scene+'_'+kind)
            if not bundle.exists():
                with zipfile.ZipFile(UNIT/'browser'/(scene+'_'+kind+'.zip')) as z:z.extractall(bundle)
            output=package/'runs'/(scene+'_'+kind+'_cold')
            completed=UNIT/'logs'/(scene+'_'+kind+'_cold.receipt.json')
            if completed.exists() and (output/'REPLAY.json').exists():
                assert json.loads(completed.read_text())['returncode']==0
                prior=json.loads((output/'REPLAY.json').read_text())
                assert prior['all_png_exact'] and prior['all_arrays_exact']
                expected=json.loads((bundle/'PRESENTATION.json').read_text())['frame_png_sha256']
                assert all(sha(output/f'frame_{i:03d}_image.png')==digest for i,digest in enumerate(expected))
                reports.append(dict(kind=kind,**prior));continue
            cmd=[sys.executable,str(package/'source/catalog_demo.py'),'replay','--catalog',str(package/'CATALOG.json'),
                '--scene',scene,'--bundle',str(bundle),'--output',str(output)]
            start=time.monotonic()
            with (UNIT/'logs'/(scene+'_'+kind+'_cold.log')).open('w') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=240)
            receipt=dict(command=cmd,returncode=r.returncode,seconds=time.monotonic()-start)
            js(UNIT/'logs'/(scene+'_'+kind+'_cold.receipt.json'),receipt);r.check_returncode()
            reports.append(dict(kind=kind,**json.loads((output/'REPLAY.json').read_text())))
    js(UNIT/'metrics/COLD_REPLAY.json',dict(all_png_exact=all(r['all_png_exact'] for r in reports),all_arrays_exact=all(r['all_arrays_exact'] for r in reports),replays=reports))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['stage','refresh','source','media','replay']);p.add_argument('--scene');a=p.parse_args()
    if a.phase=='source':source_render(a.scene)
    else:dict(stage=stage,refresh=refresh,media=review_media,replay=replay_all)[a.phase]()
