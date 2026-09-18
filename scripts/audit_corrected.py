#!/usr/bin/env python3
"""Check every completed corrected-run native-open trace without broad data exemptions."""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.foundation import freeze_json
from src.corrected_audit import audit_policy,verified_source_exception,stage_record_paths
from src.multiscene_audit import bytecode_status

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--output',type=Path);args=p.parse_args();root=ROOT/'out/multiscene_foundation_corrected';rows=[]
bootstrap=[ROOT,ROOT/'scripts',ROOT/'src',ROOT/'src/__pycache__',root/'config.json',root/'config.json.sha256',root/'PREREG.md']
upstream=ROOT/'out/multiscene_foundation/vendor/gaussian-splatting'
source_inventory=json.loads((ROOT/'out/multiscene_foundation/setup/training_source.json').read_text())
entry=source_inventory['files']['arguments/__init__.py']
expected=entry['sha256'] if isinstance(entry,dict) else entry
bootstrap += [upstream,Path(verified_source_exception(upstream/'arguments/__init__.py',expected))]
for policy_path in sorted(root.rglob('allowlist.json')):
 policy=json.loads(policy_path.read_text());scene=policy['scene'];task=policy.get('task');stage=policy.get('stage')
 if stage:key=f"{scene}_{policy['seed']}_{stage}"
 elif task in ['layers','primary','repeat','cross']:key=f"local_{scene}_{policy['asset']}_{task}"
 else:key=f"evaluation_{scene}_{task}"
 trace,status=stage_record_paths(root,policy_path,key)
 if not status.exists():continue
 if not trace.exists():raise FileNotFoundError(trace)
 extra=bootstrap+[root/f'scenes/{scene}/eligibility.json',root/f'scenes/{scene}/eligibility.json.sha256',root/f'local/{scene}/F/frozen.json',root/f'local/{scene}/F/frozen.json.sha256']
 cache_records=[]
 for cache in (ROOT/'src/__pycache__').glob('*.cpython-39.pyc'):
  source=cache.with_name(cache.name.split('.')[0]+'.py').parent.parent/(cache.name.split('.')[0]+'.py')
  if not source.exists():continue
  record=bytecode_status(cache,source)
  if record['status']!='UNVERIFIED':extra.append(cache);cache_records.append(dict(path=str(cache),source=str(source),**record))
 result=audit_policy(trace.read_text(),policy,policy_path.parent,extra)
 for record in cache_records:
  if record['path'] in result['successful_paths'] and record['requires_observed_source_fallback'] and record['source'] not in result['successful_paths']:
   result['forbidden_successes'].append(record['path']);result['passed']=False
 result.update(label=key,trace=str(trace),trace_sha256=sha(trace),policy_path=str(policy_path),policy_sha256=sha(policy_path),execution_status=json.loads(status.read_text()),bytecode_records=[r for r in cache_records if r['path'] in result['successful_paths']])
 rows.append(result)
 print(key,result['passed'],'forbidden',result['forbidden_successes'],'unparsed',len(result['unparsed_open_lines']),flush=True)
 if result['unparsed_open_lines']:print(result['unparsed_open_lines'][:3])
result=dict(passed=all(r['passed'] for r in rows),trace_count=len(rows),forbidden_successes=sum(len(r['forbidden_successes']) for r in rows),unparsed_open_lines=sum(len(r['unparsed_open_lines']) for r in rows),stages=rows,scope='Kernel native-open audit includes startup, with explicit metadata/source-cache exceptions. Landlock precedes asset and photograph access. Evaluation is read-only on method roots; DEV photography only after output freezing. No TEST, mesh, learned-normal/depth cache, or historical scientific array is allowed.')
if args.output:freeze_json(args.output,result)
