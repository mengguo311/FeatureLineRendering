import json,pathlib,sys
O=pathlib.Path(__file__).resolve().parents[1];R=O.parents[1];sys.path[:0]=[str(O/'code'),str(R)]
from cc_verify import audit_one
from cc_io import read_json,write_json
from cc_io import sha
from src.multiscene_audit import bytecode_status
results=[]
statuses=[*list((O/'setup').glob('*_exit.json')),*list((O/'setup/attempt_00').glob('*_exit.json'))]
for status in sorted(statuses):
 key=status.name[:-10];trace=status.parent/f'{key}.strace'
 if not trace.exists():continue
 run=read_json(status);command=run['command'];scene=command[command.index('--scene')+1];base=O/'scenes'/scene
 if '--task' in command:
  task=command[command.index('--task')+1];asset=command[command.index('--asset')+1];out=base/('F' if task=='primary' else 'C' if task=='cross' else 'repeats/'+asset)
 else:
  task='visibility' if key.endswith('_visibility') else 'evaluation';out=O/task/scene
 policy_path=(O/'attempts/evaluation_lego_00/allowlist.json') if status.parent.name=='attempt_00' else out/'allowlist.json'
 policy=read_json(policy_path)
 bootstrap=[O/'config.json',O/'config.json.sha256',O/'PREREG.md',O/'input_hashes.json',R,O/'code',R/'src']
 if task in ['cross','repeat']:
  bootstrap += [base/'F',base/'F/frozen.json',*[base/'F'/p for p in read_json(base/'F/frozen.json')['artifacts']]]
 if task=='evaluation':bootstrap += [base,*[p for p in base.rglob('*') if p.is_dir()]]
 bytecode=[]
 if task=='visibility':
  ev=O/'evaluation'/scene
  bootstrap += [O/'setup',O/'setup/visibility_worker.py',R/'out/multiscene_foundation_corrected/MANIFEST.json',ev/'frozen.json',*[ev/p for p in read_json(ev/'frozen.json')['artifacts']],base/'F',ev]
  for name in ['__init__','common','corrected_layers','corrected_qualification','corrected_sampling','foundation','multiscene','multiscene_probe','multiscene_qualification']:
   source=R/f'src/{name}.py';cache=R/f'src/__pycache__/{name}.cpython-39.pyc';state=bytecode_status(cache,source)
   assert state['status']=='SOURCE_EQUIVALENT', (cache,state)
   bootstrap.append(cache);bytecode.append(dict(cache=str(cache),cache_sha256=sha(cache),source=str(source),source_sha256=sha(source),**state))
 result=audit_one(trace.read_text(),policy,out,bootstrap);result.update(stage=str(status.relative_to(O/'setup')),exit_code=run['exit_code'],trace=str(trace),policy=str(policy_path),bootstrap_allowlist=list(map(str,bootstrap)))
 result['verified_bootstrap_bytecode']=bytecode
 results.append(result)
 print(key,result['passed'],'forbidden',result['forbidden_successes'][:12],'unparsed',len(result['unparsed_open_lines']),'bootstrap_precedes_policy',result['bootstrap_precedes_policy'])
summary=dict(passed=bool(results) and all(r['passed'] for r in results),trace_count=len(results),forbidden_successes=sum(len(r['forbidden_successes']) for r in results),unparsed_open_lines=sum(len(r['unparsed_open_lines']) for r in results),failed_execution_attempts=[r['stage'] for r in results if r['exit_code']!=0],stages=results,scope='Native opens, including pre-confinement byte hashing; exact administrative bootstrap reads must precede policy creation. Access validity is separate from process exit status. The archived display failure remains an execution failure; final canonical stage exit codes are checked in VERIFICATION.json.')
write_json(O/(sys.argv[1] if len(sys.argv)>1 else 'ACCESS_AUDIT.json'),summary)
