"""Actual Firefox edit, layout and fresh-server ZIP round trips on two models."""
import runtime
from runtime import js,sha,now
from pathlib import Path
import argparse,json,shutil,time,zipfile
import numpy as np
from scipy.ndimage import binary_dilation,binary_erosion
from unit025_run import U
from browser_demo_test import run

def exercise(unit,out,app,root,request,execute,click,ready,wait,screenshot,downloads):
    cold='cold' in out.name;events=[];p=json.loads((unit/'PROTOCOL.json').read_text())
    def state():return request(app+'/state')
    def path(s):return out/'session'/s['images']['image'].removeprefix('/image/')
    def snapshot(s,name):
        dest=out/name;dest.mkdir()
        for f in path(s).parent.iterdir():shutil.copy2(f,dest/f.name)
        js(dest/'STATE.json',s)
        return dest
    def exact(a,b):
        assert sha(a/'frame_000_image.png')==sha(b/'frame_000_image.png')
        with np.load(a/'frame_000_arrays.npz') as x,np.load(b/'frame_000_arrays.npz') as y:
            assert set(x.files)==set(y.files) and all(np.array_equal(x[k],y[k]) for k in x.files)
    def choose(id,value):
        execute('document.getElementById('+json.dumps(id)+').value='+json.dumps(value)+';document.getElementById('+json.dumps(id)+').dispatchEvent(new Event("change"));')
    def action(selector):
        rev=state()['revision'];t=time.monotonic();click(selector)
        wait(lambda:state()['revision']==rev+1);wait(ready)
        s=state();events.append(dict(scene=s['scene'],action=selector,observed_seconds=time.monotonic()-t,operation_seconds=s.get('operation_seconds'),draw_seconds=s['seconds'],cache=s['render_cache']))
        return s
    def ink(value):
        choose('region','4')
        execute('document.getElementById("inkStrength").value='+str(value)+';document.getElementById("inkStrength").dispatchEvent(new Event("input"));')
        return action('#apply')
    def download(selector,name):
        prior={f.name for f in downloads.iterdir()};click(selector)
        def complete():
            files=[f for f in downloads.iterdir() if f.name not in prior and f.suffix in ('.zip','.png')]
            return files[0] if len(files)==1 and not list(downloads.glob('*.part')) else None
        source=wait(complete,240);wait(ready);dest=out/name;shutil.copy2(source,dest);return dest
    def layout(label):
        data=execute('''return {width:innerWidth,height:innerHeight,scroll:scrollY,documentWidth:document.documentElement.scrollWidth,controls:Object.fromEntries(['apply','undo','downloadAsset','downloadPng','status'].map(id=>{const e=document.getElementById(id),r=e.getBoundingClientRect(),x=r.x+r.width/2,y=r.y+r.height/2,top=document.elementFromPoint(x,y);return [id,{x:r.x,y:r.y,width:r.width,height:r.height,visible:r.x>=0&&r.y>=0&&r.right<=innerWidth&&r.bottom<=innerHeight,uncovered:top===e||e.contains(top)}]}))};''')
        screenshot(label)
        assert data['documentWidth']<=data['width'],data
        assert all(v['visible'] and v['uncovered'] for v in data['controls'].values()),data
        events.append(dict(action='primary actions and status visible, no horizontal overflow',label=label,layout=data))
    if not cold:
        for w,h in [(1280,800),(1024,768),(390,844)]:
            request(root+'/window/rect','POST',dict(width=w,height=h));execute('window.scrollTo(0,0);');layout(f'layout_{w}_top')
            execute('document.querySelector("aside").scrollTop=10000;window.scrollTo(0,document.body.scrollHeight);');layout(f'layout_{w}_bottom')
        request(root+'/window/rect','POST',dict(width=1280,height=900));execute('window.scrollTo(0,0);document.querySelector("aside").scrollTop=0;')
    for scene,details in p['inputs'].items():
        if cold:
            old=state()['example']
            element=request(root+'/element','POST',{'using':'css selector','value':'#importFile'})['value']['element-6066-11e4-a52e-4f735466cecf']
            request(root+'/element/'+element+'/value','POST',{'text':str(unit/'browser'/f'{scene}_edited.zip')});click('#importAsset')
            wait(lambda:state()['example']!=old);wait(ready);s=state()
            assert s['scene']==scene and not s['can_undo'] and not s['render_cache']['hit'] and s['render_cache']['builds']==1
            current=snapshot(s,scene+'_imported');exact(current,unit/'browser'/(scene+'_edited'))
            source=json.loads((unit/'browser'/(scene+'_edited')/'STATE.json').read_text())
            assert s['camera']==source['camera'] and s['styles']==source['styles']
            assert all(sha(f)==sha(Path(s['asset'])/f.name) for f in Path(source['asset']).iterdir() if f.suffix=='.npz')
            events.append(dict(action='fresh-server ZIP cold import exact PNG/arrays and paths',scene=scene,first_draw_cache_miss=True))
            screenshot(scene+'_cold_import')
            # Imported data remains editable; restore the same edited state afterwards.
            ink(.5);s=ink(details['ink_strength']);exact(path(s).parent,current)
        else:
            if state()['scene']!=scene:
                choose('scene',scene);wait(lambda:state()['scene']==scene);wait(ready)
            choose('example',details['example']);wait(lambda:state()['example']==details['example']);wait(ready)
            s=state();baseline=snapshot(s,scene+'_baseline');original=Path(s['asset'])
            edited=ink(details['ink_strength']);dest=snapshot(edited,scene+'_edited')
            assert edited['operation_seconds']>=edited['seconds']
            status=execute('return document.getElementById("status").textContent;')
            assert 'ready in' in status and 'save + render' in status,status
            assert all(sha(f)==sha(Path(edited['asset'])/f.name) for f in original.iterdir() if f.suffix=='.npz')
            with np.load(baseline/'frame_000_arrays.npz') as a,np.load(dest/'frame_000_arrays.npz') as b:
                delta=np.abs(a['image']-b['image']);target=a['regions']==4
                band=binary_dilation(target,iterations=2)&~binary_erosion(target,iterations=2)
                masks=dict(target=target&~band,boundary=band,far_other=(a['regions']>0)&~target&~band,far_background=(a['regions']==0)&~band)
                locality={k:dict(pixels=int(v.sum()),L1=float(delta[v].sum())) for k,v in masks.items()}
                assert delta.sum()>0
                unchanged=[k for k in a.files if k in ('depth','regions','contour') or k.startswith('layer_') and k!='layer_4']
                assert all(np.array_equal(a[k],b[k]) for k in unchanged)
            events.append(dict(action='real local ink edit; all NPZ paths and non-target layers preserved',scene=scene,status=status,locality=locality))
            screenshot(scene+'_edited_desktop')
            undone=action('#undo');exact(path(undone).parent,baseline)
            s=ink(details['ink_strength']);exact(path(s).parent,dest)
            request(root+'/refresh','POST',{});wait(ready);choose('region','4')
            assert execute('return +document.getElementById("inkStrength").value;')==details['ink_strength']
        # Actual navigation still uses fixed saved 3D paths.
        asset=state()['asset'];action('#right');action('#closer');assert state()['asset']==asset
        execute('for(const [k,v] of Object.entries('+json.dumps(details['camera'])+'))document.getElementById(k).value=v;')
        saved=action('#updateView');exact(path(saved).parent,unit/'browser'/(scene+'_edited') if cold else out/(scene+'_edited'))
        download('#downloadAsset',scene+'_edited.zip')
        png=download('#downloadPng',scene+'_edited.png');assert sha(png)==sha(path(saved))
        if cold and scene=='chair':
            for kind in ('orbit','zoom'):
                archive=download('#export'+kind.title(),scene+'_'+kind+'.zip')
                with zipfile.ZipFile(archive) as z:z.extractall(out/(scene+'_'+kind))
                receipt=json.loads((out/(scene+'_'+kind)/'PRESENTATION.json').read_text())
                assert receipt['all_proxy_vertices_inside'] and not receipt['paths_regenerated']
                videos=json.loads((out/(scene+'_'+kind)/'VIDEO_RECEIPTS.json').read_text())
                assert all(v['encode_returncode']==v['decode_returncode']==0 and v['decoded_frames']==receipt['frame_count'] for v in videos)
                assert next(v for v in videos if v['file'].endswith('.mkv'))['all_frames_exact']
                events.append(dict(action='actual motion export and full decode',scene=scene,kind=kind,frames=receipt['frame_count']))
        execute('window.scrollTo(0,0);document.querySelector("aside").scrollTop=0;');layout(scene+'_finished')
    js(out/'BROWSER_VALIDATION.json',dict(status='PASS',utc=now(),actual_browser=True,fresh_server=cold,events=events,scope='Finite UI tasks on existing CPU-derived proxies; not independent geometry or temporal certification.'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--name',default='browser');p.add_argument('--catalog',type=Path);a=p.parse_args()
    run(U,a.name,catalog=a.catalog or U/'portable_demo/CATALOG.json',exercise=exercise)
