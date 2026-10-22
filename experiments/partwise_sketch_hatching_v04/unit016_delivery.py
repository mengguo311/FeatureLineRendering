"""Stage, package and cold-check the saved regional ink demo."""
import runtime
from runtime import js,sha,now
from pathlib import Path
import argparse,json,shutil,tarfile,subprocess,time,signal,urllib.request
from unit016_run import UNIT as U,PREVIOUS,SOURCE,protocol

def stage():
    assert json.loads((U/'browser/BROWSER_VALIDATION.json').read_text())['status']=='PASS'
    package=U/'portable_demo';package.mkdir()
    for name in ('run.sh','CATALOG.json','PORTABLE_DEMO.json','requirements.txt','TESTED_ENVIRONMENT.json'):
        shutil.copy2(PREVIOUS/'portable_demo'/name,package/name)
    for name in ('assets','examples'):shutil.copytree(PREVIOUS/'portable_demo'/name,package/name)
    shutil.copytree(U/'browser/exported_asset',package/'examples/lego_platform_ink')
    for kind in ('orbit','zoom'):
        src=U/'browser'/('lego_'+kind)
        shutil.copytree(src,package/'presentations'/('lego_ink_'+kind))
        for suffix in ('mp4','mkv'):shutil.copy2(src/('animation.'+suffix),U/'media'/('lego_ink_'+kind+'.'+suffix))
        shutil.copy2(src/'contact_sheet.png',U/'media'/('lego_ink_'+kind+'_all_frames.png'))
    (package/'source').mkdir()
    for file in sorted((PREVIOUS/'portable_demo/source').iterdir()):
        if file.is_file():shutil.copy2(SOURCE/file.name,package/'source'/file.name)
    meta=json.loads((package/'PORTABLE_DEMO.json').read_text())
    meta.update(source_unit='unit_016',created_utc=now(),new_example='Lego local platform ink .40; fixed geometry and paths',defaults_unchanged=True)
    js(package/'PORTABLE_DEMO.json',meta)
    default_hashes={}
    for scene in ('chair','lego','drums','ficus'):
        files={f.name:sha(f) for f in (package/'assets'/scene).iterdir() if f.is_file()}
        assert files=={f.name:sha(f) for f in (PREVIOUS/'portable_demo/assets'/scene).iterdir() if f.is_file()}
        default_hashes[scene]=files
    js(U/'metrics/DEFAULT_ASSETS.json',dict(files=default_hashes,all_exact=True))

def build():
    package=U/'portable_demo';cold={};videos={}
    for kind in ('orbit','zoom'):
        r=json.loads((package/'runs'/('cold_'+kind)/'REPLAY.json').read_text())
        assert r['all_png_exact'] and r['all_arrays_exact']
        cold[kind]={k:r[k] for k in ('scene','frame_count','all_png_exact','all_arrays_exact')}
        video=json.loads((package/'presentations'/('lego_ink_'+kind)/'VIDEO_RECEIPTS.json').read_text())
        assert all(v['encode_returncode']==v['decode_returncode']==0 and v['decoded_frames']==r['frame_count'] for v in video)
        assert next(v for v in video if v['file'].endswith('.mkv'))['all_frames_exact']
        videos[kind]=video
    shutil.copy2(Path('docs/partwise_sketch_hatching_v04/UNIT016_DEMO_README_ZH.md'),package/'README_ZH.md')
    shutil.copy2(package/'README_ZH.md',U/'PACKAGE_README_ZH.md')
    (package/'previews').mkdir()
    for file in (U/'media').iterdir():
        if file.is_file():shutil.copy2(file,package/'previews'/file.name)
    for name in ('02_legacy_platform.png','03_local_ink_saved.png','05_export_complete.png'):
        shutil.copy2(U/'browser'/name,package/'previews'/name)
    js(U/'metrics/COLD_REPLAY.json',cold)
    js(package/'VALIDATION.json',dict(unit='unit_016',utc=now(),edit=json.loads((U/'metrics/ASSET_EDIT.json').read_text()),
        browser=json.loads((U/'browser/BROWSER_VALIDATION.json').read_text()),cold_replay=cold,video_decode=videos,
        visual_quality='partial; lighter hatch separates platform visually but reveals dark hole contours. No geometry improvement.',scientific_seal=False))
    js(package/'PACKAGE_FILES.json',dict(files={str(f.relative_to(package)):sha(f) for f in sorted(package.rglob('*'))
        if f.is_file() and 'runs' not in f.relative_to(package).parts and '__pycache__' not in f.parts and f.name!='PACKAGE_FILES.json'}))
    archive=U/'portable_demo.tar.gz'
    def exclude(info):return None if any(x in ('runs','__pycache__') for x in Path(info.name).parts) else info
    with tarfile.open(archive,'w:gz') as tar:tar.add(package,arcname='portable_demo',filter=exclude)
    destination=U/'final_archive';destination.mkdir()
    with tarfile.open(archive,'r:gz') as tar:tar.extractall(destination)
    extracted=destination/'portable_demo';manifest=json.loads((extracted/'PACKAGE_FILES.json').read_text())
    assert all(sha(extracted/name)==digest for name,digest in manifest['files'].items())
    js(U/'metrics/PACKAGE_INTEGRITY.json',dict(archive=archive.name,sha256=sha(archive),bytes=archive.stat().st_size,
        extracted_files_verified=len(manifest['files']),all_exact=True))

def check():
    package=U/'final_archive/portable_demo';events=[]
    def command(name,args):
        cmd=[str(package/'run.sh'),*args];start=time.monotonic()
        with (U/'logs'/(name+'.log')).open('w') as log:r=subprocess.run(cmd,cwd=package,stdout=log,stderr=subprocess.STDOUT,timeout=180)
        receipt=dict(command=cmd,cwd=str(package),returncode=r.returncode,seconds=time.monotonic()-start)
        js(U/'logs'/(name+'.receipt.json'),receipt);r.check_returncode();events.append(receipt)
    command('final_cli_edit',['edit','--scene','lego','--asset',str(package/'examples/lego_bucket_refined'),'--region','1',
                             '--ink-strength','.4','--output',str(package/'runs/cli_ink')])
    for file in (package/'examples/lego_platform_ink').iterdir():
        if file.is_file() and file.name!='asset.json':assert sha(file)==sha(package/'runs/cli_ink'/file.name)
    command('final_cli_image',['export','--scene','lego','--asset',str(package/'runs/cli_ink'),'--kind','image',
                              '--azimuth','-112','--elevation','30','--distance','5.1','--output',str(package/'runs/cli_image')])
    assert sha(package/'runs/cli_image/frames/frame_000_image.png')==sha(U/'browser/lego_image.png')
    # An actual prior-unit legacy image, not two calls to the new implementation.
    command('legacy_default_image',['export','--scene','lego','--asset',str(package/'examples/lego_bucket_refined'),'--kind','image',
                                   '--azimuth','-127','--elevation','30','--distance','5.1','--output',str(package/'runs/legacy_default')])
    assert sha(package/'runs/legacy_default/frames/frame_000_image.png')==sha(PREVIOUS/'browser/lego_image.png')
    out=package/'runs/cold_viewer'
    cmd=[str(package/'run.sh'),'viewer','--scene','lego','--asset',str(package/'examples/lego_platform_ink'),'--output',str(out),'--port','0']
    process=None
    def stop(signum,frame):raise KeyboardInterrupt('stop owned package test')
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    try:
        with (U/'logs/final_viewer.log').open('w') as log:
            process=subprocess.Popen(cmd,cwd=package,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            js(U/'logs/FINAL_VIEWER_CHILD.json',dict(pid=process.pid,command=cmd))
            start=time.monotonic()
            while not (out/'SERVER.json').exists():
                if process.poll() is not None:raise RuntimeError('cold viewer exited')
                if time.monotonic()-start>30:raise TimeoutError('cold viewer readiness')
                time.sleep(.1)
            port=json.loads((out/'SERVER.json').read_text())['port'];url='http://127.0.0.1:'+str(port)
            with urllib.request.urlopen(url+'/state',timeout=15) as r:state=json.loads(r.read())
            saved=json.loads((U/'browser/EXPORT_STATE.json').read_text())
            assert state['styles']==saved['styles'] and state['camera']==saved['camera'] and state['display']==saved['display']
            assert state['selected_region']==1 and state['manual_regions']==1
            with urllib.request.urlopen(url+state['images']['image'],timeout=15) as r:png=r.read()
            assert png==(U/'browser/lego_image.png').read_bytes()
    finally:
        signal.signal(signal.SIGTERM,signal.SIG_IGN);signal.signal(signal.SIGINT,signal.SIG_IGN)
        if process is not None:
            if process.poll() is None:process.terminate()
            try:process.wait(timeout=15)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
            js(U/'logs/FINAL_VIEWER_CLEANUP.json',dict(pid=process.pid,returncode=process.returncode,own_process_exited=True))
    js(U/'metrics/FINAL_ARCHIVE_REPLAY.json',dict(utc=now(),documented_CLI_ink_edit=True,CLI_all_binary_files_equal_browser=True,
        CLI_PNG_exact=True,legacy_unit015_PNG_exact=True,cold_viewer_PNG_exact=True,cold_viewer_style_camera_display_exact=True,
        archive_sha256=sha(U/'portable_demo.tar.gz'),commands=events))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['stage','build','check']);a=p.parse_args();globals()[a.phase]()
