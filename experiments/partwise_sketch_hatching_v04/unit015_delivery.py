"""Portable delivery and cold replay of the separately versioned local proxy."""
import runtime
from runtime import OUTPUT_ROOT,js,sha,now
from pathlib import Path
import argparse,json,shutil,tarfile,subprocess,time,signal,urllib.request,datetime
import numpy as np
from unit015_run import UNIT as U,PREVIOUS,SOURCE,protocol

def stage():
    package=U/'portable_demo';package.mkdir()
    for name in ('run.sh','CATALOG.json','PORTABLE_DEMO.json','requirements.txt','TESTED_ENVIRONMENT.json'):
        shutil.copy2(PREVIOUS/'portable_demo'/name,package/name)
    for name in ('assets','examples'):
        shutil.copytree(PREVIOUS/'portable_demo'/name,package/name)
    shutil.copytree(U/'browser/exported_asset',package/'examples/lego_bucket_refined')
    for kind in ('orbit','zoom'):
        shutil.copytree(U/'browser'/('lego_'+kind),package/'presentations'/('lego_refined_'+kind))
        for suffix in ('mp4','mkv'):
            shutil.copy2(U/'browser'/('lego_'+kind)/('animation.'+suffix),U/'media'/('lego_refined_'+kind+'.'+suffix))
        shutil.copy2(U/'browser'/('lego_'+kind)/'contact_sheet.png',U/'media'/('lego_refined_'+kind+'_all_frames.png'))
    (package/'source').mkdir()
    names=('runtime.py catalog_demo.py demo.py viewer.py viewer.html scene_catalog.py geometry.py hatching.py '
           'render.py display_settings.py region_tools.py screen_selection.py selection_draft.py presentation.py media.py '
           'local_refinement.py refine_proxy.py').split()
    for name in names:shutil.copy2(SOURCE/name,package/'source'/name)
    meta=json.loads((package/'PORTABLE_DEMO.json').read_text())
    meta.update(source_unit='unit_015',created_utc=now(),new_example='Lego opt-in bounded bucket proxy refinement',defaults_unchanged=True)
    js(package/'PORTABLE_DEMO.json',meta)
    js(U/'metrics/INPUT_LOCK.json',dict(protocol_sha256=sha(U/'PROTOCOL.json'),
        default_assets={s:{f.name:sha(f) for f in (package/'assets'/s).iterdir() if f.is_file()} for s in ('chair','lego','drums','ficus')}))

def build():
    package=U/'portable_demo'
    assert json.loads((U/'browser/BROWSER_VALIDATION.json').read_text())['status']=='PASS'
    cold={}
    for kind in ('orbit','zoom'):
        r=json.loads((package/'runs'/('cold_'+kind)/'REPLAY.json').read_text())
        assert r['all_png_exact'] and r['all_arrays_exact']
        cold[kind]={k:r[k] for k in ('scene','frame_count','all_png_exact','all_arrays_exact')}
    shutil.copy2(Path('docs/partwise_sketch_hatching_v04/UNIT015_DEMO_README_ZH.md'),package/'README_ZH.md')
    shutil.copy2(package/'README_ZH.md',U/'PACKAGE_README_ZH.md')
    (package/'previews').mkdir()
    for file in (U/'media').iterdir():
        if file.is_file():shutil.copy2(file,package/'previews'/file.name)
    for name in ('02_refined_bucket.png','03_local_angle_edit.png','05_export_complete.png'):
        shutil.copy2(U/'browser'/name,package/'previews'/name)
    js(package/'VALIDATION.json',dict(unit='unit_015',utc=now(),
        refinement=json.loads((U/'metrics/REFINEMENT.json').read_text()),browser=json.loads((U/'browser/BROWSER_VALIDATION.json').read_text()),
        cold_replay=cold,visual_quality='partial; see before/after and weak views. Exploratory proxy revision is opt-in.',scientific_seal=False))
    js(U/'metrics/COLD_REPLAY.json',cold)
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

def audit_recovery():
    records={}
    for kind in ('orbit','zoom'):
        old=U/'attempt_schedule_overlap'/('cold_'+kind)
        new=U/'portable_demo/runs'/('cold_'+kind)
        files=sorted(f for f in old.iterdir() if f.suffix in ('.png','.npz'))
        assert files and all(sha(file)==sha(new/file.name) for file in files)
        replay=json.loads((new/'REPLAY.json').read_text());assert replay['all_png_exact'] and replay['all_arrays_exact']
        video=json.loads((U/'browser'/('lego_'+kind)/'VIDEO_RECEIPTS.json').read_text())
        assert len(video)==2 and all(v['encode_returncode']==0 and v['decode_returncode']==0 and v['decoded_frames']==replay['frame_count'] for v in video)
        assert next(v for v in video if v['file'].endswith('.mkv'))['all_frames_exact']
        records[kind]=dict(original_available_files=len(files),original_available_files_exact=True,final_frames=replay['frame_count'],all_png_arrays_exact=True,
            lossless_decoded_exact=True,mp4_full_decode_count=True)
    a=json.loads((U/'logs/cold_orbit_recovery.receipt.json').read_text());b=json.loads((U/'logs/cold_zoom_recovery.receipt.json').read_text())
    gap=(datetime.datetime.fromisoformat(b['start_utc'])-datetime.datetime.fromisoformat(a['end_utc'])).total_seconds()
    assert gap>=0
    js(U/'metrics/RECOVERY_AUDIT.json',dict(utc=now(),final_replay_serial_gap_seconds=gap,comparisons=records,original_failure_retained=True))
    amend=json.loads((U/'EXECUTION_AMENDMENT.json').read_text())
    amend['recovery_completed']=dict(browser='logs/browser_recovery.receipt.json',cold_orbit='logs/cold_orbit_recovery.receipt.json',cold_zoom='logs/cold_zoom_recovery.receipt.json',all_returncodes=0,audit='metrics/RECOVERY_AUDIT.json')
    js(U/'EXECUTION_AMENDMENT.json',amend)

def check():
    package=U/'final_archive/portable_demo';events=[]
    def command(name,args):
        cmd=[str(package/'run.sh'),*args];start=time.monotonic()
        with (U/'logs'/(name+'.log')).open('w') as log:r=subprocess.run(cmd,cwd=package,stdout=log,stderr=subprocess.STDOUT,timeout=240)
        receipt=dict(command=cmd,cwd=str(package),returncode=r.returncode,seconds=time.monotonic()-start)
        js(U/'logs'/(name+'.receipt.json'),receipt);r.check_returncode();events.append(receipt)
    command('final_cli_refine',['refine','--scene','lego','--asset',str(package/'examples/lego_bucket_cross'),'--region','4',
                              '--iterations','10','--max-displacement','.018','--output',str(package/'runs/cli_refined')])
    for name in ('mesh.npz','selection_4.npz','region_1.npz','region_2.npz','region_3.npz','region_4.npz'):
        assert sha(package/'runs/cli_refined'/name)==sha(package/'examples/lego_bucket_refined'/name),name
    command('final_cli_image',['export','--scene','lego','--asset',str(package/'runs/cli_refined'),'--kind','image','--azimuth','-127','--elevation','30','--distance','5.1','--output',str(package/'runs/cli_image')])
    assert sha(package/'runs/cli_image/frames/frame_000_image.png')==sha(U/'browser/lego_image.png')
    command('final_cli_edit',['edit','--scene','lego','--asset',str(package/'runs/cli_refined'),'--region','4','--angle','50','--output',str(package/'runs/cli_edited')])
    for name in ('mesh.npz','selection_4.npz','region_1.npz','region_2.npz','region_3.npz','region_4.npz'):
        assert sha(package/'runs/cli_edited'/name)==sha(U/'assets/style_probe'/name),name
    out=package/'runs/cold_viewer'
    cmd=[str(package/'run.sh'),'viewer','--scene','lego','--asset',str(package/'examples/lego_bucket_refined'),'--output',str(out),'--port','0']
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
            meta=json.loads((Path(state['asset'])/'asset.json').read_text())
            assert meta['geometry_history'][-1]['mesh_sha256']==meta['mesh_sha256']
    finally:
        if process is not None:
            if process.poll() is None:process.terminate()
            process.wait(timeout=15)
            js(U/'logs/FINAL_VIEWER_CLEANUP.json',dict(pid=process.pid,returncode=process.returncode,own_process_exited=True))
    js(U/'metrics/FINAL_ARCHIVE_REPLAY.json',dict(utc=now(),documented_CLI_refinement=True,CLI_mesh_and_all_paths_equal_browser=True,
        CLI_PNG_exact=True,CLI_followup_style_edit_paths_exact=True,cold_viewer_PNG_exact=True,cold_viewer_style_camera_display_exact=True,
        geometry_revision_and_selection_retained=True,archive_sha256=sha(U/'portable_demo.tar.gz'),commands=events))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['stage','build','check','audit_recovery']);a=p.parse_args();globals()[a.phase]()
