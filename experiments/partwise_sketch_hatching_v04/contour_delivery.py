"""Package/reopen the actual saved contour controls without modifying old units."""
import runtime
from runtime import OUTPUT_ROOT,js,sha,now,output_guard
from pathlib import Path
import argparse,json,shutil,subprocess,sys,tarfile,time,urllib.request,urllib.error,os,signal
from validate_replays import compare

HERE=Path(__file__).resolve().parent

def command(unit,name,args,cwd=None):
    receipt=unit/'logs'/f'{name}.receipt.json'
    if receipt.exists():
        saved=json.loads(receipt.read_text())
        assert saved['command']==args and saved['returncode']==0, 'only resume an identical already successful command'
        return saved['returncode']
    start=now();t=time.monotonic()
    result=subprocess.run(args,cwd=cwd,capture_output=True,text=True,timeout=180)
    (unit/'logs'/f'{name}.log').write_text(result.stdout+result.stderr)
    js(unit/'logs'/f'{name}.receipt.json',dict(command=args,cwd=str(cwd or Path.cwd()),start_utc=start,end_utc=now(),seconds=time.monotonic()-t,returncode=result.returncode))
    result.check_returncode();return result.returncode

def run(unit,phase):
    unit=output_guard(unit);p=json.loads((unit/'PROTOCOL.json').read_text());previous=Path(p['previous_unit']);old=previous/'portable_demo'
    if phase=='catalog':
        cat=json.loads((old/'CATALOG.json').read_text());sources={}
        for scene,entry in cat['scenes'].items():
            source=old/entry['asset'];dest=unit/'catalog_assets'/scene;shutil.copytree(source,dest)
            sources[scene]=dict(source=str(source),files={f.name:sha(f) for f in source.iterdir() if f.is_file()})
            entry['asset']=f'catalog_assets/{scene}'
        cat['default_scene']='ficus';js(unit/'CATALOG.json',cat);js(unit/'CATALOG_INPUTS.json',sources)
    elif phase=='stage':
        package=unit/'portable_demo';shutil.copytree(old,package)
        assert not (package/'runs').exists()
        for f in (package/'source').iterdir():
            if f.is_file():shutil.copy2(HERE/f.name,f)
        shutil.copy2(HERE/'display_settings.py',package/'source/display_settings.py')
        for scene in ('ficus','chair'):shutil.copytree(unit/'assets'/scene/'reduced',package/'assets'/f'{scene}_contours35')
        preview=package/'previews/unit011';preview.mkdir()
        for f in (unit/'media').iterdir():
            if f.suffix in ('.png','.mkv'):shutil.copy2(f,preview/f.name)
        shutil.copy2(unit/'browser/08_display_restored.png',preview/'viewer.png')
        shutil.copy2(unit/'PACKAGE_README_ZH.md',package/'README_ZH.md')
        metadata=json.loads((package/'PORTABLE_DEMO.json').read_text())
        metadata.update(source_unit=unit.name,created_utc=now(),previous_package_sha256=sha(previous/'portable_demo.tar.gz'),
            contour_display='Saved global on/off and [0,1] strength, legacy default preserved',default_assets_unchanged=True)
        js(package/'PORTABLE_DEMO.json',metadata)
        with tarfile.open(unit/'portable_demo.tar.gz','w:gz') as archive:archive.add(package,arcname='portable_demo')
        relocated=unit/'relocated';relocated.mkdir()
        with tarfile.open(unit/'portable_demo.tar.gz') as archive:archive.extractall(relocated,filter='data')
        js(unit/'metrics/PACKAGE.json',dict(archive_sha256=sha(unit/'portable_demo.tar.gz'),bytes=(unit/'portable_demo.tar.gz').stat().st_size,
            dependencies_bundled=False,original_PLY_required=False,source_files={f.name:sha(f) for f in (package/'source').iterdir() if f.is_file()}))
    elif phase=='refresh':
        package=unit/'portable_demo';old_archive=unit/'attempt_camera_sizes/portable_demo.tar.gz'
        (unit/'portable_demo.tar.gz').rename(old_archive)
        shutil.copy2(unit/'metrics/PACKAGE.json',unit/'attempt_camera_sizes/PACKAGE.json')
        for f in (unit/'media').iterdir():
            if f.suffix in ('.png','.mkv'):shutil.copy2(f,package/'previews/unit011'/f.name)
        shutil.copy2(unit/'browser/06_reduced_contours.png',package/'previews/unit011/viewer_controls.png')
        with tarfile.open(unit/'portable_demo.tar.gz','w:gz') as archive:archive.add(package,arcname='portable_demo')
        # Changed previews only. Check every executable and asset against the
        # relocated package actually exercised before creating the final archive.
        for sub in ('source','assets'):
            for f in (package/sub).rglob('*'):
                if f.is_file():assert sha(f)==sha(unit/'relocated/portable_demo'/f.relative_to(package))
        metadata=json.loads((unit/'metrics/PACKAGE.json').read_text())
        metadata.update(archive_sha256=sha(unit/'portable_demo.tar.gz'),bytes=(unit/'portable_demo.tar.gz').stat().st_size,
            preview_resolution_corrected=True,executable_and_asset_content_exact_to_tested_relocated_package=True,
            original_archive_retained=str(old_archive))
        js(unit/'metrics/PACKAGE.json',metadata)
        final=unit/'relocated_final';final.mkdir()
        with tarfile.open(unit/'portable_demo.tar.gz') as archive:archive.extractall(final,filter='data')
        package=final/'portable_demo';out=package/'runs/final_cold_ficus'
        command(unit,'final_archive_preview',[str(package/'run.sh'),'preview','--scene','ficus','--asset',str(package/'assets/ficus_contours35'),'--output',str(out)],package)
        rows=[compare(unit/f'renders/ficus/reduced/frame_000_{s}',out/f'frame_000_{s}') for s in ('image.png','arrays.npz')]
        js(unit/'metrics/FINAL_ARCHIVE_REPLAY.json',dict(status='PASS',archive_sha256=sha(unit/'portable_demo.tar.gz'),exact_files=rows))
    elif phase=='replay':
        package=unit/'relocated/portable_demo';rows=[]
        for scene in ('chair','lego','drums','ficus'):
            out=package/f'runs/cold_{scene}'
            cmd=[str(package/'run.sh'),'preview','--scene',scene,'--output',str(out)]
            rc=command(unit,f'portable_preview_{scene}',cmd,package)
            reference=previous/f'relocated/portable_demo/runs/cold_{scene}'
            exact=[compare(reference/f'frame_000_{suffix}',out/f'frame_000_{suffix}') for suffix in ('image.png','arrays.npz')]
            rows.append(dict(scene=scene,command=cmd,returncode=rc,exact_files=exact))
        reduced=package/'runs/ficus_soft'
        command(unit,'portable_display',[str(package/'run.sh'),'display','--scene','ficus','--contour-strength','.35','--output',str(reduced)],package)
        out=package/'runs/ficus_soft_preview'
        command(unit,'portable_soft_preview',[str(package/'run.sh'),'preview','--scene','ficus','--asset',str(reduced),'--output',str(out)],package)
        exact=[compare(unit/f'renders/ficus/reduced/frame_000_{suffix}',out/f'frame_000_{suffix}') for suffix in ('image.png','arrays.npz')]
        edited=package/'runs/ficus_soft_edited'
        command(unit,'portable_edit',[str(package/'run.sh'),'edit','--scene','ficus','--asset',str(reduced),'--part','2','--angle','45','--output',str(edited)],package)
        out=package/'runs/ficus_soft_edited_preview'
        command(unit,'portable_edited_preview',[str(package/'run.sh'),'preview','--scene','ficus','--asset',str(edited),'--output',str(out)],package)
        edit_exact=[compare(unit/f'renders/ficus/edited_reduced/frame_000_{suffix}',out/f'frame_000_{suffix}') for suffix in ('image.png','arrays.npz')]
        js(unit/'metrics/PORTABLE_REPLAY.json',dict(status='PASS',default_scenes=rows,reduced_exact=exact,edited_reduced_exact=edit_exact,
            scope='Fresh documented commands in relocated package; original model not needed. Four old default images and arrays match unit010 exactly.'))
    elif phase=='export':
        package=unit/'relocated/portable_demo';asset=package/'runs/imported_asset';shutil.copytree(unit/'browser/exported_asset',asset)
        reference=json.loads((unit/'browser/EXPORT_REFERENCE.json').read_text());folder=Path(reference['frame_directory'])
        meta=json.loads((asset/'asset.json').read_text());camera=meta['viewer_camera'];out=package/'runs/export_cli'
        cmd=[sys.executable,str(package/'source/demo.py'),'render','--scene',meta['scene'],'--asset',str(asset),'--output',str(out)]
        for k,v in camera.items():cmd+=['--'+k,str(v)]
        command(unit,'export_cold_cli',cmd,package)
        rows=[compare(folder/f'frame_000_{s}',out/f'frame_000_{s}') for s in ('image.png','arrays.npz')]
        session=package/'runs/export_viewer'
        cmd=[str(package/'run.sh'),'viewer','--scene',meta['scene'],'--asset',str(asset),'--output',str(session),'--port','0']
        log=open(unit/'logs/export_viewer.log','w');child=subprocess.Popen(cmd,cwd=package,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        js(unit/'metrics/EXPORT_VIEWER_START.json',dict(command=cmd,pid=child.pid,own_process_group=child.pid))
        def interrupted(signum,frame):raise KeyboardInterrupt('stop own export viewer test')
        signal.signal(signal.SIGTERM,interrupted)
        try:
            end=time.monotonic()+45
            while not (session/'SERVER.json').is_file():
                if child.poll() is not None:raise RuntimeError('viewer exited')
                if time.monotonic()>end:raise TimeoutError('viewer start')
                time.sleep(.1)
            port=json.loads((session/'SERVER.json').read_text())['port'];url=f'http://127.0.0.1:{port}'
            def request(path,body=None):
                req=urllib.request.Request(url+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json'})
                with urllib.request.urlopen(req,timeout=30) as response:return json.loads(response.read())
            state=request('/state');assert state['display']==meta['display'] and state['camera']==camera and state['styles']==meta['styles']
            rows += [compare(folder/f'frame_000_{s}',session/f'view_0000/frame_000_{s}') for s in ('image.png','arrays.npz')]
            invalid=[]
            for data in ({'contour_strength':-1},{'contour_strength':1.01},{'contour_strength':float('nan')},{'contours_visible':0},{'contour_strenght':.35}):
                try:request('/display',dict(revision=0,display=data))
                except urllib.error.HTTPError as error:
                    assert error.code==422;invalid.append(dict(input=str(data),status=error.code,body=error.read().decode()))
                else:raise AssertionError('invalid display accepted')
                assert request('/state')==state
            try:request('/display',dict(revision=-1,display=meta['display']))
            except urllib.error.HTTPError as error:assert error.code==422
            else:raise AssertionError('stale revision accepted')
            assert request('/state')==state
            js(unit/'metrics/EXPORT_REPLAY.json',dict(status='PASS',cold_cli_and_viewer_exact=rows,display=state['display'],camera=state['camera'],
                invalid_HTTP_requests=invalid,stale_revision_rejected=True,invalid_requests_leave_state_exact=True,
                browser_server_stopped_before_reopen=True,scope='Exported ZIP copied to relocated package, fresh CLI process and fresh HTTP viewer'))
        finally:
            if child.poll() is None:os.killpg(child.pid,signal.SIGTERM)
            try:child.wait(timeout=10)
            except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=10)
            log.close();js(unit/'metrics/EXPORT_VIEWER_CLEANUP.json',dict(pid=child.pid,returncode=child.returncode,own_process_group_only=True))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['catalog','stage','refresh','replay','export']);p.add_argument('--unit',type=Path,default=OUTPUT_ROOT/'units/unit_011');a=p.parse_args();run(a.unit,a.phase)
