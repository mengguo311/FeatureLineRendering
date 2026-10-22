"""Actual controls/downloads on the saved bounded Lego proxy revision."""
import runtime
from runtime import js,sha,now
from pathlib import Path
import json,shutil,zipfile
from demo import load_asset

def exercise(unit,out,app,root,request,execute,click,ready,wait,screenshot,downloads):
    p=json.loads((unit/'PROTOCOL.json').read_text());events=[]
    def state():return request(app+'/state')
    def raster(s):return out/'session'/s['images']['image'].removeprefix('/image/')
    def action(selector):
        rev=state()['revision'];click(selector)
        wait(lambda:state()['revision']==rev+1);wait(ready)
        return state()
    initial=state();assert initial['scene']=='lego' and initial['selected_region']==4
    values=dict(p['viewer_camera']);values['azimuth']=(values['azimuth']+180)%360-180
    execute('for(const [k,v] of Object.entries('+json.dumps(values)+'))document.getElementById(k).value=v;')
    baseline=action('#updateView')
    assert sha(raster(baseline))==sha(unit/'renders/refined/frame_000_image.png')
    screenshot('02_refined_bucket')
    execute("document.getElementById('region').value='4';document.getElementById('region').dispatchEvent(new Event('change'));document.getElementById('angle').value=50;document.getElementById('angle').dispatchEvent(new Event('input'));")
    edited=action('#apply')
    assert sha(raster(edited))==sha(unit/'renders/style_probe/frame_000_image.png')
    for r in (1,2,3):assert sha(Path(edited['asset'])/f'region_{r}.npz')==sha(Path(baseline['asset'])/f'region_{r}.npz')
    screenshot('03_local_angle_edit')
    restored=action('#undo');assert sha(raster(restored))==sha(raster(baseline))
    request(root+'/refresh','POST',{});wait(ready)
    assert execute("return +document.getElementById('angle').value;")==35
    assert execute("return document.getElementById('crossEnabled').checked;") is True
    events.append(dict(action='open geometry revision, change bucket angle35->50, save, undo, reload',CLI_images_exact=True,non_target_files_exact=True,manual_region_restored=True))
    original=state();rotated=action('#right');zoomed=action('#closer')
    assert sha(raster(rotated))!=sha(raster(original)) and sha(raster(zoomed))!=sha(raster(rotated))
    screenshot('04_orbit_zoom')
    execute('for(const [k,v] of Object.entries('+json.dumps(values)+'))document.getElementById(k).value=v;')
    saved=action('#updateView');assert sha(raster(saved))==sha(raster(baseline))
    events.append(dict(action='actual orbit and zoom buttons, then restore frozen camera',distinct_images=True))
    js(out/'EXPORT_STATE.json',saved)
    def download_after(selector,seconds=240):
        before={f.name for f in downloads.iterdir()};click(selector)
        def complete():
            candidates=[f for f in downloads.iterdir() if f.name not in before and f.is_file() and f.suffix in ('.png','.zip')]
            return candidates[0] if len(candidates)==1 and not list(downloads.glob('*.part')) else None
        result=wait(complete,seconds=seconds);wait(ready)
        return result
    downloaded=download_after('a.download[href="/export"]',60);shutil.copy2(downloaded,out/'lego_asset.zip')
    with zipfile.ZipFile(out/'lego_asset.zip') as z:z.extractall(out/'exported_asset')
    _,_,meta=load_asset(out/'exported_asset')
    assert meta['geometry_history'][-1]['mesh_sha256']==meta['mesh_sha256']
    assert meta['styles']==saved['styles'] and meta['viewer_camera']==saved['camera']
    exports=[]
    for control,kind in [('downloadPng','image'),('exportOrbit','orbit'),('exportZoom','zoom')]:
        downloaded=download_after('#'+control);target=out/('lego_'+kind+downloaded.suffix);shutil.copy2(downloaded,target)
        if kind=='image':
            assert sha(target)==sha(raster(saved));record=dict(kind=kind,png_exact=True)
        else:
            bundle=out/('lego_'+kind)
            with zipfile.ZipFile(target) as z:z.extractall(bundle)
            receipt=json.loads((bundle/'PRESENTATION.json').read_text())
            assert receipt['all_proxy_vertices_inside'] and not receipt['paths_regenerated']
            for file in Path(saved['asset']).iterdir():
                if file.is_file() and file.name!='asset.json':assert sha(file)==sha(bundle/'asset'/file.name)
            record=dict(kind=kind,frame_count=receipt['frame_count'],all_inside=True,snapshot_files_exact=True,seconds=receipt['seconds'])
        assert state()['revision']==saved['revision'];exports.append(record)
    screenshot('05_export_complete')
    js(out/'BROWSER_VALIDATION.json',dict(status='PASS',utc=now(),events=events,exports=exports,actual_browser=True,
        software_rendering=True,actual_download_count=4,saved_asset_download=True,camera=saved['camera'],
        geometry_revision_preserved=True,scope='Finite browser operations on real-model proxy revision; no human usability or temporal certification.'))
