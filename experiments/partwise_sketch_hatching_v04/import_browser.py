"""Actual browser file uploads, local edits, downloads and a fresh-server cycle."""
import runtime
from runtime import js,sha,now
from pathlib import Path
import json,shutil,zipfile,urllib.request,urllib.error
import numpy as np
from PIL import Image
from media import contact

def locality(before,after,region,output):
    with np.load(before.with_name('frame_000_arrays.npz')) as z:a={k:z[k] for k in z.files}
    with np.load(after.with_name('frame_000_arrays.npz')) as z:b={k:z[k] for k in z.files}
    fixed=[k for k in a if k in ('regions','depth','contour') or k.startswith('layer_') and k!=f'layer_{region}' or k.startswith('stroke_layer_') and not k.startswith(f'stroke_layer_{region}_')]
    assert all(np.array_equal(a[k],b[k]) for k in fixed)
    from scipy.ndimage import binary_dilation,binary_erosion
    mask=a['regions']==region;band=binary_dilation(mask,iterations=2)&~binary_erosion(mask,iterations=2)
    delta=np.abs(a['image']-b['image']);far=(a['regions']>0)&~mask&~band;background=(a['regions']==0)&~band
    assert delta[mask&~band].sum()>0 and delta[far].sum()==0 and delta[background].sum()==0
    result=dict(region=region,target_interior_L1=float(delta[mask&~band].sum()),far_other_L1=float(delta[far].sum()),
        far_background_L1=float(delta[background].sum()),boundary_band_L1=float(delta[band].sum()),
        ink_before=float(a[f'layer_{region}'].sum()),ink_after=float(b[f'layer_{region}'].sum()),unchanged_arrays=fixed,
        scope='One saved camera per model, proxy labels with fixed 2px band; not independent semantic truth.')
    js(output,result);return result

def exercise(unit,out,app,root,request,execute,click,ready,wait,screenshot,downloads,cold=False):
    states={};items=[];exports=[];events=[]
    def state():return request(app+'/state')
    def raster(s,session=out/'session'):return session/s['images']['image'].removeprefix('/image/')
    def save(key,s):
        states[key]=s;shutil.copy2(raster(s),out/(key+'.png'))
        items.append((s['scene'].title()+' | '+key,Image.open(raster(s)).copy()))
    def upload(path,valid=True):
        old=state()
        element=request(root+'/element','POST',{'using':'css selector','value':'#importFile'})['value']['element-6066-11e4-a52e-4f735466cecf']
        request(root+'/element/'+element+'/value','POST',{'text':str(path.resolve())})
        click('#importAsset')
        if valid:wait(lambda:state()['example']!=old['example']);wait(ready)
        else:
            wait(lambda:execute("return document.getElementById('status').textContent.startsWith('Invalid saved asset:');"));wait(ready)
            assert state()==old
        return state()
    def action(selector):
        revision=state()['revision'];click(selector);wait(lambda:state()['revision']==revision+1);wait(ready);return state()
    def edit(region,strength):
        execute("document.getElementById('region').value="+json.dumps(str(region))+";document.getElementById('region').dispatchEvent(new Event('change'));document.getElementById('inkStrength').value="+str(strength)+";")
        return action('#apply')
    def switch(key,model=False):
        control='scene' if model else 'example'
        execute("document.getElementById('"+control+"').value="+json.dumps(key)+";document.getElementById('"+control+"').dispatchEvent(new Event('change'));")
        wait(lambda:state()[control]==key);wait(ready);return state()
    def download(selector,destination,seconds=240):
        before={p.name for p in downloads.iterdir()};click(selector)
        def complete():
            files=[p for p in downloads.iterdir() if p.name not in before and p.suffix in ('.zip','.png')]
            return files[0] if len(files)==1 and not list(downloads.glob('*.part')) else None
        file=wait(complete,seconds);wait(ready);shutil.copy2(file,destination);return destination
    def same_state(actual,reference):
        for key in ('scene','styles','camera','display','selected_region'):assert actual[key]==reference[key],key
    if cold:
        # Previous harness exited and reaped its viewer and Firefox before this run.
        assert (unit/'browser/CLEANUP.json').is_file()
        source=json.loads((unit/'browser/EXPORT_STATES.json').read_text());checks=[]
        for scene,region,prior in [('lego',1,.6),('chair',2,.8)]:
            current=upload(unit/'browser'/(scene+'_saved_asset.zip'));reference=source[scene]
            same_state(current,reference);assert not current['can_undo'] and current['draft'] is None
            assert current['import_receipt']['integrity']=='manifest_sha256_and_anchor_validation'
            expected=raster(reference,unit/'browser/session')
            assert sha(raster(current))==sha(expected)
            with np.load(raster(current).with_name('frame_000_arrays.npz')) as a,np.load(expected.with_name('frame_000_arrays.npz')) as b:
                assert set(a.files)==set(b.files) and all(np.array_equal(a[k],b[k]) for k in a.files)
            save(scene+'_cold_import',current)
            changed=edit(region,prior);assert sha(raster(changed))!=sha(expected)
            restored=action('#undo');assert sha(raster(restored))==sha(expected)
            request(root+'/refresh','POST',{});wait(ready)
            assert execute("return document.getElementById('example').value;")==restored['example']
            checks.append(dict(scene=scene,PNG_exact=True,all_arrays_exact=True,final_state_exact=True,continue_edit_and_undo=True,
                archive_sha256=sha(unit/'browser'/(scene+'_saved_asset.zip'))))
        screenshot('02_cold_import_edit_undo')
        contact(unit/'media/cold_import.png',items,cols=2,size=512,title='Fresh server | browser upload | saved final states restored exactly')
        js(out/'BROWSER_VALIDATION.json',dict(status='PASS',utc=now(),actual_browser=True,new_server=True,old_server_cleanup_verified=True,checks=checks))
        return
    initial=state();save('default_lego',initial)
    legacy=unit.parent/'unit_017/browser/lego_asset.zip'
    imported=upload(legacy);save('legacy_lego_import',imported);legacy_id=imported['example']
    reference=json.loads((unit.parent/'unit_017/browser/EXPORT_STATE.json').read_text())
    same_state(imported,reference)
    assert sha(raster(imported))==sha(unit.parent/'unit_017/browser/lego_image.png')
    assert not imported['can_undo'] and imported['draft'] is None
    screenshot('02_legacy_file_import')
    edited=edit(1,.35);save('lego_local_edit',edited)
    for f in Path(imported['asset']).iterdir():
        if f.is_file() and f.name!='asset.json':assert sha(f)==sha(Path(edited['asset'])/f.name)
    locality(raster(imported),raster(edited),1,out/'LEGO_LOCALITY.json')
    default=switch('default');assert default['asset']==initial['asset'] and not default['can_undo']
    restored=switch(legacy_id);assert restored['asset']==edited['asset']
    rotated=action('#right');zoomed=action('#closer')
    assert sha(raster(rotated))!=sha(raster(edited)) and sha(raster(zoomed))!=sha(raster(rotated))
    execute('for(const [k,v] of Object.entries('+json.dumps(edited['camera'])+'))document.getElementById(k).value=v;')
    lego=action('#updateView');assert sha(raster(lego))==sha(raster(edited))
    file=download('#downloadAsset',out/'lego_saved_asset.zip',60)
    with zipfile.ZipFile(file) as z:
        assert 'ASSET_MANIFEST.json' in z.namelist();z.extractall(out/'exported_lego')
    for control,kind in [('downloadPng','image'),('exportOrbit','orbit'),('exportZoom','zoom')]:
        target=out/('lego_'+kind+('.png' if kind=='image' else '.zip'))
        file=download('#'+control,target)
        if kind=='image':assert sha(file)==sha(raster(lego));exports.append(dict(kind=kind,PNG_exact=True))
        else:
            with zipfile.ZipFile(file) as z:z.extractall(out/('lego_'+kind))
            receipt=json.loads((out/('lego_'+kind)/'PRESENTATION.json').read_text())
            assert receipt['all_proxy_vertices_inside'] and not receipt['paths_regenerated']
            exports.append(dict(kind=kind,frame_count=receipt['frame_count'],whole_proxy_inside=True))
    chair=switch('chair',True);save('default_chair',chair)
    file=download('#downloadAsset',out/'chair_default_asset.zip',60)
    chair_import=upload(file);save('chair_import',chair_import);chair_id=chair_import['example']
    assert sha(raster(chair_import))==sha(raster(chair));assert not chair_import['can_undo']
    chair_edited=edit(2,.5);save('chair_local_edit',chair_edited)
    locality(raster(chair_import),raster(chair_edited),2,out/'CHAIR_LOCALITY.json')
    download('#downloadAsset',out/'chair_saved_asset.zip',60)
    with zipfile.ZipFile(out/'chair_saved_asset.zip') as z:z.extractall(out/'exported_chair')
    switch('default');assert state()['asset']==chair['asset'] and state()['styles']==chair['styles']
    switch(chair_id);assert state()['asset']==chair_edited['asset']
    # Bad file upload and stale identity must leave the active session intact.
    (out/'invalid.zip').write_bytes(b'not a saved asset zip');upload(out/'invalid.zip',False)
    before=state()
    req=urllib.request.Request(app+'/import?scene=chair&example=default&revision=0',data=b'invalid',headers={'Content-Type':'application/zip'})
    try:urllib.request.urlopen(req,timeout=10)
    except urllib.error.HTTPError as error:assert error.code==422
    else:raise AssertionError('stale upload accepted')
    assert state()==before
    screenshot('03_bad_upload_preserves_edit')
    restored=switch('lego',True);assert restored['asset']==lego['asset'] and restored['example']==legacy_id
    request(root+'/refresh','POST',{});wait(ready)
    assert execute("return document.getElementById('example').value;")==legacy_id
    screenshot('04_imported_example_restored')
    js(out/'EXPORT_STATES.json',dict(lego=lego,chair=chair_edited));js(out/'STATES.json',states)
    contact(unit/'media/import_local_edits.png',items,cols=3,size=512,title='Real model assets | imported states and local ink edits | geometry unchanged')
    js(out/'BROWSER_VALIDATION.json',dict(status='PASS',utc=now(),actual_browser=True,software_rendering=True,
        models=['lego','chair'],legacy_Lego_PNG_exact=True,Chair_manifest_PNG_exact=True,
        imported_session_edit_undo_isolation=True,invalid_upload_active_state_unchanged=True,stale_import_rejected=True,
        actual_download_count=6,exports=exports,scope='Finite CPU browser import/edit/export exercise; no visual or scientific quality promotion.'))
