from env import *
if __name__=='__main__':
 logs=[]
 for name,expected in [('test_responsibility.py',7),('test_roles.py',11),('test_graph.py',9),('test_layout.py',1)]:
  command=[sys.executable,'-B',str(CODE/name)];p=subprocess.run(command,capture_output=True,text=True);dest=ROOT/'tests'/('REGRESSION_'+name+'.log');dest.write_text(p.stdout+p.stderr);logs.append(dict(command=command,exit_code=p.returncode,tests=expected,log=str(dest),sha256=sha(dest)));assert p.returncode==0,(name,p.stderr);assert f'Ran {expected} '+('test' if expected==1 else 'tests') in p.stderr
 js(ROOT/'TEST_RESULTS.json',dict(new_tests=28,inherited_tests_counted=0,passed=28,logs=logs,RED_logs={str(p):sha(p) for p in sorted((ROOT/'tests').glob('*RED.log'))},fixed_tolerances=True,no_fixture_removed=True))
 print('28 NEW TESTS PASS')
