"""Serial real source rendering, portable package and relocated cold checks."""
import runtime
from runtime import js,sha,now
from pathlib import Path
import argparse,json,shutil,tarfile,subprocess,time,signal,urllib.request,urllib.error
from unit017_run import U,PREV,SOURCE,hashes,command

def source():
    import numpy as np
    from PIL import Image
    import model_adapter
    from geometry import orbit_camera
    from media import contact
    from demo import new_output
    p=json.loads((U/'PROTOCOL.json').read_text());out=new_output(U/'source_model')
    model_adapter.LIB_PATH=out/'libsource.so';shutil.copy2(PREV/'build/libsource.so',model_adapter.LIB_PATH)
    saved=json.loads((U/'browser/EXPORT_STATE.json').read_text());camera=orbit_camera(**saved['camera'])
    start=time.monotonic();model=model_adapter.load_source(p['original']['original_ply'],p['original']['sha256'])
    result=model_adapter.render_source(model,camera)
    Image.fromarray(np.uint8(np.clip(result['rgb'],0,1)*255+.5)).save(out/'source_rgb.png')
    np.savez_compressed(out/'source_arrays.npz',**result)
    js(out/'RECEIPT.json',dict(original=p['original'],original_gaussians=model['audit']['count'],camera=camera,
        seconds=time.monotonic()-start,adapter='CPU SH3 EWA of original vanilla GS; not independent geometry or GPU equivalence',
        library_sha256=sha(model_adapter.LIB_PATH)))
    raster=U/'browser/session'/saved['images']['image'].removeprefix('/image/')
    contact(U/'media/source_proxy_regions_edit.png',[(label,Image.open(file)) for label,file in [
        ('Actual original GS RGB',out/'source_rgb.png'),('Inherited optional proxy',raster.with_name('frame_000_proxy.png')),
        ('Authored style regions',raster.with_name('frame_000_region_rgb.png')),('Saved named example: ink .40',U/'browser/lego_platform_ink.png'),
        ('Local edit: ink .60',U/'browser/platform_edited.png')]],cols=3,size=512,title='Lego | example selection and session isolation | geometry limitations unchanged')

def stage():
    assert json.loads((U/'browser/BROWSER_VALIDATION.json').read_text())['status']=='PASS'
    package=U/'portable_demo';(package/'source').mkdir()
    for f in (PREV/'portable_demo/source').iterdir():
        if f.is_file():shutil.copy2(SOURCE/f.name,package/'source'/f.name)
    shutil.copytree(U/'browser/exported_asset',package/'saved/edited_asset')
    for kind in ('orbit','zoom'):
        src=U/'browser'/('lego_'+kind)
        shutil.copytree(src,package/'presentations'/('lego_'+kind))
        for suffix in ('mp4','mkv'):shutil.copy2(src/('animation.'+suffix),U/'media'/('lego_'+kind+'.'+suffix))
        shutil.copy2(src/'contact_sheet.png',U/'media'/('lego_'+kind+'_all_frames.png'))
    meta=json.loads((package/'PORTABLE_DEMO.json').read_text());meta.update(source_unit='unit_017',created_utc=now(),
        optional_examples=['lego_bucket_cross','lego_bucket_refined','lego_platform_ink'],default_assets_unchanged=True)
    meta.pop('new_example',None);js(package/'PORTABLE_DEMO.json',meta)
    p=json.loads((U/'PROTOCOL.json').read_text())
    assert all(hashes(package/name)==p['inputs'][name] for name in ('assets','examples'))
    js(U/'metrics/INPUT_PRESERVATION.json',dict(all_four_defaults_and_all_inherited_examples_byte_exact=True,files=p['inputs']))

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
    shutil.copy2(SOURCE.parents[1]/'docs/partwise_sketch_hatching_v04/UNIT017_DEMO_README_ZH.md',package/'README_ZH.md')
    shutil.copy2(package/'README_ZH.md',U/'PACKAGE_README_ZH.md')
    (package/'previews').mkdir()
    for f in (U/'media').iterdir():shutil.copy2(f,package/'previews'/f.name)
    for name in ('02_named_example.png','03_edit_restored.png','04_export_complete.png'):shutil.copy2(U/'browser'/name,package/'previews'/name)
    js(package/'VALIDATION.json',dict(unit='unit_017',utc=now(),browser=json.loads((U/'browser/BROWSER_VALIDATION.json').read_text()),
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
    command('relocated_cli_edit',[run,'edit','--scene','lego','--example','lego_platform_ink','--region','1','--ink-strength','.6','--output',str(root/'cli_edit')])
    command('relocated_cli_image',[run,'export','--scene','lego','--asset',str(root/'cli_edit'),'--kind','image','--output',str(root/'cli_image')])
    assert sha(root/'cli_image/frames/frame_000_image.png')==sha(U/'browser/lego_image.png')
    for f in (package/'saved/edited_asset').iterdir():
        if f.is_file() and f.name!='asset.json':assert sha(f)==sha(root/'cli_edit'/f.name)
    # Named example rejection must occur before any output is written.
    command('wrong_model_example',[run,'edit','--scene','chair','--example','lego_platform_ink','--region','1','--ink-strength','.6','--output',str(root/'invalid')],expected=2)
    assert not (root/'invalid').exists()
    results=[]
    def stopped(signum,frame):raise KeyboardInterrupt('stop owned cold viewer')
    signal.signal(signal.SIGTERM,stopped);signal.signal(signal.SIGINT,stopped)
    for name,args,reference in [
        ('named',['--example','lego_platform_ink'],json.loads((U/'browser/STATES.json').read_text())['lego_platform_ink']),
        ('saved',['--asset',str(package/'saved/edited_asset')],json.loads((U/'browser/EXPORT_STATE.json').read_text()))]:
        process=None;output=root/('cold_'+name)
        cmd=[run,'viewer','--scene','lego',*args,'--output',str(output),'--port','0']
        start=time.monotonic()
        try:
            with (U/'logs'/('cold_'+name+'_viewer.log')).open('w') as log:
                process=subprocess.Popen(cmd,cwd=package,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                js(U/'logs'/('cold_'+name+'_child.json'),dict(pid=process.pid,command=cmd))
                while not (output/'SERVER.json').exists():
                    if process.poll() is not None:raise RuntimeError('viewer exited')
                    if time.monotonic()-start>45:raise TimeoutError('cold viewer readiness')
                    time.sleep(.1)
                url='http://127.0.0.1:'+str(json.loads((output/'SERVER.json').read_text())['port'])
                with urllib.request.urlopen(url+'/state',timeout=15) as response:state=json.loads(response.read())
                for key in ('styles','camera','display','selected_region','demo_example'):assert state[key]==reference[key],key
                if name=='named':
                    assert state['example']=='lego_platform_ink' and len(state['available_examples'])==4
                    try:urllib.request.urlopen(url+'/export?scene=lego&example=default&revision=0',timeout=15)
                    except urllib.error.HTTPError as error:assert error.code==422
                    else:raise AssertionError('stale example asset download accepted')
                else:assert 'available_examples' not in state
                with urllib.request.urlopen(url+state['images']['image'],timeout=15) as response:png=response.read()
                expected=U/'browser'/('lego_platform_ink.png' if name=='named' else 'lego_image.png')
                assert png==expected.read_bytes()
                results.append(dict(kind=name,PNG_exact=True,styles_camera_display_provenance_exact=True,command=cmd,seconds=time.monotonic()-start))
        finally:
            if process is not None:
                if process.poll() is None:process.terminate()
                try:process.wait(timeout=15)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
                js(U/'logs'/('cold_'+name+'_cleanup.json'),dict(pid=process.pid,returncode=process.returncode,own_process_exited=True))
    js(U/'metrics/FINAL_ARCHIVE_REPLAY.json',dict(utc=now(),CLI_named_example_edit=True,CLI_PNG_exact=True,
        wrong_model_example_rejected=True,viewers=results,archive_sha256=sha(U/'portable_demo.tar.gz')))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['source','stage','build','check']);a=p.parse_args();globals()[a.phase]()
