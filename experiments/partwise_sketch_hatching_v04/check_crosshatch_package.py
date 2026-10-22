"""Fresh-process checks of the extracted archive using documented commands."""
import runtime
from runtime import OUTPUT_ROOT,js,sha,now
from pathlib import Path
import json,subprocess,time,urllib.request,signal
import numpy as np
u=OUTPUT_ROOT/'units/unit_013';package=u/'final_archive/portable_demo';events=[]
def command(name,args):
    cmd=[str(package/'run.sh'),*args];start=time.monotonic()
    with (u/'logs'/(name+'.log')).open('w') as log:r=subprocess.run(cmd,cwd=package,stdout=log,stderr=subprocess.STDOUT,timeout=240)
    receipt=dict(command=cmd,cwd=str(package),returncode=r.returncode,seconds=time.monotonic()-start)
    js(u/'logs'/(name+'.receipt.json'),receipt);r.check_returncode();events.append(receipt)
command('final_cli_edit',['edit','--scene','chair','--region','2','--cross','on','--cross-angle','60','--cross-spacing','.060','--output',str(package/'runs/cli_cross')])
command('final_cli_image',['export','--scene','chair','--asset',str(package/'runs/cli_cross'),'--kind','image','--azimuth','47','--elevation','25','--distance','5.2','--output',str(package/'runs/cli_image')])
assert sha(package/'runs/cli_image/frames/frame_000_image.png')==sha(u/'browser/chair_image.png')
command('final_cli_off',['edit','--scene','chair','--asset',str(package/'runs/cli_cross'),'--region','2','--cross','off','--output',str(package/'runs/cli_off')])
assert sha(package/'runs/cli_cross/region_2.npz')==sha(package/'runs/cli_off/region_2.npz')
for region in (1,3):assert sha(package/f'assets/chair/region_{region}.npz')==sha(package/f'runs/cli_cross/region_{region}.npz')
with np.load(package/'runs/cli_cross/region_2.npz') as a,np.load(package/'examples/chair_cross/region_2.npz') as b:
    assert set(a.files)==set(b.files) and all(np.array_equal(a[k],b[k]) for k in a.files)
out=package/'runs/cold_viewer';cmd=[str(package/'run.sh'),'viewer','--scene','chair','--asset',str(package/'examples/chair_cross'),'--output',str(out),'--port','0']
process=None
def stop(signum,frame):raise KeyboardInterrupt('stop owned package test')
signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
try:
    with (u/'logs/final_viewer.log').open('w') as log:
        process=subprocess.Popen(cmd,cwd=package,stdout=log,stderr=subprocess.STDOUT)
        js(u/'logs/FINAL_VIEWER_CHILD.json',dict(pid=process.pid,command=cmd))
        start=time.monotonic()
        while not (out/'SERVER.json').exists():
            if process.poll() is not None:raise RuntimeError('cold viewer exited')
            if time.monotonic()-start>30:raise TimeoutError('cold viewer readiness')
            time.sleep(.1)
        port=json.loads((out/'SERVER.json').read_text())['port'];url='http://127.0.0.1:'+str(port)
        with urllib.request.urlopen(url+'/state',timeout=15) as r:state=json.loads(r.read())
        saved=json.loads((u/'browser/EXPORT_STATE.json').read_text())
        assert state['styles']==saved['styles'] and state['camera']==saved['camera'] and state['display']==saved['display']
        with urllib.request.urlopen(url+state['images']['image'],timeout=15) as r:png=r.read()
        assert png==(u/'browser/chair_image.png').read_bytes()
        with urllib.request.urlopen(url,timeout=15) as r:assert b'id="crossEnabled"' in r.read()
finally:
    if process is not None:
        if process.poll() is None:process.terminate()
        process.wait(timeout=15)
        js(u/'logs/FINAL_VIEWER_CLEANUP.json',dict(pid=process.pid,returncode=process.returncode,own_process_exited=True))
js(u/'metrics/FINAL_ARCHIVE_REPLAY.json',dict(utc=now(),documented_CLI_edit_on_off=True,CLI_generated_paths_equal_browser=True,
    CLI_PNG_exact=True,cold_viewer_PNG_exact=True,cold_viewer_style_camera_display_exact=True,
    archive='portable_demo.tar.gz',archive_sha256=sha(u/'portable_demo.tar.gz'),commands=events))
