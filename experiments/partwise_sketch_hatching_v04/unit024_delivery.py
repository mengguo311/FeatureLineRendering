"""Package validated code/assets, then execute documented cold commands."""
import runtime
from runtime import js,sha,now
from pathlib import Path
import argparse,json,shutil,tarfile,sys,difflib
import numpy as np
from unit024_run import U,PREV,SOURCE,protocol,hashes,command

def stage_media():
    p=U/'portable_demo'
    for folder in ('browser','cold_browser'):
        assert json.loads((U/folder/'BROWSER_VALIDATION.json').read_text())['status']=='PASS'
        assert json.loads((U/folder/'CLEANUP.json').read_text())['own_child_groups_only']
    for kind in ('orbit','zoom'):
        src=U/'cold_browser'/('chair_'+kind)
        shutil.copytree(src,p/'presentations'/('chair_'+kind))
        for suffix in ('mp4','mkv'):shutil.copy2(src/('animation.'+suffix),U/'media'/('chair_'+kind+'.'+suffix))
        shutil.copy2(src/'contact_sheet.png',U/'media'/('chair_'+kind+'_all_frames.png'))
        records=json.loads((src/'VIDEO_RECEIPTS.json').read_text())
        assert all(r['encode_returncode']==r['decode_returncode']==0 for r in records)
        assert all(r['decoded_frames']==(12 if kind=='orbit' else 6) for r in records)
        assert next(r for r in records if r['file'].endswith('.mkv'))['all_frames_exact']
    (p/'saved_zips').mkdir();shutil.copy2(U/'browser/chair_edited.zip',p/'saved_zips/chair_edited.zip')
    (p/'previews').mkdir()
    for f in (U/'media').iterdir():shutil.copy2(f,p/'previews'/f.name)
    shutil.copy2(U/'browser/02_ink_edit.png',p/'previews/browser_ink_edit.png')
    interrupted=json.loads((U/'logs/COLD_BROWSER_OUTER_INTERRUPTION.json').read_text())
    interrupted.update(child_completed_behavior=True,browser_validation='cold_browser/BROWSER_VALIDATION.json',cleanup='cold_browser/CLEANUP.json',
        recovery='No duplicate browser run: original child completed both exports and cleanup. Independent relocated CLI cold replay provides known return codes.')
    js(U/'logs/COLD_BROWSER_OUTER_INTERRUPTION.json',interrupted)

def build():
    p=U/'portable_demo'
    for f in (p/'source').iterdir():
        if f.is_file():shutil.copy2(SOURCE/f.name,f)
    shutil.copy2(SOURCE.parents[1]/'docs/partwise_sketch_hatching_v04/UNIT024_DEMO_README_ZH.md',p/'README_ZH.md')
    shutil.copy2(p/'README_ZH.md',U/'PACKAGE_README_ZH.md')
    keys=['STATIC','TIMINGS_FINAL','REGRESSIONS','PRESERVATION','VISUAL_REVIEW']
    validation={k.lower():json.loads((U/'metrics'/f'{k}.json').read_text()) for k in keys}
    validation.update(unit='unit_024',utc=now(),new_cache_tests=4,
        browser=json.loads((U/'browser/BROWSER_VALIDATION.json').read_text()),
        cold_browser=json.loads((U/'cold_browser/BROWSER_VALIDATION.json').read_text()),
        retained_outer_interruption=json.loads((U/'logs/COLD_BROWSER_OUTER_INTERRUPTION.json').read_text()),
        scientific_seal=False,supervisor_verification='reported_not_independently_verified')
    js(p/'VALIDATION.json',validation)
    files={n:v for n,v in hashes(p).items() if not n.startswith('runs/') and n!='PACKAGE_FILES.json'}
    js(p/'PACKAGE_FILES.json',dict(files=files))
    with tarfile.open(U/'portable_demo.tar.gz','w:gz') as tar:
        tar.add(p,arcname='portable_demo',filter=lambda info:None if any(x in ('runs','__pycache__') for x in Path(info.name).parts) else info)
    dest=U/'final_archive';dest.mkdir()
    with tarfile.open(U/'portable_demo.tar.gz','r:gz') as tar:tar.extractall(dest)
    assert all(sha(dest/'portable_demo'/n)==v for n,v in files.items())
    js(U/'metrics/PACKAGE_INTEGRITY.json',dict(archive_sha256=sha(U/'portable_demo.tar.gz'),bytes=(U/'portable_demo.tar.gz').stat().st_size,verified_files=len(files),all_exact=True))
    shutil.copytree(SOURCE,U/'source_snapshot',ignore=shutil.ignore_patterns('__pycache__'))
    js(U/'SOURCE_SNAPSHOT.json',hashes(U/'source_snapshot'))
    diff=[]
    for name in sorted(set(hashes(U/'source_before'))|set(hashes(SOURCE))):
        before=U/'source_before'/name;after=SOURCE/name
        if after.suffix not in ('.py','.html','.cpp','.sh'):continue
        if before.is_file() and after.is_file() and sha(before)==sha(after):continue
        diff.extend(difflib.unified_diff(before.read_text().splitlines(True) if before.exists() else [],after.read_text().splitlines(True) if after.exists() else [],fromfile='before/'+name,tofile='after/'+name))
    (U/'UNIT024_DIFF.patch').write_text(''.join(diff))

def check(receipt_prefix='relocated_'):
    p=U/'final_archive/portable_demo';run=str(p/'run.sh');out=p/'runs'
    sequence=[
        ('cold_image',['export','--scene','chair','--example','chair_ink_preview','--kind','image','--output',str(out/'cold_image')]),
        ('darker',['edit','--scene','chair','--example','chair_ink_preview','--region','4','--ink-strength','0.8','--output',str(out/'darker')]),
        ('darker_image',['export','--scene','chair','--asset',str(out/'darker'),'--kind','image','--output',str(out/'darker_image')]),
        ('dim_again',['edit','--scene','chair','--asset',str(out/'darker'),'--region','4','--ink-strength','0.35','--output',str(out/'dim_again')]),
        ('dim_again_image',['export','--scene','chair','--asset',str(out/'dim_again'),'--kind','image','--output',str(out/'dim_again_image')])]
    for name,args in sequence:command(receipt_prefix+name,[run,*args])
    for name,arm in [('cold_image','edited'),('darker_image','baseline'),('dim_again_image','edited')]:
        assert sha(out/name/'frames/frame_000_image.png')==sha(U/'renders'/arm/'frame_000_image.png')
    for f in (p/'examples/chair_ink_preview').iterdir():
        if f.name!='asset.json':assert sha(f)==sha(out/'dim_again'/f.name)
    # A new process loads the actual browser ZIP and does its first uncached draw.
    code="import sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);import runtime;from asset_archive import unpack_archive;from viewer import Editor;unpack_archive(Path(sys.argv[2]).read_bytes(),Path(sys.argv[3]),{'chair':sys.argv[5]});e=Editor(Path(sys.argv[3]),Path(sys.argv[4]));assert not e.record['render_cache']['hit'];assert e.record['render_cache']['builds']==1"
    command(receipt_prefix+'ZIP_cold_editor',[sys.executable,'-c',code,str(p/'source'),str(p/'saved_zips/chair_edited.zip'),str(out/'imported'),str(out/'cold_editor'),protocol()['original']['sha256']])
    assert sha(out/'cold_editor/view_0000/frame_000_image.png')==sha(U/'renders/edited/frame_000_image.png')
    replays={}
    for kind in ('orbit','zoom'):
        command(receipt_prefix+kind,[run,'replay','--scene','chair','--bundle',str(p/'presentations'/('chair_'+kind)),'--output',str(out/('cold_'+kind))])
        r=json.loads((out/('cold_'+kind)/'REPLAY.json').read_text());assert r['all_png_exact'] and r['all_arrays_exact'];replays[kind]=r
    js(U/'metrics/FINAL_ARCHIVE_REPLAY.json',dict(utc=now(),archive_sha256=sha(U/'portable_demo.tar.gz'),cold_image_edit_inverse_exact=True,
        actual_ZIP_fresh_editor_first_draw_cache_miss=True,cold_ZIP_PNG_exact=True,all_binary_asset_files_retained=True,replays=replays))

def check_final():check('final_')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['stage_media','build','check','check_final']);a=p.parse_args();globals()[a.phase]()
