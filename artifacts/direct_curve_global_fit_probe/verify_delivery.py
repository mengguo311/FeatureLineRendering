"""Administrative final audit, composing tested integrity/media/access helpers."""
import json,hashlib,sys,shlex
from pathlib import Path
import numpy as np
ROOT=Path.cwd();sys.path.insert(0,str(ROOT))
from scripts.verify_direct_curve_probe import compare_science,decode_media,verify_fixed_geometry,sha
from src.corrected_audit import audit_policy,bootstrap_reads_before_policy
from src.multiscene_verify import inventory,verify_inventory
art=ROOT/'artifacts/direct_curve_global_fit_probe';out=ROOT/'out/direct_curve_global_fit_probe'
checks={};comparison={};geometry={};media={};access={}
cfg=json.loads((art/'INPUTS.json').read_text());freeze=json.loads((art/'FREEZE.json').read_text())
checks['protocol']=sha(art/'PROTOCOL.md')==freeze['protocol_sha256'];checks['inputs']=sha(art/'INPUTS.json')==freeze['inputs_sha256']
implementation=json.loads((art/'IMPLEMENTATION_V2.json').read_text())
implementation.update(json.loads((art/'EVALUATION_IMPLEMENTATION_V4.json').read_text()))
for p,h in implementation.items():checks['implementation:'+p]=sha(p)==h
suite=json.loads((art/'SUITE_ACCESS_AUDIT.json').read_text())
checks['suite_access']=suite['passed'] and not suite['forbidden_successes'] and not suite['unparsed_open_lines']
for scene,s in cfg['scenes'].items():
    checks[scene+':checkpoint']=sha(s['checkpoint']['path'])==s['checkpoint']['sha256']
    for i,c in s['cameras'].items():checks[scene+':image:'+i]=sha(c['path'])==c['sha256']
    comparison[scene]=compare_science(out/'run'/scene,out/'rerun'/scene)
    checks[scene+':deterministic']=comparison[scene]['passed']
    for run in ['run','rerun']:
        base=out/run/scene;fitdir=base/'fit';ev=base/'evaluate';seal=json.loads((fitdir/'SEAL.json').read_text());result=json.loads((ev/'RESULTS.json').read_text());census=json.loads((ev/'CENSUS.json').read_text())
        checks[f'{run}:{scene}:18_assets']=len(seal['assets'])==18
        checks[f'{run}:{scene}:census']=all(len(census[sp][a])==512 for sp in ['F','C'] for a in ['D','I','L'])
        checks[f'{run}:{scene}:arcs']=len(result['arcs'])==len(s['arcs'])==2 and all(a['frames']==33 for a in result['arcs'])
        checks[f'{run}:{scene}:seal_hash']=sha(fitdir/'SEAL.json')==(fitdir/'SEAL.json.sha256').read_text().split()[0]
        checks[f'{run}:{scene}:assets']=all(sha(fitdir/(k+'.npz'))==h for k,h in seal['assets'].items())
        checks[f'{run}:{scene}:native_calibration']=all(max(json.loads(p.read_text())['calibration'].values())<=1/255 for folder in [fitdir/'native',ev/'native'] for p in folder.glob('*.json'))
        for a,key in seal['chosen'].items():
            with np.load(fitdir/(key+'.npz')) as f:control=f['control'];active=f['active']
            rows=[];valid=True
            for p in sorted((ev/'arrays').glob('*_'+a+'.npz')):
                with np.load(p) as f:
                    rows.append(f['xyz']);valid &= set(f['visible_ids']).issubset(set(np.flatnonzero(active)))
            good=verify_fixed_geometry(control,rows) and len(rows)==82 and valid
            geometry[f'{run}:{scene}:{a}']=dict(passed=bool(good),frames=len(rows),control_sha256=hashlib.sha256(control.tobytes()).hexdigest())
            checks[f'{run}:{scene}:{a}:fixed']=bool(good)
        media[f'{run}:{scene}']=decode_media(ev,33);checks[f'{run}:{scene}:media']=media[f'{run}:{scene}']['passed'] and len(media[f'{run}:{scene}']['videos'])==2
        for stage in ['fit','evaluate']:
            path=base/stage/'allowlist.json';policy=json.loads(path.read_text());trace=out/'setup'/f'{scene}_{"fit_v2" if run=="run" and stage=="fit" else ("eval" if run=="run" else "rerun_"+("fit" if stage=="fit" else "eval"))}.strace'
            source_keys=['src/direct_curve.py','src/direct_curve_quantiles.cpp','scripts/run_direct_curve_probe.py']
            if stage=='evaluate':source_keys+=['src/direct_curve_eval.py','scripts/evaluate_direct_curve_probe.py']
            checks[f'{run}:{scene}:{stage}:executed_source']=all(policy['source_hashes'][str(ROOT/p)]==implementation[p] for p in source_keys)
            text=trace.read_text();exceptions=[str(ROOT),str(ROOT/'tests')]
            audit=audit_policy(text,policy,base/stage,exceptions);audit['bootstrap_before_policy']=bootstrap_reads_before_policy(text,path,exceptions);audit['passed'] &= audit['bootstrap_before_policy'];audit['trace_sha256']=sha(trace)
            access[f'{run}:{scene}:{stage}']=audit;checks[f'{run}:{scene}:{stage}:access']=audit['passed']
# Preserve explicitly excluded attempts; audit their original path names from policy.
for scene in ['lego','chair']:
    p=out/'engineering/attempt_01_depth_scale'/scene/'fit/allowlist.json';policy=json.loads(p.read_text());trace=out/'engineering/attempt_01_source'/f'{scene}_fit.strace';text=trace.read_text();original=Path(policy['writable'][0]);exceptions=[str(ROOT),str(ROOT/'tests')]
    a=audit_policy(text,policy,original,exceptions);a['bootstrap_before_policy']=bootstrap_reads_before_policy(text,original/'allowlist.json',exceptions);a['passed'] &= a['bootstrap_before_policy'];access['excluded:'+scene]=a;checks['excluded:'+scene+':access']=a['passed']
preserved=json.loads((art/'PRESERVATION.json').read_text());preservation={p:sha(p)==h for p,h in preserved['files'].items()};checks['old_files']=all(preservation.values())
# Every RED is an observed failure and has a subsequent successful GREEN.
journal=[json.loads(line) for line in (art/'JOURNAL.jsonl').read_text().splitlines()];tdd={}
for r in journal:checks['log:'+r['label']+str(r['start'])]=sha(r['log'])==r['log_sha256']
checks['complete_suite']=any(r['label']=='COMPLETE_UNTRACED_221' and r['exit']==0 for r in journal)
checks['traced_suite']=any(r['label']=='FULL_SUITE_TRACED_221' and r['exit']==0 for r in journal)
for i in range(1,25):
    reds=[r for r in journal if r['label']==f'RED{i:02d}'];greens=[r for r in journal if r['label'].startswith(f'GREEN{i:02d}') and r['exit']==0]
    tdd[str(i)]=bool(reds and greens and reds[0]['exit']!=0 and reds[0]['start']<greens[-1]['start']);checks['TDD:'+str(i)]=tdd[str(i)]
for name,value in [('COMPARISON.json',comparison),('GEOMETRY_VERIFICATION.json',geometry),('MEDIA_VERIFICATION.json',media),('ACCESS_AUDIT.json',access),('PRESERVATION_VERIFICATION.json',dict(passed=checks['old_files'],files=preservation,excluded=preserved['excluded_test_named']))]:
    (art/name).write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
result=dict(passed=all(checks.values()),checks=checks,tdd=tdd,scope='Independent full optimization/native/evaluation reruns; timing fields excluded from semantic equality, byte hashes retained.')
(art/'VERIFICATION.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
(art/'COMMANDS.md').write_text('# Exact execution journal\n\n'+''.join(f"## {r['label']} — exit {r['exit']}\n\n```sh\n{shlex.join(r['argv'])}\n```\n\nLog: `{r['log']}`; SHA256 `{r['log_sha256']}`; seconds {r['seconds']:.3f}.\n\n" for r in sorted(journal,key=lambda r:r['start'])))
print(json.dumps(dict(passed=result['passed'],failed=[k for k,v in checks.items() if not v]),indent=2));sys.exit(0 if result['passed'] else 1)
