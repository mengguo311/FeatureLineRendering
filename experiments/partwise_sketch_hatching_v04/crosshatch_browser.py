"""Actual Firefox controls/downloads for the optional second saved hatch layer."""
import runtime
from runtime import js,sha,now
from pathlib import Path
import json,shutil,zipfile
import numpy as np
from demo import load_asset

def exercise(unit,out,app,root,request,execute,click,ready,wait,screenshot,downloads):
    events=[];p=json.loads((unit/'PROTOCOL.json').read_text())
    scene=p['scene'];region=p['local_edit']['region'];style_key=str(region)
    cross_angle=p['local_edit']['cross_angle'];cross_spacing=p['local_edit']['cross_spacing']
    def state():return request(app+'/state')
    def raster(s):return out/'session'/s['images']['image'].removeprefix('/image/')
    def action(selector):
        rev=state()['revision'];click(selector)
        wait(lambda:state()['revision']==rev+1);wait(ready)
        return state()
    def file_equal(a,b):
        return all(sha(Path(a)/f'region_{r}.npz')==sha(Path(b)/f'region_{r}.npz') for r in regions)
    assert state()['scene']==scene
    regions=sorted(map(int,state()['regions']));others=[r for r in regions if r!=region]
    assert execute("return document.getElementById('crossEnabled').checked;") is False
    values=dict(p['viewer_camera']);values['azimuth']=(values['azimuth']+180)%360-180
    execute('for(const [k,v] of Object.entries('+json.dumps(values)+'))document.getElementById(k).value=v;')
    baseline=action('#updateView')
    execute("document.getElementById('region').value="+json.dumps(style_key)+";document.getElementById('region').dispatchEvent(new Event('change'));")
    if p.get('base_edit'):
        for control,value in p['base_edit'].items():
            execute('document.getElementById('+json.dumps(control)+').value='+json.dumps(value)+';')
        original=baseline;baseline=action('#apply')
        assert sha(raster(baseline))==sha(unit/'renders/single/frame_000_image.png')
        for r in others:assert sha(Path(original['asset'])/f'region_{r}.npz')==sha(Path(baseline['asset'])/f'region_{r}.npz')
        screenshot('02_short_single')
        events.append(dict(action='saved short sparse preset in existing manually authored region',region=region,changes=p['base_edit'],non_target_files_exact=True,cli_png_exact=True))
    execute("document.getElementById('crossAngle').value="+str(cross_angle)+";document.getElementById('crossSpacing').value="+str(cross_spacing)+";")
    click('#crossEnabled');action('#apply');on=state()
    assert on['styles'][style_key]['cross_enabled'] and on['styles'][style_key]['cross_angle']==cross_angle and on['styles'][style_key]['cross_spacing']==cross_spacing
    assert sha(raster(on))==sha(unit/'renders/cross/frame_000_image.png')
    original=load_asset(Path(baseline['asset']))[1][region];paths=load_asset(Path(on['asset']))[1][region]
    for key in original:np.testing.assert_array_equal(original[key],paths[key][paths['layer_id']==0])
    for r in others:assert sha(Path(baseline['asset'])/f'region_{r}.npz')==sha(Path(on['asset'])/f'region_{r}.npz')
    screenshot('02_cross_enabled')
    events.append(dict(action='actual checkbox + save creates selected-region cross layer',region=region,base_arrays_exact=True,other_region_files_exact=True,cli_png_exact=True))
    click('#crossEnabled');off=action('#apply')
    assert file_equal(on['asset'],off['asset']) and sha(raster(off))==sha(raster(baseline))
    click('#crossEnabled');again=action('#apply')
    assert file_equal(on['asset'],again['asset']) and sha(raster(again))==sha(raster(on))
    events.append(dict(action='actual off/on controls',all_path_bytes_exact=True,off_png_equals_baseline=True,on_png_restored=True))
    probe=p.get('interaction_probe',dict(cross_angle=75.,cross_spacing=.075))
    execute("document.getElementById('crossAngle').value="+str(probe['cross_angle'])+";document.getElementById('crossSpacing').value="+str(probe['cross_spacing'])+";document.getElementById('crossAngle').dispatchEvent(new Event('input'));document.getElementById('crossSpacing').dispatchEvent(new Event('input'));")
    changed=action('#apply')
    assert changed['styles'][style_key]['cross_angle']==probe['cross_angle'] and changed['styles'][style_key]['cross_spacing']==probe['cross_spacing']
    changed_paths=load_asset(Path(changed['asset']))[1][region]
    for key in original:np.testing.assert_array_equal(original[key],changed_paths[key][changed_paths['layer_id']==0])
    assert sha(raster(changed))!=sha(raster(on))
    restored=action('#undo');assert sha(raster(restored))==sha(raster(on))
    request(root+'/refresh','POST',{});wait(ready)
    assert execute("return [document.getElementById('crossEnabled').checked,+document.getElementById('crossAngle').value,+document.getElementById('crossSpacing').value];")==[True,cross_angle,cross_spacing]
    events.append(dict(action='second direction angle+spacing sliders, save, undo and page reload',base_arrays_exact=True,controls_restored=True))
    if restored.get('available_scenes'):
        other=next(s for s in restored['available_scenes'] if s!=scene)
        for destination in (other,scene):
            execute("document.getElementById('scene').value="+json.dumps(destination)+";document.getElementById('scene').dispatchEvent(new Event('change'));")
            wait(lambda:state()['scene']==destination);wait(ready)
            expected=destination==scene;assert execute("return document.getElementById('crossEnabled').checked;") is expected
        assert sha(raster(state()))==sha(raster(on))
        events.append(dict(action='model switch preserves selected model cross settings; other stays disabled',scene=scene,other=other))
    saved=state();js(out/'EXPORT_STATE.json',saved)
    def download_after(selector):
        prior={file.name for file in downloads.iterdir()};click(selector)
        def finished():
            candidates=[file for file in downloads.iterdir() if file.name not in prior and file.is_file() and file.suffix!='.part']
            return candidates[0] if len(candidates)==1 and not list(downloads.glob('*.part')) else None
        return wait(finished,seconds=60)
    downloaded=download_after('a.download[href="/export"]');shutil.copy2(downloaded,out/(scene+'_asset.zip'))
    with zipfile.ZipFile(out/(scene+'_asset.zip')) as archive:archive.extractall(out/'exported_asset')
    loaded=load_asset(out/'exported_asset')
    assert loaded[2]['styles']==saved['styles'] and loaded[2]['viewer_camera']==saved['camera']
    for file in Path(saved['asset']).iterdir():
        if file.name!='asset.json' and file.is_file():assert sha(file)==sha(out/'exported_asset'/file.name)
    exports=[]
    for selector,kind in [('downloadPng','image'),('exportOrbit','orbit'),('exportZoom','zoom')]:
        prior={file.name for file in downloads.iterdir()};click('#'+selector)
        wait(lambda:execute("return !document.getElementById('downloadPng').disabled && document.querySelector('#exportLinks a')!==null;"),seconds=240)
        def finished():
            candidates=[file for file in downloads.iterdir() if file.name not in prior and file.suffix in ('.png','.zip')]
            return candidates[0] if candidates and not list(downloads.glob('*.part')) else None
        downloaded=wait(finished,seconds=20);target=out/(scene+'_'+kind+downloaded.suffix);shutil.copy2(downloaded,target)
        if kind=='image':
            assert sha(target)==sha(raster(saved));record=dict(kind=kind,png_exact=True)
        else:
            bundle=out/(scene+'_'+kind)
            with zipfile.ZipFile(target) as archive:archive.extractall(bundle)
            receipt=json.loads((bundle/'PRESENTATION.json').read_text())
            assert receipt['all_proxy_vertices_inside'] and not receipt['paths_regenerated']
            assert file_equal(saved['asset'],bundle/'asset')
            record=dict(kind=kind,frame_count=receipt['frame_count'],all_inside=True,snapshot_paths_exact=True,seconds=receipt['seconds'])
        exports.append(record);assert state()['revision']==saved['revision']
    screenshot('03_export_complete')
    js(out/'BROWSER_VALIDATION.json',dict(status='PASS',utc=now(),events=events,exports=exports,
        actual_browser=True,software_rendering=True,saved_asset_download=True,actual_download_count=4,
        camera=saved['camera'],scope='Finite scripted browser behavior; no human usability or continuous temporal certification'))
