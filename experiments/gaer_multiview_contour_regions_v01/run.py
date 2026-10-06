import runtime as rt
import sys,traceback,time,json
def main():
 from protocol import freeze
 freeze()
 for scene in ['lego','chair']:
  for key in ['r_7','r_33']:
   p=rt.ART/'tdd'/('native_calibration_'+scene+'_'+key+'.json')
   if not p.exists() or json.loads(p.read_text())['status']!='PASS':raise RuntimeError('native replica calibration not valid')
   if json.loads(p.read_text()).get('code_binding',{}).get('cpu_native_py_sha256')!=rt.sha(rt.EXP/'cpu_native.py'):raise RuntimeError('native calibration code binding stale')
 from pipeline import extract_scene,fusion_arm,dev_scene,seal_scene,eval_scene,arc_scene
 command=sys.argv[1] if len(sys.argv)>1 else 'all';scenes=sys.argv[2:] or ['lego','chair'];failures=[]
 stages=[('extract',extract_scene),('fuse',lambda n:[fusion_arm(n,'two_source'),fusion_arm(n,'multi24')]),('develop',dev_scene),('seal',seal_scene),('eval',eval_scene),('arc',arc_scene)]
 for stage,fn in stages:
  if command not in ('all',stage):continue
  for n in scenes:
   try:rt.guard(stage+'_'+n);fn(n)
   except Exception as e:
    failure=dict(scene=n,stage=stage,error=repr(e),traceback=traceback.format_exc(),utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),status='INVALID_EXECUTION_NOT_SCIENTIFIC_NO_GO');failures.append(failure)
    with (rt.ART/'logs/failures.jsonl').open('a') as f:f.write(json.dumps(failure)+'\n')
    print('FAILED',n,stage,traceback.format_exc(),flush=True)
 rt.atomic_json(rt.ART/'results'/('RUN_'+command+'.json'),dict(command=command,scenes=scenes,failures=failures,status='COMPLETE' if not failures else 'PARTIAL_EXECUTION'))
 if failures:sys.exit(1)
if __name__=='__main__':main()
