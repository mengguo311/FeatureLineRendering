from env import *
if __name__=='__main__':
 records=[]
 try:
  for script,args,log in [('test_runner.py',[],'TEST_REGRESSION_02.log'),('report.py',[],'REPORT_BUILD.log'),('verify.py',['--readonly','--replay'],'VERIFY_REPLAY.log')]:
   guard();cmd=[sys.executable,'-B',str(CODE/script)]+args;dest=ROOT/log;assert not dest.exists();start=now()
   with dest.open('w') as out:
    p=subprocess.Popen(cmd,stdout=out,stderr=subprocess.STDOUT);state('FINAL_VALIDATION',status='RUNNING',children=[p.pid],active_command=script);rc=p.wait()
   records.append(dict(command=cmd,pid=p.pid,exit_code=rc,started=start,ended=now(),log=str(dest),sha256=sha(dest)));js(ROOT/'FINAL_EXECUTION.json',dict(records=records));state('VALIDATION_UNIT_EXIT',status='READY_FOR_REVIEW' if rc==0 else 'ENGINEERING_NOT_READY',children=[],active_command=None)
   if rc:raise RuntimeError((script,rc))
 except Exception as e:state('VALIDATION_FAILED',status='ENGINEERING_NOT_READY',children=[],error=repr(e));raise
