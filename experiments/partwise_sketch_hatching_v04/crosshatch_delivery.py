"""Unit013 real-model execution and portable delivery, one serial phase at a time."""
import runtime
from runtime import OUTPUT_ROOT,js,sha,now,output_guard
from pathlib import Path
import argparse,json,shutil,time,sys,subprocess,zipfile
import numpy as np
from PIL import Image
from demo import load_asset,save_frame,new_output,edit
from geometry import orbit_camera
from hatching import layer_ids
from media import contact

UNIT=OUTPUT_ROOT/'units/unit_013'
PREVIOUS=OUTPUT_ROOT/'units/unit_012'
def protocol():return json.loads((UNIT/'PROTOCOL.json').read_text())

def stage():
    package=new_output(UNIT/'portable_demo')
    for name in ('run.sh','CATALOG.json','PORTABLE_DEMO.json','requirements.txt','TESTED_ENVIRONMENT.json'):
        shutil.copy2(PREVIOUS/'portable_demo'/name,package/name)
    for scene in ('chair','lego','drums','ficus'):
        shutil.copytree(PREVIOUS/'portable_demo/assets'/scene,package/'assets'/scene)
    meta=json.loads((package/'PORTABLE_DEMO.json').read_text())
    meta.update(source_unit='unit_013',created_utc=now(),cross_hatching='Optional saved second layer per region; default off, actual Chair demonstration included.')
    js(package/'PORTABLE_DEMO.json',meta)
    (UNIT/'build').mkdir();shutil.copy2(PREVIOUS/'build/libsource.so',UNIT/'build/libsource.so')
    js(UNIT/'INPUT_LOCK.json',dict(protocol_sha256=sha(UNIT/'PROTOCOL.json'),
        assets={scene:{p.name:sha(p) for p in (package/'assets'/scene).iterdir() if p.is_file()} for scene in ('chair','lego','drums','ficus')},
        libsource_sha256=sha(UNIT/'build/libsource.so')))
    refresh()

def refresh():
    source=UNIT/'portable_demo/source';source.mkdir(exist_ok=True)
    names=set(('runtime.py catalog_demo.py demo.py viewer.py viewer.html scene_catalog.py geometry.py '
               'hatching.py render.py display_settings.py region_tools.py screen_selection.py selection_draft.py '
               'presentation.py media.py').split())
    # Only runtime modules are distributed; full experimental source lives in the unit snapshot.
    for file in source.iterdir():
        if file.is_file() and file.name not in names:file.unlink()
    for file in Path(__file__).parent.iterdir():
        if file.is_file() and file.name in names:shutil.copy2(file,source/file.name)

def candidate():
    p=protocol();changes=dict(p['local_edit']);region=changes.pop('region')
    edit(p['asset'],UNIT/'assets/cross',region,changes)
    edit(UNIT/'assets/cross',UNIT/'assets/off',region,dict(cross_enabled=False))
    before=load_asset(p['asset']);after=load_asset(UNIT/'assets/cross')
    original=before[1][region];layer=after[1][region];mask=layer_ids(layer)==0
    exact=all(np.array_equal(layer[k][mask],v) for k,v in original.items());assert exact
    assert sha(p['asset']+'/mesh.npz')==sha(UNIT/'assets/cross/mesh.npz')
    assert all(sha(Path(p['asset'])/f'region_{r}.npz')==sha(UNIT/f'assets/cross/region_{r}.npz') for r in (1,3))
    counts={str(k):dict(segments=int((layer_ids(layer)==k).sum()),paths=len(np.unique(layer['stroke_id'][layer_ids(layer)==k])),
        length_world=float(np.linalg.norm(np.diff(layer['points'][layer_ids(layer)==k],axis=1),axis=2).sum())) for k in (0,1)}
    js(UNIT/'metrics/PATHS.json',dict(scene='chair',base_arrays_exact=exact,non_target_files_exact=True,mesh_file_exact=True,
        toggle_path_bytes_exact=sha(UNIT/'assets/cross/region_2.npz')==sha(UNIT/'assets/off/region_2.npz'),layers=counts,
        geometry_faces=len(after[0]['faces']),geometry_vertices=len(after[0]['vertices']),
        identities='base original IDs; cross region*1e9+500000000+local path number; face IDs are proxy IDs only'))

def source():
    import model_adapter
    p=protocol();model_adapter.LIB_PATH=UNIT/'build/libsource.so'
    model=model_adapter.load_source(p['original']['original_ply'],p['original']['sha256'])
    folder=new_output(UNIT/'source_model');camera=orbit_camera(**p['viewer_camera']);start=time.monotonic()
    result=model_adapter.render_source(model,camera)
    Image.fromarray(np.uint8(np.clip(result['rgb'],0,1)*255+.5)).save(folder/'source_rgb.png')
    np.savez_compressed(folder/'source_arrays.npz',**result)
    js(folder/'RECEIPT.json',dict(original=p['original'],original_gaussians=model['audit']['count'],camera=camera,
        seconds=time.monotonic()-start,adapter='CPU SH3 EWA from original unchanged GS checkpoint; no GPU-equivalence or independent geometry claim'))

def static():
    from scipy.ndimage import binary_dilation,binary_erosion
    p=protocol();rows=[];items=[]
    assets={'baseline':Path(p['asset']),'cross':UNIT/'assets/cross'}
    loaded={name:load_asset(a) for name,a in assets.items()}
    for name in assets:(UNIT/'renders'/name).mkdir(parents=True)
    for i,values in enumerate(p['static_camera_values']):
        c=orbit_camera(**values)
        for name,(mesh,paths,meta) in loaded.items():
            row=save_frame(UNIT/'renders'/name,f'frame_{i:03d}',mesh,paths,meta,c)
            assert row['bounds']['all_proxy_vertices_inside']
        with np.load(UNIT/f'renders/baseline/frame_{i:03d}_arrays.npz') as a,np.load(UNIT/f'renders/cross/frame_{i:03d}_arrays.npz') as b:
            for k in ('depth','regions','contour','layer_1','layer_3'):np.testing.assert_array_equal(a[k],b[k])
            np.testing.assert_array_equal(a['layer_2'],b['stroke_layer_2_0'])
            delta=a['image']-b['image'];assert delta.min()>=-1e-7
            target=a['regions']==2
            band=binary_dilation(target,iterations=2)&~binary_erosion(target,iterations=2)
            core=target&~band;other=(a['regions']>0)&~target&~band;bg=(a['regions']==0)&~band
            masks=dict(target_interior=core,boundary_band=band,far_other=other,far_background=bg)
            assert sum(mask.astype(int) for mask in masks.values()).min()==1
            assert sum(mask.astype(int) for mask in masks.values()).max()==1
            base=b['stroke_layer_2_0'];cross=b['stroke_layer_2_1']
            row=dict(camera=values,total_L1=float(delta.sum()),target_L1=float(delta[target].sum()),
                masks={key:dict(pixels=int(mask.sum()),L1=float(delta[mask].sum())) for key,mask in masks.items()},
                baseline_total_ink=float((1-a['image']).sum()),cross_total_ink=float((1-b['image']).sum()),
                base_layer_ink=float(base.sum()),cross_layer_ink=float(cross.sum()),
                target_union_ink=float(b['layer_2'].sum()),target_visible_pixels=int(target.sum()),
                cross_supported_pixels=int((cross>0).sum()),
                both_layers_supported_pixels=int(((base>0)&(cross>0)).sum()),
                base_layer_exact=True,non_target_layers_exact=True,
                far_changed_yx=np.argwhere((other|bg)&(delta>0)).tolist())
            assert row['target_L1']>0 and row['cross_layer_ink']>0
            rows.append(row)
            for key,array in [('base_layer',1-base),('cross_layer',1-cross),('change',1-delta)]:
                Image.fromarray(np.uint8(np.clip(array,0,1)*255+.5)).save(UNIT/f'renders/cross/frame_{i:03d}_{key}.png')
        for name,key,title in [('baseline','image','Before'),('cross','image','Cross layer on'),('cross','base_layer','Base retained'),('cross','cross_layer','Added layer only')]:
            items.append((f"Az {values['azimuth']} | {title}",Image.open(UNIT/f'renders/{name}/frame_{i:03d}_{key}.png')))
    contact(UNIT/'media/local_edit_all_views.png',items,cols=4,size=512,title='Chair | frozen cameras | middle region second direction only | all views')
    sourceitems=[('Actual original GS RGB',Image.open(UNIT/'source_model/source_rgb.png'))]
    for label,arm,key in [('Model-derived proxy','baseline','proxy'),('Authored height regions','baseline','region_rgb'),('Before: single layer','baseline','image'),('After: optional cross layer','cross','image')]:
        sourceitems.append((label,Image.open(UNIT/f'renders/{arm}/frame_000_{key}.png')))
    contact(UNIT/'media/source_proxy_regions_edit.png',sourceitems,cols=5,size=512,title='Chair | unchanged geometry and base paths | 60 degree plane offset, 0.060 spacing')
    js(UNIT/'metrics/LOCAL_EDIT.json',dict(frames=rows,scope='Proxy-label masks, not independent semantic truth; disjoint interior/band/other/background; fixed2px band; actual float32 raster differences.',
        ink_note='Increased ink is the intended style control, not calibrated tone or geometry/aesthetic gain. Low-resolution layer overlap is descriptive, not subpixel crossing length.'))

def import_browser():
    browser=UNIT/'browser';package=UNIT/'portable_demo'
    report=json.loads((browser/'BROWSER_VALIDATION.json').read_text());assert report['status']=='PASS'
    for kind in ('orbit','zoom'):
        bundle=package/'presentations'/('chair_cross_'+kind)
        with zipfile.ZipFile(browser/('chair_'+kind+'.zip')) as archive:archive.extractall(bundle)
        record=json.loads((bundle/'PRESENTATION.json').read_text())
        assert record['all_proxy_vertices_inside']
        shutil.copy2(bundle/'contact_sheet.png',UNIT/'media'/('chair_'+kind+'_all_frames.png'))
        for suffix in ('mp4','mkv'):shutil.copy2(bundle/('animation.'+suffix),UNIT/'media'/('chair_'+kind+'.'+suffix))
    with zipfile.ZipFile(browser/'chair_asset.zip') as archive:archive.extractall(package/'examples/chair_cross')
    refresh()

def legacy():
    old=PREVIOUS/'baseline/chair'
    record=json.loads((old/'frame_000.json').read_text())
    mesh,paths,meta=load_asset(protocol()['asset']);meta['display']=record['display']
    folder=new_output(UNIT/'renders/legacy_chair')
    save_frame(folder,'frame_000',mesh,paths,meta,record['camera'])
    png=sha(folder/'frame_000_image.png')==sha(old/'frame_000_image.png')
    with np.load(folder/'frame_000_arrays.npz') as a,np.load(old/'frame_000_arrays.npz') as b:
        arrays=set(a.files)==set(b.files) and all(np.array_equal(a[k],b[k]) for k in a.files)
    assert png and arrays
    js(UNIT/'metrics/LEGACY_COMPATIBILITY.json',dict(scene='chair',previous_frame=str(old),PNG_exact=png,all_arrays_exact=arrays,
        scope='One inherited unit012 legacy asset/frame without a cross layer; same saved camera and display.'))

def replay(kind):
    package=UNIT/'portable_demo';bundle=package/'presentations'/('chair_cross_'+kind)
    output=package/'runs'/('cold_'+kind)
    command=[str(package/'run.sh'),'replay','--scene','chair','--bundle',str(bundle),'--output',str(output)]
    # run_logged owns this phase's process group. Direct subprocess is serial and bounded.
    start=time.monotonic();result=subprocess.run(command,timeout=240)
    js(UNIT/'metrics'/('COLD_'+kind.upper()+'.json'),dict(command=command,returncode=result.returncode,seconds=time.monotonic()-start))
    result.check_returncode()
    check=json.loads((output/'REPLAY.json').read_text());assert check['all_png_exact'] and check['all_arrays_exact']

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['stage','refresh','candidate','source','static','import','replay','legacy']);p.add_argument('--kind',choices=['orbit','zoom']);a=p.parse_args()
    if a.phase=='replay':replay(a.kind)
    else:{'stage':stage,'refresh':refresh,'candidate':candidate,'source':source,'static':static,'import':import_browser,'legacy':legacy}[a.phase]()
