"""One frozen Chair middle-region refinement; existing algorithms, new real evidence."""
import runtime
from runtime import OUTPUT_ROOT,js,sha,now,output_guard
from pathlib import Path
import argparse,json,shutil,subprocess,time,sys
import numpy as np
from PIL import Image
from demo import load_asset,new_output,save_frame,edit
from geometry import orbit_camera
from media import contact

U=OUTPUT_ROOT/'units/unit_019'
PREV=OUTPUT_ROOT/'units/unit_018'
SOURCE=Path(__file__).resolve().parent

def hashes(folder):
    return {str(f.relative_to(folder)):sha(f) for f in sorted(folder.rglob('*')) if f.is_file() and '__pycache__' not in f.parts}

def protocol():return json.loads((U/'PROTOCOL.json').read_text())

def command(name,args,expected=0):
    assert not (U/'logs'/f'{name}.receipt.json').exists(),name
    start=time.monotonic();began=now()
    with (U/'logs'/f'{name}.log').open('w') as f:
        result=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,timeout=540)
    receipt=dict(command=args,cwd=str(Path.cwd()),started_utc=began,finished_utc=now(),returncode=result.returncode,
        expected_returncode=expected,seconds=time.monotonic()-start,cpu_affinity=sorted(__import__('os').sched_getaffinity(0)))
    js(U/'logs'/f'{name}.receipt.json',receipt);print(json.dumps(receipt),flush=True)
    if result.returncode!=expected:raise RuntimeError('command failed; original log retained: '+name)

def freeze():
    output_guard(U)
    assert Path.cwd()==SOURCE.parents[1]
    assert subprocess.check_output(['git','branch','--show-current'],text=True).strip()=='partwise-sketch-hatching-models-v04'
    assert not (U/'PROTOCOL.json').exists()
    for name in ('logs','metrics','media'):(U/name).mkdir()
    asset=PREV/'portable_demo/assets/chair';mesh,paths,meta=load_asset(asset)
    assert sha(meta['original']['original_ply'])==meta['original']['sha256']
    p=dict(unit='unit_019',frozen_utc=now(),scene='chair',asset=str(asset),inputs=hashes(asset),original=meta['original'],
        inherited_catalog_inputs={k:hashes(PREV/'portable_demo'/k) for k in ('assets','examples')},
        geometry=meta['geometry'],region=2,region_source=meta['region_provenance'],region_definition=meta['regions']['2'],styles=meta['styles'],
        decision='Test ONE bounded local smoothing of Chair middle height-region using existing tested refinement. Improve the visible surface/path kinks, preserve default and whole object. No new geometry evidence or hypothesis test.',
        critical_previous_review='unit018 images show complete but warped Chair seat hatching and broken thin geometry. Save/import/edit already works. Source shows Chair already received one global bounded refinement; this additional local pass may have modest benefit and cannot repair holes. Original GS reference will be rerendered before candidate.',
        alternatives_ranked=['One local Chair surface revision, all-view visual check and runnable optional asset.',
            'Direction/spacing-only seat style change: defer to separate explicit artistic edit if geometry change is weak.',
            'New models or more archive UI: lower value; four models and cold import already available.'],
        refinement=dict(iterations=10,positive_step=.5,negative_step=-.53,max_displacement=.018),
        fixed='Faces/labels, all non-target incident vertices, open/nonmanifold edges and region boundaries, other path files, styles/renderer/depth tolerance; 512x512/2xAA. No sweep.',
        changed_variable='Only target interior vertex positions; regenerate only region2 fixed 3D hatch paths on revised mesh. Same topology/labels, revisioned target paths. No fill/weld/remesh/GT/GS training.',
        static_camera_values=[dict(azimuth=a,elevation=25,distance=4.7) for a in (17,107,197,287)],
        viewer_camera=dict(azimuth=17,elevation=25,distance=4.7),local_style_probe=dict(region=2,angle=65.),
        motion=dict(orbit_frames=12,zoom_frames=6,fps=6,trajectory='Unchanged presentation.py all-vertex fit from viewer camera; retain every frame.'),
        expected_visual='Some reduction of middle-surface wrinkles without loss of whole-object shape. Report target ink/coverage, path counts/length, all four views and weak sides; lower adjacent-normal roughness is imposed by smoothing, not an accuracy score.',
        checks=['Real original Chair PLY CPU SH3/EWA reference at all four frozen cameras, before candidate.',
            'Real saved Chair asset refinement tests: same labels/faces, exact non-target geometry/paths, bounded displacement, oriented areas, cold saved anchors and continued angle edit.',
            'Four before/after/edit full objects; baseline and union two-pixel masks, actual other-layer/contour changes, coverage and ink. No perfect raster-locality presumption for geometry changes.',
            'Browser select optional asset, angle95->65->undo, save ZIP/PNG/orbit/zoom; stop service and cold import, edit and undo; relocated package CLI and cold replay.'],
        promotion='Default unchanged. Add optional catalog example only if visual review shows at least modest benefit without severe new defects; otherwise keep candidate evidence outside the main catalog.',
        exposure='Previously exposed Chair/proxy; these camera values frozen before candidate but not blind training/geometry holdouts. Region labels authored; no independent geometry or semantic truth.',
        implementation='Existing local_refinement/refine_proxy algorithm unchanged. No new material algorithm behavior, so no artificial TDD-red requirement; run meaningful real-asset contract checks.',
        resource=dict(cpu=2,numeric_threads=1,serial=True,gpu=False,nested_models=False,finish_by_jst='2026-10-22T08:21:49+09:00'))
    js(U/'PROTOCOL.json',p)
    shutil.copy2(U/'PROTOCOL.json',SOURCE.parents[1]/'docs/partwise_sketch_hatching_v04/UNIT019_PROTOCOL.json')
    shutil.copytree(SOURCE,U/'source_before',ignore=shutil.ignore_patterns('__pycache__'))
    js(U/'SOURCE_BEFORE.json',hashes(SOURCE))
    (U/'INHERITED_WORKTREE.diff').write_bytes(subprocess.check_output(['git','diff','--','experiments/partwise_sketch_hatching_v04','docs/partwise_sketch_hatching_v04']))
    js(U/'STATUS.json',dict(stage='PROTOCOL_FROZEN',execution_state='partial',scientific_verdict='H1_H2_H5_NOT_TESTED',
        demo_progress=dict(genuinely_ran_old_model=False,reasoning=p['decision']),artifacts=['PROTOCOL.json'],blockers=[]))
    print(json.dumps(dict(protocol_sha256=sha(U/'PROTOCOL.json'),frozen_utc=p['frozen_utc'])),flush=True)

def reference():
    import model_adapter
    p=protocol();out=new_output(U/'source_model');base=new_output(U/'renders/baseline')
    model_adapter.LIB_PATH=out/'libsource.so';shutil.copy2(PREV/'source_model/libsource.so',model_adapter.LIB_PATH)
    start=time.monotonic();model=model_adapter.load_source(p['original']['original_ply'],p['original']['sha256'])
    mesh,paths,meta=load_asset(p['asset']);items=[];receipts=[]
    for i,values in enumerate(p['static_camera_values']):
        camera=orbit_camera(**values);t=time.monotonic();result=model_adapter.render_source(model,camera)
        Image.fromarray(np.uint8(np.clip(result['rgb'],0,1)*255+.5)).save(out/f'frame_{i:03d}_rgb.png')
        np.savez_compressed(out/f'frame_{i:03d}_arrays.npz',**result)
        row=save_frame(base,f'frame_{i:03d}',mesh,paths,meta,camera);assert row['bounds']['all_proxy_vertices_inside']
        receipts.append(dict(camera=camera,seconds=time.monotonic()-t))
        for title,file in [('Original GS RGB',out/f'frame_{i:03d}_rgb.png'),('Exploratory proxy',base/f'frame_{i:03d}_proxy.png'),
                           ('Authored regions',base/f'frame_{i:03d}_region_rgb.png'),('Saved hatching',base/f'frame_{i:03d}_image.png')]:
            items.append((f"Az {values['azimuth']} | {title}",Image.open(file)))
    contact(U/'media/source_reference_all_views.png',items,cols=4,size=384,title='Chair | actual original checkpoint vs existing proxy | four frozen complete-object views')
    js(out/'RECEIPT.json',dict(original=p['original'],original_gaussians=model['audit']['count'],views=receipts,seconds=time.monotonic()-start,
        adapter='CPU SH3/EWA original vanilla GS; not independent geometry truth or GPU-equivalence evidence',library_sha256=sha(model_adapter.LIB_PATH)))

def candidate():
    from local_refinement import refine_asset
    p=protocol();assert hashes(Path(p['asset']))==p['inputs']
    result=refine_asset(p['asset'],U/'assets/refined',p['region'],p['refinement'])
    js(U/'metrics/REFINEMENT.json',result)
    edit(U/'assets/refined',U/'assets/style_probe',p['region'],dict(angle=p['local_style_probe']['angle']))
    print(json.dumps(result),flush=True)

def static():
    from scipy.ndimage import binary_dilation,binary_erosion,distance_transform_edt
    p=protocol();target=p['region'];rows=[];items=[];proxies=[];crops=[]
    loaded={a:load_asset(U/'assets'/a) for a in ('refined','style_probe')}
    for arm in loaded:new_output(U/'renders'/arm)
    def partition(mask,regions):
        band=binary_dilation(mask,iterations=2)&~binary_erosion(mask,iterations=2)
        result=dict(target_interior=mask&~band,boundary_band=band,far_other=(regions>0)&~mask&~band,far_background=(regions==0)&~band)
        assert np.all(sum(v.astype(int) for v in result.values())==1)
        return result
    def delta(a,b,masks):
        d=np.abs(a['image']-b['image'])
        return {k:dict(pixels=int(m.sum()),L1=float(d[m].sum()),changed_pixels=int((d[m]>0).sum())) for k,m in masks.items()}
    for i,values in enumerate(p['static_camera_values']):
        c=orbit_camera(**values);data={}
        for arm in ('baseline','refined','style_probe'):
            if arm!='baseline':
                row=save_frame(U/'renders'/arm,f'frame_{i:03d}',*loaded[arm],c)
                assert row['bounds']['all_proxy_vertices_inside']
            with np.load(U/f'renders/{arm}/frame_{i:03d}_arrays.npz') as z:data[arm]={k:z[k] for k in z.files}
        a,b,e=(data[k] for k in ('baseline','refined','style_probe'));m0=a['regions']==target;m1=b['regions']==target;union=m0|m1
        non_target=[r for r in loaded['refined'][1] if r!=target]
        unchanged={k:bool(np.array_equal(b[k],e[k])) for k in ['depth','regions','contour']+[f'layer_{r}' for r in non_target]}
        assert all(unchanged.values())
        coverage={}
        for arm,d in data.items():
            mask=d['regions']==target;layer=d[f'layer_{target}'];support=layer>.1
            coverage[arm]=dict(visible_target_pixels=int(mask.sum()),ink=float(layer.sum()),nonzero_pixels=int((layer>0).sum()),
                visible_target_support_pixels=int((support&mask).sum()),visible_target_support_fraction=float((support&mask).sum()/mask.sum()),
                distance_to_hatch_p95_px=float(np.quantile(distance_transform_edt(~support)[mask],.95)),
                whole_object_ink=float((1-d['image']).sum()))
        row=dict(camera=values,baseline_mask=delta(a,b,partition(m0,a['regions'])),union_mask=delta(a,b,partition(union,np.maximum(a['regions'],b['regions']))),
            style_probe=delta(b,e,partition(m1,b['regions'])),style_unchanged_arrays=unchanged,coverage=coverage,
            region_label_changed_pixels=int((a['regions']!=b['regions']).sum()),
            non_target_layer_L1={str(r):float(np.abs(a[f'layer_{r}']-b[f'layer_{r}']).sum()) for r in non_target},
            contour_L1=float(np.abs(a['contour']-b['contour']).sum()))
        rows.append(row)
        ys,xs=np.where(union);box=(max(0,int(xs.min())-10),max(0,int(ys.min())-10),min(512,int(xs.max())+11),min(512,int(ys.max())+11))
        for arm,title in [('baseline','Current default'),('refined','Local middle smoothing'),('style_probe','Smoothed / local angle 65')]:
            image=Image.open(U/f'renders/{arm}/frame_{i:03d}_image.png');items.append((f"Az {values['azimuth']} | {title}",image))
            crops.append((f"Az {values['azimuth']} | {title}",image.crop(box)))
        for arm in ('baseline','refined'):
            for key in ('proxy','region_rgb'):proxies.append((f"Az {values['azimuth']} | {arm} {key}",Image.open(U/f'renders/{arm}/frame_{i:03d}_{key}.png')))
    contact(U/'media/full_object_before_after.png',items,cols=3,size=512,title='Chair | one bounded middle-region geometry change | fixed style, then local angle edit')
    contact(U/'media/proxy_regions_all_views.png',proxies,cols=4,size=384,title='Chair | unchanged topology and authored labels | before and after local smoothing')
    contact(U/'media/middle_detail_supplement.png',crops,cols=3,size=384,title='Supplementary middle-region crops | same crop per camera | full objects also supplied')
    js(U/'metrics/LOCALITY.json',dict(views=rows,scope='Proxy labels, fixed2px band, baseline and union masks. Not independent geometry/semantics. Geometry edits can change other-region visibility; actual effects reported.'))

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='run':command(sys.argv[2],sys.argv[3:])
    else:
        ap=argparse.ArgumentParser();ap.add_argument('phase',choices=['freeze','reference','candidate','static']);a=ap.parse_args();globals()[a.phase]()
