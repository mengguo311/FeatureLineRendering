"""Real Firefox multi-scene and pointer selection UI test through local WebDriver, using a fresh task-local profile."""
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
import numpy as np
from demo import load_asset
from geometry import ray_surface
from screen_selection import visible_faces


def run(unit, name):
    unit=output_guard(unit);out=unit/name;out.mkdir()
    profile=out/'fresh_profile';profile.mkdir()
    logs=[];processes=[];sid=None;base=None;events=[]
    def interrupted(signum,frame):
        raise KeyboardInterrupt(f'Interrupted by signal {signum}; cleaning own children')
    signal.signal(signal.SIGTERM,interrupted)
    def start(command, logfile):
        log=open(logfile,'w');logs.append(log)
        child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        processes.append(child)
        js(out/'OWN_CHILDREN.json',dict(children=[dict(pid=p.pid,own_process_group=p.pid) for p in processes]))
        return child
    def request(url,method='GET',body=None):
        req=urllib.request.Request(url,method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=35) as response:return json.loads(response.read())
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
        server=start([sys.executable,str(Path(__file__).with_name('viewer.py')),'--catalog',str(unit/'CATALOG.json'),
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
                         'toolkit.telemetry.enabled':False,'network.prefetch-next':False}}}}})['value']
        sid=value['sessionId'];root=base+'/session/'+sid
        js(out/'CAPABILITIES.json',dict(browser=value['capabilities']['browserName'],
           version=value['capabilities']['browserVersion'],gpu=False,fresh_profile=str(profile)))
        def execute(script):return request(root+'/execute/sync','POST',{'script':script,'args':[]})['value']
        def click(selector):
            elem=request(root+'/element','POST',{'using':'css selector','value':selector})['value']
            ident=elem['element-6066-11e4-a52e-4f735466cecf']
            request(root+'/element/'+ident+'/click','POST',{})
        def ready():
            return execute("return document.querySelector('#preview').complete && document.querySelector('#preview').naturalWidth === 512 && !document.querySelector('#updateView').disabled;")
        def screenshot(name):
            png=request(root+'/screenshot')['value'];(out/(name+'.png')).write_bytes(base64.b64decode(png))
        request(root+'/window/rect','POST',dict(width=1280,height=1800))
        request(root+'/url','POST',{'url':app});wait(ready);screenshot('01_loaded')
        initial=request(app+'/state')
        protocol=json.loads((unit/'PROTOCOL.json').read_text());recipe=protocol['selection']
        original_asset=Path(initial['asset'])
        original_hashes={f.name:sha(f) for f in original_asset.iterdir() if f.is_file()}
        def pointer(points):
            execute("document.querySelector('#preview').scrollIntoView({block:'center'});")
            bounds=execute("const b=document.querySelector('#preview').getBoundingClientRect();return {x:b.left,y:b.top,w:b.width,h:b.height};")
            def move(point):
                return dict(type='pointerMove',duration=150,origin='viewport',
                    x=round(bounds['x']+point[0]/512*bounds['w']),y=round(bounds['y']+point[1]/512*bounds['h']))
            actions=[move(points[0]),dict(type='pointerDown',button=0)]
            if len(points)>1:actions.append(move(points[1]))
            actions.append(dict(type='pointerUp',button=0))
            request(root+'/actions','POST',dict(actions=[dict(type='pointer',id='mouse',parameters=dict(pointerType='mouse'),actions=actions)]))
            request(root+'/actions','DELETE')
        def revision():return request(app+'/state')['revision']
        def rejected(path,body):
            body={'scene':request(app+'/state')['scene'],**body}
            try:request(app+path,'POST',body)
            except urllib.error.HTTPError as error:
                assert error.code==422;return
            raise AssertionError('invalid request accepted: '+path)
        def navigate(az,el,dist=4.9):
            before=request(app+'/state');old_ids=json.loads((out/'session/lego/DRAFT.json').read_text()).get('face_ids') if before['draft'] else None
            execute(f"for(const [k,v] of {json.dumps([['azimuth',((az+180)%360)-180],['elevation',el],['distance',dist]])})document.getElementById(k).value=v;")
            click('#updateView');wait(lambda:revision()==before['revision']+1);wait(ready)
            after=request(app+'/state')
            assert after['asset']==before['asset']
            if old_ids is not None:
                assert json.loads((out/'session/lego/DRAFT.json').read_text())['face_ids']==old_ids
                rejected('/author',dict(token=before['draft']['token'],name='stale'))
            return after
        def select(step):
            before=request(app+'/state');count=before['draft']['step_count'] if before['draft'] else 0
            execute(f"document.querySelector('#selectionOperation').value={json.dumps(step['operation'])};")
            rect=step['rectangle'];pointer([rect[:2],rect[2:]])
            wait(lambda:(request(app+'/state').get('draft') or {}).get('step_count')==count+1);wait(ready)
            current=request(app+'/state');assert current['revision']==before['revision']
            assert current['asset']==str(original_asset)
            assert original_hashes=={f.name:sha(f) for f in original_asset.iterdir() if f.is_file()}
            return current
        def switch_scene(scene):
            click('#scene');click('#scene option[value="'+scene+'"]')
            wait(lambda:request(app+'/state')['scene']==scene);wait(ready)
            assert execute("return document.querySelector('#scene').value;")==scene
            screenshot('scene_'+scene+'_'+str(len(events)))
            return request(app+'/state')
        assert set(initial['available_scenes'])=={'chair','lego','drums'}
        chair=switch_scene('chair')
        assert execute("return document.title.startsWith('Chair');")
        rejected('/view',dict(scene='lego',revision=chair['revision'],azimuth=10,elevation=30,distance=5))
        assert request(app+'/state')['scene']=='chair'
        switch_scene('drums');switch_scene('lego')
        events.append(dict(action='three real model dropdown selections; stale scene mutation rejected',scenes=['chair','drums','lego']))
        pointer([[10,10]])
        wait(lambda:execute("return document.querySelector('#status').textContent.includes('background:');"))
        pointer([[315,125]])
        wait(lambda:execute("return document.querySelector('#region').value === '3';"));wait(ready)
        execute("document.querySelector('#interaction').value='visible';document.querySelector('#interaction').dispatchEvent(new Event('change'));")
        name_element=request(root+'/element','POST',{'using':'css selector','value':'#regionName'})['value']['element-6066-11e4-a52e-4f735466cecf']
        request(root+'/element/'+name_element+'/clear','POST',{})
        request(root+'/element/'+name_element+'/value','POST',{'text':recipe['name']})
        select(recipe['steps'][0]);click('#clearSelection')
        wait(lambda:request(app+'/state')['draft'] is None);wait(ready)
        assert revision()==0
        events.append(dict(action='actual pointer pick, first draft, clear',asset_unchanged=True))
        steps=[]
        for index,step in enumerate(recipe['steps']):
            if index:
                camera=step['camera'];view=camera['view'].split('_')
                navigate(float(view[1]),float(view[2]),float(view[3]))
            state=select(step);steps.append(state['draft']['steps'][-1])
            screenshot(f'0{index+2}_selection_step')
            if index==0:
                ids_before=json.loads((out/'session/lego/DRAFT.json').read_text())['face_ids']
                lego_token=state['draft']['token']
                switch_scene('chair');switch_scene('drums');switch_scene('lego')
                assert json.loads((out/'session/lego/DRAFT.json').read_text())['face_ids']==ids_before
                assert request(app+'/state')['draft']['token']==lego_token
                assert execute("return document.querySelector('#regionName').value;")==recipe['name']
                events.append(dict(action='Lego draft and name survive two other models and return',face_count=len(ids_before)))
            assert execute("return document.querySelector('#apply').disabled;")
            rejected('/selection',dict(revision=-1,source_region=3,mode='visible',rectangle=step['rectangle'],operation='add'))
        final_ids=json.loads((out/'session/lego/DRAFT.json').read_text())['face_ids']
        with np.load(unit/'assets/baseline/selection_4.npz') as f:np.testing.assert_array_equal(final_ids,f['face_ids'])
        token=request(app+'/state')['draft']['token']
        click('#undoSelection');wait(lambda:request(app+'/state')['draft']['step_count']==len(recipe['steps'])-1);wait(ready)
        assert request(app+'/state')['draft']['face_count']<len(final_ids)
        rejected('/author',dict(token=token,name='stale selection'))
        select(recipe['steps'][-1])
        assert json.loads((out/'session/lego/DRAFT.json').read_text())['face_ids']==final_ids
        request(root+'/refresh','POST',{});wait(ready)
        assert execute("return !document.querySelector('#saveRegion').disabled;")
        assert execute("return document.querySelector('#interaction').value;")=='visible'
        assert execute("return document.querySelector('#regionName').value;")==recipe['name']
        assert execute("return document.querySelector('#region').value;")=='3'
        click('#hatch');wait(ready);click('#showSelection');wait(ready);screenshot('06_total_preview_after_refresh')
        assert json.loads((out/'session/lego/DRAFT.json').read_text())['face_ids']==final_ids
        events.append(dict(action='three actual pointer rectangles across three views, undo last step, redo, refresh and total preview',
            steps=steps,final_face_count=len(final_ids),CLI_face_ids_exact=True,original_asset_unmodified=True,
            display_width=execute("return document.querySelector('#preview').getBoundingClientRect().width;")))
        before=revision();click('#saveRegion');wait(lambda:revision()==before+1);wait(ready)
        authored=request(app+'/state');assert authored['draft'] is None and len(authored['regions'])==4
        assert execute("return document.querySelector('#region').value;")=='4'
        assert authored['regions']['4']==recipe['name']
        for r in (1,2,3,4):assert sha(Path(authored['asset'])/f'region_{r}.npz')==sha(unit/f'assets/baseline/region_{r}.npz')
        screenshot('07_region_saved')
        execute("document.querySelector('#angle').value=35;document.querySelector('#angle').dispatchEvent(new Event('input'));")
        before=revision();click('#apply');wait(lambda:revision()==before+1);wait(ready)
        click('#hatch');wait(ready);screenshot('08_region_angle_edit')
        edited=request(app+'/state')
        for r in (1,2,3,4):assert sha(Path(edited['asset'])/f'region_{r}.npz')==sha(unit/f'assets/edited/region_{r}.npz')
        switch_scene('chair');switch_scene('lego')
        assert request(app+'/state')['asset']==edited['asset']
        assert request(app+'/state')['styles']==edited['styles']
        events.append(dict(action='single region commit and angle35 edit',CLI_paths_exact=True,other_regions_exact=True))
        execute("for(const [k,v] of [['spacing',.06],['length',.16],['width',1.6]])document.getElementById(k).value=v;")
        before=revision();click('#apply');wait(lambda:revision()==before+1);wait(ready)
        changed=request(app+'/state');assert all(changed['styles']['4'][k]==v for k,v in [('spacing',.06),('length',.16),('width',1.6)])
        for r in (1,2,3):assert sha(Path(edited['asset'])/f'region_{r}.npz')==sha(Path(changed['asset'])/f'region_{r}.npz')
        before=revision();click('#undo');wait(lambda:revision()==before+1);wait(ready)
        assert request(app+'/state')['styles']==edited['styles']
        before=revision();click('#right');wait(lambda:revision()==before+1);wait(ready)
        before=revision();click('#closer');wait(lambda:revision()==before+1);wait(ready)
        current=request(app+'/state');assert current['asset']==edited['asset']
        request(root+'/refresh','POST',{});wait(ready);screenshot('09_orbit_zoom_export')
        with urllib.request.urlopen(app+'/export',timeout=20) as response:(out/'export.zip').write_bytes(response.read())
        import zipfile,io
        with zipfile.ZipFile(out/'export.zip') as z:meta=json.loads(z.read('asset.json'))
        assert meta['viewer_camera']==current['camera'] and meta['selected_region']==4
        assert meta['regions']['4']==recipe['name']
        events.append(dict(action='spacing/length/width, undo, camera-only orbit/zoom, refresh, export',camera=current['camera'],
            navigation_asset_identity_unchanged=True,export_camera_exact=True))
        # Export every model, then cold replay in new processes after server cleanup.
        exported=[]
        for scene in ('chair','drums','lego'):
            rec=switch_scene(scene)
            with urllib.request.urlopen(app+'/export',timeout=20) as response:(out/(scene+'_export.zip')).write_bytes(response.read())
            exported.append(dict(scene=scene,camera=rec['camera'],revision=rec['revision'],asset=rec['asset'],
                                 image=rec['images']['image'],regions=rec['regions']))
        js(out/'EXPORTED_SCENES.json',dict(scenes=exported))
        js(out/'BROWSER_VALIDATION.json',dict(utc=now(),status='PASS',events=events,
            actual_browser=True,software_rendering=True,scope='finite local UI behavior; no human usability, semantic or realtime claim'))
    finally:
        if sid is not None:
            try:request(base+'/session/'+sid,'DELETE')
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
    p.add_argument('--name',default='browser');a=p.parse_args();run(a.unit,a.name)
