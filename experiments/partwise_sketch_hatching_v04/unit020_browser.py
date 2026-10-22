"""Actual Firefox seat edit, save/export, stopped-server cold import and edit."""
import runtime
from runtime import js,sha,now
from pathlib import Path
import argparse,json,shutil,zipfile
import numpy as np
from unit020_run import U,protocol
from browser_demo_test import run

def exercise(unit,out,app,root,request,execute,click,ready,wait,screenshot,downloads):
    cold=out.name.startswith('cold_browser');events=[]
    def state():return request(app+'/state')
    def raster(s):return out/'session'/s['images']['image'].removeprefix('/image/')
    def action(selector):
        rev=state()['revision'];click(selector);wait(lambda:state()['revision']==rev+1);wait(ready);return state()
    def angle(value):
        execute("document.getElementById('region').value='4';document.getElementById('region').dispatchEvent(new Event('change'));document.getElementById('angle').value="+str(value)+";document.getElementById('angle').dispatchEvent(new Event('input'));")
        return action('#apply')
    def same_arrays(actual,expected):
        assert sha(actual)==sha(expected)
        with np.load(actual.with_name('frame_000_arrays.npz')) as a,np.load(expected.with_name('frame_000_arrays.npz')) as b:
            assert set(a.files)==set(b.files) and all(np.array_equal(a[k],b[k]) for k in a.files)
    if cold:
        assert (unit/'browser/CLEANUP.json').is_file()
        old=state();file=unit/'browser/chair_saved_asset.zip'
        element=request(root+'/element','POST',{'using':'css selector','value':'#importFile'})['value']['element-6066-11e4-a52e-4f735466cecf']
        request(root+'/element/'+element+'/value','POST',{'text':str(file.resolve())});click('#importAsset')
        wait(lambda:state()['example']!=old['example']);wait(ready);baseline=state()
        reference=json.loads((unit/'browser/EXPORT_STATE.json').read_text())
        for key in ('scene','styles','camera','display','selected_region'):assert baseline[key]==reference[key],key
        assert not baseline['can_undo'] and baseline['import_receipt']['integrity']=='manifest_sha256_and_anchor_validation'
        expected=unit/'browser/session'/reference['images']['image'].removeprefix('/image/')
        same_arrays(raster(baseline),expected)
        events.append(dict(action='new server and Firefox upload edited seat ZIP',PNG_arrays_and_state_exact=True))
    else:
        baseline=state();assert baseline['scene']=='chair' and baseline['selected_region']==4
        same_arrays(raster(baseline),unit/'renders/authored/frame_000_image.png')
        events.append(dict(action='open saved manual seat patch',PNG_arrays_match_CLI=True))
    screenshot('02_saved_seat')
    edited=angle(95. if cold else 65.)
    same_arrays(raster(edited),unit/f"renders/{'authored' if cold else 'edited'}/frame_000_image.png")
    for name in ('mesh.npz','region_1.npz','region_2.npz','region_3.npz'):
        assert sha(Path(baseline['asset'])/name)==sha(Path(edited['asset'])/name)
    screenshot('03_local_angle_edit')
    restored=action('#undo');same_arrays(raster(restored),raster(baseline))
    request(root+'/refresh','POST',{});wait(ready)
    assert execute("return +document.getElementById('angle').value;")== (65. if cold else 95.)
    events.append(dict(action='seat-only edit, undo and page refresh',non_target_paths_exact=True,edited_PNG_arrays_match_CLI=True))
    if cold:
        shutil.copy2(raster(restored),out/'cold_import.png');screenshot('04_cold_import_restored')
        js(out/'BROWSER_VALIDATION.json',dict(status='PASS',utc=now(),actual_browser=True,new_server=True,
            PNG_exact=True,all_arrays_exact=True,continue_edit_and_undo=True,events=events))
        return
    current=angle(65.)
    rotated=action('#right');zoomed=action('#closer')
    assert sha(raster(rotated))!=sha(raster(current)) and sha(raster(zoomed))!=sha(raster(rotated))
    execute('for(const [k,v] of Object.entries('+json.dumps(protocol()['viewer_camera'])+'))document.getElementById(k).value=v;')
    saved=action('#updateView');same_arrays(raster(saved),unit/'renders/edited/frame_000_image.png');js(out/'EXPORT_STATE.json',saved)
    def download(selector,destination,seconds=240):
        prior={f.name for f in downloads.iterdir()};click(selector)
        def complete():
            files=[f for f in downloads.iterdir() if f.name not in prior and f.suffix in ('.zip','.png')]
            return files[0] if len(files)==1 and not list(downloads.glob('*.part')) else None
        f=wait(complete,seconds=seconds);wait(ready);shutil.copy2(f,destination);return destination
    file=download('#downloadAsset',out/'chair_saved_asset.zip',60)
    with zipfile.ZipFile(file) as z:z.extractall(out/'exported_asset')
    meta=json.loads((out/'exported_asset/asset.json').read_text());assert meta['styles']['4']['angle']==65. and meta['region_history'][-1]['selected_faces']>0
    exports=[]
    for selector,kind in [('downloadPng','image'),('exportOrbit','orbit'),('exportZoom','zoom')]:
        file=download('#'+selector,out/('chair_'+kind+('.png' if kind=='image' else '.zip')))
        if kind=='image':assert sha(file)==sha(raster(saved));entry=dict(kind=kind,PNG_exact=True)
        else:
            bundle=out/('chair_'+kind)
            with zipfile.ZipFile(file) as z:z.extractall(bundle)
            r=json.loads((bundle/'PRESENTATION.json').read_text());assert r['all_proxy_vertices_inside'] and not r['paths_regenerated']
            for f in Path(saved['asset']).iterdir():
                if f.is_file() and f.name!='asset.json':assert sha(f)==sha(bundle/'asset'/f.name)
            entry=dict(kind=kind,frame_count=r['frame_count'],whole_proxy_inside=True,saved_paths_exact=True)
        assert state()['revision']==saved['revision'];exports.append(entry)
    screenshot('05_export_complete')
    js(out/'BROWSER_VALIDATION.json',dict(status='PASS',utc=now(),actual_browser=True,software_rendering=True,events=events,
        actual_download_count=4,exports=exports,orbit_zoom_buttons_distinct=True,
        scope='Finite local CPU browser operations; manual partial seat patch, no all-view geometry or temporal certification.'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cold',action='store_true');a=p.parse_args()
    run(U,'cold_browser' if a.cold else 'browser',catalog=U/'portable_demo/CATALOG.json' if a.cold else None,
        asset=None if a.cold else U/'portable_demo/candidates/chair_seat_authored',exercise=exercise)
