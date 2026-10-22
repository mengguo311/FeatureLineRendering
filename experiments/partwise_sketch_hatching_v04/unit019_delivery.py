"""Package and independently cold-replay the current Chair candidate only."""
import runtime
from runtime import js,sha,now
from pathlib import Path
import argparse,json,shutil,tarfile,subprocess,time,signal,urllib.request
from unit019_run import U,PREV,SOURCE,protocol,hashes,command
COLD=U/'cold_browser_recovery'

def stage():
    review=json.loads((U/'metrics/VISUAL_REVIEW.json').read_text());assert not review['optional_example']
    package=U/'portable_demo';package.mkdir()
    for name in ('run.sh','CATALOG.json','PORTABLE_DEMO.json','requirements.txt','TESTED_ENVIRONMENT.json'):
        shutil.copy2(PREV/'portable_demo'/name,package/name)
    for name in ('assets','examples'):shutil.copytree(PREV/'portable_demo'/name,package/name)
    (package/'source').mkdir()
    for f in (PREV/'portable_demo/source').iterdir():
        if f.is_file():shutil.copy2(SOURCE/f.name,package/'source'/f.name)
    example=package/'candidates/chair_middle_refined';shutil.copytree(U/'assets/refined',example)
    meta=json.loads((example/'asset.json').read_text());meta['viewer_camera']=protocol()['viewer_camera'];meta['selected_region']=2;js(example/'asset.json',meta)
    meta=json.loads((package/'PORTABLE_DEMO.json').read_text());meta.update(source_unit='unit_019',created_utc=now(),
        review_candidate='candidates/chair_middle_refined',candidate_promoted=False,
        visual_quality='partial: marginal local change, unchanged thin-part defects',scientific_seal=False)
    js(package/'PORTABLE_DEMO.json',meta)
    p=protocol();assert hashes(package/'assets')==p['inherited_catalog_inputs']['assets']
    assert all(sha(package/'examples'/f)==digest for f,digest in p['inherited_catalog_inputs']['examples'].items())
    assert sha(package/'CATALOG.json')==sha(PREV/'portable_demo/CATALOG.json')
    js(U/'metrics/INPUT_PRESERVATION.json',dict(all_four_defaults_catalog_and_inherited_examples_byte_exact=True,unpromoted_candidate='candidates/chair_middle_refined'))

def media_stage():
    for folder in (U/'browser',COLD):assert json.loads((folder/'BROWSER_VALIDATION.json').read_text())['status']=='PASS'
    package=U/'portable_demo';(package/'saved_zips').mkdir()
    shutil.copy2(U/'browser/chair_saved_asset.zip',package/'saved_zips/chair_saved_asset.zip')
    shutil.copytree(U/'browser/exported_asset',package/'saved/chair')
    (package/'saved/chair/ASSET_MANIFEST.json').unlink()
    for kind in ('orbit','zoom'):
        src=U/'browser'/('chair_'+kind);shutil.copytree(src,package/'presentations'/('chair_'+kind))
        for suffix in ('mp4','mkv'):shutil.copy2(src/('animation.'+suffix),U/'media'/('chair_'+kind+'.'+suffix))
        shutil.copy2(src/'contact_sheet.png',U/'media'/('chair_'+kind+'_all_frames.png'))
    shutil.copy2(COLD/'cold_import.png',U/'media/cold_import.png')

def build():
    package=U/'portable_demo';cold={};videos={}
    for kind in ('orbit','zoom'):
        r=json.loads((package/'runs'/('cold_'+kind)/'REPLAY.json').read_text());assert r['all_png_exact'] and r['all_arrays_exact']
        cold[kind]={k:r[k] for k in ('scene','frame_count','all_png_exact','all_arrays_exact')}
        videos[kind]=json.loads((package/'presentations'/('chair_'+kind)/'VIDEO_RECEIPTS.json').read_text())
        assert all(v['encode_returncode']==v['decode_returncode']==0 and v['decoded_frames']==r['frame_count'] for v in videos[kind])
        assert next(v for v in videos[kind] if v['file'].endswith('.mkv'))['all_frames_exact']
    js(U/'metrics/COLD_REPLAY.json',cold)
    shutil.copy2(SOURCE.parents[1]/'docs/partwise_sketch_hatching_v04/UNIT019_DEMO_README_ZH.md',package/'README_ZH.md')
    shutil.copy2(package/'README_ZH.md',U/'PACKAGE_README_ZH.md')
    (package/'previews').mkdir()
    for f in (U/'media').iterdir():shutil.copy2(f,package/'previews'/f.name)
    for folder,name in [(U/'browser','05_export_complete.png'),(COLD,'04_cold_import_restored.png')]:shutil.copy2(folder/name,package/'previews'/name)
    js(package/'VALIDATION.json',dict(unit='unit_019',utc=now(),real_asset_tests=json.loads((U/'metrics/REAL_ASSET_TEST.json').read_text()),
        browser=json.loads((U/'browser/BROWSER_VALIDATION.json').read_text()),cold_browser=json.loads((COLD/'BROWSER_VALIDATION.json').read_text()),
        cold_replay=cold,video_decode=videos,visual_review=json.loads((U/'metrics/VISUAL_REVIEW.json').read_text()),scientific_seal=False))
    files={k:v for k,v in hashes(package).items() if not k.startswith('runs/') and k!='PACKAGE_FILES.json'};js(package/'PACKAGE_FILES.json',dict(files=files))
    archive=U/'portable_demo.tar.gz'
    def exclude(info):return None if any(x in ('runs','__pycache__') for x in Path(info.name).parts) else info
    with tarfile.open(archive,'w:gz') as tar:tar.add(package,arcname='portable_demo',filter=exclude)
    dest=U/'final_archive';dest.mkdir()
    with tarfile.open(archive,'r:gz') as tar:tar.extractall(dest)
    extracted=dest/'portable_demo';assert all(sha(extracted/n)==v for n,v in files.items())
    js(U/'metrics/PACKAGE_INTEGRITY.json',dict(sha256=sha(archive),bytes=archive.stat().st_size,extracted_files_verified=len(files),all_exact=True))

def check():
    package=U/'final_archive/portable_demo';run=str(package/'run.sh');out=package/'runs'
    candidate=package/'candidates/chair_middle_refined'
    command('relocated_cli_image',[run,'export','--scene','chair','--asset',str(candidate),'--kind','image','--output',str(out/'saved_image')])
    assert sha(out/'saved_image/frames/frame_000_image.png')==sha(U/'browser/chair_image.png')
    command('relocated_cli_refine',[run,'refine','--scene','chair','--region','2','--iterations','10','--max-displacement','.018','--output',str(out/'refined')])
    for name in ('mesh.npz','region_1.npz','region_2.npz','region_3.npz'):assert sha(out/'refined'/name)==sha(candidate/name),name
    command('relocated_cli_edit',[run,'edit','--scene','chair','--asset',str(candidate),'--region','2','--angle','65','--output',str(out/'continued_edit')])
    command('relocated_cli_edited_image',[run,'export','--scene','chair','--asset',str(out/'continued_edit'),'--kind','image','--output',str(out/'continued_image')])
    assert sha(out/'continued_image/frames/frame_000_image.png')==sha(U/'renders/style_probe/frame_000_image.png')
    process=None;destination=out/'cold_catalog';cmd=[run,'viewer','--scene','chair','--output',str(destination),'--port','0']
    def stopped(signum,frame):raise KeyboardInterrupt('stop owned cold viewer')
    signal.signal(signal.SIGTERM,stopped);signal.signal(signal.SIGINT,stopped)
    try:
        with (U/'logs/relocated_viewer.log').open('w') as log:
            process=subprocess.Popen(cmd,cwd=package,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            js(U/'logs/relocated_viewer_child.json',dict(pid=process.pid,command=cmd));start=time.monotonic()
            while not (destination/'SERVER.json').exists():
                if process.poll() is not None:raise RuntimeError('viewer exited')
                if time.monotonic()-start>45:raise TimeoutError('cold viewer readiness')
                time.sleep(.1)
            url='http://127.0.0.1:'+str(json.loads((destination/'SERVER.json').read_text())['port'])
            with urllib.request.urlopen(url+'/state',timeout=15) as r:state=json.loads(r.read())
            assert state['example']=='default'
            from urllib.parse import urlencode
            query=urlencode(dict(scene=state['scene'],example=state['example'],revision=state['revision'],name='chair.zip'))
            req=urllib.request.Request(url+'/import?'+query,data=(package/'saved_zips/chair_saved_asset.zip').read_bytes(),headers={'Content-Type':'application/zip'})
            with urllib.request.urlopen(req,timeout=45) as r:state=json.loads(r.read())
            reference=json.loads((U/'browser/EXPORT_STATE.json').read_text())
            for key in ('scene','styles','camera','display','selected_region'):assert state[key]==reference[key],key
            with urllib.request.urlopen(url+state['images']['image'],timeout=15) as r:assert r.read()==(U/'browser/chair_image.png').read_bytes()
    finally:
        if process is not None:
            if process.poll() is None:process.terminate()
            try:process.wait(timeout=15)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
            js(U/'logs/relocated_viewer_cleanup.json',dict(pid=process.pid,returncode=process.returncode,own_process_exited=True))
    js(U/'metrics/FINAL_ARCHIVE_REPLAY.json',dict(utc=now(),CLI_candidate_PNG_exact=True,CLI_refinement_mesh_paths_exact=True,
        CLI_local_edit_PNG_exact=True,cold_catalog_and_import_PNG_exact=True,archive_sha256=sha(U/'portable_demo.tar.gz')))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['stage','media_stage','build','check']);a=p.parse_args();globals()[a.phase]()
