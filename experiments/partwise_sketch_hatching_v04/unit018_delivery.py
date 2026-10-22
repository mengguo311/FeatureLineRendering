"""Real source, current-only package, cold replay and relocated import checks."""
import runtime
from runtime import js,sha,now
from pathlib import Path
import argparse,json,shutil,tarfile,subprocess,time,signal,urllib.request
from unit018_run import U,PREV,SOURCE,hashes,command

def source():
    import numpy as np
    from PIL import Image
    import model_adapter
    from geometry import orbit_camera
    from media import contact
    from demo import new_output
    p=json.loads((U/'PROTOCOL.json').read_text());out=new_output(U/'source_model')
    model_adapter.LIB_PATH=out/'libsource.so';shutil.copy2(PREV/'source_model/libsource.so',model_adapter.LIB_PATH)
    saved=json.loads((U/'browser/EXPORT_STATES.json').read_text())['lego'];camera=orbit_camera(**saved['camera'])
    start=time.monotonic();model=model_adapter.load_source(p['original']['original_ply'],p['original']['sha256'])
    result=model_adapter.render_source(model,camera)
    Image.fromarray(np.uint8(np.clip(result['rgb'],0,1)*255+.5)).save(out/'source_rgb.png')
    np.savez_compressed(out/'source_arrays.npz',**result)
    js(out/'RECEIPT.json',dict(original=p['original'],original_gaussians=model['audit']['count'],camera=camera,
        seconds=time.monotonic()-start,adapter='CPU SH3/EWA original vanilla GS; not independent geometry truth or GPU equivalence',library_sha256=sha(model_adapter.LIB_PATH)))
    raster=U/'browser/session'/saved['images']['image'].removeprefix('/image/')
    contact(U/'media/source_proxy_import_edit.png',[(label,Image.open(file)) for label,file in [
        ('Actual original GS RGB',out/'source_rgb.png'),('Inherited model-derived proxy',raster.with_name('frame_000_proxy.png')),
        ('Authored style regions',raster.with_name('frame_000_region_rgb.png')),('Imported saved Lego: ink .60',U/'browser/legacy_lego_import.png'),
        ('Continue editing: ink .35',U/'browser/lego_local_edit.png')]],cols=3,size=512,title='Lego | original model and imported editable asset | geometry limitations unchanged')

def stage():
    for folder in ('browser','cold_browser'):
        assert json.loads((U/folder/'BROWSER_VALIDATION.json').read_text())['status']=='PASS'
    package=U/'portable_demo';(package/'source').mkdir()
    names=[f.name for f in (PREV/'portable_demo/source').iterdir() if f.is_file()]+['asset_archive.py']
    for name in names:shutil.copy2(SOURCE/name,package/'source'/name)
    for scene in ('lego','chair'):
        shutil.copytree(U/'browser'/('exported_'+scene),package/'saved'/scene)
        # Manifest describes the transport ZIP; subsequent edits recompute it on download.
        (package/'saved'/scene/'ASSET_MANIFEST.json').unlink()
        (package/'saved_zips').mkdir(exist_ok=True)
        shutil.copy2(U/'browser'/(scene+'_saved_asset.zip'),package/'saved_zips'/(scene+'_saved_asset.zip'))
    for kind in ('orbit','zoom'):
        src=U/'browser'/('lego_'+kind)
        shutil.copytree(src,package/'presentations'/('lego_'+kind))
        for suffix in ('mp4','mkv'):shutil.copy2(src/('animation.'+suffix),U/'media'/('lego_'+kind+'.'+suffix))
        shutil.copy2(src/'contact_sheet.png',U/'media'/('lego_'+kind+'_all_frames.png'))
    meta=json.loads((package/'PORTABLE_DEMO.json').read_text());meta.update(source_unit='unit_018',created_utc=now(),
        saved_asset_import='Catalog browser: flat data-only ZIP, known model SHA, checksum/anchor validation, independent sessions; no undo/drafts restored.')
    js(package/'PORTABLE_DEMO.json',meta)
    p=json.loads((U/'PROTOCOL.json').read_text());assert all(hashes(package/name)==p['inputs'][name] for name in ('assets','examples'))
    js(U/'metrics/INPUT_PRESERVATION.json',dict(all_four_defaults_and_all_examples_byte_exact=True,files=p['inputs']))

def build():
    package=U/'portable_demo';cold={};videos={}
    for kind in ('orbit','zoom'):
        r=json.loads((package/'runs'/('cold_'+kind)/'REPLAY.json').read_text())
        assert r['all_png_exact'] and r['all_arrays_exact']
        cold[kind]={k:r[k] for k in ('scene','frame_count','all_png_exact','all_arrays_exact')}
        videos[kind]=json.loads((package/'presentations'/('lego_'+kind)/'VIDEO_RECEIPTS.json').read_text())
        assert all(v['encode_returncode']==v['decode_returncode']==0 and v['decoded_frames']==r['frame_count'] for v in videos[kind])
        assert next(v for v in videos[kind] if v['file'].endswith('.mkv'))['all_frames_exact']
    js(U/'metrics/COLD_REPLAY.json',cold)
    shutil.copy2(SOURCE.parents[1]/'docs/partwise_sketch_hatching_v04/UNIT018_DEMO_README_ZH.md',package/'README_ZH.md')
    shutil.copy2(package/'README_ZH.md',U/'PACKAGE_README_ZH.md')
    (package/'previews').mkdir()
    for f in (U/'media').iterdir():shutil.copy2(f,package/'previews'/f.name)
    for folder,name in [('browser','04_imported_example_restored.png'),('cold_browser','02_cold_import_edit_undo.png')]:
        shutil.copy2(U/folder/name,package/'previews'/name)
    js(package/'VALIDATION.json',dict(unit='unit_018',utc=now(),
        browser=json.loads((U/'browser/BROWSER_VALIDATION.json').read_text()),
        cold_browser=json.loads((U/'cold_browser/BROWSER_VALIDATION.json').read_text()),
        cold_replay=cold,video_decode=videos,scientific_seal=False,visual_quality='partial, inherited proxy defects unchanged'))
    files={k:v for k,v in hashes(package).items() if not k.startswith('runs/') and k!='PACKAGE_FILES.json'}
    js(package/'PACKAGE_FILES.json',dict(files=files))
    def exclude(info):return None if any(x in ('runs','__pycache__') for x in Path(info.name).parts) else info
    archive=U/'portable_demo.tar.gz'
    with tarfile.open(archive,'w:gz') as tar:tar.add(package,arcname='portable_demo',filter=exclude)
    destination=U/'final_archive';destination.mkdir()
    with tarfile.open(archive,'r:gz') as tar:tar.extractall(destination)
    extracted=destination/'portable_demo';manifest=json.loads((extracted/'PACKAGE_FILES.json').read_text())
    assert all(sha(extracted/name)==digest for name,digest in manifest['files'].items())
    js(U/'metrics/PACKAGE_INTEGRITY.json',dict(sha256=sha(archive),bytes=archive.stat().st_size,extracted_files_verified=len(files),all_exact=True))

def check():
    package=U/'final_archive/portable_demo';run=str(package/'run.sh');root=package/'runs'
    # Exact commands documented in the package, with explicit new outputs.
    command('relocated_cli_image',[run,'export','--scene','lego','--asset',str(package/'saved/lego'),'--kind','image','--output',str(root/'saved_image')])
    assert sha(root/'saved_image/frames/frame_000_image.png')==sha(U/'browser/lego_image.png')
    command('relocated_cli_edit',[run,'edit','--scene','lego','--asset',str(package/'saved/lego'),'--region','1','--ink-strength','.6','--output',str(root/'continued_edit')])
    command('relocated_cli_edited_image',[run,'export','--scene','lego','--asset',str(root/'continued_edit'),'--kind','image','--output',str(root/'continued_image')])
    assert sha(root/'continued_image/frames/frame_000_image.png')==sha(U/'browser/legacy_lego_import.png')
    process=None;output=root/'cold_catalog'
    cmd=[run,'viewer','--scene','lego','--output',str(output),'--port','0'];start=time.monotonic()
    def stopped(signum,frame):raise KeyboardInterrupt('stop owned cold viewer')
    signal.signal(signal.SIGTERM,stopped);signal.signal(signal.SIGINT,stopped)
    checks=[]
    try:
        with (U/'logs/relocated_viewer.log').open('w') as log:
            process=subprocess.Popen(cmd,cwd=package,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            js(U/'logs/relocated_viewer_child.json',dict(pid=process.pid,command=cmd))
            while not (output/'SERVER.json').exists():
                if process.poll() is not None:raise RuntimeError('viewer exited')
                if time.monotonic()-start>45:raise TimeoutError('cold viewer readiness')
                time.sleep(.1)
            url='http://127.0.0.1:'+str(json.loads((output/'SERVER.json').read_text())['port'])
            with urllib.request.urlopen(url+'/state',timeout=15) as response:state=json.loads(response.read())
            for scene in ('lego','chair'):
                from urllib.parse import urlencode
                query=urlencode(dict(scene=state['scene'],example=state['example'],revision=state['revision'],name=scene+'.zip'))
                req=urllib.request.Request(url+'/import?'+query,data=(package/'saved_zips'/(scene+'_saved_asset.zip')).read_bytes(),headers={'Content-Type':'application/zip'})
                with urllib.request.urlopen(req,timeout=45) as response:state=json.loads(response.read())
                assert state['scene']==scene and not state['can_undo']
                reference=json.loads((U/'browser/EXPORT_STATES.json').read_text())[scene]
                for key in ('styles','camera','display','selected_region'):assert state[key]==reference[key],key
                with urllib.request.urlopen(url+state['images']['image'],timeout=15) as response:png=response.read()
                expected=U/'browser/session'/reference['images']['image'].removeprefix('/image/')
                assert png==expected.read_bytes()
                checks.append(dict(scene=scene,PNG_exact=True,styles_camera_display_selection_exact=True,import_new_session=True))
    finally:
        if process is not None:
            if process.poll() is None:process.terminate()
            try:process.wait(timeout=15)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
            js(U/'logs/relocated_viewer_cleanup.json',dict(pid=process.pid,returncode=process.returncode,own_process_exited=True))
    js(U/'metrics/FINAL_ARCHIVE_REPLAY.json',dict(utc=now(),CLI_saved_PNG_exact=True,CLI_continue_edit_PNG_exact=True,
        import_checks=checks,archive_sha256=sha(U/'portable_demo.tar.gz'),command=cmd))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['source','stage','build','check']);a=p.parse_args();globals()[a.phase]()
