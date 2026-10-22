"""Bounded real Lego bucket style composition; every write belongs to unit014."""
import runtime
from runtime import OUTPUT_ROOT, js, sha, now, output_guard
from pathlib import Path
import argparse, json, shutil, subprocess, time, zipfile
import numpy as np
from PIL import Image
from demo import load_asset, new_output, edit, save_frame
from geometry import orbit_camera
from hatching import layer_ids
from media import contact

UNIT = OUTPUT_ROOT/'units/unit_014'
PREVIOUS = OUTPUT_ROOT/'units/unit_013'
SOURCE = Path(__file__).parent

def protocol():
    return json.loads((UNIT/'PROTOCOL.json').read_text())

def refresh():
    dst=UNIT/'portable_demo/source';dst.mkdir(exist_ok=True)
    names=('runtime.py catalog_demo.py demo.py viewer.py viewer.html scene_catalog.py geometry.py '
           'hatching.py render.py display_settings.py region_tools.py screen_selection.py selection_draft.py '
           'presentation.py media.py').split()
    for name in names:shutil.copy2(SOURCE/name,dst/name)

def freeze():
    output_guard(UNIT)
    assert subprocess.check_output(['git','branch','--show-current'],text=True).strip()=='partwise-sketch-hatching-models-v04'
    assert Path.cwd()==Path('/home/u00134/3dgs_line/partwise_sketch_hatching_models_v04')
    assert not (UNIT/'PROTOCOL.json').exists()
    asset=PREVIOUS/'portable_demo/assets/lego';mesh,paths,meta=load_asset(asset)
    assert sha(meta['original']['original_ply'])==meta['original']['sha256']
    for name in ('logs','metrics','media'):(UNIT/name).mkdir(exist_ok=True)
    p=dict(unit='unit_014',frozen_utc=now(),previous_unit=str(PREVIOUS),scene='lego',asset=str(asset),
        input_files={f.name:sha(f) for f in sorted(asset.iterdir()) if f.is_file()},original=meta['original'],
        geometry=meta['geometry'],regions=meta['regions'],region_provenance=meta['region_provenance'],
        selection=meta['region_history'],styles=meta['styles'],
        decision='Reuse existing 2030-face manually selected bucket region4; validate composed short/sparse/cross controls on second real model. No geometry or selection revision.',
        changed_variable='One authored style preset: bucket spacing .045->.060, length .22->.12; optional second direction offset60/spacing.075. Three states separate shortening/sparsening from adding cross layer; not an H1/H2 or aesthetic comparison.',
        base_edit=dict(spacing=.060,length=.12),
        local_edit=dict(region=4,cross_enabled=True,cross_angle=60.,cross_spacing=.075),
        interaction_probe=dict(cross_angle=75.,cross_spacing=.09),
        display=dict(contours_visible=True,contour_strength=1.),
        static_camera_values=[dict(azimuth=a,elevation=30,distance=5.1) for a in (233,323,53,143)],
        viewer_camera=dict(azimuth=233,elevation=30,distance=5.1),
        motion=dict(orbit_frames=12,zoom_frames=6,fps=6,rule='Existing presentation.py trajectory, 16px fit of all proxy vertices; all frames retained.'),
        fixed='PLY, proxy geometry/labels/selection, region1/2/3 paths and styles, region4 base angle35/plane xz/width1, renderer depth tolerance, 512square/2xAA, contour1.0.',
        expected='Selected bucket changes visibly in multiple whole-object views; other saved regions exact. Short base is intentionally regenerated; adding/toggling cross preserves it. Weak views and nonzero locality residuals are reported.',
        validation=['real Lego composition tests and missing/corrupt selection checks; no new hatch algorithm so no artificial failing test required',
                    'four whole-object three-state images, isolated target layers, disjoint fixed2px proxy-label locality partitions',
                    'fresh CPU SH3 EWA image of original Lego checkpoint, reference/proxy/regions/hatch panel',
                    'actual Firefox controls, undo/reload/model switch, four downloaded files',
                    '12orbit/6zoom, full lossless exact decode and MP4 decode/count; relocated CLI and cold viewer/trajectory replay'],
        exposure='Existing known model and manually selected surfaces; camera values fixed before candidate generation. Not blind holdout, independent geometry truth, or independent part labels.',
        resource=dict(cpu=2,numeric_threads=1,serial=True,gpu=False,nested_models=False,unit_deadline_jst='2026-10-22T07:10:50+09:00'))
    js(UNIT/'PROTOCOL.json',p)
    shutil.copy2(UNIT/'PROTOCOL.json',Path('docs/partwise_sketch_hatching_v04/UNIT014_PROTOCOL.json'))
    shutil.copytree(SOURCE,UNIT/'source_before',ignore=shutil.ignore_patterns('__pycache__'))
    js(UNIT/'SOURCE_BEFORE.json',dict(files={f.name:sha(f) for f in SOURCE.iterdir() if f.is_file()},git_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()))
    (UNIT/'INHERITED_WORKTREE.diff').write_bytes(subprocess.check_output(['git','diff','--','experiments/partwise_sketch_hatching_v04','docs/partwise_sketch_hatching_v04']))
    js(UNIT/'STATUS.json',dict(stage='PROTOCOL_FROZEN',execution_state='partial',scientific_verdict='H1_H2_NOT_TESTED',demo_progress=dict(genuinely_ran_old_model=False,reasoning=p['decision']),artifacts=['PROTOCOL.json'],blockers=[]))
    print(json.dumps(dict(protocol_sha256=sha(UNIT/'PROTOCOL.json'),frozen_utc=p['frozen_utc'])))

def stage():
    package=new_output(UNIT/'portable_demo')
    for name in ('run.sh','CATALOG.json','PORTABLE_DEMO.json','requirements.txt','TESTED_ENVIRONMENT.json'):
        shutil.copy2(PREVIOUS/'portable_demo'/name,package/name)
    shutil.copytree(PREVIOUS/'portable_demo/assets',package/'assets')
    shutil.copytree(PREVIOUS/'portable_demo/examples/chair_cross',package/'examples/chair_cross')
    cat=json.loads((package/'CATALOG.json').read_text());cat['default_scene']='lego';js(package/'CATALOG.json',cat)
    meta=json.loads((package/'PORTABLE_DEMO.json').read_text());meta.update(source_unit='unit_014',created_utc=now(),new_example='Lego manual bucket short cross-hatching');js(package/'PORTABLE_DEMO.json',meta)
    (UNIT/'build').mkdir();shutil.copy2(PREVIOUS/'build/libsource.so',UNIT/'build/libsource.so')
    refresh()
    js(UNIT/'INPUT_LOCK.json',dict(protocol_sha256=sha(UNIT/'PROTOCOL.json'),libsource_sha256=sha(UNIT/'build/libsource.so'),assets={s:{f.name:sha(f) for f in (package/'assets'/s).iterdir() if f.is_file()} for s in ('chair','lego','drums','ficus')}))

def candidate():
    p=protocol();r=p['local_edit']['region'];changes={k:v for k,v in p['local_edit'].items() if k!='region'}
    edit(p['asset'],UNIT/'assets/single',r,p['base_edit'])
    edit(UNIT/'assets/single',UNIT/'assets/cross',r,changes)
    edit(UNIT/'assets/cross',UNIT/'assets/off',r,dict(cross_enabled=False))
    m,orig,j=load_asset(p['asset']);_,base,_=load_asset(UNIT/'assets/single');_,after,_=load_asset(UNIT/'assets/cross')
    mask=layer_ids(after[r])==0
    assert all(np.array_equal(after[r][k][mask],v) for k,v in base[r].items())
    assert not np.array_equal(orig[r]['points'],base[r]['points'])
    others=sorted(set(orig)-{r})
    for arm in ('single','cross','off'):
        for name in ['mesh.npz','selection_4.npz']+[f'region_{x}.npz' for x in others]:
            assert sha(Path(p['asset'])/name)==sha(UNIT/'assets'/arm/name)
    assert sha(UNIT/'assets/cross/region_4.npz')==sha(UNIT/'assets/off/region_4.npz')
    def stats(data):
        result={}
        for k in np.unique(layer_ids(data)):
            take=layer_ids(data)==k;ids=data['stroke_id'][take];lengths=np.linalg.norm(np.diff(data['points'][take],axis=1),axis=2).ravel()
            _,idx=np.unique(ids,return_inverse=True);path_lengths=np.bincount(idx,weights=lengths)
            result[str(k)]=dict(segments=int(take.sum()),paths=len(path_lengths),length_world=float(lengths.sum()),max_path_length=float(path_lengths.max()),median_path_length=float(np.median(path_lengths)))
        return result
    js(UNIT/'metrics/PATHS.json',dict(scene='lego',target_region=r,selected_faces=int((m['regions']==r).sum()),geometry_faces=len(m['faces']),geometry_vertices=len(m['vertices']),
        original=stats(orig[r]),single=stats(base[r]),cross=stats(after[r]),base_arrays_exact_after_cross=True,non_target_files_exact=True,mesh_and_selection_exact=True,toggle_path_bytes_exact=True,
        identities='Proxy face IDs; base/cross path coordinates revisioned on short preset, not Gaussian source indices. No unchanged target ID coordinates claim relative to original.'))

def source():
    import model_adapter
    p=protocol();model_adapter.LIB_PATH=UNIT/'build/libsource.so'
    start=time.monotonic();model=model_adapter.load_source(p['original']['original_ply'],p['original']['sha256'])
    folder=new_output(UNIT/'source_model');camera=orbit_camera(**p['viewer_camera']);result=model_adapter.render_source(model,camera)
    Image.fromarray(np.uint8(np.clip(result['rgb'],0,1)*255+.5)).save(folder/'source_rgb.png')
    np.savez_compressed(folder/'source_arrays.npz',**result)
    js(folder/'RECEIPT.json',dict(original=p['original'],original_gaussians=model['audit']['count'],camera=camera,seconds=time.monotonic()-start,
        adapter='CPU SH3 EWA of unchanged original GS; no independent geometry or GPU-equivalence claim'))

def static():
    from scipy.ndimage import binary_dilation,binary_erosion
    p=protocol();r=p['local_edit']['region'];loaded={a:load_asset(Path(p['asset']) if a=='baseline' else UNIT/'assets'/a) for a in ('baseline','single','cross')}
    rows=[];items=[];layers=[]
    for arm in loaded:(UNIT/'renders'/arm).mkdir(parents=True)
    for i,values in enumerate(p['static_camera_values']):
        c=orbit_camera(**values)
        for arm,(mesh,paths,meta) in loaded.items():
            record=save_frame(UNIT/'renders'/arm,f'frame_{i:03d}',mesh,paths,meta,c)
            assert record['bounds']['all_proxy_vertices_inside']
        data={}
        for arm in loaded:
            with np.load(UNIT/f'renders/{arm}/frame_{i:03d}_arrays.npz') as z:data[arm]={k:z[k] for k in z.files}
        for arm in ('single','cross'):
            for key in ('depth','regions','contour','layer_1','layer_2','layer_3'):np.testing.assert_array_equal(data['baseline'][key],data[arm][key])
        np.testing.assert_array_equal(data['single']['layer_4'],data['cross']['stroke_layer_4_0'])
        target=data['baseline']['regions']==r
        band=binary_dilation(target,iterations=2)&~binary_erosion(target,iterations=2)
        masks=dict(target_interior=target&~band,boundary_band=band,far_other=(data['baseline']['regions']>0)&~target&~band,far_background=(data['baseline']['regions']==0)&~band)
        assert np.all(sum(v.astype(int) for v in masks.values())==1)
        comparisons={}
        for before,after in [('baseline','single'),('single','cross'),('baseline','cross')]:
            delta=np.abs(data[before]['image']-data[after]['image'])
            comparisons[before+'_to_'+after]=dict(total_L1=float(delta.sum()),target_L1=float(delta[target].sum()),
                masks={key:dict(pixels=int(mask.sum()),L1=float(delta[mask].sum()),changed_pixels=int((delta[mask]>0).sum())) for key,mask in masks.items()})
        base=data['cross']['stroke_layer_4_0'];cross=data['cross']['stroke_layer_4_1']
        rows.append(dict(camera=values,target_visible_pixels=int(target.sum()),comparisons=comparisons,
            total_ink={a:float((1-d['image']).sum()) for a,d in data.items()},
            base_ink=float(base.sum()),cross_ink=float(cross.sum()),both_layers_supported_pixels=int(((base>0)&(cross>0)).sum()),
            non_target_layers_exact=True,short_base_layer_exact_after_cross=True))
        for arm,title in [('baseline','Original single'),('single','Short / sparse single'),('cross','Short cross')]:
            items.append((f"Az {values['azimuth']} | {title}",Image.open(UNIT/f'renders/{arm}/frame_{i:03d}_image.png')))
        for name,array in [('base_layer',1-base),('cross_layer',1-cross)]:
            file=UNIT/f'renders/cross/frame_{i:03d}_{name}.png';Image.fromarray(np.uint8(np.clip(array,0,1)*255+.5)).save(file)
            layers.append((f"Az {values['azimuth']} | {name}",Image.open(file)))
    assert any(row['comparisons']['single_to_cross']['target_L1']>1 for row in rows)
    contact(UNIT/'media/local_edit_all_views.png',items,cols=3,size=512,title='Lego | manual bucket region4 only | original, short single, short cross | all frozen views')
    contact(UNIT/'media/isolated_layers_all_views.png',layers,cols=2,size=512,title='Lego | isolated saved bucket directions | weak views retained')
    source_items=[('Actual original GS RGB',Image.open(UNIT/'source_model/source_rgb.png'))]
    for title,arm,key in [('Model-derived proxy','baseline','proxy'),('Authored regions / bucket','baseline','region_rgb'),('Original single','baseline','image'),('Short cross','cross','image')]:
        source_items.append((title,Image.open(UNIT/f'renders/{arm}/frame_000_{key}.png')))
    contact(UNIT/'media/source_proxy_regions_edit.png',source_items,cols=5,size=512,title='Lego | unchanged learned-model proxy and manual faces | bucket length .12, spacing .060, cross +60/.075')
    js(UNIT/'metrics/LOCAL_EDIT.json',dict(frames=rows,scope='Proxy-label masks; fixed2px disjoint band/interior/other/background. Descriptive ink, no independent semantics or tone-matched aesthetic conclusion.'))

def import_browser():
    browser=UNIT/'browser';package=UNIT/'portable_demo'
    assert json.loads((browser/'BROWSER_VALIDATION.json').read_text())['status']=='PASS'
    for kind in ('orbit','zoom'):
        bundle=package/'presentations'/('lego_bucket_'+kind)
        with zipfile.ZipFile(browser/('lego_'+kind+'.zip')) as z:z.extractall(bundle)
        receipt=json.loads((bundle/'PRESENTATION.json').read_text());assert receipt['all_proxy_vertices_inside']
        shutil.copy2(bundle/'contact_sheet.png',UNIT/'media'/('lego_'+kind+'_all_frames.png'))
        for suffix in ('mp4','mkv'):shutil.copy2(bundle/('animation.'+suffix),UNIT/'media'/('lego_'+kind+'.'+suffix))
    with zipfile.ZipFile(browser/'lego_asset.zip') as z:z.extractall(package/'examples/lego_bucket_cross')
    refresh()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['freeze','stage','refresh','candidate','source','static','import']);a=p.parse_args()
    {'freeze':freeze,'stage':stage,'refresh':refresh,'candidate':candidate,'source':source,'static':static,'import':import_browser}[a.phase]()
