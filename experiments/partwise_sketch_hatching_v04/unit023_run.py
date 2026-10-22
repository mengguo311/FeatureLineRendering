"""Bounded real-Chair evidence for restoring independently authored regions."""
import runtime
from runtime import OUTPUT_ROOT,js,sha,now,output_guard
from pathlib import Path
import argparse,json,shutil,subprocess,sys,time
import numpy as np
from demo import load_asset,new_output,edit,save_frame
from geometry import orbit_camera

U=OUTPUT_ROOT/'units/unit_023'
PREV=OUTPUT_ROOT/'units/unit_022'
SOURCE=Path(__file__).resolve().parent
ASSET=PREV/'portable_demo/assets/chair'
def hashes(folder):
    return {str(f.relative_to(folder)):sha(f) for f in sorted(folder.rglob('*')) if f.is_file() and '__pycache__' not in f.parts}
def protocol():return json.loads((U/'PROTOCOL.json').read_text())
def command(name,args,expect=0):
    target=U/'logs'/f'{name}.receipt.json';assert not target.exists()
    start=time.monotonic();began=now();rc=None
    try:
        with (U/'logs'/f'{name}.log').open('w') as log:
            # Isolate this known child from the receipt writer's process group.
            # Browser cleanup owns additional groups; it must finish before we
            # return, including on a bounded timeout.
            child=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            try:rc=child.wait(timeout=540)
            except subprocess.TimeoutExpired:
                import os,signal
                os.killpg(child.pid,signal.SIGTERM)
                try:rc=child.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid,signal.SIGKILL);rc=child.wait(timeout=10)
                raise
    finally:
        js(target,dict(command=list(map(str,args)),cwd=str(Path.cwd()),start_utc=began,end_utc=now(),seconds=time.monotonic()-start,returncode=rc,expected_returncode=expect))
        print(target.read_text(),flush=True)
    if rc!=expect:raise RuntimeError('unexpected command return code: '+name)
def freeze():
    output_guard(U)
    assert subprocess.check_output(['git','branch','--show-current'],text=True).strip()=='partwise-sketch-hatching-models-v04'
    assert not (U/'PROTOCOL.json').exists()
    for name in ('logs','metrics','media'):(U/name).mkdir()
    _,_,meta=load_asset(ASSET)
    assert sha(meta['original']['original_ply'])==meta['original']['sha256']
    shutil.copy2(PREV/'SELECTION_RECIPE.json',U/'SELECTION_RECIPE.json')
    p=dict(unit='unit_023',frozen_utc=now(),started_utc='2026-10-21T23:28:55.808077+00:00',asset=str(ASSET),inputs=hashes(ASSET),original=meta['original'],
        decision='Make a saved manual seat region restorable after a separate back-region creation, while rejecting changed target anchors or shared support.',
        critical_review='Inspected actual unit022 source-GS/proxy/region/hatch panels, four-view restored images, all orbit frames and source/report/NEXT. Four model demo already works; restore currently invalidates on unrelated labels. Proxy ripples, thin parts and incomplete manual seat remain.',
        alternatives_ranked=['Restore survives independent authoring','More smoothing: previous weak gain','Fifth model: four genuine models already runnable'],
        region_source='Seat: inherited two visible manual rectangles, 2704 faces. Back: one explicit world AABB in region3, includes hidden faces. Neither is learned semantics.',
        second_bounds=[-.32,-1.,.4,.32,1.,1.1],second_source_region=3,second_name='Manual upper back patch',
        recipe_sha256=sha(U/'SELECTION_RECIPE.json'),target_region=4,second_region=5,angle=65.,second_ink=.45,
        static_camera_values=[dict(azimuth=a,elevation=28,distance=4.9) for a in (38,128,218,308)],viewer_camera=dict(azimuth=38,elevation=28,distance=4.9),
        fixed='Same learned-model-derived mesh, seat recipe, original path coordinates/styles, renderer and depth tolerance. No geometry sweep.',
        changed='Snapshot validity dependency: target/support face membership, indexed support geometry and per-mask face acceptance instead of whole labeled-mesh file hash. Exact saved paths/style copied on restore.',
        expected='Nonzero seat edit. After independent back creation and back ink edit, seat restore exactly matches two-region baseline with back ink retained; non-target bytes unchanged. Cold ZIP/GUI/relocated CLI work. Shared-support relabel/target split/support geometry change refuse restore before output.',
        compatibility='New snapshots only; legacy whole-mesh snapshots retain conservative validity. Support fingerprints deliberately cover whole accepted regions, not a camera-dependent footprint. Unrelated geometry may affect current occlusion; no unchanged-image claim across geometry revisions.',
        exposure='Four new fixed cameras chosen before results; scene and inherited seat selection exposed, not blind reconstruction holdouts.',
        motion=dict(orbit_frames=12,zoom_frames=6,fps=6),
        scope='Engineering usability only. H1/H2/H5 not tested; historical P1 NO_GO and P2 unidentifiability retained.',
        resources=dict(cpu=2,threads=1,serial=True,gpu=False,nested_models=False,finish_by_jst='2026-10-22T09:23:55+09:00'))
    js(U/'PROTOCOL.json',p)
    shutil.copy2(U/'PROTOCOL.json',SOURCE.parents[1]/'docs/partwise_sketch_hatching_v04/UNIT023_PROTOCOL.json')
    shutil.copytree(SOURCE,U/'source_before',ignore=shutil.ignore_patterns('__pycache__'))
    js(U/'SOURCE_BEFORE.json',hashes(SOURCE))
    js(U/'STATUS.json',dict(stage='PROTOCOL_FROZEN',execution_state='partial',scientific_verdict=p['scope'],demo_progress=dict(genuinely_ran_old_model=False,reasoning=p['decision']),artifacts=['PROTOCOL.json'],blockers=[]))
    print(json.dumps(dict(protocol_sha256=sha(U/'PROTOCOL.json'))))
def author(output):
    from selection_draft import replay_recipe
    from region_tools import author_face_selection
    m,_,meta=load_asset(ASSET);recipe=json.loads((U/'SELECTION_RECIPE.json').read_text())
    draft=replay_recipe(m,meta['mesh_sha256'],recipe)
    return author_face_selection(ASSET,output,draft.face_ids,2,recipe['name'],draft.provenance())
def second(asset,output):
    from region_tools import author_region
    p=protocol()
    return author_region(asset,output,p['second_bounds'],3,p['second_name'])
def candidate():
    from region_restore import restore_region,restore_status
    assert hashes(ASSET)==protocol()['inputs']
    author(U/'assets/seat')
    second(U/'assets/seat',U/'assets/two_regions')
    edit(U/'assets/two_regions',U/'assets/baseline',5,dict(ink_strength=.45))
    edit(U/'assets/baseline',U/'assets/edited',4,dict(angle=65.))
    restore_region(U/'assets/edited',U/'assets/restored',4)
    for arm in ('seat','two_regions','baseline','edited','restored'):
        file=U/'assets'/arm/'asset.json';m=json.loads(file.read_text());m['viewer_camera']=protocol()['viewer_camera'];m['selected_region']=4;js(file,m)
    m,_,meta=load_asset(U/'assets/restored')
    assert restore_status(meta,4,m)['available'] and restore_status(meta,5,m)['available']
    assert sha(U/'assets/restored/region_4.npz')==sha(U/'assets/seat/region_4.npz')
    for f in (U/'assets/edited').iterdir():
        if f.name not in ('asset.json','region_4.npz'):assert sha(f)==sha(U/'assets/restored'/f.name)
    js(U/'metrics/CANDIDATE.json',dict(regions=meta['regions'],manual_history=meta['region_history'],restore4=restore_status(meta,4,m),restore5=restore_status(meta,5,m),other_files_exact=True,restored_target_byte_exact=True))
def static():
    from media import contact
    from PIL import Image
    from scipy.ndimage import binary_dilation,binary_erosion
    loaded={arm:load_asset(U/'assets'/arm) for arm in ('baseline','edited','restored')};rows=[];panels=[]
    for arm in loaded:new_output(U/'renders'/arm)
    for i,c in enumerate(protocol()['static_camera_values']):
        arrays={}
        for arm in loaded:
            record=save_frame(U/'renders'/arm,f'frame_{i:03d}',*loaded[arm],orbit_camera(**c))
            assert record['bounds']['all_proxy_vertices_inside']
            with np.load(U/f'renders/{arm}/frame_{i:03d}_arrays.npz') as z:arrays[arm]={k:z[k] for k in z.files}
            panels.append((f"Az{c['azimuth']} | {arm}",Image.open(U/f'renders/{arm}/frame_{i:03d}_image.png')))
        a,b,r=(arrays[k] for k in ('baseline','edited','restored'))
        assert all(np.array_equal(a[k],r[k]) for k in a)
        mask=a['regions']==4;band=binary_dilation(mask,iterations=2)&~binary_erosion(mask,iterations=2)
        masks=dict(target_interior=mask&~band,boundary_band=band,far_other=(a['regions']>0)&~mask&~band,far_background=(a['regions']==0)&~band)
        delta=np.abs(a['image']-b['image'])
        row=dict(camera=c,restore_all_arrays_exact=True,edit_delta={k:dict(pixels=int(v.sum()),changed_pixels=int((delta[v]>0).sum()),L1=float(delta[v].sum())) for k,v in masks.items()})
        assert row['edit_delta']['target_interior']['L1']>0
        assert all(np.array_equal(a[f'layer_{n}'],b[f'layer_{n}']) for n in (1,2,3,5))
        rows.append(row)
    contact(U/'media/full_object_restore.png',panels,cols=3,size=512,title='Chair | two manual regions, local seat edit, seat restore retaining edited back')
    js(U/'metrics/STATIC.json',dict(views=rows,scope='Same-proxy masks; not independent semantics or temporal certification'))
def reference():
    import model_adapter
    from media import contact
    from PIL import Image
    p=protocol();out=new_output(U/'source_model');items=[]
    model_adapter.LIB_PATH=out/'libsource.so';shutil.copy2(PREV/'source_model/libsource.so',model_adapter.LIB_PATH)
    old=json.loads((PREV/'source_model/LIBRARY_PROVENANCE.json').read_text())
    assert sha(model_adapter.LIB_PATH)==old['library_sha256'] and sha(SOURCE/'model_adapter.py')==old['adapter_sha256'] and sha(SOURCE/'source_ewa.cpp')==old['source_sha256']
    js(out/'LIBRARY_PROVENANCE.json',dict(**old,reused_from='unit_022',current_verified=True))
    model=model_adapter.load_source(p['original']['original_ply'],p['original']['sha256'])
    for i,c in enumerate(p['static_camera_values']):
        r=model_adapter.render_source(model,orbit_camera(**c));Image.fromarray(np.uint8(np.clip(r['rgb'],0,1)*255+.5)).save(out/f'frame_{i:03d}_rgb.png')
        np.savez_compressed(out/f'frame_{i:03d}_arrays.npz',**r)
        for label,file in [('Original GS RGB',out/f'frame_{i:03d}_rgb.png'),('Model-derived proxy',U/f'renders/baseline/frame_{i:03d}_proxy.png'),('Manual regions',U/f'renders/baseline/frame_{i:03d}_region_rgb.png'),('Restored seat; edited back',U/f'renders/restored/frame_{i:03d}_image.png')]:
            items.append((f"Az{c['azimuth']} | {label}",Image.open(file)))
    contact(U/'media/source_reference_all_views.png',items,cols=4,size=384,title='Chair | original checkpoint, approximate proxy, two manual regions, persistent hatching')
    js(out/'RECEIPT.json',dict(original=p['original'],gaussians=model['audit']['count'],views=4,library_sha256=sha(model_adapter.LIB_PATH),scope='CPU SH3/EWA source rendering; not independent geometry truth or GPU equivalence'))
def negatives():
    from region_tools import author_face_selection
    from region_restore import restore_region,restore_status
    from asset_archive import export_archive
    _,paths,_=load_asset(U/'assets/seat')
    folder=U/'assets/shared_support_changed'
    author_face_selection(U/'assets/seat',folder,np.unique(paths[2]['face'])[::2],2,'Shared support changed',{})
    mesh,_,meta=load_asset(folder);status=restore_status(meta,4,mesh);assert not status['available']
    try:restore_region(folder,U/'assets/refused_restore',4)
    except ValueError as error:reason=str(error)
    else:raise AssertionError('changed shared support was accepted')
    assert not (U/'assets/refused_restore').exists()
    (U/'shared_support_changed.zip').write_bytes(export_archive(folder,protocol()['viewer_camera'],4))
    output=new_output(U/'renders/shared_support_changed');save_frame(output,'frame_000',*load_asset(folder),orbit_camera(**protocol()['viewer_camera']))
    js(U/'metrics/EXPECTED_REJECTION.json',dict(case='Split original region2; original seat support mask includes region2, so semantic acceptance changed even though seat anchors did not.',status=status,restore_error=reason,no_output_created=True,asset='assets/shared_support_changed',preview='renders/shared_support_changed/frame_000_image.png'))
def stage():
    package=new_output(U/'portable_demo')
    for n in ('run.sh','CATALOG.json','PORTABLE_DEMO.json','requirements.txt','TESTED_ENVIRONMENT.json'):shutil.copy2(PREV/'portable_demo'/n,package/n)
    for n in ('assets','examples'):shutil.copytree(PREV/'portable_demo'/n,package/n)
    (package/'source').mkdir()
    for f in (PREV/'portable_demo/source').iterdir():
        if f.is_file():shutil.copy2(SOURCE/f.name,package/'source'/f.name)
    shutil.copytree(U/'assets/edited',package/'examples/chair_two_regions')
    shutil.copytree(U/'assets/baseline',package/'candidates/chair_two_regions_baseline')
    (package/'recipes').mkdir();shutil.copy2(U/'SELECTION_RECIPE.json',package/'recipes/chair_seat.json')
    catalog=json.loads((package/'CATALOG.json').read_text())
    catalog['examples']['chair_two_regions']=dict(scene='chair',asset='examples/chair_two_regions',label='Two patches · independent restore',description='Manual seat and upper-back patches. Seat angle65; upper-back ink .45. Restore region4 after independent region5 authoring, including a saved ZIP and fresh session. Approximate proxy; manual partial regions.')
    js(package/'CATALOG.json',catalog)
    m=json.loads((package/'PORTABLE_DEMO.json').read_text());m.update(source_unit='unit_023',created_utc=now(),optional_example='chair_two_regions',scientific_seal=False);js(package/'PORTABLE_DEMO.json',m)
    assert hashes(package/'assets')==hashes(PREV/'portable_demo/assets')
    assert all(sha(package/'examples'/n)==v for n,v in hashes(PREV/'portable_demo/examples').items())
    js(U/'metrics/PRESERVATION.json',dict(all_previous_defaults_and_examples_byte_exact=True))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['freeze','candidate','static','reference','negatives','stage','command']);p.add_argument('args',nargs=argparse.REMAINDER);a=p.parse_args()
    if a.phase=='command':
        name=a.args[0];args=a.args[1:];expect=0
        if args[:1]==['--expect']:expect=int(args[1]);args=args[2:]
        if args[:1]==['--']:args=args[1:]
        command(name,args,expect)
    else:globals()[a.phase]()
