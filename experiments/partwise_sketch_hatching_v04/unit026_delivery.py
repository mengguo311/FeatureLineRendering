"""Build and cold-run the self-contained unit026 demo package."""
import runtime
from runtime import js,sha,now,output_guard
from pathlib import Path
import argparse,difflib,json,shutil,subprocess,tarfile,sys,time,signal,os,urllib.request
import numpy as np
from PIL import Image
from unit026_run import U,PREV,SOURCE,hashes,command

def media():
    from media import contact
    p=U/'portable_demo'
    for name in ('browser','cold_browser'):
        assert json.loads((U/name/'BROWSER_VALIDATION.json').read_text())['status']=='PASS'
        assert json.loads((U/name/'CLEANUP.json').read_text())['own_child_groups_only']
    items=[];details=[]
    for scene in ('chair','lego'):
        for name,label in [('baseline','Before'),('edited','Local ink edit')]:
            path=U/'browser'/(scene+'_'+name)
            items.append((scene.title()+' | '+label,Image.open(path/'frame_000_image.png')))
        items.append((scene.title()+' | Cold ZIP import',Image.open(U/'cold_browser'/(scene+'_imported')/'frame_000_image.png')))
        for key,label in [('proxy','Approximate proxy'),('region_rgb','Authored style regions'),('image','Local ink edit')]:
            details.append((scene.title()+' | '+label,Image.open(U/'browser'/(scene+'_edited')/('frame_000_'+key+'.png'))))
    contact(U/'media/two_model_edit_cold.png',items,cols=3,size=512,title='Real-model demo | complete object | local edit and fresh-server cold import')
    contact(U/'media/two_model_proxy_regions.png',details,cols=3,size=512,title='Existing GS-derived proxy | authored regions | fixed 3D hatch paths')
    for kind in ('orbit','zoom'):
        src=U/'cold_browser'/('chair_'+kind)
        shutil.copytree(src,p/'presentations'/('chair_'+kind))
        shutil.copy2(src/'contact_sheet.png',U/'media'/('chair_'+kind+'_all_frames.png'))
        for ext in ('mp4','mkv'):shutil.copy2(src/('animation.'+ext),U/'media'/('chair_'+kind+'.'+ext))
    from asset_archive import unpack_archive
    (p/'saved_zips').mkdir()
    protocol=json.loads((U/'PROTOCOL.json').read_text())
    for scene in ('chair','lego'):
        archive=U/'browser'/(scene+'_edited.zip');shutil.copy2(archive,p/'saved_zips'/archive.name)
        receipt=unpack_archive(archive.read_bytes(),p/'edited_assets'/scene,{scene:protocol['inputs'][scene]['original']['sha256']})
        js(U/'metrics'/(scene+'_package_import.json'),receipt)
    shutil.copytree(U/'media',p/'previews')
    for file in ('chair_edited_desktop.png','lego_edited_desktop.png','layout_1024_bottom.png','layout_390_bottom.png'):
        shutil.copy2(U/'browser'/file,p/'previews'/file)
    shutil.copytree(PREV/'portable_demo/references',p/'references')
    js(U/'metrics/REFERENCE_PROVENANCE.json',dict(source=str(PREV/'portable_demo/references'),files=hashes(p/'references'),newly_rendered_in_unit026=False))

def build():
    p=U/'portable_demo'
    for f in SOURCE.iterdir():
        if f.is_file():shutil.copy2(f,p/'source'/f.name)
    shutil.copy2(SOURCE.parents[1]/'docs/partwise_sketch_hatching_v04/UNIT026_DEMO_README_ZH.md',p/'README_ZH.md')
    shutil.copy2(p/'README_ZH.md',U/'PACKAGE_README_ZH.md')
    validation=dict(unit='unit_026',utc=now(),browser=json.loads((U/'browser/BROWSER_VALIDATION.json').read_text()),cold_browser=json.loads((U/'cold_browser/BROWSER_VALIDATION.json').read_text()),preservation=json.loads((U/'metrics/PRESERVATION.json').read_text()),scientific_seal=False,supervisor_verification='reported_not_independently_verified')
    js(p/'VALIDATION.json',validation)
    files={k:v for k,v in hashes(p).items() if not k.startswith('runs/') and k!='PACKAGE_FILES.json'}
    js(p/'PACKAGE_FILES.json',dict(files=files))
    with tarfile.open(U/'portable_demo.tar.gz','w:gz') as tar:tar.add(p,arcname='portable_demo')
    dest=U/'final_archive';dest.mkdir()
    with tarfile.open(U/'portable_demo.tar.gz','r:gz') as tar:tar.extractall(dest)
    assert all(sha(dest/'portable_demo'/k)==v for k,v in files.items())
    js(U/'metrics/PACKAGE_INTEGRITY.json',dict(archive_sha256=sha(U/'portable_demo.tar.gz'),bytes=(U/'portable_demo.tar.gz').stat().st_size,verified_files=len(files),all_exact=True))
    shutil.copytree(SOURCE,U/'source_snapshot',ignore=shutil.ignore_patterns('__pycache__'))
    js(U/'SOURCE_SNAPSHOT.json',hashes(U/'source_snapshot'))
    diff=[]
    for name in sorted(set(hashes(U/'source_before'))|set(hashes(SOURCE))):
        before=U/'source_before'/name;after=SOURCE/name
        if after.suffix not in ('.py','.html','.cpp','.sh'):continue
        if before.is_file() and after.is_file() and sha(before)==sha(after):continue
        diff.extend(difflib.unified_diff(before.read_text().splitlines(True) if before.exists() else [],after.read_text().splitlines(True) if after.exists() else [],fromfile='before/'+name,tofile='after/'+name))
    (U/'UNIT026_DIFF.patch').write_text(''.join(diff))

def check():
    p=U/'final_archive/portable_demo';run=str(p/'run.sh');out=p/'runs';rows=[]
    def exact(actual,expected):
        assert sha(actual/'frame_000_image.png')==sha(expected/'frame_000_image.png')
        with np.load(actual/'frame_000_arrays.npz') as a,np.load(expected/'frame_000_arrays.npz') as b:
            assert set(a.files)==set(b.files) and all(np.array_equal(a[k],b[k]) for k in a.files)
    for scene in ('chair','lego'):
        command('packaged_cold_'+scene,[run,'export','--scene',scene,'--asset',str(p/'edited_assets'/scene),'--kind','image','--output',str(out/('cold_'+scene))])
        exact(out/('cold_'+scene)/'frames',U/'browser'/(scene+'_edited'));rows.append(dict(scene=scene,PNG_arrays_exact=True))
    command('packaged_lighter',[run,'edit','--scene','chair','--asset',str(p/'edited_assets/chair'),'--region','4','--ink-strength','0.35','--output',str(out/'chair_lighter')])
    command('packaged_lighter_image',[run,'export','--scene','chair','--asset',str(out/'chair_lighter'),'--kind','image','--output',str(out/'chair_lighter_image')])
    exact(out/'chair_lighter_image/frames',U/'browser/chair_baseline')
    for f in (p/'edited_assets/chair').iterdir():
        if f.suffix=='.npz':assert sha(f)==sha(out/'chair_lighter'/f.name)
    replays={}
    for kind in ('orbit','zoom'):
        command('packaged_'+kind,[run,'replay','--scene','chair','--bundle',str(p/'presentations'/('chair_'+kind)),'--output',str(out/('cold_'+kind))])
        r=json.loads((out/('cold_'+kind)/'REPLAY.json').read_text());assert r['all_png_exact'] and r['all_arrays_exact'];replays[kind]=r
    session=out/'cold_viewer';argv=[run,'viewer','--scene','chair','--example','chair_ink_preview','--port','0','--output',str(session)]
    started=now();clock=time.monotonic();imports=[]
    with (U/'logs/packaged_viewer.log').open('w') as log:
        proc=subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            while not (session/'SERVER.json').is_file():
                assert proc.poll() is None,'packaged viewer exited before ready'
                if time.monotonic()-clock>30:raise TimeoutError('packaged viewer start')
                time.sleep(.1)
            port=json.loads((session/'SERVER.json').read_text())['port'];url=f'http://127.0.0.1:{port}'
            def get():
                with urllib.request.urlopen(url+'/state',timeout=30) as response:return json.loads(response.read())
            for scene in ('chair','lego'):
                before=get()
                from urllib.parse import urlencode
                query=urlencode(dict(scene=before['scene'],example=before['example'],revision=before['revision'],name=scene+'_edited.zip'))
                req=urllib.request.Request(url+'/import?'+query,data=(p/'saved_zips'/(scene+'_edited.zip')).read_bytes(),headers={'Content-Type':'application/zip'},method='POST')
                with urllib.request.urlopen(req,timeout=30) as response:loaded=json.loads(response.read())
                assert loaded['scene']==scene and not loaded['render_cache']['hit'] and loaded['render_cache']['builds']==1
                frame=session/loaded['images']['image'].removeprefix('/image/')
                exact(frame.parent,U/'browser'/(scene+'_edited'))
                imports.append(dict(scene=scene,PNG_arrays_exact=True,first_render_without_cache=True))
        finally:
            if proc.poll() is None:
                os.killpg(proc.pid,signal.SIGINT)
                try:proc.wait(timeout=15)
                except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=5)
            js(U/'logs/packaged_viewer.receipt.json',dict(argv=argv,started_utc=started,finished_utc=now(),seconds=time.monotonic()-clock,returncode=proc.returncode,own_process_group=proc.pid,imports=imports))
    assert proc.returncode==0 and len(imports)==2
    js(U/'metrics/FINAL_ARCHIVE_REPLAY.json',dict(utc=now(),archive_sha256=sha(U/'portable_demo.tar.gz'),real_models=rows,inverse_local_edit_exact=True,all_binary_assets_preserved=True,packaged_viewer_imports=imports,replays=replays))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['media','build','check']);a=p.parse_args();globals()[a.phase]()
