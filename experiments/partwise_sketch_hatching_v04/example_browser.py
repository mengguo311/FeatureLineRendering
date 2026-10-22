"""Actual browser example switching, independent local editing and downloads."""
import runtime
from runtime import js,sha,now
from pathlib import Path
import json,shutil,zipfile,urllib.error
import numpy as np
from PIL import Image
from media import contact

def exercise(unit,out,app,root,request,execute,click,ready,wait,screenshot,downloads):
    events=[];states={};items=[]
    def state():return request(app+'/state')
    def idle():return execute("return document.getElementById('preview').complete && document.getElementById('preview').naturalWidth===512 && !document.getElementById('scene').disabled;")
    def raster(s):return out/'session'/s['images']['image'].removeprefix('/image/')
    def save_state(key,s):
        states[key]=s;shutil.copy2(raster(s),out/(key+'.png'))
        items.append((s['scene'].title()+' | '+s['demo_example']['label']+' | '+key,Image.open(raster(s)).copy()))
    def switch(key,scene=False):
        control='scene' if scene else 'example'
        execute("document.getElementById('"+control+"').value="+json.dumps(key)+";document.getElementById('"+control+"').dispatchEvent(new Event('change'));")
        wait(lambda:state()[control]==key);wait(idle);return state()
    def action(selector):
        rev=state()['revision'];click(selector);wait(lambda:state()['revision']==rev+1);wait(ready);return state()
    def post(path,body):
        s=state();return request(app+path,'POST',dict(scene=s['scene'],example=s['example'],**body))
    initial=state();save_state('default_lego',initial)
    assert list(initial['available_examples'])==['default','lego_bucket_cross','lego_bucket_refined','lego_platform_ink']
    for key in ('lego_bucket_cross','lego_bucket_refined','lego_platform_ink'):
        s=switch(key);save_state(key,s)
        assert s['demo_example']['id']==key and not s['can_undo']
        assert execute("return document.getElementById('exampleSource').textContent;")==s['demo_example']['description']
    baseline=state()
    assert sha(raster(baseline))==sha(unit.parent/'unit_016/browser/lego_image.png')
    screenshot('02_named_example')
    def edit():
        execute("document.getElementById('region').value='1';document.getElementById('region').dispatchEvent(new Event('change'));document.getElementById('inkStrength').value=.6;document.getElementById('inkStrength').dispatchEvent(new Event('input'));")
        return action('#apply')
    edited=edit();save_state('platform_edited',edited)
    assert sha(raster(edited))!=sha(raster(baseline))
    for f in Path(baseline['asset']).iterdir():
        if f.is_file() and f.name!='asset.json':assert sha(f)==sha(Path(edited['asset'])/f.name)
    for r in ('2','3','4'):assert baseline['styles'][r]==edited['styles'][r]
    # Real rendered locality: the saved paths stay fixed and only target ink changes.
    def arrays(s):
        with np.load(raster(s).with_name('frame_000_arrays.npz')) as z:return {k:z[k] for k in z.files}
    a,b=arrays(baseline),arrays(edited)
    fixed=('depth','regions','contour','layer_2','layer_3','layer_4','stroke_layer_4_0','stroke_layer_4_1')
    assert all(np.array_equal(a[k],b[k]) for k in fixed)
    from scipy.ndimage import binary_dilation,binary_erosion
    mask=a['regions']==1;band=binary_dilation(mask,iterations=2)&~binary_erosion(mask,iterations=2)
    delta=np.abs(a['image']-b['image']);far=(a['regions']>0)&~mask&~band;background=(a['regions']==0)&~band
    assert delta[mask&~band].sum()>0 and delta[far].sum()==0 and delta[background].sum()==0
    js(out/'LOCALITY.json',dict(target_interior_L1=float(delta[mask&~band].sum()),far_other_L1=float(delta[far].sum()),
        far_background_L1=float(delta[background].sum()),target_ink_before=float(a['layer_1'].sum()),target_ink_after=float(b['layer_1'].sum()),
        unchanged_arrays=list(fixed),all_path_mesh_files_exact=True,scope='Single saved camera; proxy-label mask and fixed2px band, not independent semantics.'))
    other=switch('lego_bucket_cross');assert not other['can_undo']
    assert sha(raster(other))==sha(out/'lego_bucket_cross.png')
    # Same model and revision can still refer to the wrong example; reject it.
    stale=dict(scene='lego',example='lego_platform_ink',revision=other['revision'])
    rejected=[]
    for endpoint,extra in [('/render',dict(region=1,**edited['styles']['1'],**edited['camera'])),('/undo',{}),
                           ('/view',other['camera']),('/display',dict(display=other['display'])),
                           ('/presentation',dict(kind='image')),('/example',dict(target_example='default'))]:
        try:request(app+endpoint,'POST',stale|extra)
        except urllib.error.HTTPError as e:assert e.code==422;rejected.append(endpoint)
        else:raise AssertionError('stale example accepted: '+endpoint)
        assert state()==other
    # Keep a genuine visible-face draft in another example while the ink edit remains saved.
    draft=post('/selection',dict(revision=other['revision'],source_region=4,mode='visible',rectangle=[200,60,440,280],operation='replace'))
    assert draft['face_count']>0
    restored=switch('lego_platform_ink');assert restored['asset']==edited['asset'] and restored['draft'] is None
    restored=switch('lego_bucket_cross');assert restored['draft']['face_count']==draft['face_count'] and restored['draft']['token']==draft['token']
    click('#clearSelection');wait(lambda:state()['draft'] is None);wait(idle)
    switch('lego_platform_ink')
    for scene in ('chair','drums','ficus'):
        s=switch(scene,True);save_state('default_'+scene,s)
        assert s['example']=='default' and len(s['available_examples'])==1
    restored=switch('lego',True)
    assert restored['example']=='lego_platform_ink' and restored['asset']==edited['asset']
    request(root+'/refresh','POST',{});wait(ready)
    assert execute("return document.getElementById('example').value;")=='lego_platform_ink'
    assert execute("return +document.getElementById('inkStrength').value;")==.6
    undone=action('#undo');assert sha(raster(undone))==sha(raster(baseline))
    edited=edit();assert sha(raster(edited))==sha(out/'platform_edited.png')
    screenshot('03_edit_restored')
    rotated=action('#right');zoomed=action('#closer')
    assert sha(raster(rotated))!=sha(raster(edited)) and sha(raster(zoomed))!=sha(raster(rotated))
    execute('for(const [k,v] of Object.entries('+json.dumps(edited['camera'])+'))document.getElementById(k).value=v;')
    saved=action('#updateView');assert sha(raster(saved))==sha(raster(edited));js(out/'EXPORT_STATE.json',saved)
    def download(selector,seconds=240):
        before={f.name for f in downloads.iterdir()};click(selector)
        def complete():
            files=[f for f in downloads.iterdir() if f.name not in before and f.is_file() and f.suffix in ('.png','.zip')]
            return files[0] if len(files)==1 and not list(downloads.glob('*.part')) else None
        file=wait(complete,seconds);wait(ready);return file
    file=download('#downloadAsset',60);shutil.copy2(file,out/'lego_asset.zip')
    with zipfile.ZipFile(file) as z:z.extractall(out/'exported_asset')
    meta=json.loads((out/'exported_asset/asset.json').read_text())
    assert meta['styles']==saved['styles'] and meta['demo_example']==saved['demo_example'] and meta['selected_region']==1
    exports=[]
    for control,kind in [('downloadPng','image'),('exportOrbit','orbit'),('exportZoom','zoom')]:
        file=download('#'+control);shutil.copy2(file,out/('lego_'+kind+file.suffix))
        if kind=='image':assert sha(file)==sha(raster(saved));record=dict(kind=kind,png_exact=True)
        else:
            bundle=out/('lego_'+kind)
            with zipfile.ZipFile(file) as z:z.extractall(bundle)
            receipt=json.loads((bundle/'PRESENTATION.json').read_text())
            assert receipt['all_proxy_vertices_inside'] and not receipt['paths_regenerated']
            assert json.loads((bundle/'asset/asset.json').read_text())['demo_example']==saved['demo_example']
            record=dict(kind=kind,frame_count=receipt['frame_count'],all_inside=True)
        exports.append(record)
    screenshot('04_export_complete')
    contact(unit/'media/catalog_all_models_examples.png',items,cols=3,size=512,title='Actual saved model examples | independent sessions | unchanged source assets')
    contact(unit/'media/local_edit.png',[('Platform ink .40',Image.open(raster(baseline))),('Saved local ink .60',Image.open(raster(edited)))],cols=2,size=512,title='Lego | region 1 only | fixed paths and geometry')
    js(out/'STATES.json',states)
    js(out/'BROWSER_VALIDATION.json',dict(status='PASS',utc=now(),actual_browser=True,software_rendering=True,
        models_visited=['lego','chair','drums','ficus'],examples_visited=list(initial['available_examples']),
        independent_edit_undo_camera=True,draft_isolation_face_count=draft['face_count'],stale_example_rejected=rejected,
        previous_unit_PNG_exact=True,actual_download_count=4,exports=exports,events=events,
        scope='Finite browser/session operations on real-model proxies; no human usability or scientific/temporal certification.'))
