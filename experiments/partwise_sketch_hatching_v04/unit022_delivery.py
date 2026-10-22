"""Package validated restore demo; replay the relocated documented commands."""
import runtime
from runtime import js,sha,now
from pathlib import Path
import argparse,json,shutil,tarfile,sys
import numpy as np
from unit022_run import U,PREV,SOURCE,protocol,hashes,command

def media_stage():
    for folder in ('browser','cold_browser'):assert json.loads((U/folder/'BROWSER_VALIDATION.json').read_text())['status']=='PASS'
    package=U/'portable_demo'
    for kind in ('orbit','zoom'):
        src=U/'cold_browser'/('chair_'+kind)
        shutil.copytree(src,package/'presentations'/('chair_'+kind))
        for suffix in ('mp4','mkv'):shutil.copy2(src/('animation.'+suffix),U/'media'/('chair_'+kind+'.'+suffix))
        shutil.copy2(src/'contact_sheet.png',U/'media'/('chair_'+kind+'_all_frames.png'))
    (package/'saved_zips').mkdir()
    shutil.copy2(U/'browser/chair_edited.zip',package/'saved_zips/chair_edited.zip')
    shutil.copy2(U/'cold_browser/chair_restored.zip',package/'saved_zips/chair_restored.zip')

def build():
    package=U/'portable_demo';cold={};videos={}
    for f in (package/'source').iterdir():
        if f.is_file():shutil.copy2(SOURCE/f.name,f)
    for kind in ('orbit','zoom'):
        r=json.loads((package/'runs'/('cold_'+kind)/'REPLAY.json').read_text())
        assert r['all_png_exact'] and r['all_arrays_exact']
        cold[kind]={k:r[k] for k in ('scene','frame_count','all_png_exact','all_arrays_exact')}
        video=json.loads((package/'presentations'/('chair_'+kind)/'VIDEO_RECEIPTS.json').read_text())
        assert all(v['encode_returncode']==v['decode_returncode']==0 and v['decoded_frames']==r['frame_count'] for v in video)
        assert next(v for v in video if v['file'].endswith('.mkv'))['all_frames_exact']
        videos[kind]=video
    js(U/'metrics/COLD_REPLAY.json',cold)
    shutil.copy2(SOURCE.parents[1]/'docs/partwise_sketch_hatching_v04/UNIT022_DEMO_README_ZH.md',package/'README_ZH.md')
    shutil.copy2(package/'README_ZH.md',U/'PACKAGE_README_ZH.md')
    (package/'previews').mkdir()
    for f in (U/'media').iterdir():shutil.copy2(f,package/'previews'/f.name)
    shutil.copy2(U/'cold_browser/03_restored.png',package/'previews/browser_restored.png')
    js(package/'VALIDATION.json',dict(unit='unit_022',utc=now(),restore_tests=5,regressions=json.loads((U/'metrics/REGRESSIONS.json').read_text()),
        static=json.loads((U/'metrics/STATIC.json').read_text()),visual_review=json.loads((U/'metrics/VISUAL_REVIEW.json').read_text()),
        browser=json.loads((U/'browser/BROWSER_VALIDATION.json').read_text()),cold_browser=json.loads((U/'cold_browser/BROWSER_VALIDATION.json').read_text()),
        retained_outer_interruption=json.loads((U/'logs/COLD_BROWSER_OUTER_INTERRUPTION.json').read_text()),
        bounded_recovery=json.loads((U/'ENGINEERING_RECOVERY.json').read_text()),
        recovery_browser=json.loads((U/'cold_browser_receipt/BROWSER_VALIDATION.json').read_text()),
        cold_replay=cold,video_decode=videos,scientific_seal=False))
    files={k:v for k,v in hashes(package).items() if not k.startswith('runs/') and k!='PACKAGE_FILES.json'}
    js(package/'PACKAGE_FILES.json',dict(files=files))
    with tarfile.open(U/'portable_demo.tar.gz','w:gz') as tar:
        tar.add(package,arcname='portable_demo',filter=lambda info:None if any(x in ('runs','__pycache__') for x in Path(info.name).parts) else info)
    dest=U/'final_archive';dest.mkdir()
    with tarfile.open(U/'portable_demo.tar.gz','r:gz') as tar:tar.extractall(dest)
    assert all(sha(dest/'portable_demo'/n)==v for n,v in files.items())
    js(U/'metrics/PACKAGE_INTEGRITY.json',dict(sha256=sha(U/'portable_demo.tar.gz'),bytes=(U/'portable_demo.tar.gz').stat().st_size,verified_files=len(files),all_exact=True))

def check():
    package=U/'final_archive/portable_demo';run=str(package/'run.sh');out=package/'runs'
    command('relocated_restore',[run,'restore','--scene','chair','--example','chair_seat_restorable','--region','4','--output',str(out/'restored')])
    command('relocated_image',[run,'export','--scene','chair','--asset',str(out/'restored'),'--kind','image','--output',str(out/'restored_image')])
    assert sha(out/'restored_image/frames/frame_000_image.png')==sha(U/'renders/authored/frame_000_image.png')
    command('relocated_author',[run,'author','--scene','chair','--region','2','--selection-recipe',str(package/'recipes/chair_seat.json'),'--name','Manual seat surface patch','--output',str(out/'authored')])
    command('relocated_edit',[run,'edit','--scene','chair','--asset',str(out/'authored'),'--region','4','--angle','65','--output',str(out/'edited')])
    command('relocated_reset',[run,'restore','--scene','chair','--asset',str(out/'edited'),'--region','4','--output',str(out/'reset')])
    command('relocated_reset_image',[run,'export','--scene','chair','--asset',str(out/'reset'),'--kind','image','--azimuth','33','--elevation','27','--distance','4.9','--output',str(out/'reset_image')])
    assert sha(out/'reset_image/frames/frame_000_image.png')==sha(U/'renders/authored/frame_000_image.png')
    for n in ('mesh.npz','region_1.npz','region_2.npz','region_3.npz','region_4.npz','origin_4.npz','selection_4.npz'):
        assert sha(out/'reset'/n)==sha(U/'assets/authored'/n),n
    # Fresh Python process imports only the extracted runtime and ZIP, restores,
    # then renders through the same documented entrypoint.
    code="import sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);import runtime;from asset_archive import unpack_archive;from region_restore import restore_region;unpack_archive(Path(sys.argv[2]).read_bytes(),Path(sys.argv[3]),{'chair':sys.argv[5]});restore_region(Path(sys.argv[3]),Path(sys.argv[4]),4)"
    command('relocated_cold_import',[sys.executable,'-c',code,str(package/'source'),str(package/'saved_zips/chair_edited.zip'),str(out/'imported'),str(out/'import_restored'),protocol()['original']['sha256']])
    command('relocated_import_image',[run,'export','--scene','chair','--asset',str(out/'import_restored'),'--kind','image','--output',str(out/'import_image')])
    assert sha(out/'import_image/frames/frame_000_image.png')==sha(U/'renders/authored/frame_000_image.png')
    js(U/'metrics/FINAL_ARCHIVE_REPLAY.json',dict(utc=now(),documented_example_restore_PNG_exact=True,documented_author_edit_restore_PNG_paths_exact=True,
        new_process_ZIP_import_restore_PNG_exact=True,archive_sha256=sha(U/'portable_demo.tar.gz')))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['media_stage','build','check']);a=p.parse_args();globals()[a.phase]()
