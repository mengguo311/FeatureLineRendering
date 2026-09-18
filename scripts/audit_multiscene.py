#!/usr/bin/env python3
"""Audit completed native traces, retaining explicit startup exceptions."""
import argparse,json,marshal,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.foundation import freeze_json
from src.multiscene_training import sha256,utc
from src.multiscene_audit import audit_stage,bytecode_status

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--training-only',action='store_true')
parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
root=ROOT/'out/multiscene_foundation'
bootstrap=[ROOT,ROOT/'scripts',ROOT/'src',ROOT/'src/__pycache__']
boot_records=[]
for name in ['__init__','foundation','common','multiscene','multiscene_training','multiscene_qualification','multiscene_diagnostic']:
 p=ROOT/'src'/f'{name}.py';bootstrap.append(p)
 for cache in (ROOT/'src/__pycache__').glob(name+'.'+sys.implementation.cache_tag+'.pyc'):
  status=bytecode_status(cache,p)
  if status['status']=='UNVERIFIED':raise RuntimeError('unverified bootstrap bytecode: '+str(cache))
  bootstrap.append(cache);boot_records.append(dict(path=str(cache),sha256=sha256(cache),source=str(p),**status))
for p in ['config.json','config.json.sha256']:bootstrap.append(root/p)
rows=[]
def check(trace,files,roots,output,label,extra=()):
 a=audit_stage(trace.read_text(),files,roots,str(output),[*map(str,bootstrap),*map(str,extra)])
 for record in boot_records:
  if record['path'] in a['successful_paths'] and record['requires_observed_source_fallback']:
   if record['source'] not in a['successful_paths']:
    a['forbidden_successes'].append(record['path']);a['passed']=False
 a.update(label=label,trace=str(trace),trace_sha256=sha256(trace));rows.append(a)
 print(label,'passed',a['passed'],'forbidden',len(a['forbidden_successes']),'unparsed',len(a['unparsed_open_lines']),flush=True)
 if not a['passed']:print(a['forbidden_successes'],a['unparsed_open_lines'][:5],flush=True)
for d in sorted((root/'training').glob('*/*')):
 if not d.is_dir():continue
 spec=json.loads((d/'entry.json').read_text());data=spec['data']
 runtime=[sys.prefix,'/usr','/etc','/proc','/sys','/dev',spec['source'],*spec['site'],data]
 extra=[ROOT/'scripts/multiscene_train_entry.py',d/'entry.json']
 if not (d/'completion.json').exists():raise RuntimeError('unfinished training: '+str(d))
 check(d/'training.strace',[str(d/'entry.json')],runtime,Path(spec['output']),f'training/{d.parent.name}/{d.name}',extra)
 attempt=d/'attempt_00_runtime_init/training.strace'
 if attempt.exists():check(attempt,[str(d/'entry.json')],runtime,Path(spec['output']),f'pretraining_failure/{d.parent.name}/{d.name}',extra)
if not args.training_only:
 for status in sorted((root/'setup/routes').glob('*_exit.json')):
  s=json.loads(status.read_text());scene,seed,stage=s['scene'],s['seed'],s['stage']
  d=root/'training'/scene/f'seed_{seed}'
  output=d/'quality' if stage=='quality' else root/'controlled'/scene
  policy=json.loads((output/'allowlist.json').read_text())
  files=[p for p in policy['readonly'] if Path(p).is_file()]
  runtime=[p for p in policy['readonly'] if Path(p).is_dir()]+['/dev']
  extra=[d/'completion.json',d/'completion.json.sha256']
  check(status.with_name(status.name.replace('_exit.json','.strace')),files,runtime,output,f'{stage}/{scene}/{seed}',extra)
 for status in sorted((root/'setup/diagnostic').glob('*_exit.json')):
  s=json.loads(status.read_text());scene,seed=s['scene'],s['seed'];d=root/'training'/scene/f'seed_{seed}'
  output=root/'diagnostics/resolution'/scene/f'seed_{seed}'
  policy=json.loads((output/'allowlist.json').read_text())
  files=[p for p in policy['readonly'] if Path(p).is_file()]
  runtime=[p for p in policy['readonly'] if Path(p).is_dir()]+['/dev']
  extra=[d/'completion.json',d/'completion.json.sha256']
  check(status.with_name(status.name.replace('_exit.json','.strace')),files,runtime,output,f'diagnostic/{scene}/{seed}',extra)
 expected=36
 if len(rows)!=expected:raise RuntimeError(f'Expected {expected} completed traces, got {len(rows)}')
result=dict(created_utc=utc(),passed=all(r['passed'] for r in rows),trace_count=len(rows),
 forbidden_successes=sum(len(r['forbidden_successes']) for r in rows),unparsed_open_lines=sum(len(r['unparsed_open_lines']) for r in rows),
 bootstrap_bytecode=boot_records,stages=rows,
 scope='Native open audit includes runtime startup. Landlock is installed after CUDA initialization, before scene asset/photo reads. Phase0 hashed original train DEV/TEST bytes for provenance without decoding; that administrative hashing is outside these method traces. Original test-split photographs were never opened.')
freeze_json(args.output,result)
