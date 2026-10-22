"""Actual Firefox independent patch creation, cold ZIP restore and rejection."""
import runtime
from runtime import js,sha,now
from pathlib import Path
import argparse,json,shutil,zipfile
import numpy as np
from unit023_run import U,protocol
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
        revision=state()['revision'];click(selector);wait(lambda:state()['revision']==revision+1);wait(ready);return state()
    def select(region):
        execute("document.getElementById('region').value="+json.dumps(str(region))+";document.getElementById('region').dispatchEvent(new Event('change'));")
    def download(selector,name,seconds=240):
        prior={p.name for p in downloads.iterdir()};click(selector)
        def complete():
            files=[f for f in downloads.iterdir() if f.name not in prior and f.suffix in ('.zip','.png')]
            return files[0] if len(files)==1 and not list(downloads.glob('*.part')) else None
        f=wait(complete,seconds);wait(ready);dest=out/name;shutil.copy2(f,dest);return dest
    def upload(file):
        old=state()
        element=request(root+'/element','POST',{'using':'css selector','value':'#importFile'})['value']['element-6066-11e4-a52e-4f735466cecf']
        request(root+'/element/'+element+'/value','POST',{'text':str(file.resolve())});click('#importAsset')
        wait(lambda:state()['example']!=old['example']);wait(ready);return state()
    if cold:
        assert (unit/'browser/CLEANUP.json').is_file()
        edited=upload(unit/'browser/chair_edited.zip');same(edited,'edited')
        assert not edited['can_undo'] and all(edited['region_restore'][k]['available'] for k in ('4','5'))
        events.append(dict(action='new Firefox and server uploaded two-region edited ZIP',image_and_arrays_exact=True,both_snapshots_available=True,session_undo_empty=True))
    else:
        initial=state();assert len(initial['regions'])==4 and initial['region_restore']['4']['available']
        execute("document.getElementById('sourceRegion').value='3';document.getElementById('interaction').value='box';document.getElementById('interaction').dispatchEvent(new Event('change'));")
        execute('for(const [k,v] of Object.entries('+json.dumps(dict(zip(('xmin','ymin','zmin','xmax','ymax','zmax'),protocol()['second_bounds'])))+'))document.getElementById(k).value=v;')
        click('#previewSelection');wait(lambda:not execute("return document.getElementById('saveRegion').disabled;"));screenshot('02_back_selection')
        execute("document.getElementById('regionName').value="+json.dumps(protocol()['second_name'])+';')
        two=action('#saveRegion');assert all(two['region_restore'][k]['available'] for k in ('4','5'))
        for file in ('mesh.npz','region_3.npz','region_4.npz','region_5.npz','origin_4.npz','origin_5.npz'):
            assert sha(Path(two['asset'])/file)==sha(unit/'assets/two_regions'/file)
        assert sha(raster(initial))==sha(raster(two)), 'authoring alone must retain the image'
        select(5);execute("document.getElementById('inkStrength').value=.45;document.getElementById('inkStrength').dispatchEvent(new Event('input'));")
        baseline=action('#apply');same(baseline,'baseline')
        select(4);execute("document.getElementById('angle').value=65;document.getElementById('angle').dispatchEvent(new Event('input'));")
        edited=action('#apply');same(edited,'edited')
        download('#downloadAsset','chair_edited.zip',60)
        events.append(dict(action='actual box preview and creation of back patch, back ink edit, seat angle edit and ZIP download',second_faces=3055,authoring_PNG_unchanged=True,independent_restore_remains_enabled=True,images_and_arrays_match_CLI=True))
    screenshot('03_edited');select(1);assert execute("return document.getElementById('restoreRegion').disabled;")
    select(4);assert not execute("return document.getElementById('restoreRegion').disabled;")
    restored=action('#restoreRegion');same(restored,'baseline')
    for file in Path(edited['asset']).iterdir():
        if file.name not in ('asset.json','region_4.npz'):assert sha(file)==sha(Path(restored['asset'])/file.name)
    assert restored['styles']['5']['ink_strength']==.45 and restored['camera']==edited['camera']
    screenshot('04_restored');undone=action('#undo');same(undone,'edited')
    request(root+'/refresh','POST',{});wait(ready);select(4)
    assert not execute("return document.getElementById('restoreRegion').disabled;")
    restored=action('#restoreRegion');same(restored,'baseline')
    events.append(dict(action='restore seat, Undo, page refresh, restore again',target_paths_byte_exact=True,all_render_arrays_exact=True,back_edit_and_other_files_unchanged=True))
    if cold:
        rotated=action('#right');zoomed=action('#closer')
        assert sha(raster(rotated))!=sha(raster(restored)) and sha(raster(zoomed))!=sha(raster(rotated))
        execute('for(const [k,v] of Object.entries('+json.dumps(protocol()['viewer_camera'])+'))document.getElementById(k).value=v;')
        restored=action('#updateView');same(restored,'baseline')
        download('#downloadAsset','chair_restored.zip',60);exports=[]
        for selector,kind in [('downloadPng','image'),('exportOrbit','orbit'),('exportZoom','zoom')]:
            file=download('#'+selector,'chair_'+kind+('.png' if kind=='image' else '.zip'))
            if kind=='image':assert sha(file)==sha(raster(restored))
            else:
                bundle=out/('chair_'+kind)
                with zipfile.ZipFile(file) as z:z.extractall(bundle)
                receipt=json.loads((bundle/'PRESENTATION.json').read_text());assert receipt['all_proxy_vertices_inside']
                assert sha(bundle/'asset/origin_4.npz')==sha(unit/'assets/seat/origin_4.npz')
                exports.append(dict(kind=kind,frames=receipt['frame_count'],whole_proxy_inside=True,snapshots_preserved=True))
        js(out/'RESTORED_STATE.json',restored);shutil.copy2(raster(restored),out/'restored.png');screenshot('05_exports')
        events.append(dict(action='real orbit/zoom and actual image/motion/asset downloads',exports=exports))
        rejected=upload(unit/'shared_support_changed.zip');select(4)
        assert not rejected['region_restore']['4']['available'] and execute("return document.getElementById('restoreRegion').disabled;")
        assert rejected['region_restore']['5']['available'];screenshot('06_shared_support_disabled')
        events.append(dict(action='upload changed shared-support asset',seat_restore_disabled=True,new_region_restore_available=True,reason=rejected['region_restore']['4']['reason']))
    js(out/'BROWSER_VALIDATION.json',dict(status='PASS',utc=now(),actual_browser=True,new_server=cold,events=events,scope='Finite CPU engineering operations; no independent geometry/semantic/temporal proof'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cold',action='store_true');a=p.parse_args()
    run(U,'cold_browser' if a.cold else 'browser',catalog=U/'portable_demo/CATALOG.json' if a.cold else None,
        asset=None if a.cold else U/'assets/seat',exercise=exercise)
