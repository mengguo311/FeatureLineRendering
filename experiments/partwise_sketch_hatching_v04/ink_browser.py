"""Actual ink slider, saved local edit and downloads on real Lego."""
import runtime
from runtime import js,sha,now
from pathlib import Path
import json,shutil,zipfile,urllib.error
from demo import load_asset

def exercise(unit,out,app,root,request,execute,click,ready,wait,screenshot,downloads):
    p=json.loads((unit/'PROTOCOL.json').read_text());events=[]
    def state():return request(app+'/state')
    def raster(s):return out/'session'/s['images']['image'].removeprefix('/image/')
    def action(selector):
        rev=state()['revision'];click(selector)
        wait(lambda:state()['revision']==rev+1);wait(ready)
        return state()
    values=p['viewer_camera']
    execute('for(const [k,v] of Object.entries('+json.dumps(values)+'))document.getElementById(k).value=v;')
    baseline=action('#updateView')
    assert sha(raster(baseline))==sha(unit/'renders/baseline/frame_000_image.png')
    execute("document.getElementById('region').value='1';document.getElementById('region').dispatchEvent(new Event('change'));")
    assert execute("return +document.getElementById('inkStrength').value;")==.8
    screenshot('02_legacy_platform')
    def set_ink():
        execute("document.getElementById('region').value='1';document.getElementById('region').dispatchEvent(new Event('change'));document.getElementById('inkStrength').value=.4;document.getElementById('inkStrength').dispatchEvent(new Event('input'));")
        return action('#apply')
    edited=set_ink()
    assert sha(raster(edited))==sha(unit/'renders/ink/frame_000_image.png')
    for f in Path(baseline['asset']).iterdir():
        if f.is_file() and f.name!='asset.json':assert sha(f)==sha(Path(edited['asset'])/f.name)
    for r in ('2','3','4'):assert edited['styles'][r]==baseline['styles'][r]
    assert load_asset(edited['asset'])[2]['edit']['regenerated_layers']==[]
    screenshot('03_local_ink_saved')
    request(root+'/refresh','POST',{});wait(ready)
    assert execute("return +document.getElementById('inkStrength').value;")==.4
    execute("document.getElementById('region').value='4';document.getElementById('region').dispatchEvent(new Event('change'));")
    assert execute("return +document.getElementById('inkStrength').value;")==.8
    restored=action('#undo');assert sha(raster(restored))==sha(raster(baseline))
    edited=set_ink();assert sha(raster(edited))==sha(unit/'renders/ink/frame_000_image.png')
    # Invalid HTTP values must not create a new saved state.
    for value in (-.1,1.1,True,'0.4',None):
        body=dict(edited['styles']['1'],region=1,**values);body['ink_strength']=value
        try:request(app+'/render','POST',body)
        except urllib.error.HTTPError as e:assert e.code==422
        else:raise AssertionError('invalid ink accepted')
        assert state()==edited
    events.append(dict(action='legacy default, local ink .80->.40, save, refresh, region isolation, undo and reapply',CLI_images_exact=True,all_asset_binary_files_exact=True,invalid_HTTP_values_rejected=5))
    rotated=action('#right');zoomed=action('#closer')
    assert sha(raster(rotated))!=sha(raster(edited)) and sha(raster(zoomed))!=sha(raster(rotated))
    screenshot('04_orbit_zoom')
    execute('for(const [k,v] of Object.entries('+json.dumps(values)+'))document.getElementById(k).value=v;')
    saved=action('#updateView');assert sha(raster(saved))==sha(raster(edited))
    js(out/'EXPORT_STATE.json',saved)
    def download_after(selector,seconds=240):
        before={f.name for f in downloads.iterdir()};click(selector)
        def complete():
            candidates=[f for f in downloads.iterdir() if f.name not in before and f.is_file() and f.suffix in ('.png','.zip')]
            return candidates[0] if len(candidates)==1 and not list(downloads.glob('*.part')) else None
        result=wait(complete,seconds=seconds);wait(ready);return result
    downloaded=download_after('a.download[href="/export"]',60);shutil.copy2(downloaded,out/'lego_asset.zip')
    with zipfile.ZipFile(out/'lego_asset.zip') as z:z.extractall(out/'exported_asset')
    _,_,meta=load_asset(out/'exported_asset')
    assert meta['styles']==saved['styles'] and meta['viewer_camera']==saved['camera'] and meta['selected_region']==1
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
        scope='Finite browser operations with real-model proxy; no human usability or full temporal certification.'))
