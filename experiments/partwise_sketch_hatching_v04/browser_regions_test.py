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


def run(unit, name):
    unit=output_guard(unit);out=unit/name;out.mkdir()
    profile=out/'fresh_profile';profile.mkdir()
    logs=[];processes=[];sid=None;base=None;events=[]
    def start(command, logfile):
        log=open(logfile,'w');logs.append(log)
        child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        processes.append(child);return child
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
        server=start([sys.executable,str(Path(__file__).with_name('viewer.py')),'--asset',str(unit/'assets/original'),
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
            return execute("return document.querySelector('#preview').complete && document.querySelector('#preview').naturalWidth === 512 && !document.querySelector('#apply').disabled;")
        def screenshot(name):
            png=request(root+'/screenshot')['value'];(out/(name+'.png')).write_bytes(base64.b64decode(png))
        request(root+'/window/rect','POST',dict(width=1280,height=1500))
        request(root+'/url','POST',{'url':app});wait(ready);screenshot('01_loaded')
        initial=request(app+'/state')
        assert execute('return document.title;')==initial['scene'].title()+' · Partwise Hatch Demo'
        protocol=json.loads((unit/'PROTOCOL.json').read_text())
        selection=protocol['selection']
        assert len(initial['regions'])==3
        script="document.querySelector('#sourceRegion').value='3';"
        for key,value in zip(['xmin','ymin','zmin','xmax','ymax','zmax'],selection['bounds']):
            script+=f"document.querySelector('#{key}').value={value};"
        script+="document.querySelector('#regionName').value='Front bucket area (manual)';"
        execute(script)
        click('#previewSelection')
        wait(lambda:execute("return !document.querySelector('#saveRegion').disabled;"))
        screenshot('02_selection_preview')
        assert request(app+'/state')['revision']==0
        selection_text=execute("return document.querySelector('#selectionStatus').textContent;")
        assert '3001 of 5040 faces' in selection_text
        events.append(dict(action='preview authored frozen box',description=selection_text,asset_unchanged=True))
        # A preview token binds the exact box and current revision.
        token='no-fresh-preview'
        click('#saveRegion');wait(lambda:request(app+'/state')['revision']==1);wait(ready)
        screenshot('03_region_saved')
        authored=request(app+'/state')
        assert len(authored['regions'])==4
        assert execute("return document.querySelector('#region').value;")=='4'
        for r in (1,2,3,4):
            assert sha(Path(authored['asset'])/f'region_{r}.npz')==sha(unit/f'assets/baseline/region_{r}.npz')
        events.append(dict(action='save new region in real browser',saved_region=4,CLI_paths_exact=True))
        execute("document.querySelector('#angle').value=35;document.querySelector('#angle').dispatchEvent(new Event('input'));")
        click('#apply');wait(lambda:request(app+'/state')['revision']==2);wait(ready)
        click('#hatch');wait(ready);screenshot('04_region_angle_edit')
        edited=request(app+'/state')
        for r in (1,2,3,4):
            assert sha(Path(edited['asset'])/f'region_{r}.npz')==sha(unit/f'assets/edited/region_{r}.npz')
        try:
            request(app+'/author','POST',dict(token=token,name='stale selection'))
            raise AssertionError('stale preview accepted')
        except urllib.error.HTTPError as error:assert error.code==422
        assert request(app+'/state')['revision']==2
        events.append(dict(action='new region angle35 and author without fresh preview rejection',other_regions_exact=True,status_for_stale=422))
        execute("for(const [k,v] of [['spacing',.06],['length',.16],['width',1.6]])document.getElementById(k).value=v;")
        click('#apply');wait(lambda:request(app+'/state')['revision']==3);wait(ready)
        changed=request(app+'/state');assert all(changed['styles']['4'][k]==v for k,v in [('spacing',.06),('length',.16),('width',1.6)])
        for r in (1,2,3):assert sha(Path(edited['asset'])/f'region_{r}.npz')==sha(Path(changed['asset'])/f'region_{r}.npz')
        screenshot('05_extra_controls')
        click('#undo');wait(lambda:request(app+'/state')['revision']==4);wait(ready)
        undo=request(app+'/state');assert undo['styles']==edited['styles']
        assert sha(out/'session/view_0004/frame_000_image.png')==sha(out/'session/view_0002/frame_000_image.png')
        events.append(dict(action='spacing/length/width edit, then undo',other_regions_exact=True,undo_image_exact=True))
        click('#right');wait(lambda:request(app+'/state')['revision']==5);wait(ready)
        click('#closer');wait(lambda:request(app+'/state')['revision']==6);wait(ready);screenshot('06_orbit_zoom')
        request(root+'/refresh','POST',{});wait(ready)
        current=request(app+'/state')
        displayed=execute("return Object.fromEntries(['azimuth','elevation','distance'].map(k=>[k,+document.getElementById(k).value]));")
        assert displayed==current['camera']
        assert execute("return document.querySelector('#region').value;")=='4'
        with urllib.request.urlopen(app+'/export',timeout=20) as response:(out/'export.zip').write_bytes(response.read())
        meta=json.loads((Path(current['asset'])/'asset.json').read_text())
        assert meta['viewer_camera']==current['camera'] and meta['selected_region']==4
        screenshot('07_reload_export')
        events.append(dict(action='orbit/zoom/refresh/export',camera=current['camera'],selected_region=4,saved_camera_exact=True))
        js(out/'BROWSER_VALIDATION.json',dict(utc=now(),status='PASS',events=events,
            actual_browser=True,software_rendering=True,scope='finite local UI operations, not human usability or performance certification'))
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
