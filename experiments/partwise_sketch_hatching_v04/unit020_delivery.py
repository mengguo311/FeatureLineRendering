"""Portable four-model delivery with an optional explicitly manual Chair patch."""
import runtime
from runtime import js,sha,now
from pathlib import Path
import argparse,json,shutil,tarfile,subprocess,time
from unit020_run import U,PREV,SOURCE,protocol,hashes

def command(name,args):
    assert not (U/'logs'/f'{name}.receipt.json').exists()
    start=time.monotonic();began=now()
    with (U/'logs'/f'{name}.log').open('w') as f:r=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,timeout=540)
    js(U/'logs'/f'{name}.receipt.json',dict(command=args,cwd=str(Path.cwd()),start_utc=began,end_utc=now(),seconds=time.monotonic()-start,returncode=r.returncode))
    if r.returncode:raise RuntimeError('command failed: '+name)

def stage():
    review=json.loads((U/'metrics/VISUAL_REVIEW.json').read_text())
    package=U/'portable_demo';package.mkdir()
    for n in ('run.sh','CATALOG.json','PORTABLE_DEMO.json','requirements.txt','TESTED_ENVIRONMENT.json'):shutil.copy2(PREV/'portable_demo'/n,package/n)
    for n in ('assets','examples'):shutil.copytree(PREV/'portable_demo'/n,package/n)
    (package/'source').mkdir()
    for f in (PREV/'portable_demo/source').iterdir():
        if f.is_file():shutil.copy2(SOURCE/f.name,package/'source'/f.name)
    shutil.copytree(U/'assets/authored',package/'candidates/chair_seat_authored')
    shutil.copytree(U/'assets/edited',package/'examples/chair_seat_patch')
    (package/'recipes').mkdir();shutil.copy2(U/'SELECTION_RECIPE.json',package/'recipes/chair_seat.json')
    catalog=json.loads((package/'CATALOG.json').read_text())
    if review['optional_example']:
        catalog.setdefault('examples',{})['chair_seat_patch']=dict(scene='chair',asset='examples/chair_seat_patch',label='Manual seat patch · angle 65',
            description='Two manually placed visible rectangles define a partial seat surface. Region 4 changes direction only; original geometry and outside paths stay fixed. Borders and proxy wrinkles remain.')
    js(package/'CATALOG.json',catalog)
    meta=json.loads((package/'PORTABLE_DEMO.json').read_text())
    for key in ('review_candidate','candidate_promoted'):meta.pop(key,None)
    meta.update(source_unit='unit_020',created_utc=now(),optional_example='chair_seat_patch',visual_quality='partial: useful local artistic control, rectangular patch borders and inherited geometry defects remain',scientific_seal=False)
    js(package/'PORTABLE_DEMO.json',meta)
    p=protocol();assert hashes(package/'assets')==p['inherited_catalog_inputs']['assets']
    assert all(sha(package/'examples'/f)==digest for f,digest in p['inherited_catalog_inputs']['examples'].items())
    previous=json.loads((PREV/'portable_demo/CATALOG.json').read_text());assert catalog['scenes']==previous['scenes']
    assert all(catalog['examples'][k]==v for k,v in previous.get('examples',{}).items())
    js(U/'metrics/INPUT_PRESERVATION.json',dict(all_four_defaults_and_inherited_examples_byte_exact=True,original_catalog_entries_exact=True,new_optional_example=review['optional_example']))

def media_stage():
    for folder in (U/'browser',U/'cold_browser'):assert json.loads((folder/'BROWSER_VALIDATION.json').read_text())['status']=='PASS'
    package=U/'portable_demo';(package/'saved_zips').mkdir()
    shutil.copy2(U/'browser/chair_saved_asset.zip',package/'saved_zips/chair_saved_asset.zip')
    shutil.copytree(U/'browser/exported_asset',package/'saved/chair');(package/'saved/chair/ASSET_MANIFEST.json').unlink()
    for kind in ('orbit','zoom'):
        src=U/'browser'/('chair_'+kind);shutil.copytree(src,package/'presentations'/('chair_'+kind))
        for suffix in ('mp4','mkv'):shutil.copy2(src/('animation.'+suffix),U/'media'/('chair_'+kind+'.'+suffix))
        shutil.copy2(src/'contact_sheet.png',U/'media'/('chair_'+kind+'_all_frames.png'))
    shutil.copy2(U/'cold_browser/cold_import.png',U/'media/cold_import.png')

def build():
    package=U/'portable_demo';cold={};videos={}
    for kind in ('orbit','zoom'):
        r=json.loads((package/'runs'/('cold_'+kind)/'REPLAY.json').read_text());assert r['all_png_exact'] and r['all_arrays_exact']
        cold[kind]={k:r[k] for k in ('scene','frame_count','all_png_exact','all_arrays_exact')}
        videos[kind]=json.loads((package/'presentations'/('chair_'+kind)/'VIDEO_RECEIPTS.json').read_text())
        assert all(v['encode_returncode']==v['decode_returncode']==0 and v['decoded_frames']==r['frame_count'] for v in videos[kind])
        assert next(v for v in videos[kind] if v['file'].endswith('.mkv'))['all_frames_exact']
    js(U/'metrics/COLD_REPLAY.json',cold)
    shutil.copy2(SOURCE.parents[1]/'docs/partwise_sketch_hatching_v04/UNIT020_DEMO_README_ZH.md',package/'README_ZH.md');shutil.copy2(package/'README_ZH.md',U/'PACKAGE_README_ZH.md')
    (package/'previews').mkdir()
    for f in (U/'media').iterdir():shutil.copy2(f,package/'previews'/f.name)
    for folder,name in [(U/'browser','05_export_complete.png'),(U/'cold_browser','04_cold_import_restored.png')]:shutil.copy2(folder/name,package/'previews'/name)
    js(package/'VALIDATION.json',dict(unit='unit_020',utc=now(),real_asset_tests=json.loads((U/'metrics/REAL_ASSET_TEST.json').read_text()),
        browser=json.loads((U/'browser/BROWSER_VALIDATION.json').read_text()),cold_browser=json.loads((U/'cold_browser/BROWSER_VALIDATION.json').read_text()),
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
    import signal,urllib.request
    from urllib.parse import urlencode
    package=U/'final_archive/portable_demo';run=str(package/'run.sh');out=package/'runs'
    command('relocated_cli_image',[run,'export','--scene','chair','--example','chair_seat_patch','--kind','image','--output',str(out/'saved_image')])
    assert sha(out/'saved_image/frames/frame_000_image.png')==sha(U/'browser/chair_image.png')
    command('relocated_cli_author',[run,'author','--scene','chair','--region','2','--selection-recipe',str(package/'recipes/chair_seat.json'),'--name','Manual seat surface patch','--output',str(out/'authored')])
    for n in ('mesh.npz','region_1.npz','region_2.npz','region_3.npz','region_4.npz','selection_4.npz'):assert sha(out/'authored'/n)==sha(package/'candidates/chair_seat_authored'/n),n
    command('relocated_cli_edit',[run,'edit','--scene','chair','--asset',str(out/'authored'),'--region','4','--angle','65','--output',str(out/'edited')])
    for n in ('mesh.npz','region_1.npz','region_2.npz','region_3.npz','region_4.npz'):assert sha(out/'edited'/n)==sha(package/'examples/chair_seat_patch'/n),n
    command('relocated_cli_edited_image',[run,'export','--scene','chair','--asset',str(out/'edited'),'--kind','image','--azimuth','17','--elevation','25','--distance','4.7','--output',str(out/'edited_image')])
    assert sha(out/'edited_image/frames/frame_000_image.png')==sha(U/'renders/edited/frame_000_image.png')
    process=None;destination=out/'cold_catalog';cmd=[run,'viewer','--scene','chair','--example','chair_seat_patch','--output',str(destination),'--port','0']
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
            assert state['example']=='chair_seat_patch' and state['selected_region']==4
            with urllib.request.urlopen(url+state['images']['image'],timeout=15) as r:assert r.read()==(U/'browser/chair_image.png').read_bytes()
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
    js(U/'metrics/FINAL_ARCHIVE_REPLAY.json',dict(utc=now(),CLI_example_PNG_exact=True,CLI_author_mesh_paths_selection_exact=True,
        CLI_local_edit_mesh_paths_PNG_exact=True,cold_catalog_example_and_import_PNG_exact=True,archive_sha256=sha(U/'portable_demo.tar.gz')))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['stage','media_stage','build','check']);a=p.parse_args();globals()[a.phase]()
