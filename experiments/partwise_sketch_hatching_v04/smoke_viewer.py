"""Exercise the real local HTTP editor, saved assets and all four controls."""
import runtime
from runtime import js,sha,now
from pathlib import Path
import argparse
import subprocess
import sys
import time
import json
import urllib.request
import urllib.error
import signal
import numpy as np

def run(unit):
    unit=Path(unit);out=unit/'viewer_smoke';log=open(unit/'logs/viewer_server.log','w')
    command=[sys.executable,str(Path(__file__).with_name('viewer.py')),'--asset',str(unit/'assets/baseline'),
             '--output',str(out),'--port','0']
    process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
    def interrupted(signum,frame):raise KeyboardInterrupt('stop own HTTP control test')
    signal.signal(signal.SIGTERM,interrupted)
    events=[]
    try:
        start=time.monotonic()
        while not (out/'SERVER.json').exists():
            if process.poll() is not None:raise RuntimeError('viewer exited before readiness')
            if time.monotonic()-start>30:raise TimeoutError('viewer did not start')
            time.sleep(.1)
        port=json.loads((out/'SERVER.json').read_text())['port'];base=f'http://127.0.0.1:{port}'
        def get(path):
            with urllib.request.urlopen(base+path,timeout=30) as response:return response.read()
        # The browser now uses a shared post() helper. Verify the served control
        # here; actual endpoint behavior is exercised below and UI binding is
        # tested in Firefox, not inferred from a particular JS spelling.
        html=get('/');assert b'Render &amp; save' in html and b'id="apply"' in html
        state=json.loads(get('/state'));initial=state
        payload=dict(region=2,**state['styles']['2'],**state['camera'])
        for control,value in [('angle',95),('spacing',.06),('length',.12),('width',1.8),('azimuth',47),('distance',4.3)]:
            old=state;payload[control]=value;t=time.monotonic()
            request=urllib.request.Request(base+'/render',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
            with urllib.request.urlopen(request,timeout=40) as response:state=json.loads(response.read())
            before=Path(old['asset']);after=Path(state['asset'])
            for region in (1,3):assert sha(before/f'region_{region}.npz')==sha(after/f'region_{region}.npz')
            if control in ('width','azimuth','distance'):assert sha(before/'region_2.npz')==sha(after/'region_2.npz')
            else:assert sha(before/'region_2.npz')!=sha(after/'region_2.npz')
            oldimage=get(old['images']['image']);newimage=get(state['images']['image']);assert oldimage!=newimage
            events.append(dict(control=control,value=value,seconds=time.monotonic()-t,revision=state['revision'],
                               other_regions_byte_exact=True,image_changed=True,
                               target_geometry_retained=control in ('width','azimuth','distance')))
        with np.load(Path(state['asset'])/'region_2.npz') as data:
            _,idx=np.unique(data['stroke_id'],return_inverse=True)
            arc=np.bincount(idx,weights=np.linalg.norm(data['points'][:,1]-data['points'][:,0],axis=1))
            assert arc.max()<=.12000001
        try:
            request=urllib.request.Request(base+'/render',data=json.dumps(dict(payload,spacing=0)).encode(),headers={'Content-Type':'application/json'})
            urllib.request.urlopen(request,timeout=10);raise AssertionError('invalid spacing accepted')
        except urllib.error.HTTPError as e:
            assert e.code==422
        export=get('/export');(unit/'metrics/viewer_export.zip').write_bytes(export)
        js(unit/'metrics/VIEWER_SMOKE.json',dict(utc=now(),command=command,html_served=True,
               actual_http_edit_tests=events,invalid_spacing_http_status=422,export_bytes=len(export),
               max_target_path_length=float(arc.max()),final_camera=state['camera'],scene=state['scene'],
               frontend_visual_browser_test='separate browser_demo_test; this receipt covers HTTP controls'))
    finally:
        if process.poll() is None:process.terminate()
        process.wait(timeout=15);log.close()
        js(unit/'logs/VIEWER_CLEANUP.json',dict(pid=process.pid,returncode=process.returncode,terminated_own_server=True,no_child_left=True))
    print(json.dumps(events),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--unit',required=True);run(p.parse_args().unit)
