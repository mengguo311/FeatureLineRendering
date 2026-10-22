"""Actual Firefox edit/export, fresh-server import, restore and Undo."""
import runtime
from runtime import js,sha,now
from pathlib import Path
import argparse,json,shutil,zipfile
import numpy as np
from unit022_run import U,protocol
from browser_demo_test import run

def exercise(unit,out,app,root,request,execute,click,ready,wait,screenshot,downloads):
    cold=out.name.startswith('cold_browser');receipt_only=out.name=='cold_browser_receipt';events=[]
    def state():return request(app+'/state')
    def raster(s):return out/'session'/s['images']['image'].removeprefix('/image/')
    def same(s,arm):
        expected=unit/f'renders/{arm}/frame_000_image.png';actual=raster(s)
        assert sha(actual)==sha(expected)
        with np.load(actual.with_name('frame_000_arrays.npz')) as a,np.load(expected.with_name('frame_000_arrays.npz')) as b:
            assert set(a.files)==set(b.files) and all(np.array_equal(a[k],b[k]) for k in a.files)
    def action(selector):
        before=state()['revision'];click(selector);wait(lambda:state()['revision']==before+1);wait(ready);return state()
    def select(region):
        execute("document.getElementById('region').value="+json.dumps(str(region))+";document.getElementById('region').dispatchEvent(new Event('change'));")
    def download(selector,name,seconds=240):
        prior={p.name for p in downloads.iterdir()};click(selector)
        def complete():
            files=[f for f in downloads.iterdir() if f.name not in prior and f.suffix in ('.zip','.png')]
            return files[0] if len(files)==1 and not list(downloads.glob('*.part')) else None
        f=wait(complete,seconds);wait(ready);dest=out/name;shutil.copy2(f,dest);return dest
    if cold:
        assert (unit/'browser/CLEANUP.json').is_file()
        old=state();upload=unit/'browser/chair_edited.zip'
        element=request(root+'/element','POST',{'using':'css selector','value':'#importFile'})['value']['element-6066-11e4-a52e-4f735466cecf']
        request(root+'/element/'+element+'/value','POST',{'text':str(upload.resolve())});click('#importAsset')
        wait(lambda:state()['example']!=old['example']);wait(ready)
        edited=state();same(edited,'edited');assert not edited['can_undo']
        assert edited['region_restore']['4']['available']
        events.append(dict(action='fresh Firefox and server uploaded edited ZIP',image_and_arrays_exact=True,creation_snapshot_available=True,session_undo_empty=True))
    else:
        original=state();same(original,'authored');select(4)
        execute("document.getElementById('angle').value=65;document.getElementById('angle').dispatchEvent(new Event('input'));")
        edited=action('#apply');same(edited,'edited')
        download('#downloadAsset','chair_edited.zip',60)
        js(out/'EXPORT_STATE.json',edited)
        events.append(dict(action='actual angle edit and saved ZIP download',angle=65,image_and_arrays_exact=True))
    screenshot('02_edited')
    select(1);assert execute("return document.getElementById('restoreRegion').disabled;")
    select(4);assert not execute("return document.getElementById('restoreRegion').disabled;")
    restored=action('#restoreRegion');same(restored,'authored')
    for n in ('mesh.npz','region_1.npz','region_2.npz','region_3.npz','origin_4.npz'):
        assert sha(Path(edited['asset'])/n)==sha(Path(restored['asset'])/n)
    assert restored['camera']==edited['camera'] and restored['display']==edited['display']
    screenshot('03_restored')
    undone=action('#undo');same(undone,'edited')
    request(root+'/refresh','POST',{});wait(ready)
    assert execute("return +document.getElementById('angle').value;")==65
    restored=action('#restoreRegion');same(restored,'authored')
    events.append(dict(action='restore selected region, Undo, page refresh, restore again',target_paths_byte_exact=True,all_render_arrays_exact=True,other_regions_mesh_view_display_unchanged=True))
    if cold and not receipt_only:
        rotated=action('#right');zoomed=action('#closer')
        assert sha(raster(rotated))!=sha(raster(restored)) and sha(raster(zoomed))!=sha(raster(rotated))
        execute('for(const [k,v] of Object.entries('+json.dumps(protocol()['viewer_camera'])+'))document.getElementById(k).value=v;')
        restored=action('#updateView');same(restored,'authored')
        download('#downloadAsset','chair_restored.zip',60)
        exports=[]
        for selector,kind in [('downloadPng','image'),('exportOrbit','orbit'),('exportZoom','zoom')]:
            file=download('#'+selector,'chair_'+kind+('.png' if kind=='image' else '.zip'))
            if kind=='image':assert sha(file)==sha(raster(restored))
            else:
                bundle=out/('chair_'+kind)
                with zipfile.ZipFile(file) as z:z.extractall(bundle)
                receipt=json.loads((bundle/'PRESENTATION.json').read_text());assert receipt['all_proxy_vertices_inside']
                assert sha(bundle/'asset/origin_4.npz')==sha(unit/'assets/authored/origin_4.npz')
                exports.append(dict(kind=kind,frames=receipt['frame_count'],whole_proxy_inside=True,origin_snapshot_preserved=True))
        js(out/'RESTORED_STATE.json',restored);shutil.copy2(raster(restored),out/'restored.png');screenshot('04_exports')
        events.append(dict(action='restored orbit/zoom and actual image/motion/asset downloads',exports=exports))
    js(out/'BROWSER_VALIDATION.json',dict(status='PASS',utc=now(),actual_browser=True,new_server=cold,events=events,scope='Finite CPU engineering operations; no independent geometry/semantic/temporal proof'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cold',action='store_true');p.add_argument('--receipt-only',action='store_true');a=p.parse_args()
    run(U,'cold_browser_receipt' if a.receipt_only else 'cold_browser' if a.cold else 'browser',catalog=U/'portable_demo/CATALOG.json' if a.cold else None,
        asset=None if a.cold else U/'assets/authored',exercise=exercise)
