"""Real Firefox UI test through local WebDriver, using a fresh task-local profile."""
import runtime
from runtime import js, now, sha, output_guard
from pathlib import Path
import argparse
import base64
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request


def run(unit, name, catalog=None, display_controls=False, presentations=False, cross_hatching=False, asset=None, local_refinement=False, ink_strength=False, examples=False, imports=False, cold_import=False, exercise=None):
    unit=output_guard(unit);out=unit/name;out.mkdir()
    profile=out/'fresh_profile';profile.mkdir()
    downloads=out/'downloads';downloads.mkdir()
    logs=[];processes=[];sid=None;base=None;events=[]
    def interrupted(signum,frame):raise KeyboardInterrupt('stop own browser validation')
    signal.signal(signal.SIGTERM,interrupted)
    signal.signal(signal.SIGINT,interrupted)
    def start(command, logfile):
        log=open(logfile,'w');logs.append(log)
        child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        processes.append(child)
        js(out/'OWN_CHILDREN.json',dict(children=[dict(pid=p.pid,process_group=p.pid) for p in processes]))
        return child
    def request(url,method='GET',body=None,timeout=35):
        req=urllib.request.Request(url,method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=timeout) as response:return json.loads(response.read())
    def wait(check,seconds=35):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            try:
                result=check()
                if result:return result
            except (OSError,ValueError,KeyError):pass
            time.sleep(.1)
        raise TimeoutError('browser test condition timed out')
    try:
        source_args=(['--asset',str(asset)] if asset else (['--catalog',str(catalog)] if catalog else ['--asset',str(unit/'assets/baseline')]))
        if cross_hatching and catalog:
            source_args+=['--scene',json.loads((unit/'PROTOCOL.json').read_text())['scene']]
        server=start([sys.executable,str(Path(__file__).with_name('viewer.py')),*source_args,
                      '--output',str(out/'session'),'--port','0'],out/'viewer.log')
        wait(lambda:(out/'session/SERVER.json').is_file())
        port=json.loads((out/'session/SERVER.json').read_text())['port']
        app=f'http://127.0.0.1:{port}'
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));driver_port=sock.getsockname()[1]
        driver=start(['/snap/firefox/current/usr/lib/firefox/geckodriver','--host','127.0.0.1',
                      '--port',str(driver_port),'--profile-root',str(out)],out/'webdriver.log')
        base=f'http://127.0.0.1:{driver_port}'
        wait(lambda:request(base+'/status')['value']['ready'])
        value=request(base+'/session','POST',{'capabilities':{'alwaysMatch':{
            'browserName':'firefox','moz:firefoxOptions':{
                'binary':'/snap/firefox/current/usr/lib/firefox/firefox',
                'args':['-headless','-profile',str(profile)],
                'prefs':{'layers.acceleration.disabled':True,'gfx.webrender.software':True,
                         'webgl.disabled':True,'media.hardware-video-decoding.enabled':False,
                         'browser.shell.checkDefaultBrowser':False,'browser.startup.homepage':'about:blank',
                         'browser.newtabpage.enabled':False,'datareporting.healthreport.uploadEnabled':False,
                         'toolkit.telemetry.enabled':False,'network.prefetch-next':False,
                         'browser.download.folderList':2,'browser.download.dir':str(downloads.resolve()),
                         'browser.download.useDownloadDir':True,'browser.download.alwaysOpenPanel':False,
                         'browser.helperApps.neverAsk.saveToDisk':'application/zip,image/png,video/mp4'}}}}})['value']
        sid=value['sessionId'];root=base+'/session/'+sid
        js(out/'CAPABILITIES.json',dict(browser=value['capabilities']['browserName'],
           version=value['capabilities']['browserVersion'],gpu=False,fresh_profile=str(profile)))
        def execute(script):return request(root+'/execute/sync','POST',{'script':script,'args':[]})['value']
        def click(selector):
            elem=request(root+'/element','POST',{'using':'css selector','value':selector})['value']
            ident=elem['element-6066-11e4-a52e-4f735466cecf']
            request(root+'/element/'+ident+'/click','POST',{})
        def ready():
            return execute("return document.querySelector('#preview').complete && document.querySelector('#preview').naturalWidth === 512 && !document.querySelector('#apply').disabled;")
        def screenshot(name):
            png=request(root+'/screenshot')['value'];(out/(name+'.png')).write_bytes(base64.b64decode(png))
        request(root+'/window/rect','POST',dict(width=1280,height=1100))
        request(root+'/url','POST',{'url':app});wait(ready);screenshot('01_loaded')
        initial=request(app+'/state')
        assert execute('return document.title;')==initial['scene'].title()+' · Partwise Hatch Demo'
        labels=execute("return Array.from(document.querySelector('#region').options).map(x=>x.textContent);")
        assert labels==[initial['regions'][str(k)] for k in sorted(map(int,initial['regions']))]
        events.append(dict(action='scene title and authored region labels match loaded asset',scene=initial['scene'],labels=labels))
        if exercise is not None:
            exercise(unit,out,app,root,request,execute,click,ready,wait,screenshot,downloads)
            return
        if imports or cold_import:
            from import_browser import exercise
            exercise(unit,out,app,root,request,execute,click,ready,wait,screenshot,downloads,cold=cold_import)
            return
        if examples:
            from example_browser import exercise
            exercise(unit,out,app,root,request,execute,click,ready,wait,screenshot,downloads)
            return
        if ink_strength:
            from ink_browser import exercise
            exercise(unit,out,app,root,request,execute,click,ready,wait,screenshot,downloads)
            return
        if local_refinement:
            from refinement_browser import exercise
            exercise(unit,out,app,root,request,execute,click,ready,wait,screenshot,downloads)
            return
        if cross_hatching:
            from crosshatch_browser import exercise
            exercise(unit,out,app,root,request,execute,click,ready,wait,screenshot,downloads)
            return
        edit_angle=45 if display_controls else 95
        execute("document.querySelector('#angle').value="+str(edit_angle)+"; document.querySelector('#angle').dispatchEvent(new Event('input'));")
        click('#apply');wait(lambda:request(app+'/state')['revision']==1);wait(ready);screenshot('02_angle_edit')
        edited=request(app+'/state')
        assert initial['images']['image']!=edited['images']['image']
        for region in sorted(map(int,initial['regions'])):
            if region!=2:assert sha(Path(initial['asset'])/f'region_{region}.npz')==sha(Path(edited['asset'])/f'region_{region}.npz')
        events.append(dict(action='select middle angle and click Render & save',angle=edit_angle,revision=1,other_regions_exact=True))
        if catalog:
            choices=execute("return Array.from(document.querySelector('#scene').options).map(x=>x.value);")
            assert set(choices)==set(initial['available_scenes'])
            for scene in [s for s in choices if s!=initial['scene']]+[initial['scene']]:
                execute("document.querySelector('#scene').value="+json.dumps(scene)+"; document.querySelector('#scene').dispatchEvent(new Event('change'));")
                wait(lambda:request(app+'/state')['scene']==scene);wait(ready)
            restored=request(app+'/state')
            assert restored['asset']==edited['asset'] and restored['revision']==1
            assert restored['styles']==edited['styles']
            screenshot('02b_catalog_restored')
            events.append(dict(action='actual model dropdown visits every scene and restores Ficus edit',scenes=choices,restored_scene=restored['scene']))
        click('#right');wait(lambda:request(app+'/state')['revision']==2);wait(ready)
        click('#closer');wait(lambda:request(app+'/state')['revision']==3);wait(ready);screenshot('03_orbit_zoom')
        events.append(dict(action='Orbit +30 and Zoom in buttons',revision=3))
        click('#regions');wait(ready);screenshot('04_regions')
        request(root+'/refresh','POST',{});wait(ready)
        camera=request(app+'/state')['camera']
        displayed=execute("return Object.fromEntries(['azimuth','elevation','distance'].map(k=>[k,+document.getElementById(k).value]));")
        js(out/'RELOAD_CAMERA.json',dict(server_camera=camera,displayed_controls=displayed))
        assert displayed==camera, 'page reload must restore displayed controls to saved camera'
        screenshot('05_reloaded')
        events.append(dict(action='page reload retains edited image and camera controls',camera=camera))
        if display_controls:
            before=request(app+'/state')
            execute("document.querySelector('#contourStrength').value=.35; document.querySelector('#contourStrength').dispatchEvent(new Event('input'));")
            click('#saveDisplay');wait(lambda:request(app+'/state')['revision']==4);wait(ready)
            reduced=request(app+'/state');assert reduced['display']==dict(contours_visible=True,contour_strength=.35)
            for f in Path(before['asset']).iterdir():
                if f.name!='asset.json' and f.is_file():assert sha(f)==sha(Path(reduced['asset'])/f.name)
            def raster(s):return out/'session'/s['images']['image'].removeprefix('/image/')
            assert sha(raster(before))!=sha(raster(reduced))
            screenshot('06_reduced_contours')
            click('#contoursVisible');click('#saveDisplay');wait(lambda:request(app+'/state')['revision']==5);wait(ready)
            hidden=request(app+'/state');assert not hidden['display']['contours_visible']
            screenshot('07_hidden_contours')
            click('#contoursVisible');click('#saveDisplay');wait(lambda:request(app+'/state')['revision']==6);wait(ready)
            assert sha(raster(request(app+'/state')))==sha(raster(reduced))
            click('#undo');wait(lambda:request(app+'/state')['revision']==7);wait(ready)
            assert sha(raster(request(app+'/state')))==sha(raster(hidden))
            click('#undo');wait(lambda:request(app+'/state')['revision']==8);wait(ready)
            assert sha(raster(request(app+'/state')))==sha(raster(reduced))
            if catalog:
                for scene in ('chair',initial['scene']):
                    execute("document.querySelector('#scene').value="+json.dumps(scene)+"; document.querySelector('#scene').dispatchEvent(new Event('change'));")
                    wait(lambda:request(app+'/state')['scene']==scene);wait(ready)
                    expected=.35 if scene==initial['scene'] else 1.
                    assert request(app+'/state')['display']['contour_strength']==expected
            request(root+'/refresh','POST',{});wait(ready)
            assert execute("return +document.querySelector('#contourStrength').value;")==.35
            assert execute("return document.querySelector('#contoursVisible').checked;") is True
            screenshot('08_display_restored')
            final=request(app+'/state')
            import zipfile,io
            with urllib.request.urlopen(app+'/export',timeout=35) as response:payload=response.read()
            (out/'exported_asset.zip').write_bytes(payload)
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:archive.extractall(out/'exported_asset')
            saved=json.loads((out/'exported_asset/asset.json').read_text())
            assert saved['display']==final['display'] and saved['viewer_camera']==final['camera']
            js(out/'EXPORT_REFERENCE.json',dict(state=final,frame_directory=str(raster(final).parent),zip_sha256=sha(out/'exported_asset.zip')))
            events.append(dict(action='contour strength/hide/show/undo/model isolation/page reload/export',
                display=final['display'],all_paths_byte_exact=True,hidden_and_restored_images_checked=True))
        if presentations:
            import zipfile,shutil
            presentation_results=[]
            protocol=json.loads((unit/'PROTOCOL.json').read_text())
            for scene in ('chair','ficus'):
                execute("document.querySelector('#scene').value="+json.dumps(scene)+"; document.querySelector('#scene').dispatchEvent(new Event('change'));")
                wait(lambda:request(app+'/state')['scene']==scene);wait(ready)
                current=request(app+'/state')
                # Explicitly exercise a real local edit for both objects.
                if current['styles']['2']['angle']!=45:
                    revision=current['revision']
                    execute("document.querySelector('#region').value='2'; document.querySelector('#region').dispatchEvent(new Event('change'));document.querySelector('#angle').value=45;")
                    click('#apply');wait(lambda:request(app+'/state')['revision']==revision+1);wait(ready)
                current=request(app+'/state')
                if current['display']['contour_strength']!=.35:
                    revision=current['revision']
                    execute("document.querySelector('#contourStrength').value=.35;")
                    click('#saveDisplay');wait(lambda:request(app+'/state')['revision']==revision+1);wait(ready)
                c=protocol['scenes'][scene]['camera'];revision=request(app+'/state')['revision']
                execute('for(const [k,v] of Object.entries('+json.dumps(c)+'))document.getElementById(k).value=v;')
                click('#updateView');wait(lambda:request(app+'/state')['revision']==revision+1);wait(ready)
                saved=request(app+'/state');js(out/(scene+'_EXPORT_STATE.json'),saved)
                for key,kind in [('downloadPng','image'),('exportOrbit','orbit'),('exportZoom','zoom')]:
                    prior={p.name for p in downloads.iterdir()}
                    click('#'+key)
                    wait(lambda:execute("return !document.querySelector('#downloadPng').disabled && document.querySelector('#exportLinks a') !== null;"),seconds=240)
                    def finished_download():
                        candidates=[p for p in downloads.iterdir() if p.name not in prior and p.suffix in ('.png','.zip')]
                        return candidates[0] if candidates and not list(downloads.glob('*.part')) else None
                    downloaded=wait(finished_download,seconds=20)
                    destination=out/(scene+'_'+kind+downloaded.suffix);shutil.copy2(downloaded,destination)
                    if kind=='image':
                        source=out/'session'/saved['images']['image'].removeprefix('/image/')
                        assert sha(destination)==sha(source)
                        entry=dict(scene=scene,kind=kind,actual_browser_download=True,png_exact=True,file=destination.name)
                    else:
                        extracted=out/(scene+'_'+kind)
                        with zipfile.ZipFile(destination) as archive:archive.extractall(extracted)
                        receipt=json.loads((extracted/'PRESENTATION.json').read_text())
                        assert receipt['scene']==scene and receipt['kind']==kind
                        assert receipt['all_proxy_vertices_inside'] and receipt['paths_regenerated'] is False
                        meta=json.loads((extracted/'asset/asset.json').read_text())
                        assert meta['styles']==saved['styles'] and meta['display']==saved['display']
                        assert meta['viewer_camera']==saved['camera']
                        for f in Path(saved['asset']).iterdir():
                            if f.is_file() and f.name!='asset.json':assert sha(f)==sha(extracted/'asset'/f.name)
                        entry=dict(scene=scene,kind=kind,actual_browser_download=True,archive=destination.name,
                                   frame_count=receipt['frame_count'],all_inside=True,snapshot_paths_exact=True,seconds=receipt['seconds'])
                    assert request(app+'/state')['revision']==saved['revision']
                    presentation_results.append(entry)
                    js(out/'PRESENTATIONS.json',dict(status='in_progress',exports=presentation_results))
                screenshot(scene+'_export_complete')
            # Failed stale-scene export cannot silently capture the newly selected object.
            try:request(app+'/presentation','POST',dict(scene='chair',revision=saved['revision'],kind='image'))
            except urllib.error.HTTPError as error:assert error.code==422
            else:raise AssertionError('stale scene export accepted')
            js(out/'PRESENTATIONS.json',dict(status='PASS',exports=presentation_results,stale_scene_rejected=True))
            events.append(dict(action='Actual PNG/orbit/zoom buttons download both edited models',exports=presentation_results))
        js(out/'BROWSER_VALIDATION.json',dict(utc=now(),status='PASS',events=events,
            actual_browser=True,software_rendering=True,scope='finite local UI operations, not human usability or performance certification'))
    finally:
        # Repeated external termination must not interrupt cleanup of our own
        # viewer/WebDriver groups. The first signal has already stopped work.
        signal.signal(signal.SIGTERM,signal.SIG_IGN)
        signal.signal(signal.SIGINT,signal.SIG_IGN)
        if sid is not None:
            try:request(base+'/session/'+sid,'DELETE',timeout=3)
            except OSError:pass
        cleanup=[]
        for process in reversed(processes):
            if process.poll() is None:
                os.killpg(process.pid,signal.SIGTERM)
                try:process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=10)
            # Only this test's own process groups are eligible for cleanup.
            try:os.killpg(process.pid,signal.SIGTERM)
            except ProcessLookupError:pass
            cleanup.append(dict(pid=process.pid,returncode=process.returncode))
        for log in logs:log.close()
        js(out/'CLEANUP.json',dict(utc=now(),own_child_groups_only=True,children=cleanup))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--unit',type=Path,required=True)
    p.add_argument('--name',required=True);p.add_argument('--catalog',type=Path)
    p.add_argument('--display-controls',action='store_true')
    p.add_argument('--presentations',action='store_true')
    p.add_argument('--cross-hatching',action='store_true')
    p.add_argument('--asset',type=Path);p.add_argument('--local-refinement',action='store_true')
    p.add_argument('--ink-strength',action='store_true')
    p.add_argument('--examples',action='store_true')
    p.add_argument('--imports',action='store_true');p.add_argument('--cold-import',action='store_true')
    a=p.parse_args();run(a.unit,a.name,a.catalog,a.display_controls,a.presentations,a.cross_hatching,a.asset,a.local_refinement,a.ink_strength,a.examples,a.imports,a.cold_import)
