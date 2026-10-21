"""Start the relocated documented viewer command; exercise all scenes serially."""
import runtime
from runtime import OUTPUT_ROOT,js,now
import json,subprocess,os,signal,time,urllib.request
U=OUTPUT_ROOT/'units/unit_008';package=U/'relocated/portable_demo';out=package/'runs/viewer_smoke'
cmd=[str(package/'run.sh'),'viewer','--scene','lego','--port','0','--output',str(out)]
log=open(U/'logs/portable_viewer_server.log','w');child=subprocess.Popen(cmd,cwd=package,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
js(U/'metrics/PORTABLE_VIEWER_START.json',dict(command=cmd,pid=child.pid,own_process_group=child.pid))
def interrupted(signum,frame):raise KeyboardInterrupt('stop own portable smoke')
signal.signal(signal.SIGTERM,interrupted)
def request(url,body=None):
 req=urllib.request.Request(url,data=json.dumps(body).encode() if body else None,headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=30) as response:return response.read()
try:
 end=time.monotonic()+45
 while not (out/'SERVER.json').is_file():
  if child.poll() is not None:raise RuntimeError('viewer exited')
  if time.monotonic()>end:raise TimeoutError('viewer startup')
  time.sleep(.1)
 port=json.loads((out/'SERVER.json').read_text())['port'];app=f'http://127.0.0.1:{port}'
 state=json.loads(request(app+'/state'));assert state['scene']=='lego' and state['selected_region']==4
 assert b'id="scene"' in request(app+'/')
 rows=[]
 for scene in ('chair','drums','lego'):
  state=json.loads(request(app+'/scene',dict(scene=scene,from_scene=state['scene'])))
  assert state['scene']==scene
  assert request(app+state['images']['image']).startswith(b'\x89PNG')
  rows.append(dict(scene=scene,regions=state['regions'],image=state['images']['image'],seconds=state['seconds']))
 js(U/'metrics/PORTABLE_VIEWER.json',dict(status='PASS',command=cmd,utc=now(),scenes=rows,actual_local_HTTP_server=True,scope='relocated package launch and scene switching; full browser controls tested separately on identical source'))
finally:
 if child.poll() is None:os.killpg(child.pid,signal.SIGTERM)
 try:child.wait(timeout=10)
 except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=10)
 log.close();js(U/'metrics/PORTABLE_VIEWER_CLEANUP.json',dict(pid=child.pid,returncode=child.returncode,own_process_group_only=True))
