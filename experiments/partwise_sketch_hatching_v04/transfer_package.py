"""Extend a validated saved-model package without writing to its source unit."""
import runtime
from runtime import OUTPUT_ROOT, js, sha, now, output_guard
from pathlib import Path
import argparse, json, shutil, subprocess, sys, os, signal, time, urllib.request
from validate_replays import compare


def run(unit,phase):
    unit=output_guard(unit);p=json.loads((unit/'PROTOCOL.json').read_text())
    scene=p['scene'];previous=Path(p['previous_unit']);old=previous/'portable_demo'
    here=Path(__file__).resolve().parent
    package=unit/'portable_demo'
    if phase=='catalog':
        entries=json.loads((old/'CATALOG.json').read_text())['scenes']
        provenance={}
        for key,entry in entries.items():
            source=old/entry['asset'];dest=unit/'catalog_assets'/key
            shutil.copytree(source,dest)
            provenance[key]=dict(source=str(source),files={f.name:sha(f) for f in source.iterdir() if f.is_file()})
        entries={key:dict(label=entry['label'],asset=f'catalog_assets/{key}') for key,entry in entries.items()}
        entries[scene]=dict(label=scene.capitalize(),asset='assets/baseline')
        js(unit/'CATALOG.json',dict(schema='partwise_scene_catalog_v1',default_scene=scene,scenes=entries))
        js(unit/'CATALOG_INPUTS.json',dict(previous_package_sha256=sha(previous/'portable_demo.tar.gz'),scenes=provenance,
            new_scene_source=scene,new_scene_asset_sha256=sha(unit/'assets/baseline/asset.json')))
    elif phase=='overview':
        from media import contact
        from PIL import Image
        catalog=json.loads((unit/'CATALOG.json').read_text())
        items=[]
        for key in catalog['scenes']:
            revision='0001' if key==scene else '0000'
            image=unit/f'browser_complete/session/{key}/view_{revision}/frame_000_image.png'
            items.append((key.capitalize()+' | saved real-model asset',Image.open(image)))
        contact(unit/'media/four_models.png',items,cols=4,size=384,
                title='Four-model CPU editor | persistent 3D paths | exploratory geometry, foliage remains partial')
    elif phase=='stage':
        shutil.copytree(old,package)
        # Source package has no mutable run directories; fail instead of copying sessions.
        assert not (package/'runs').exists()
        for file in (package/'source').iterdir():
            if file.is_file():shutil.copy2(here/file.name,file)
        shutil.copytree(unit/'assets/edited',package/'assets'/scene)
        for name in ('CATALOG.json','AUTHORING_CATALOG.json'):
            cat=json.loads((package/name).read_text());cat['scenes'][scene]=dict(label=scene.capitalize(),asset=f'assets/{scene}')
            cat['default_scene']=scene;js(package/name,cat)
        dst=package/'previews'/scene;dst.mkdir()
        for file in (unit/'media').iterdir():
            if file.suffix in ('.png','.mkv'):shutil.copy2(file,dst/file.name)
        shutil.copy2(unit/'renders/static_edited/frame_000_image.png',package/'previews'/f'{scene}.png')
        metadata=json.loads((package/'PORTABLE_DEMO.json').read_text())
        metadata.update(scenes=list(json.loads((package/'CATALOG.json').read_text())['scenes']),created_utc=now(),source_unit=unit.name,
                        previous_package_sha256=sha(previous/'portable_demo.tar.gz'))
        metadata['original_models'][scene]=p['original']
        js(package/'PORTABLE_DEMO.json',metadata)
        shutil.copy2(unit/'PACKAGE_README_ZH.md',package/'README_ZH.md')
    elif phase=='replay':
        package=unit/'relocated/portable_demo';cat=json.loads((package/'CATALOG.json').read_text());rows=[]
        for key in cat['scenes']:
            dest=package/f'runs/cold_{key}'
            cmd=[str(package/'run.sh'),'preview','--scene',key,'--output',str(dest)]
            if dest.exists():
                receipt=json.loads((unit/f'logs/portable_preview_{key}.receipt.json').read_text())
                assert receipt['command']==cmd and receipt['returncode']==0
                returncode=receipt['returncode']
            else:
                r=subprocess.run(cmd,cwd=package,timeout=120);r.check_returncode();returncode=r.returncode
            reference=unit/'renders/static_edited' if key==scene else previous/f'catalog_reference/{key}'
            if key=='lego':reference=previous/'renders/static_edited'
            exact=[compare(reference/f'frame_000_{s}',dest/f'frame_000_{s}') for s in ('image.png','arrays.npz')]
            rows.append(dict(scene=key,command=cmd,returncode=returncode,exact_files=exact))
        # Correct-model CLI edit is a real positive control after the mismatch fix.
        edit_cmd=[str(package/'run.sh'),'edit','--scene',scene,'--asset',str(package/'assets'/scene),
                  '--part','2','--angle','45','--output',str(package/'runs/baseline_recreated')]
        edited=subprocess.run(edit_cmd,cwd=package,timeout=120);edited.check_returncode()
        preview_cmd=[str(package/'run.sh'),'preview','--scene',scene,'--asset',str(package/'runs/baseline_recreated'),
                     '--output',str(package/'runs/baseline_preview')]
        rendered=subprocess.run(preview_cmd,cwd=package,timeout=120);rendered.check_returncode()
        exact=[compare(unit/f'renders/static_baseline/frame_000_{s}',package/f'runs/baseline_preview/frame_000_{s}')
               for s in ('image.png','arrays.npz')]
        js(unit/'metrics/PORTABLE_REPLAY.json',dict(status='PASS',scenes=rows,
            actual_edit_command=edit_cmd,edit_returncode=edited.returncode,preview_command=preview_cmd,
            preview_returncode=rendered.returncode,recreated_baseline_exact=exact,
            original_PLY_not_required=True,python_environment_bundled=False))
    elif phase=='reopen':
        package=unit/'relocated/portable_demo'
        asset=package/'runs/imported_asset';shutil.copytree(unit/'exported_reload/asset',asset)
        out=package/'runs/exported_viewer'
        cmd=[sys.executable,str(here/'test_viewer_asset_override.py'),'--unit',str(unit),
             '--package',str(package),'--asset',str(asset),'--output',str(out)]
        result=subprocess.run(cmd,timeout=120);result.check_returncode()
        exact=[compare(unit/f'viewer_smoke/view_0006/frame_000_{s}',out/f'session/view_0000/frame_000_{s}')
               for s in ('image.png','arrays.npz')]
        js(unit/'metrics/EXPORTED_VIEWER_REOPEN.json',dict(status='PASS',command=cmd,returncode=result.returncode,
            exact_files=exact,server_stopped=True,original_PLY_not_required=True,
            source='actual HTTP-exported Ficus asset copied inside relocated package and reopened by run.sh viewer --asset'))
    elif phase=='viewer':
        package=unit/'relocated/portable_demo';out=package/'runs/viewer_smoke'
        cmd=[str(package/'run.sh'),'viewer','--scene',scene,'--port','0','--output',str(out)]
        log=open(unit/'logs/portable_viewer_server.log','w')
        child=subprocess.Popen(cmd,cwd=package,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        js(unit/'metrics/PORTABLE_VIEWER_START.json',dict(command=cmd,pid=child.pid,own_process_group=child.pid))
        def interrupted(signum,frame):raise KeyboardInterrupt('stop own portable viewer test')
        signal.signal(signal.SIGTERM,interrupted)
        def request(url,body=None):
            req=urllib.request.Request(url,data=json.dumps(body).encode() if body else None,headers={'Content-Type':'application/json'})
            with urllib.request.urlopen(req,timeout=30) as response:return response.read()
        try:
            end=time.monotonic()+45
            while not (out/'SERVER.json').is_file():
                if child.poll() is not None:raise RuntimeError('viewer exited')
                if time.monotonic()>end:raise TimeoutError('viewer startup')
                time.sleep(.1)
            port=json.loads((out/'SERVER.json').read_text())['port'];app=f'http://127.0.0.1:{port}'
            state=json.loads(request(app+'/state'));assert state['scene']==scene
            assert b'id="scene"' in request(app+'/')
            rows=[]
            for key in [s for s in state['available_scenes'] if s!=scene]+[scene]:
                state=json.loads(request(app+'/scene',dict(scene=key,from_scene=state['scene'])))
                assert state['scene']==key and request(app+state['images']['image']).startswith(b'\x89PNG')
                rows.append(dict(scene=key,image=state['images']['image'],seconds=state['seconds']))
            js(unit/'metrics/PORTABLE_VIEWER.json',dict(status='PASS',utc=now(),command=cmd,scenes=rows,
                actual_local_HTTP_server=True,scope='relocated launch and scene switches; full browser separately tested'))
        finally:
            if child.poll() is None:os.killpg(child.pid,signal.SIGTERM)
            try:child.wait(timeout=10)
            except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=10)
            log.close();js(unit/'metrics/PORTABLE_VIEWER_CLEANUP.json',dict(pid=child.pid,returncode=child.returncode,own_process_group_only=True))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--unit',type=Path,required=True)
    p.add_argument('phase',choices=['catalog','overview','stage','replay','viewer','reopen']);a=p.parse_args();run(a.unit,a.phase)
