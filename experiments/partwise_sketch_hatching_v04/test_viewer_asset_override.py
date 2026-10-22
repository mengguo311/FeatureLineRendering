"""A real viewer must load the explicit saved asset instead of its catalog default."""
import runtime
from runtime import js,now,output_guard
from pathlib import Path
import argparse,json,subprocess,sys,time,urllib.request,os,signal

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--unit',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--package',type=Path)
    p.add_argument('--asset',type=Path);a=p.parse_args()
    out=output_guard(a.output);out.mkdir(parents=True)
    asset=(a.asset or a.unit/'assets/edited').resolve()
    expected=json.loads((asset/'asset.json').read_text())
    prefix=([str(a.package/'run.sh'),'viewer'] if a.package else
            [sys.executable,str(Path(__file__).with_name('catalog_demo.py')),'viewer','--catalog',str(a.unit/'CATALOG.json')])
    cmd=[*prefix,'--scene',expected['scene'],'--asset',str(asset),'--output',str(out/'session'),'--port','0']
    log=open(out/'server.log','w');child=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    def interrupted(signum,frame):raise KeyboardInterrupt('stop own viewer override test')
    signal.signal(signal.SIGTERM,interrupted)
    try:
        end=time.monotonic()+45
        while not (out/'session/SERVER.json').exists():
            if child.poll() is not None:raise RuntimeError('viewer exited before ready')
            if time.monotonic()>end:raise TimeoutError('viewer startup')
            time.sleep(.1)
        port=json.loads((out/'session/SERVER.json').read_text())['port']
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/state',timeout=30) as response:state=json.loads(response.read())
        js(out/'RESULT.json',dict(utc=now(),command=cmd,requested_asset=str(asset),state=state))
        assert Path(state['asset']).resolve()==asset, 'viewer silently ignored explicit --asset'
        assert state['styles']==expected['styles'] and state['camera']==expected['viewer_camera']
        assert 'available_scenes' not in state, 'explicit asset should use single-model viewer'
        print('PASS: actual viewer loaded explicit saved asset and camera')
    finally:
        if child.poll() is None:os.killpg(child.pid,signal.SIGTERM)
        try:child.wait(timeout=10)
        except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=10)
        log.close();js(out/'CLEANUP.json',dict(pid=child.pid,returncode=child.returncode,own_process_group_only=True))
