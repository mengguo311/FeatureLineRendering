"""Fail-closed resume verification; read-only science, immutable proof output."""
import ast,json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from scripts.schedule_direct_curve_probe import atomic_json,fit_state,sha
from scripts.verify_direct_curve_probe import compare_science,decode_media,verify_fixed_geometry
from src.corrected_audit import audit_policy,bootstrap_reads_before_policy
ART=Path(__file__).resolve().parent;OUT=ROOT/'out/direct_curve_global_fit_probe'

def audit(trace,policy_path):
 policy=json.loads(policy_path.read_text());text=trace.read_text();original=Path(policy['writable'][0]);exc=[str(ROOT),str(ROOT/'tests')]
 result=audit_policy(text,policy,original,exc);result['bootstrap_before_policy']=bootstrap_reads_before_policy(text,original/'allowlist.json',exc)
 result['passed'] &= result['bootstrap_before_policy'];result['trace_sha256']=sha(trace)
 return result

def main():
 import argparse
 ap=argparse.ArgumentParser();ap.add_argument('--session',default='resume_20260929_v2');ap.add_argument('--output',required=True);args=ap.parse_args()
 target=Path(args.output);target.mkdir(parents=True,exist_ok=False)
 checks={};details={};comparison={};geometry={};media={};access={};budgets={}
 frozen=json.loads((ART/'FREEZE.json').read_text());cfg=json.loads((ART/'INPUTS.json').read_text())
 checks['protocol']=sha(ART/'PROTOCOL.md')==frozen['protocol_sha256'];checks['inputs']=sha(ART/'INPUTS.json')==frozen['inputs_sha256']
 manifest=json.loads((ART/'RESUME_IMPLEMENTATION_V2.json').read_text())
 checks['sources']=all(sha(ROOT/p)==h for p,h in manifest['files'].items())
 saved=OUT/'engineering/resume_20260929';preserved=json.loads((saved/'PRESERVATION.json').read_text())
 protected={p:sha(ROOT/p)==h for p,h in preserved.items() if '/lego/fit/' in p or p.endswith(('PROTOCOL.md','INPUTS.json'))}
 checks['sealed_lego_and_frozen_preserved']=bool(protected) and all(protected.values());details['preservation']=protected
 interrupted=json.loads((ART/'INTERRUPTED_ATTEMPTS_PRESERVATION.json').read_text())
 checks['interrupted_attempts_preserved']=all(sha(ROOT/p)==h for p,h in interrupted['files'].items())
 old=ast.parse((saved/'source/src/direct_curve.py').read_text());new=ast.parse((ROOT/'src/direct_curve.py').read_text())
 old={n.name:ast.dump(n,include_attributes=False) for n in old.body if isinstance(n,ast.FunctionDef)};new={n.name:ast.dump(n,include_attributes=False) for n in new.body if isinstance(n,ast.FunctionDef)}
 changes=[k for k in old if old[k]!=new.get(k)];checks['fit_objective_unchanged']=changes==['native_quantiles'];details['changed_functions']=changes
 suite=json.loads((ART/'SUITE_ACCESS_AUDIT_RESUME_226.json').read_text());checks['suite_access']=suite['passed']
 journal=[json.loads(x) for x in (ART/'JOURNAL.jsonl').read_text().splitlines()]
 checks['complete_226_tests']=any(r['label']=='RESUME_COMPLETE_SUITE_226' and r['exit']==0 and sha(r['log'])==r['log_sha256'] for r in journal)
 for i in [25,26]:
  red=[r for r in journal if r['label']==f'RED{i}' and r['exit']!=0];green=[r for r in journal if r['label'].startswith(f'GREEN{i}') and r['exit']==0]
  checks[f'regression_{i}']=bool(red and green and min(r['start'] for r in red)<max(r['start'] for r in green))
 for scene in ['lego','chair','drums','ficus']:
  source=cfg['scenes'][scene]
  checks[scene+':checkpoint_hash']=sha(source['checkpoint']['path'])==source['checkpoint']['sha256']
  for index in cfg['F']+cfg['C']:
   camera=source['cameras'][str(index)]
   checks[f'{scene}:input_{index}_hash']=sha(camera['path'])==camera['sha256']
  baseline=json.loads((ART/'RESUME_BUDGET_BASELINE.json').read_text())[scene]
  cost=baseline['charged_seconds'];costs=[]
  for job in (OUT/'scheduler').glob('*/*/jobs/*/START.json'):
   r=json.loads(job.read_text())
   if r['scene']==scene:
    end=job.parent/'END.json'
    checks[str(end.relative_to(OUT))+':closed']=end.exists()
    if end.exists():v=json.loads(end.read_text());cost+=v['seconds'];costs.append(dict(path=str(job.parent),**v))
  budgets[scene]=dict(charged_seconds=cost,conservative_gpu_hours=cost/3600,within_12_hours=cost<=43200,baseline=baseline,stages=costs)
  checks[scene+':budget']=cost<=43200
  first=OUT/'run'/scene;second=OUT/'rerun'/scene
  comparison[scene]=compare_science(first,second);checks[scene+':deterministic']=comparison[scene]['passed']
  for run in ['run','rerun']:
   key=f'{run}:{scene}';base=OUT/run/scene;fit=base/'fit';ev=base/'evaluate';scheduler=OUT/'scheduler'/args.session/run
   checks[key+':fit_sealed']=fit_state(fit)=='sealed'
   try:
    seal=json.loads((fit/'SEAL.json').read_text());result=json.loads((ev/'RESULTS.json').read_text());census=json.loads((ev/'CENSUS.json').read_text())
   except Exception as e:checks[key+':complete']=False;details[key+':error']=repr(e);continue
   checks[key+':complete']=True
   checks[key+':census']=all(len(census[split][arm])==512 and {(row['view'],row['cell']) for row in census[split][arm]}=={(view,cell) for view in cfg[split] for cell in range(64)} for split in ['F','C'] for arm in ['D','I','L'])
   checks[key+':arcs']=len(result['arcs'])==2 and all(a['frames']==33 for a in result['arcs'])
   checks[key+':calibration_gate']=all(max(json.loads(p.read_text())['calibration'].values())<=1/255 for folder in [fit/'native',ev/'native'] for p in folder.glob('*.json'))
   calibration=json.loads((scheduler/'calibration'/f'{scene}_all/RESULT.json').read_text());checks[key+':exhaustive_replay']=calibration['passed'] and calibration['frames']==82
   for stem in seal['assets']:
    history=json.loads((fit/(stem+'.json')).read_text())
    checks[key+':'+stem+':budget']=len(history['history'])==300 and history['seconds']<=1800
    with np.load(fit/(stem+'.npz')) as f:checks[key+':'+stem+':finite']=f['control'].shape==(128,4,3) and np.isfinite(f['control']).all() and np.isfinite(f['gate']).all()
   for arm,stem in seal['chosen'].items():
    with np.load(fit/(stem+'.npz')) as f:control=f['control'];active=f['active']
    rows=[];valid=True
    for p in sorted((ev/'arrays').glob('*_'+arm+'.npz')):
     with np.load(p) as f:rows.append(f['xyz']);valid &= set(f['visible_ids']).issubset(set(np.flatnonzero(active)))
    good=verify_fixed_geometry(control,rows) and len(rows)==82 and valid
    geometry[key+':'+arm]=dict(passed=bool(good),frames=len(rows));checks[key+':'+arm+':fixed_geometry']=bool(good)
   media[key]=decode_media(ev,33);checks[key+':media']=media[key]['passed'] and len(media[key]['videos'])==2 and len(media[key]['pngs'])>=16+66
   import cv2
   for name,record in media[key]['videos'].items():
    cap=cv2.VideoCapture(str(ev/name));record['fps']=cap.get(cv2.CAP_PROP_FPS);cap.release()
    checks[key+':'+name+':format']=record['fps']==12 and record['shape']==[828,4000,3]
   for kind in ['fit','evaluate']:
    path=base/kind/'allowlist.json'
    trace=OUT/'setup'/f'final_{run}_lego_fit.strace' if scene=='lego' and kind=='fit' else scheduler/'jobs'/f'{scene}_{kind}/access.strace'
    access[key+':'+kind]=audit(trace,path);checks[key+':'+kind+':access']=access[key+':'+kind]['passed']
    policy=json.loads(path.read_text());legacy=scene=='lego' and kind=='fit'
    executed=json.loads((saved/'source/artifacts/direct_curve_global_fit_probe/IMPLEMENTATION_V2.json').read_text()) if legacy else manifest['files']
    source_keys=['src/direct_curve.py','src/direct_curve_quantiles.cpp','scripts/run_direct_curve_probe.py']
    if not legacy:source_keys+=['src/direct_curve_quantiles.cu','scripts/evaluate_direct_curve_probe.py','src/direct_curve_eval.py']
    checks[key+':'+kind+':source_provenance']=all(policy['source_hashes'][str(ROOT/p)]==executed[p] for p in source_keys)
   for p in (scheduler/'jobs').glob(f'{scene}_*/AUDIT.json'):
    a=json.loads(p.read_text());checks[str(p.relative_to(OUT))]=a['passed']
   stage_seal=json.loads((scheduler/f'{scene}_evaluate_SEAL.json').read_text());checks[key+':atomic_evaluation_seal']=all(sha(ev/p)==h for p,h in stage_seal['files'].items())
 # Original failed evaluation attempts remain independently auditable.
 for run in ['run','rerun']:
  p=OUT/'engineering'/args.session/run/'lego/evaluate_previous/allowlist.json'
  access[run+':lego:archived_evaluation']=audit(OUT/'setup'/f'final_{run}_lego_evaluate.strace',p)
  checks[run+':lego:archived_evaluation_access']=access[run+':lego:archived_evaluation']['passed']
  record=json.loads((p.parent.parent/'EVALUATION_ARCHIVE.json').read_text());checks[run+':lego:archived_evaluation_preserved']=all(sha(p.parent/k)==h for k,h in record['files'].items())
 checks={k:bool(v) for k,v in checks.items()}
 for name,value in [('COMPARISON',comparison),('GEOMETRY',geometry),('MEDIA',media),('ACCESS',access),('BUDGETS',budgets),('DETAILS',details)]:atomic_json(target/(name+'.json'),value)
 verdict=dict(passed=all(checks.values()),checks=checks,failed=[k for k,v in checks.items() if not v],session=args.session)
 atomic_json(target/'VERIFICATION.json',verdict);print(json.dumps(verdict,indent=2));return 0 if verdict['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
