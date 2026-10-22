"""Package and cold-check the frozen unit014 real-model demo."""
import runtime
from runtime import OUTPUT_ROOT,js,sha,now
from pathlib import Path
import argparse,json,shutil,tarfile,subprocess,time,signal,urllib.request
import numpy as np
from unit014_run import refresh, protocol, UNIT as U

def build():
    package=U/'portable_demo'
    for kind in ('orbit','zoom'):
        report=json.loads((package/'runs'/('cold_'+kind)/'REPLAY.json').read_text())
        assert report['all_png_exact'] and report['all_arrays_exact']
    assert json.loads((U/'browser/BROWSER_VALIDATION.json').read_text())['status']=='PASS'
    refresh()
    readme=Path('docs/partwise_sketch_hatching_v04/UNIT014_DEMO_README_ZH.md')
    shutil.copy2(readme,package/'README_ZH.md');shutil.copy2(readme,U/'PACKAGE_README_ZH.md')
    previews=package/'previews';previews.mkdir()
    for file in (U/'media').iterdir():
        if file.is_file():shutil.copy2(file,previews/file.name)
    for name in ('02_short_single.png','02_cross_enabled.png','03_export_complete.png'):
        shutil.copy2(U/'browser'/name,previews/name)
    js(package/'VALIDATION.json',dict(unit='unit_014',utc=now(),
        paths=json.loads((U/'metrics/PATHS.json').read_text()),
        browser=json.loads((U/'browser/BROWSER_VALIDATION.json').read_text()),
        cold_replay={kind:{k:json.loads((package/'runs'/('cold_'+kind)/'REPLAY.json').read_text())[k]
            for k in ('scene','frame_count','all_png_exact','all_arrays_exact')} for kind in ('orbit','zoom')},
        visual_quality='partial; bucket style changes are visible, proxy/contour defects and manual selection limitations unchanged',scientific_seal=False))
    js(package/'PACKAGE_FILES.json',dict(files={str(f.relative_to(package)):sha(f) for f in sorted(package.rglob('*'))
        if f.is_file() and 'runs' not in f.relative_to(package).parts and '__pycache__' not in f.parts and f.name!='PACKAGE_FILES.json'}))
    archive=U/'portable_demo.tar.gz'
    def exclude(info):return None if any(x in ('runs','__pycache__') for x in Path(info.name).parts) else info
    with tarfile.open(archive,'w:gz') as tar:tar.add(package,arcname='portable_demo',filter=exclude)
    destination=U/'final_archive';destination.mkdir()
    with tarfile.open(archive,'r:gz') as tar:tar.extractall(destination)
    extracted=destination/'portable_demo';manifest=json.loads((extracted/'PACKAGE_FILES.json').read_text())
    assert all(sha(extracted/name)==digest for name,digest in manifest['files'].items())
    js(U/'metrics/PACKAGE_INTEGRITY.json',dict(archive='portable_demo.tar.gz',sha256=sha(archive),bytes=archive.stat().st_size,
        extracted_files_verified=len(manifest['files']),all_exact=True,extracted=str(extracted)))
    print(json.dumps(dict(archive_sha256=sha(archive),archive_bytes=archive.stat().st_size,verified_files=len(manifest['files']))))

def check():
    package=U/'final_archive/portable_demo';events=[];p=protocol()
    def command(name,args):
        cmd=[str(package/'run.sh'),*args];start=time.monotonic()
        with (U/'logs'/(name+'.log')).open('w') as log:r=subprocess.run(cmd,cwd=package,stdout=log,stderr=subprocess.STDOUT,timeout=240)
        receipt=dict(command=cmd,cwd=str(package),returncode=r.returncode,seconds=time.monotonic()-start)
        js(U/'logs'/(name+'.receipt.json'),receipt);r.check_returncode();events.append(receipt)
    command('final_cli_edit',['edit','--scene','lego','--region','4','--spacing','.060','--length','.12','--cross','on','--cross-angle','60','--cross-spacing','.075','--output',str(package/'runs/cli_cross')])
    command('final_cli_image',['export','--scene','lego','--asset',str(package/'runs/cli_cross'),'--kind','image','--azimuth','-127','--elevation','30','--distance','5.1','--output',str(package/'runs/cli_image')])
    assert sha(package/'runs/cli_image/frames/frame_000_image.png')==sha(U/'browser/lego_image.png')
    command('final_cli_off',['edit','--scene','lego','--asset',str(package/'runs/cli_cross'),'--region','4','--cross','off','--output',str(package/'runs/cli_off')])
    assert sha(package/'runs/cli_cross/region_4.npz')==sha(package/'runs/cli_off/region_4.npz')
    for name in ('mesh.npz','selection_4.npz','region_1.npz','region_2.npz','region_3.npz'):
        assert sha(package/'assets/lego'/name)==sha(package/'runs/cli_cross'/name)
    with np.load(package/'runs/cli_cross/region_4.npz') as a,np.load(package/'examples/lego_bucket_cross/region_4.npz') as b:
        assert set(a.files)==set(b.files) and all(np.array_equal(a[k],b[k]) for k in a.files)
    out=package/'runs/cold_viewer';cmd=[str(package/'run.sh'),'viewer','--scene','lego','--asset',str(package/'examples/lego_bucket_cross'),'--output',str(out),'--port','0']
    process=None
    def stop(signum,frame):raise KeyboardInterrupt('stop owned package test')
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    try:
        with (U/'logs/final_viewer.log').open('w') as log:
            process=subprocess.Popen(cmd,cwd=package,stdout=log,stderr=subprocess.STDOUT)
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
            assert state['selected_region']==4 and state['manual_regions']==1
            with urllib.request.urlopen(url+state['images']['image'],timeout=15) as r:png=r.read()
            assert png==(U/'browser/lego_image.png').read_bytes()
            with urllib.request.urlopen(url,timeout=15) as r:assert b'id="crossEnabled"' in r.read()
    finally:
        if process is not None:
            if process.poll() is None:process.terminate()
            process.wait(timeout=15)
            js(U/'logs/FINAL_VIEWER_CLEANUP.json',dict(pid=process.pid,returncode=process.returncode,own_process_exited=True))
    js(U/'metrics/FINAL_ARCHIVE_REPLAY.json',dict(utc=now(),documented_CLI_composition=True,CLI_generated_paths_equal_browser=True,
        CLI_PNG_exact=True,cold_viewer_PNG_exact=True,cold_viewer_style_camera_display_exact=True,selected_region_and_history_retained=True,
        archive='portable_demo.tar.gz',archive_sha256=sha(U/'portable_demo.tar.gz'),commands=events))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['build','check']);a=p.parse_args()
    {'build':build,'check':check}[a.phase]()
