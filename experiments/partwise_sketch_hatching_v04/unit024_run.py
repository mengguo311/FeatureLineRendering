"""Bounded serial render-cache engineering evidence on saved real-model assets."""
import runtime
from runtime import OUTPUT_ROOT,js,sha,now,output_guard
from pathlib import Path
import argparse,json,shutil,subprocess,sys,time

U=OUTPUT_ROOT/'units/unit_024'
PREV=OUTPUT_ROOT/'units/unit_023'
SOURCE=Path(__file__).resolve().parent
ASSET=PREV/'assets/baseline'
def hashes(folder):
    return {str(f.relative_to(folder)):sha(f) for f in sorted(folder.rglob('*')) if f.is_file() and '__pycache__' not in f.parts}
def protocol():return json.loads((U/'PROTOCOL.json').read_text())
def command(name,args,expect=0):
    target=U/'logs'/f'{name}.receipt.json';assert not target.exists()
    t=time.monotonic();began=now();rc=None
    try:
        with (U/'logs'/f'{name}.log').open('w') as log:
            child=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            js(U/'logs'/f'{name}.child.json',dict(pid=child.pid,process_group=child.pid,started_utc=began,command=list(map(str,args))))
            try:rc=child.wait(timeout=540)
            except subprocess.TimeoutExpired:
                import os,signal
                os.killpg(child.pid,signal.SIGTERM)
                try:rc=child.wait(timeout=15)
                except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);rc=child.wait(timeout=10)
                raise
    finally:
        js(target,dict(command=list(map(str,args)),cwd=str(Path.cwd()),start_utc=began,end_utc=now(),seconds=time.monotonic()-t,returncode=rc,expected_returncode=expect))
        print(target.read_text(),flush=True)
    if rc!=expect:raise RuntimeError('unexpected return code: '+name)

def durable_command(name,args,expect=0):
    """Keep the receipt writer with its owned worker if the tool shell exits.

    This still waits synchronously. Callers must inspect the receipt/worker and
    finish cleanup before doing other numerical work or returning the unit.
    """
    worker=subprocess.Popen([sys.executable,str(SOURCE/'unit024_run.py'),'command',name,str(expect),*map(str,args)],start_new_session=True)
    js(U/'logs'/f'{name}.worker.json',dict(pid=worker.pid,process_group=worker.pid,started_utc=now()))
    rc=worker.wait(timeout=580)
    if rc:raise RuntimeError('command worker failed: '+name)
def freeze():
    from demo import load_asset
    output_guard(U)
    assert subprocess.check_output(['git','branch','--show-current'],text=True).strip()=='partwise-sketch-hatching-models-v04'
    assert not (U/'PROTOCOL.json').exists()
    for folder in ('logs','metrics','media'):(U/folder).mkdir()
    _,_,meta=load_asset(ASSET)
    assert sha(meta['original']['original_ply'])==meta['original']['sha256']
    p=dict(unit='unit_024',frozen_utc=now(),started_utc='2026-10-21T23:43:47.606495+00:00',scene='chair',asset=str(ASSET),inputs=hashes(ASSET),original=meta['original'],
        critical_review='Viewed actual unit023 full-object 4-view before/edit/restore, original GS/proxy/manual-region panel and all 12 orbit frames. Usable four-model demo exists, but seconds-per-edit remains; seat ripples, missing thin geometry and partial manual regions persist. unit023 browser rc143 remains historical UNKNOWN, recovered separately.',
        alternatives_ranked=['Profile and reuse exact supersampled coverage for ink edits','Improve proxy geometry: prior weak gains and larger risk','Fifth model: four existing models already usable'],
        changed='Single-entry in-memory coverage cache for same mesh, labels, paths, widths and camera. Compose ink strength and display at supersample resolution. Cache is never saved or required by cold load.',
        fixed='Mesh, paths, manual labels, renderer tolerances, 512x512 2xAA; baseline seat strength .8, one edit .35; other regions unchanged. No visual parameter sweep.',
        region_source='Inherited manual seat region4 (2704 faces) and upper-back region5 (3055 faces), not learned semantics.',target_region=4,ink_strength=.35,
        static_camera_values=[dict(azimuth=a,elevation=28,distance=4.9) for a in (43,133,223,313)],viewer_camera=dict(azimuth=43,elevation=28,distance=4.9),
        expected='Profile real Editor; warm ink reuses coverage and matches frozen old renderer arrays/PNG, non-target layers and path bytes unchanged. Camera/width/geometry/labels/paths/cross changes invalidate. Zero ink restores without losing coverage. Cold process/ZIP/GUI and orbit/zoom remain runnable.',
        measurements='One profile, three paired unprofiled full/warm ink timings at viewer camera; report render-only and full Editor save+load+PNG latency separately. Four whole-object views. Finite evidence, no universal speed guarantee.',
        exposure='New frozen evaluation azimuths; model and manual regions historically exposed. Not blind geometry holdouts.',
        scope='Engineering performance and correctness only; no H1/H2/H5 or surface-truth claim. P1 NO_GO and P2 unidentifiability preserved.',
        resources=dict(cpu=2,threads=1,serial=True,gpu=False,nested_models=False,finish_by_jst='2026-10-22T09:38:47+09:00'))
    js(U/'PROTOCOL.json',p);shutil.copy2(U/'PROTOCOL.json',SOURCE.parents[1]/'docs/partwise_sketch_hatching_v04/UNIT024_PROTOCOL.json')
    shutil.copytree(SOURCE,U/'source_before',ignore=shutil.ignore_patterns('__pycache__'))
    js(U/'STATUS.json',dict(stage='PROTOCOL_FROZEN',execution_state='partial',scientific_verdict=p['scope'],demo_progress=dict(genuinely_ran_old_model=False,reasoning=p['changed']),artifacts=['PROTOCOL.json'],blockers=[]))
    print(json.dumps(dict(protocol_sha256=sha(U/'PROTOCOL.json'))))
def profile():
    import cProfile,pstats,io
    from viewer import Editor
    e=Editor(ASSET,U/'profile_session')
    values=dict(e.record['styles']['4'],**protocol()['viewer_camera'],region=4,ink_strength=.35)
    profiler=cProfile.Profile();t=time.monotonic();profiler.enable();e.apply(values);profiler.disable();elapsed=time.monotonic()-t
    profiler.dump_stats(U/'metrics/editor_profile.prof');stream=io.StringIO();pstats.Stats(profiler,stream=stream).sort_stats('cumulative').print_stats(35)
    (U/'metrics/editor_profile.txt').write_text(stream.getvalue())
    js(U/'metrics/PROFILE.json',dict(seconds=elapsed,draw_seconds=e.record['seconds'],note='cProfile overhead included; baseline same workload, old renderer'))
    print(stream.getvalue())
def candidate():
    from demo import edit,load_asset
    assert hashes(ASSET)==protocol()['inputs']
    shutil.copytree(ASSET,U/'assets/baseline')
    file=U/'assets/baseline/asset.json';meta=json.loads(file.read_text())
    meta['viewer_camera']=protocol()['viewer_camera'];meta['selected_region']=4;js(file,meta)
    edit(U/'assets/baseline',U/'assets/edited',4,dict(ink_strength=.35))
    a=hashes(U/'assets/baseline');b=hashes(U/'assets/edited')
    assert all(b[k]==v for k,v in a.items() if k!='asset.json')
    assert load_asset(U/'assets/edited')[2]['edit']['regenerated_layers']==[]
    js(U/'metrics/CANDIDATE.json',dict(all_binary_files_exact=True,paths_regenerated=False,only_region4_style_changed=True))

def legacy_modules():
    import importlib.util
    def load(name,file):
        spec=importlib.util.spec_from_file_location(name,U/'source_before'/file)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
    renderer=load('legacy_renderer','render.py');demo=load('legacy_demo','demo.py');demo.render=renderer.render
    return renderer,demo

def static():
    import numpy as np
    from PIL import Image
    from scipy.ndimage import binary_dilation,binary_erosion
    from demo import load_asset,save_frame,new_output
    from geometry import orbit_camera
    from render import RenderCache
    from media import contact
    _,old=legacy_modules();rows=[];panels=[]
    assets={arm:load_asset(U/'assets'/arm) for arm in ('baseline','edited')}
    for arm in ('baseline','edited','legacy_baseline','legacy_edited'):new_output(U/'renders'/arm)
    for i,values in enumerate(protocol()['static_camera_values']):
        c=orbit_camera(**values);cache=RenderCache();records={}
        for arm in ('baseline','edited'):
            args=(U/'renders'/arm,f'frame_{i:03d}',*assets[arm],c)
            records[arm]=save_frame(*args,cache=cache)
            old.save_frame(U/'renders'/('legacy_'+arm),f'frame_{i:03d}',*assets[arm],c)
            for key in ('image','hatch','contour','proxy','region_rgb'):
                name=f'frame_{i:03d}_{key}.png'
                assert sha(U/'renders'/arm/name)==sha(U/'renders'/('legacy_'+arm)/name)
            with np.load(U/'renders'/arm/f'frame_{i:03d}_arrays.npz') as a,np.load(U/'renders'/('legacy_'+arm)/f'frame_{i:03d}_arrays.npz') as b:
                assert set(a.files)==set(b.files) and all(np.array_equal(a[k],b[k]) for k in a.files)
            assert records[arm]['bounds']['all_proxy_vertices_inside']
            panels.append((f"Az{values['azimuth']} | {'Before .80' if arm=='baseline' else 'Seat ink .35'}",Image.open(U/'renders'/arm/f'frame_{i:03d}_image.png')))
        assert records['edited']['render_cache']['hit']
        with np.load(U/f'renders/baseline/frame_{i:03d}_arrays.npz') as a,np.load(U/f'renders/edited/frame_{i:03d}_arrays.npz') as b:
            delta=np.abs(a['image']-b['image']);labels=a['regions'];target=labels==4
            band=binary_dilation(target,iterations=2)&~binary_erosion(target,iterations=2)
            masks=dict(target_interior=target&~band,boundary=band,far_other=(labels>0)&~target&~band,far_background=(labels==0)&~band)
            measures={k:dict(pixels=int(v.sum()),L1=float(delta[v].sum()),changed=int((delta[v]>0).sum())) for k,v in masks.items()}
            assert delta.sum()>0
            unchanged=[k for k in a.files if k in ('depth','regions','contour') or k.startswith('layer_') and k!='layer_4']
            assert all(np.array_equal(a[k],b[k]) for k in unchanged)
        rows.append(dict(camera=values,legacy_PNG_and_arrays_exact=True,unchanged_non_target_layers=True,locality=measures,records=records))
    contact(U/'media/full_object_ink.png',panels,cols=2,size=512,title='Chair | fixed 3D paths | local seat ink edit | cache equals full renderer')
    js(U/'metrics/STATIC.json',dict(views=rows,scope='Same-proxy labels, fixed 2px target boundary; finite engineering evidence, not independent geometry/locality truth.'))

def benchmark(suffix=''):
    import numpy as np
    from demo import load_asset
    from geometry import orbit_camera
    from render import render,RenderCache
    from viewer import Editor
    m,s,meta=load_asset(U/'assets/edited');c=orbit_camera(**protocol()['viewer_camera']);cache=RenderCache()
    render(m,s,meta['styles'],c,cache=cache);rows=[]
    e=Editor(U/'assets/baseline',U/('benchmark_session'+suffix))
    for i in range(3):
        t=time.monotonic();full=render(m,s,meta['styles'],c);full_seconds=time.monotonic()-t
        t=time.monotonic();warm=render(m,s,meta['styles'],c,cache=cache);warm_seconds=time.monotonic()-t
        assert np.array_equal(full['image'],warm['image'])
        e.render_cache.clear();values=dict(e.record['styles']['4'],**protocol()['viewer_camera'],region=4,ink_strength=.8)
        t=time.monotonic();e.apply(values);full_editor=time.monotonic()-t
        values['ink_strength']=.35;t=time.monotonic();e.apply(values);warm_editor=time.monotonic()-t
        assert e.record['render_cache']['hit']
        rows.append(dict(full_render_seconds=full_seconds,warm_render_seconds=warm_seconds,full_editor_seconds=full_editor,warm_editor_seconds=warm_editor))
    med={key:float(np.median([v[key] for v in rows])) for key in rows[0]}
    js(U/'metrics'/('TIMINGS'+suffix.upper()+'.json'),dict(samples=rows,medians=med,render_speedup=med['full_render_seconds']/med['warm_render_seconds'],editor_speedup=med['full_editor_seconds']/med['warm_editor_seconds'],cache=cache.info(),
        scope='3 serial paired observations on this Linux CPU2 host, 512-square/2xAA; Editor includes asset validation, copying, quota check and saved PNG/NPZ. No browser transport or real-time guarantee.'))

def benchmark_final():benchmark('_final')

def reference():
    import numpy as np
    from PIL import Image
    from geometry import orbit_camera
    from media import contact
    import model_adapter
    out=U/'source_reference';out.mkdir(exist_ok=True);p=protocol();items=[]
    assert not any(out.iterdir())
    model_adapter.LIB_PATH=out/'libsource.so'
    shutil.copy2(PREV/'source_model/libsource.so',model_adapter.LIB_PATH)
    provenance=json.loads((PREV/'source_model/LIBRARY_PROVENANCE.json').read_text())
    assert sha(model_adapter.LIB_PATH)==provenance['library_sha256']
    assert sha(SOURCE/'model_adapter.py')==provenance['adapter_sha256'] and sha(SOURCE/'source_ewa.cpp')==provenance['source_sha256']
    js(out/'LIBRARY_PROVENANCE.json',provenance)
    model=model_adapter.load_source(p['original']['original_ply'],p['original']['sha256'])
    for i,values in enumerate(p['static_camera_values']):
        r=model_adapter.render_source(model,orbit_camera(**values))
        Image.fromarray(np.uint8(np.clip(r['rgb'],0,1)*255+.5)).save(out/f'frame_{i:03d}_rgb.png')
        np.savez_compressed(out/f'frame_{i:03d}_arrays.npz',**r)
        for label,file in [('Original GS RGB',out/f'frame_{i:03d}_rgb.png'),('Approximate proxy',U/f'renders/baseline/frame_{i:03d}_proxy.png'),('Manual style regions',U/f'renders/baseline/frame_{i:03d}_region_rgb.png'),('Seat ink .35',U/f'renders/edited/frame_{i:03d}_image.png')]:
            items.append((f"Az{values['azimuth']} | {label}",Image.open(file)))
    contact(U/'media/source_reference_all_views.png',items,cols=4,size=384,title='Chair | original model and CPU-derived proxy | manual regions and fixed hatching')
    js(out/'RECEIPT.json',dict(original=p['original'],gaussians=model['audit']['count'],views=4,scope='CPU SH3/EWA, not GPU equivalence or independent geometry truth.'))

def stage():
    package=U/'portable_demo';package.mkdir()
    for n in ('run.sh','CATALOG.json','PORTABLE_DEMO.json','requirements.txt','TESTED_ENVIRONMENT.json'):shutil.copy2(PREV/'portable_demo'/n,package/n)
    for n in ('assets','examples','recipes'):shutil.copytree(PREV/'portable_demo'/n,package/n)
    (package/'source').mkdir()
    for f in (PREV/'portable_demo/source').iterdir():
        if f.is_file():shutil.copy2(SOURCE/f.name,package/'source'/f.name)
    shutil.copytree(U/'assets/edited',package/'examples/chair_ink_preview')
    catalog=json.loads((package/'CATALOG.json').read_text())
    catalog['examples']['chair_ink_preview']=dict(scene='chair',asset='examples/chair_ink_preview',label='Seat ink · local edit',description='Two manual patches; seat ink .35 and upper-back ink .45. Adjust ink at the same view, save ZIP and reopen. Approximate geometry and incomplete regions remain.')
    js(package/'CATALOG.json',catalog)
    marker=json.loads((package/'PORTABLE_DEMO.json').read_text());marker.update(source_unit='unit_024',created_utc=now(),scientific_seal=False);js(package/'PORTABLE_DEMO.json',marker)
    assert hashes(package/'assets')==hashes(PREV/'portable_demo/assets')
    assert all(sha(package/'examples'/n)==h for n,h in hashes(PREV/'portable_demo/examples').items())
    js(U/'metrics/PRESERVATION.json',dict(default_models=4,inherited_examples=len(catalog['examples'])-1,all_previous_asset_files_byte_exact=True))

def regressions():
    import unittest,numpy as np
    import test_ink_strength,test_crosshatch,test_example_catalog
    from demo import load_asset
    from geometry import orbit_camera
    from render import render,RenderCache
    modules=[test_ink_strength,test_crosshatch,test_example_catalog]
    for module in modules:module.UNIT=U
    test_example_catalog.CATALOG=U/'portable_demo/CATALOG.json'
    test_example_catalog.OUT=U/'catalog_regressions';test_example_catalog.OUT.mkdir()
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(m) for m in modules)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    assert result.wasSuccessful()
    js(U/'metrics/REGRESSION_TESTS.json',dict(tests=result.testsRun,passed=True))
    catalog_smoke()

def catalog_smoke():
    import numpy as np
    from demo import load_asset
    from geometry import orbit_camera
    from render import render,RenderCache
    catalog=json.loads((U/'portable_demo/CATALOG.json').read_text());legacy,_=legacy_modules();smoke=[]
    for name,entry in catalog['scenes'].items():
        m,s,meta=load_asset(U/'portable_demo'/entry['asset']);c=orbit_camera(**meta.get('viewer_camera',dict(azimuth=17,elevation=20,distance=4.7)),size=192)
        cache=RenderCache();current=render(m,s,meta['styles'],c,display=meta.get('display'),cache=cache)
        old=legacy.render(m,s,meta['styles'],c,display=meta.get('display'))
        assert np.array_equal(current['image'],old['image']) and (current['image']<.99).sum()>0
        assert current['diagnostics']==old['diagnostics']
        smoke.append(dict(scene=name,nonwhite_pixels=int((current['image']<.99).sum()),legacy_exact=True))
    for entry in catalog['examples'].values():load_asset(U/'portable_demo'/entry['asset'])
    tests=json.loads((U/'metrics/REGRESSION_TESTS.json').read_text())
    js(U/'metrics/REGRESSIONS.json',dict(**tests,actual_default_model_renders=smoke,examples_loaded=len(catalog['examples'])))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase');p.add_argument('args',nargs='*');a=p.parse_args()
    if a.phase=='command':command(a.args[0],a.args[2:],int(a.args[1]))
    else:globals()[a.phase]()
