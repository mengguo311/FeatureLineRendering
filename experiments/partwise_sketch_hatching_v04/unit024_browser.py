"""Actual ink edits, width/camera invalidation, downloads and cold ZIP import."""
import runtime
from runtime import js,sha,now
from pathlib import Path
import argparse,json,shutil,zipfile,time
import numpy as np
from unit024_run import U,protocol
from browser_demo_test import run

def exercise(unit,out,app,root,request,execute,click,ready,wait,screenshot,downloads):
    cold=out.name=='cold_browser';events=[]
    def state():return request(app+'/state')
    def raster(s):return out/'session'/s['images']['image'].removeprefix('/image/')
    def same(s,arm):
        expected=unit/f'renders/{arm}/frame_000_image.png';actual=raster(s)
        assert sha(actual)==sha(expected)
        with np.load(actual.with_name('frame_000_arrays.npz')) as a,np.load(expected.with_name('frame_000_arrays.npz')) as b:
            assert set(a.files)==set(b.files) and all(np.array_equal(a[k],b[k]) for k in a.files)
    def action(selector):
        revision=state()['revision'];t=time.monotonic();click(selector)
        wait(lambda:state()['revision']==revision+1);wait(ready)
        s=state();events.append(dict(action=selector,observed_seconds=time.monotonic()-t,cache=s['render_cache']))
        return s
    def select():execute("document.getElementById('region').value='4';document.getElementById('region').dispatchEvent(new Event('change'));")
    def ink(value):
        select();execute("document.getElementById('inkStrength').value="+str(value)+";document.getElementById('inkStrength').dispatchEvent(new Event('input'));")
        return action('#apply')
    def download(selector,name,seconds=240):
        prior={p.name for p in downloads.iterdir()};click(selector)
        def complete():
            files=[f for f in downloads.iterdir() if f.name not in prior and f.suffix in ('.zip','.png')]
            return files[0] if len(files)==1 and not list(downloads.glob('*.part')) else None
        source=wait(complete,seconds);wait(ready);target=out/name;shutil.copy2(source,target);return target
    if cold:
        assert json.loads((unit/'browser/CLEANUP.json').read_text())['own_child_groups_only']
        old=state()
        element=request(root+'/element','POST',{'using':'css selector','value':'#importFile'})['value']['element-6066-11e4-a52e-4f735466cecf']
        request(root+'/element/'+element+'/value','POST',{'text':str(unit/'browser/chair_edited.zip')});click('#importAsset')
        wait(lambda:state()['example']!=old['example']);wait(ready);initial=state()
        assert not initial['can_undo'] and not initial['render_cache']['hit'];same(initial,'edited')
        assert initial['render_cache']['builds']==1
        events.append(dict(action='fresh server/browser imports saved ZIP without any cached coverage',PNG_arrays_exact=True))
    else:
        initial=state();same(initial,'baseline');assert not initial['render_cache']['hit']
        changed=ink(.35);same(changed,'edited');assert changed['render_cache']['hit']
        for f in Path(initial['asset']).iterdir():
            if f.name!='asset.json':assert sha(f)==sha(Path(changed['asset'])/f.name)
        execute("document.getElementById('width').value=1.5;document.getElementById('width').dispatchEvent(new Event('input'));")
        wide=action('#apply');assert not wide['render_cache']['hit']
        undone=action('#undo');same(undone,'edited');assert not undone['render_cache']['hit']
        events.append(dict(action='same-camera ink hit, width change and width undo rebuild',binary_paths_unchanged=True))
    zero=ink(0);assert zero['render_cache']['hit']
    edited=ink(.35);same(edited,'edited');assert edited['render_cache']['hit']
    request(root+'/refresh','POST',{});wait(ready);select()
    assert execute("return +document.getElementById('inkStrength').value;")==.35
    screenshot('02_ink_edit')
    rotated=action('#right');zoomed=action('#closer')
    assert not rotated['render_cache']['hit'] and not zoomed['render_cache']['hit']
    execute('for(const [k,v] of Object.entries('+json.dumps(protocol()['viewer_camera'])+'))document.getElementById(k).value=v;')
    saved=action('#updateView');same(saved,'edited');assert not saved['render_cache']['hit']
    download('#downloadAsset','chair_edited.zip',60)
    png=download('#downloadPng','chair_edited.png');assert sha(png)==sha(raster(saved))
    if cold:
        for selector,kind in [('exportOrbit','orbit'),('exportZoom','zoom')]:
            file=download('#'+selector,'chair_'+kind+'.zip')
            with zipfile.ZipFile(file) as z:z.extractall(out/('chair_'+kind))
            receipt=json.loads((out/('chair_'+kind)/'PRESENTATION.json').read_text())
            assert receipt['all_proxy_vertices_inside'] and not receipt['paths_regenerated']
            events.append(dict(action='actual '+kind+' download',frames=receipt['frame_count'],all_proxy_inside=True))
    screenshot('03_downloads_complete')
    js(out/'SAVED_STATE.json',saved)
    js(out/'BROWSER_VALIDATION.json',dict(status='PASS',utc=now(),actual_browser=True,new_server=cold,events=events,
        scope='Finite local operations and actual downloads. Browser timings include polling, not a latency benchmark.'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cold',action='store_true');a=p.parse_args()
    run(U,'cold_browser' if a.cold else 'browser',catalog=U/'portable_demo/CATALOG.json' if a.cold else None,
        asset=None if a.cold else U/'assets/baseline',exercise=exercise)
