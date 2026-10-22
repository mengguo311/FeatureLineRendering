"""Bounded engineering evidence for persistent manual-region restoration."""
import runtime
from runtime import OUTPUT_ROOT,js,sha,now,output_guard
from pathlib import Path
import argparse,json,shutil,subprocess,sys,time
import numpy as np
from demo import load_asset,new_output,edit,save_frame
from geometry import orbit_camera

U=OUTPUT_ROOT/'units/unit_022'
PREV=OUTPUT_ROOT/'units/unit_021'
SOURCE=Path(__file__).resolve().parent
ASSET=PREV/'portable_demo/assets/chair'
def hashes(folder):
    return {str(f.relative_to(folder)):sha(f) for f in sorted(folder.rglob('*')) if f.is_file() and '__pycache__' not in f.parts}
def protocol():return json.loads((U/'PROTOCOL.json').read_text())
def command(name,args,expect=0):
    target=U/'logs'/f'{name}.receipt.json';assert not target.exists()
    start=time.monotonic();began=now()
    with (U/'logs'/f'{name}.log').open('w') as log:
        r=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=540)
    js(target,dict(command=list(map(str,args)),cwd=str(Path.cwd()),start_utc=began,end_utc=now(),seconds=time.monotonic()-start,returncode=r.returncode,expected_returncode=expect))
    print(target.read_text(),flush=True)
    if r.returncode!=expect:raise RuntimeError('unexpected command return code: '+name)
def freeze():
    output_guard(U)
    assert subprocess.check_output(['git','branch','--show-current'],text=True).strip()=='partwise-sketch-hatching-models-v04'
    assert not (U/'PROTOCOL.json').exists()
    for name in ('logs','metrics','media'):(U/name).mkdir()
    _,_,m=load_asset(ASSET)
    assert sha(m['original']['original_ply'])==m['original']['sha256']
    shutil.copy2(PREV/'SELECTION_RECIPE.json',U/'SELECTION_RECIPE.json')
    p=dict(unit='unit_022',frozen_utc=now(),started_utc='2026-10-21T23:13:33.073737+00:00',asset=str(ASSET),inputs=hashes(ASSET),original=m['original'],
        decision='Persist creation-time paths/styles for newly authored regions, restore only the selected region after exported ZIP cold import.',
        critical_review='Read unit021 source/report/NEXT; inspected actual four-view whole Chair and original-GS/proxy/region/hatch panels. Authoring is pixel-preserving, but changing angle back cannot recover inherited breakpoints. Geometry ripple and thin-part loss remain.',
        alternatives_ranked=['Persistent exact region restore','Further proxy smoothing: weak previous gain','More models: four already available'],
        region_source='Same two manual visible rectangles and 2704 faces from unit021; partial seat, not automatic semantics.',
        recipe_sha256=sha(U/'SELECTION_RECIPE.json'),target_region=4,source_region=2,angle=65.,
        static_camera_values=[dict(azimuth=a,elevation=27,distance=4.9) for a in (33,123,213,303)],
        viewer_camera=dict(azimuth=33,elevation=27,distance=4.9),
        fixed='Source mesh, selected faces, inherited paths/styles, renderer, display, depth tolerance; no geometry or parameter sweep.',
        changed='Creation snapshot and explicit restore action, CLI and browser; exact saved NPZ and style restoration, no regeneration.',
        expected='Edit is visibly nonzero; restored whole-object image and arrays equal authored baseline; other edited regions remain as edited. Export/import persists snapshot. Missing/stale/corrupt snapshots reject without output.',
        compatibility='Legacy assets remain editable with restore unavailable. Any later mesh/label change conservatively disables old snapshots; no stale anchors restored.',
        exposure='New four camera values frozen before output; model and selection historically exposed, not blind reconstruction holdouts.',
        motion=dict(orbit_frames=12,zoom_frames=6,fps=6),
        scope='Engineering usability only, no H1/H2/H5 claim; historical P1 NO_GO and P2 unidentifiability retained.',
        resources=dict(cpu=2,threads=1,serial=True,gpu=False,nested_models=False,finish_by_jst='2026-10-22T09:08:33+09:00'))
    js(U/'PROTOCOL.json',p)
    shutil.copy2(U/'PROTOCOL.json',SOURCE.parents[1]/'docs/partwise_sketch_hatching_v04/UNIT022_PROTOCOL.json')
    shutil.copytree(SOURCE,U/'source_before',ignore=shutil.ignore_patterns('__pycache__'))
    js(U/'SOURCE_BEFORE.json',hashes(SOURCE))
    shutil.copytree(SOURCE.parents[1]/'docs/partwise_sketch_hatching_v04',U/'docs_before')
    js(U/'STATUS.json',dict(stage='PROTOCOL_FROZEN',execution_state='partial',scientific_verdict=p['scope'],demo_progress=dict(genuinely_ran_old_model=False,reasoning=p['decision']),artifacts=['PROTOCOL.json'],blockers=[]))
    print(json.dumps(dict(protocol_sha256=sha(U/'PROTOCOL.json'))))
def author(output):
    from selection_draft import replay_recipe
    from region_tools import author_face_selection
    m,_,meta=load_asset(ASSET);recipe=json.loads((U/'SELECTION_RECIPE.json').read_text())
    draft=replay_recipe(m,meta['mesh_sha256'],recipe)
    return author_face_selection(ASSET,output,draft.face_ids,2,recipe['name'],draft.provenance())
def candidate():
    from region_restore import restore_region
    assert hashes(ASSET)==protocol()['inputs']
    result=author(U/'assets/authored')
    for arm in ('authored',):
        f=U/'assets'/arm/'asset.json';m=json.loads(f.read_text());m['viewer_camera']=protocol()['viewer_camera'];m['selected_region']=4;js(f,m)
    edit(U/'assets/authored',U/'assets/edited',4,dict(angle=65.))
    restore_region(U/'assets/edited',U/'assets/restored',4)
    js(U/'metrics/CANDIDATE.json',result)
def static():
    from media import contact
    from PIL import Image
    from scipy.ndimage import binary_dilation,binary_erosion
    loaded={arm:load_asset(U/'assets'/arm) for arm in ('authored','edited','restored')};rows=[];panels=[]
    for arm in loaded:new_output(U/'renders'/arm)
    for i,c in enumerate(protocol()['static_camera_values']):
        arrays={}
        for arm in loaded:
            record=save_frame(U/'renders'/arm,f'frame_{i:03d}',*loaded[arm],orbit_camera(**c))
            assert record['bounds']['all_proxy_vertices_inside']
            with np.load(U/f'renders/{arm}/frame_{i:03d}_arrays.npz') as z:arrays[arm]={k:z[k] for k in z.files}
            panels.append((f"Az{c['azimuth']} | {arm}",Image.open(U/f'renders/{arm}/frame_{i:03d}_image.png')))
        a,b,r=(arrays[k] for k in ('authored','edited','restored'))
        assert all(np.array_equal(a[k],r[k]) for k in a)
        mask=a['regions']==4;band=binary_dilation(mask,iterations=2)&~binary_erosion(mask,iterations=2)
        masks=dict(target_interior=mask&~band,boundary_band=band,far_other=(a['regions']>0)&~mask&~band,far_background=(a['regions']==0)&~band)
        delta=np.abs(a['image']-b['image'])
        row=dict(camera=c,restore_all_arrays_exact=True,edit_delta={k:dict(pixels=int(v.sum()),L1=float(delta[v].sum())) for k,v in masks.items()})
        assert row['edit_delta']['target_interior']['L1']>0
        assert all(np.array_equal(a[f'layer_{n}'],b[f'layer_{n}']) for n in (1,2,3))
        rows.append(row)
    contact(U/'media/full_object_restore.png',panels,cols=3,size=512,title='Chair | creation-time strokes, local edit, exact restoration after saving')
    js(U/'metrics/STATIC.json',dict(views=rows,scope='Same-proxy locality; not independent semantics or temporal certification'))
def reference():
    import model_adapter
    from media import contact
    from PIL import Image
    p=protocol();out=new_output(U/'source_model');items=[]
    model_adapter.LIB_PATH=out/'libsource.so'
    shutil.copy2(PREV/'source_model/libsource.so',model_adapter.LIB_PATH)
    assert sha(model_adapter.LIB_PATH)==sha(PREV/'source_model/libsource.so')
    model=model_adapter.load_source(p['original']['original_ply'],p['original']['sha256'])
    for i,c in enumerate(p['static_camera_values']):
        r=model_adapter.render_source(model,orbit_camera(**c))
        Image.fromarray(np.uint8(np.clip(r['rgb'],0,1)*255+.5)).save(out/f'frame_{i:03d}_rgb.png')
        np.savez_compressed(out/f'frame_{i:03d}_arrays.npz',**r)
        for label,file in [('Original GS RGB',out/f'frame_{i:03d}_rgb.png'),('Model-derived proxy',U/f'renders/authored/frame_{i:03d}_proxy.png'),('Manual regions',U/f'renders/authored/frame_{i:03d}_region_rgb.png'),('Restored hatching',U/f'renders/restored/frame_{i:03d}_image.png')]:
            items.append((f"Az{c['azimuth']} | {label}",Image.open(file)))
    contact(U/'media/source_reference_all_views.png',items,cols=4,size=384,title='Chair | original checkpoint, approximate proxy, manual selection, restored strokes')
    js(out/'RECEIPT.json',dict(original=p['original'],gaussians=model['audit']['count'],views=4,library_sha256=sha(model_adapter.LIB_PATH),adapter_sha256=sha(SOURCE/'model_adapter.py'),scope='CPU SH3/EWA source rendering, not independent geometry truth or GPU equivalence'))
def stage():
    package=new_output(U/'portable_demo')
    for n in ('run.sh','CATALOG.json','PORTABLE_DEMO.json','requirements.txt','TESTED_ENVIRONMENT.json'):shutil.copy2(PREV/'portable_demo'/n,package/n)
    for n in ('assets','examples'):shutil.copytree(PREV/'portable_demo'/n,package/n)
    (package/'source').mkdir()
    for f in (PREV/'portable_demo/source').iterdir():
        if f.is_file():shutil.copy2(SOURCE/f.name,package/'source'/f.name)
    shutil.copy2(SOURCE/'region_restore.py',package/'source/region_restore.py')
    shutil.copytree(U/'assets/edited',package/'examples/chair_seat_restorable')
    shutil.copytree(U/'assets/authored',package/'candidates/chair_seat_original')
    (package/'recipes').mkdir();shutil.copy2(U/'SELECTION_RECIPE.json',package/'recipes/chair_seat.json')
    catalog=json.loads((package/'CATALOG.json').read_text())
    catalog['examples']['chair_seat_restorable']=dict(scene='chair',asset='examples/chair_seat_restorable',label='Seat edit · restore original strokes',description='Manual partial seat patch at angle 65. Restore region 4 to its exact creation-time strokes, even after ZIP export and reopening. Proxy ripples and weak thin parts remain.')
    js(package/'CATALOG.json',catalog)
    m=json.loads((package/'PORTABLE_DEMO.json').read_text());m.update(source_unit='unit_022',created_utc=now(),optional_example='chair_seat_restorable',scientific_seal=False);js(package/'PORTABLE_DEMO.json',m)
    assert hashes(package/'assets')==hashes(PREV/'portable_demo/assets')
    assert all(sha(package/'examples'/n)==v for n,v in hashes(PREV/'portable_demo/examples').items())
    js(U/'metrics/PRESERVATION.json',dict(all_previous_defaults_and_examples_byte_exact=True))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['freeze','candidate','static','reference','stage','command']);p.add_argument('args',nargs=argparse.REMAINDER);a=p.parse_args()
    if a.phase=='command':
        name=a.args[0];args=a.args[1:];expect=0
        if args[:1]==['--expect']:expect=int(args[1]);args=args[2:]
        if args[:1]==['--']:args=args[1:]
        command(name,args,expect)
    else:globals()[a.phase]()
