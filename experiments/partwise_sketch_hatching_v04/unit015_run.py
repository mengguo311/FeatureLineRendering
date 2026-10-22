"""One frozen Lego local proxy refinement; all new evidence stays in unit015."""
import runtime
from runtime import OUTPUT_ROOT, js, sha, now, output_guard
from pathlib import Path
import argparse, json, shutil, subprocess, time
import numpy as np
from PIL import Image
from demo import load_asset, new_output, save_frame
from geometry import orbit_camera
from media import contact

UNIT = OUTPUT_ROOT/'units/unit_015'
PREVIOUS = OUTPUT_ROOT/'units/unit_014'
SOURCE = Path(__file__).parent

def protocol():
    return json.loads((UNIT/'PROTOCOL.json').read_text())

def freeze():
    output_guard(UNIT)
    assert Path.cwd()==Path('/home/u00134/3dgs_line/partwise_sketch_hatching_models_v04')
    assert subprocess.check_output(['git','branch','--show-current'],text=True).strip()=='partwise-sketch-hatching-models-v04'
    assert not (UNIT/'PROTOCOL.json').exists()
    asset=PREVIOUS/'portable_demo/examples/lego_bucket_cross'
    mesh,_,meta=load_asset(asset)
    assert sha(meta['original']['original_ply'])==meta['original']['sha256']
    for name in ('logs','metrics','media'):(UNIT/name).mkdir(exist_ok=True)
    p=dict(unit='unit_015',frozen_utc=now(),previous_unit=str(PREVIOUS),scene='lego',asset=str(asset),
        inputs={f.name:sha(f) for f in sorted(asset.iterdir()) if f.is_file()},original=meta['original'],
        geometry=meta['geometry'],region=4,region_source=meta['region_history'],styles=meta['styles'],
        decision='One bounded topology-preserving smoothing of the existing manual bucket region. Keep the working original; deliver a separately versioned candidate with honest visual limitations.',
        refinement=dict(iterations=10,positive_step=.5,negative_step=-.53,max_displacement=.018),
        fixed='All faces/labels/selection; all vertices incident to non-target faces, open/nonmanifold edges and region boundaries; all other path files; hatch styles; renderer depth tolerance; 512x512/2xAA/contour1.',
        changed='Interior target vertex positions via existing adjacency-based positive/negative smoothing; target base and cached cross paths regenerated on revised mesh. No filling/welding/remeshing, parameter sweep, semantics change or source-checkpoint change.',
        static_camera_values=[dict(azimuth=a,elevation=30,distance=5.1) for a in (233,323,53,143)],
        viewer_camera=dict(azimuth=233,elevation=30,distance=5.1),
        local_style_probe=dict(region=4,angle=50.),
        motion=dict(orbit_frames=12,zoom_frames=6,fps=6,trajectory='Existing presentation.py, origin-facing with all-vertex fit, frozen before candidate; no frame exclusions.'),
        expected='Reduced bucket surface roughness and line bends without disappearing coverage or obvious lost shape. Four full-object before/after views and all weak views retained. Smoothing/roughness are not independent geometry evidence.',
        checks=['Real-asset TDD: local geometry/path revision, non-target byte preservation, stable labels, bounded displacement and oriented-area guards; arbitrary region-ID support.',
                'Per-region path length/count, target mesh adjacent-normal change, fixed two-pixel locality bands from baseline and separately union masks; report occlusion/contour changes, never presume pixel locality for geometry edits.',
                'Fresh CPU original-checkpoint render; complete object before/after/proxy/region panels, useful crop supplementary only.',
                'Selected-part style edit on candidate, saved-path cold reload and relocated CLI/viewer; orbit/zoom exports and full video decode; finite motion evidence only.'],
        promotion='Candidate remains an opt-in example. Original defaults stay unchanged even if proxy-relative roughness falls; no scientific seal prerequisite.',
        exposure='Same exposed real Lego and three authored selection views; evaluation camera values frozen before candidate. No blind holdout, independent semantic labels or geometric truth.',
        resource=dict(cpu=2,numeric_threads=1,serial=True,gpu=False,nested_models=False,unit_deadline_jst='2026-10-22T07:26:57+09:00'))
    js(UNIT/'PROTOCOL.json',p)
    shutil.copy2(UNIT/'PROTOCOL.json',Path('docs/partwise_sketch_hatching_v04/UNIT015_PROTOCOL.json'))
    shutil.copytree(SOURCE,UNIT/'source_before',ignore=shutil.ignore_patterns('__pycache__'))
    js(UNIT/'SOURCE_BEFORE.json',dict(files={f.name:sha(f) for f in SOURCE.iterdir() if f.is_file()},git_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()))
    (UNIT/'INHERITED_WORKTREE.diff').write_bytes(subprocess.check_output(['git','diff','--','experiments/partwise_sketch_hatching_v04','docs/partwise_sketch_hatching_v04']))
    js(UNIT/'STATUS.json',dict(stage='PROTOCOL_FROZEN',execution_state='partial',scientific_verdict='H1_H2_H5_NOT_TESTED',demo_progress=dict(genuinely_ran_old_model=False,reasoning=p['decision']),artifacts=['PROTOCOL.json'],blockers=[]))
    print(json.dumps(dict(protocol_sha256=sha(UNIT/'PROTOCOL.json'),frozen_utc=p['frozen_utc'])))

def candidate():
    from local_refinement import refine_asset
    p=protocol()
    assert {f.name:sha(f) for f in Path(p['asset']).iterdir() if f.is_file()}==p['inputs']
    result=refine_asset(p['asset'],UNIT/'assets/refined',p['region'],p['refinement'])
    js(UNIT/'metrics/REFINEMENT.json',result)
    print(json.dumps(result),flush=True)

def source():
    import model_adapter
    p=protocol();folder=new_output(UNIT/'source_model');(UNIT/'build').mkdir(exist_ok=True)
    shutil.copy2(PREVIOUS/'build/libsource.so',UNIT/'build/libsource.so')
    model_adapter.LIB_PATH=UNIT/'build/libsource.so'
    start=time.monotonic();model=model_adapter.load_source(p['original']['original_ply'],p['original']['sha256'])
    values=p['viewer_camera'];camera=orbit_camera(**values)
    result=model_adapter.render_source(model,camera)
    Image.fromarray(np.uint8(np.clip(result['rgb'],0,1)*255+.5)).save(folder/'source_rgb.png')
    np.savez_compressed(folder/'source_arrays.npz',**result)
    js(folder/'RECEIPT.json',dict(original=p['original'],original_gaussians=model['audit']['count'],camera=camera,seconds=time.monotonic()-start,
        adapter='CPU SH3 EWA of unchanged original GS, no independent geometry or GPU-equivalence claim',libsource_sha256=sha(model_adapter.LIB_PATH)))

def static():
    from scipy.ndimage import binary_dilation,binary_erosion
    from demo import edit
    p=protocol();target=p['region']
    edit(UNIT/'assets/refined',UNIT/'assets/style_probe',target,dict(angle=p['local_style_probe']['angle']))
    loaded={a:load_asset(Path(p['asset']) if a=='baseline' else UNIT/'assets'/a) for a in ('baseline','refined','style_probe')}
    for arm in loaded:(UNIT/'renders'/arm).mkdir(parents=True)
    items=[];proxy_items=[];crops=[];rows=[]
    for i,values in enumerate(p['static_camera_values']):
        c=orbit_camera(**values)
        data={}
        for arm,(mesh,paths,meta) in loaded.items():
            row=save_frame(UNIT/'renders'/arm,f'frame_{i:03d}',mesh,paths,meta,c)
            assert row['bounds']['all_proxy_vertices_inside']
            with np.load(UNIT/f'renders/{arm}/frame_{i:03d}_arrays.npz') as z:data[arm]={k:z[k] for k in z.files}
        base=data['baseline'];after=data['refined'];edited=data['style_probe']
        def partition(target_mask,regions):
            band=binary_dilation(target_mask,iterations=2)&~binary_erosion(target_mask,iterations=2)
            masks=dict(target_interior=target_mask&~band,boundary_band=band,
                far_other=(regions>0)&~target_mask&~band,far_background=(regions==0)&~band)
            assert np.all(sum(v.astype(int) for v in masks.values())==1)
            return masks
        def delta_rows(a,b,masks):
            delta=np.abs(a['image']-b['image'])
            return {k:dict(pixels=int(m.sum()),L1=float(delta[m].sum()),changed_pixels=int((delta[m]>0).sum())) for k,m in masks.items()}
        mask0=base['regions']==target;mask1=after['regions']==target;union=mask0|mask1
        per_view=dict(camera=values,baseline_mask=delta_rows(base,after,partition(mask0,base['regions'])),
            union_mask=delta_rows(base,after,partition(union,np.maximum(base['regions'],after['regions']))),
            style_probe=delta_rows(after,edited,partition(mask1,after['regions'])),
            region_label_changed_pixels=int((base['regions']!=after['regions']).sum()),
            non_target_layer_L1={str(r):float(np.abs(base[f'layer_{r}']-after[f'layer_{r}']).sum()) for r in (1,2,3)},
            contour_L1=float(np.abs(base['contour']-after['contour']).sum()),
            target_visible_pixels=dict(baseline=int(mask0.sum()),refined=int(mask1.sum())),
            target_layer_ink={a:float(d['layer_4'].sum()) for a,d in data.items()},
            whole_object_ink={a:float((1-d['image']).sum()) for a,d in data.items()})
        for key in ('depth','regions','contour','layer_1','layer_2','layer_3'):
            np.testing.assert_array_equal(after[key],edited[key])
        rows.append(per_view)
        ys,xs=np.where(union);box=(max(0,int(xs.min())-12),max(0,int(ys.min())-12),min(512,int(xs.max())+13),min(512,int(ys.max())+13))
        for arm,title in [('baseline','Original proxy / cross'),('refined','Bounded bucket refinement'),('style_probe','Refined / local angle 50')]:
            image=Image.open(UNIT/f'renders/{arm}/frame_{i:03d}_image.png')
            items.append((f"Az {values['azimuth']} | {title}",image))
            crops.append((f"Az {values['azimuth']} | {title}",image.crop(box)))
        for arm in ('baseline','refined'):
            for key in ('proxy','region_rgb'):
                proxy_items.append((f"Az {values['azimuth']} | {arm} {key}",Image.open(UNIT/f'renders/{arm}/frame_{i:03d}_{key}.png')))
    contact(UNIT/'media/full_object_before_after.png',items,cols=3,size=512,title='Lego | one frozen local geometry revision | same style, then local edit | all views')
    contact(UNIT/'media/proxy_regions_all_views.png',proxy_items,cols=4,size=384,title='Lego | unchanged labels and topology | original and locally refined proxy')
    contact(UNIT/'media/bucket_detail_supplement.png',crops,cols=3,size=384,title='Supplementary bucket crops | same crop per view | full objects provided separately')
    panel=[('Actual original GS RGB',Image.open(UNIT/'source_model/source_rgb.png'))]
    for arm,key,title in [('baseline','proxy','Original proxy'),('refined','proxy','Refined bucket proxy'),('refined','region_rgb','Saved manual regions'),('baseline','image','Original cross'),('refined','image','Refined cross')]:
        panel.append((title,Image.open(UNIT/f'renders/{arm}/frame_000_{key}.png')))
    contact(UNIT/'media/source_proxy_regions_edit.png',panel,cols=3,size=512,title='Lego | original learned checkpoint and bounded exploratory proxy revision')
    js(UNIT/'metrics/LOCALITY.json',dict(views=rows,scope='Descriptive proxy-label masks, fixed2px band; geometry can change visibility. Baseline and union masks both reported. Not independent semantics or geometry.'))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['freeze','candidate','source','static']);a=parser.parse_args()
    globals()[a.phase]()
