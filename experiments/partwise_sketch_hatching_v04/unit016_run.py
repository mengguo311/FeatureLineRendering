"""One frozen regional ink edit on the existing real Lego demo."""
import runtime
from runtime import OUTPUT_ROOT, js, sha, now, output_guard
from pathlib import Path
import argparse, json, shutil, subprocess
import numpy as np
from PIL import Image
from demo import load_asset, edit, new_output, save_frame
from geometry import orbit_camera
from media import contact

UNIT = OUTPUT_ROOT/'units/unit_016'
PREVIOUS = OUTPUT_ROOT/'units/unit_015'
SOURCE = Path(__file__).parent

def protocol():
    return json.loads((UNIT/'PROTOCOL.json').read_text())

def freeze():
    output_guard(UNIT)
    assert Path.cwd()==Path('/home/u00134/3dgs_line/partwise_sketch_hatching_models_v04')
    assert subprocess.check_output(['git','branch','--show-current'],text=True).strip()=='partwise-sketch-hatching-models-v04'
    assert not (UNIT/'PROTOCOL.json').exists()
    asset=PREVIOUS/'portable_demo/examples/lego_bucket_refined'
    _,_,meta=load_asset(asset)
    assert sha(meta['original']['original_ply'])==meta['original']['sha256']
    for name in ('logs','metrics','media'):(UNIT/name).mkdir(exist_ok=True)
    p=dict(unit='unit_016',frozen_utc=now(),scene='lego',asset=str(asset),
        inputs={f.name:sha(f) for f in sorted(asset.iterdir()) if f.is_file()},original=meta['original'],
        geometry=meta['geometry'],geometry_history=meta.get('geometry_history'),
        region=1,region_source=meta['region_provenance'],region_rule=meta.get('region_rule'),
        manual_region_history=meta.get('region_history'),styles=meta['styles'],
        change=dict(ink_strength=.40),legacy_ink_strength=.80,
        decision='Add local ink-strength control to the working model demo; one platform candidate. No geometric or path change.',
        fixed='All mesh/selection/path bytes and IDs, style parameters except region1 ink, proxy visibility/contours, 512 square/2xAA.',
        expected='Platform hatch becomes lighter and vehicle reads more prominently. Geometry noise remains; contours intentionally keep their original strength. Ink reduction is an artistic control, not equal-ink quality or reconstruction improvement.',
        static_camera_values=[dict(azimuth=a,elevation=30,distance=5.1) for a in (248,338,68,158)],
        viewer_camera=dict(azimuth=-112,elevation=30,distance=5.1),
        motion=dict(orbit_frames=12,zoom_frames=6,fps=6,trajectory='Existing presentation.py all-vertex fit; all frames retained.'),
        checks=['Real-asset TDD: legacy .80 exact, .40 halves target layer ink with all geometry/path bytes unchanged; cross-layer shared strength, zero/restore, invalid input rejection.',
                'Four complete-object views; layer ink and nonzero coverage; fixed2px proxy-label locality masks; original GS/reference and weak views.',
                'Actual browser region control, save, undo, refresh, PNG/asset/orbit/zoom downloads; serial cold replay and relocated documented CLI/viewer.'],
        exposure='Existing exposed Lego and inherited manual bucket. New static camera values frozen before output; not blind training-data holdouts.',
        promotion='Keep all four defaults and prior examples; add optional lego_platform_ink example. No sweep or scientific H1/H2/H5 claim.',
        resource=dict(cpu=2,numeric_threads=1,serial=True,gpu=False,nested_models=False,unit_deadline_jst='2026-10-22T07:44:07+09:00'))
    js(UNIT/'PROTOCOL.json',p)
    shutil.copy2(UNIT/'PROTOCOL.json',Path('docs/partwise_sketch_hatching_v04/UNIT016_PROTOCOL.json'))
    shutil.copytree(SOURCE,UNIT/'source_before',ignore=shutil.ignore_patterns('__pycache__'))
    js(UNIT/'SOURCE_BEFORE.json',dict(files={f.name:sha(f) for f in SOURCE.iterdir() if f.is_file()},git_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()))
    (UNIT/'INHERITED_WORKTREE.diff').write_bytes(subprocess.check_output(['git','diff','--','experiments/partwise_sketch_hatching_v04','docs/partwise_sketch_hatching_v04']))
    js(UNIT/'STATUS.json',dict(stage='PROTOCOL_FROZEN',execution_state='partial',scientific_verdict='H1_H2_H5_NOT_TESTED',demo_progress=dict(genuinely_ran_old_model=False,reasoning=p['decision']),artifacts=['PROTOCOL.json'],blockers=[]))
    print(json.dumps(dict(protocol_sha256=sha(UNIT/'PROTOCOL.json'),frozen_utc=p['frozen_utc'])))

def candidate():
    p=protocol();asset=Path(p['asset'])
    assert {f.name:sha(f) for f in asset.iterdir() if f.is_file()}==p['inputs']
    edit(asset,UNIT/'assets/ink',p['region'],p['change'])
    _,_,meta=load_asset(UNIT/'assets/ink')
    exact={f.name:sha(f)==sha(UNIT/'assets/ink'/f.name) for f in asset.iterdir() if f.is_file() and f.name!='asset.json'}
    assert all(exact.values()) and meta['edit']['regenerated_layers']==[]
    js(UNIT/'metrics/ASSET_EDIT.json',dict(unchanged_files=exact,edit=meta['edit'],styles=meta['styles']))

def source():
    # Reuse the reviewed CPU implementation, with this unit's output paths only.
    import model_adapter, time
    p=protocol();folder=new_output(UNIT/'source_model');(UNIT/'build').mkdir(exist_ok=True)
    shutil.copy2(PREVIOUS/'build/libsource.so',UNIT/'build/libsource.so')
    model_adapter.LIB_PATH=UNIT/'build/libsource.so'
    start=time.monotonic();model=model_adapter.load_source(p['original']['original_ply'],p['original']['sha256'])
    camera=orbit_camera(**p['viewer_camera']);result=model_adapter.render_source(model,camera)
    Image.fromarray(np.uint8(np.clip(result['rgb'],0,1)*255+.5)).save(folder/'source_rgb.png')
    np.savez_compressed(folder/'source_arrays.npz',**result)
    js(folder/'RECEIPT.json',dict(original=p['original'],original_gaussians=model['audit']['count'],camera=camera,seconds=time.monotonic()-start,
        adapter='CPU SH3 EWA of original vanilla GS; not independent geometry or GPU-equivalence evidence',libsource_sha256=sha(model_adapter.LIB_PATH)))

def static():
    from scipy.ndimage import binary_dilation,binary_erosion
    p=protocol();target=p['region'];rows=[];items=[]
    loaded={a:load_asset(Path(p['asset']) if a=='baseline' else UNIT/'assets/ink') for a in ('baseline','ink')}
    for arm in loaded:(UNIT/'renders'/arm).mkdir(parents=True)
    for i,values in enumerate(p['static_camera_values']):
        c=orbit_camera(**values);data={}
        for arm,(mesh,paths,meta) in loaded.items():
            row=save_frame(UNIT/'renders'/arm,f'frame_{i:03d}',mesh,paths,meta,c)
            assert row['bounds']['all_proxy_vertices_inside']
            with np.load(UNIT/f'renders/{arm}/frame_{i:03d}_arrays.npz') as z:data[arm]={k:z[k] for k in z.files}
            items.append((f"Az {values['azimuth']} | Platform ink {'.80' if arm=='baseline' else '.40'}",Image.open(UNIT/f'renders/{arm}/frame_{i:03d}_image.png')))
        a,b=data['baseline'],data['ink'];mask=a['regions']==target
        band=binary_dilation(mask,iterations=2)&~binary_erosion(mask,iterations=2)
        masks=dict(target_interior=mask&~band,boundary_band=band,far_other=(a['regions']>0)&~mask&~band,far_background=(a['regions']==0)&~band)
        assert np.all(sum(m.astype(int) for m in masks.values())==1)
        delta=np.abs(a['image']-b['image'])
        unchanged={k:bool(np.array_equal(a[k],b[k])) for k in ('depth','regions','contour','layer_2','layer_3','layer_4','stroke_layer_4_0','stroke_layer_4_1')}
        assert all(unchanged.values())
        np.testing.assert_array_equal(b['layer_1'],a['layer_1']*.5)
        locality={k:dict(pixels=int(m.sum()),L1=float(delta[m].sum()),changed_pixels=int((delta[m]>0).sum())) for k,m in masks.items()}
        assert locality['target_interior']['L1']>0 and locality['far_other']['L1']==locality['far_background']['L1']==0
        rows.append(dict(camera=values,locality=locality,unchanged_arrays=unchanged,
            target_ink={arm:float(d['layer_1'].sum()) for arm,d in data.items()},
            target_nonzero_pixels={arm:int((d['layer_1']>0).sum()) for arm,d in data.items()},
            target_threshold_point1_pixels={arm:int((d['layer_1']>.1).sum()) for arm,d in data.items()},
            whole_object_ink={arm:float((1-d['image']).sum()) for arm,d in data.items()}))
    contact(UNIT/'media/full_object_before_after.png',items,cols=2,size=512,title='Lego | fixed geometry and paths | regional ink strength only | all frozen views')
    panel=[('Actual original GS RGB',Image.open(UNIT/'source_model/source_rgb.png'))]
    for arm,key,title in [('baseline','proxy','Same model-derived proxy'),('baseline','region_rgb','Authored style regions'),('baseline','image','Original platform ink .80'),('ink','image','Platform ink .40')]:
        panel.append((title,Image.open(UNIT/f'renders/{arm}/frame_000_{key}.png')))
    contact(UNIT/'media/source_proxy_regions_edit.png',panel,cols=3,size=512,title='Lego | artistic ink control | geometry defects and original contours retained')
    js(UNIT/'metrics/LOCALITY.json',dict(views=rows,scope='Same proxy labels, fixed2px band. No independent semantic mask or surface truth; ink reduction is intentional.'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['freeze','candidate','source','static']);a=p.parse_args();globals()[a.phase]()
