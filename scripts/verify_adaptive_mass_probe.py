#!/usr/bin/env python3
"""Recompute CSR semantics, decode outputs and audit isolated adaptive runs."""
import hashlib,json,sys
from pathlib import Path
import numpy as np
import cv2
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.adaptive_mass import csr_metrics


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def verify_npz(path,tau,kmax):
    with np.load(path,allow_pickle=False) as f:data={k:f[k] for k in f.files}
    e={k:data[k] for k in ['offsets','ids','stream_position','z','alpha','T','w','rgb','tail_rgb','tail_alpha','final_T','native_final_T','count']}
    state=dict(depths=data['native_depths'],point_list=data['native_point_list'],ranges=data['native_ranges'],stock_rgb=data['stock_white'],wrapper_rgb=data['stock_white'])
    m,d=csr_metrics(e,state,data['stock_black'],tau,kmax)
    # Coverage failure is a valid negative result, not corrupted arrays.
    checks={k:v for k,v in m['checks'].items() if k!='coverage'}
    for k in d:
        if k in data:checks['saved_'+k]=bool(np.allclose(d[k],data[k],rtol=0,atol=2e-6))
    checks['K']=data['camera_K'].shape==(3,3) and np.array_equal(data['camera_K'][2],[0,0,1])
    checks['w2c']=data['w2c'].shape==(4,4)
    arrays={k:dict(shape=list(v.shape),dtype=str(v.dtype),sha256=hashlib.sha256(np.ascontiguousarray(v).tobytes()).hexdigest()) for k,v in data.items()}
    checks['finite']=all(np.isfinite(v).all() for v in data.values())
    return dict(passed=all(checks.values()),checks=checks,arrays=arrays,coverage=m['coverage'])


def compare_outputs(first,second):
    inventory=lambda d:{p.name:p for p in d.iterdir() if p.suffix in ['.png','.npz','.json'] and p.name!='allowlist.json'}
    a,b=inventory(first),inventory(second);checks={'inventory':bool(a) and set(a)==set(b)};hashes={};decoded=0
    for label,inv in [('run',a),('rerun',b)]:
        hashes[label]={}
        for name,path in inv.items():
            hashes[label][name]=sha(path)
            if path.suffix=='.png':
                im=cv2.imread(str(path));checks[label+':'+name+':decode']=im is not None;decoded+=int(im is not None)
            if path.suffix=='.json':
                try:json.loads(path.read_text());checks[label+':'+name+':json']=True
                except ValueError:checks[label+':'+name+':json']=False
    for name in set(a)&set(b):checks[name+':bytes']=hashes['run'][name]==hashes['rerun'][name]
    return dict(passed=all(checks.values()),checks=checks,hashes=hashes,decoded_pngs=decoded)


def main():
    import argparse
    from src.corrected_audit import audit_policy,bootstrap_reads_before_policy,verified_source_exception
    from scripts.render_topk_layered_probe import frozen_inputs
    from scripts.render_adaptive_mass_probe import gate_summary
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT/'out/adaptive_mass_layered_probe')
    args=parser.parse_args();root=args.root.resolve();art=ROOT/'artifacts/adaptive_mass_layered_probe'
    cfg=frozen_inputs(art);comparison=compare_outputs(root/'run',root/'rerun');semantics={};audits={}
    bootstrap=json.loads((art/'BOOTSTRAP_READS.json').read_text())
    exceptions=bootstrap['directories']+[verified_source_exception(p,h) for p,h in bootstrap['sources'].items()]
    for name in ['run','rerun']:
        out=root/name;policy=json.loads((out/'allowlist.json').read_text());trace=(root/'setup'/f'{name}.strace').read_text()
        audit=audit_policy(trace,policy,out,policy['bootstrap_files']+exceptions)
        audit['bootstrap_before_policy']=bootstrap_reads_before_policy(trace,out/'allowlist.json',exceptions+policy['bootstrap_files'])
        audit['source_unchanged']=all(sha(p)==h for key in ['source_hashes','upstream_source_hashes'] for p,h in policy[key].items())
        audit['passed'] &= audit['bootstrap_before_policy'] and audit['source_unchanged']
        audit['trace_sha256']=sha(root/'setup'/f'{name}.strace');audits[name]=audit
        for scene in ['lego','chair','drums','ficus']:
            for t in [90,95]:
                for k in [32,64,128]:
                    stem=f'{scene}_{t}_{k}'
                    semantics[f'{name}:{stem}']=verify_npz(out/(stem+'.npz'),t/100,k)
                    metrics=json.loads((out/(stem+'.json')).read_text())
                    semantics[f'{name}:{stem}']['metrics_equal']=metrics['coverage']==semantics[f'{name}:{stem}']['coverage']
                    semantics[f'{name}:{stem}']['passed'] &= semantics[f'{name}:{stem}']['metrics_equal']
                    print('verified',name,stem,semantics[f'{name}:{stem}']['passed'],flush=True)
    up=ROOT/'out/multiscene_foundation/vendor/gaussian-splatting'
    suite_policy=dict(readonly=[str(p) for p in [ROOT/'out/topk_layered_probe/setup/topk_native.so',ROOT/'src',ROOT/'scripts',ROOT/'tests',Path(sys.prefix),Path('/usr'),Path('/lib'),Path('/lib64'),Path('/etc'),Path('/proc'),Path('/sys'),Path('/home/u00134/bin/miniconda3/envs/ts_diffusion/lib'),ROOT/'out/vrss/vendor/official_site',*[up/k for k in ['gaussian_renderer','scene','utils','arguments','.git']],Path('/home/u00134/.cache/matplotlib/fontlist-v390.json'),Path('/home/u00134/.gitconfig'),ROOT/'out/multiscene_foundation/config.json',ROOT/'out/point_feature_foundation/setup/composite.so',ROOT/'out/multiscene_foundation/setup/layers.so',*[ROOT/'out/multiscene_foundation_corrected/setup'/k for k in ['area_layers.so','fast_query.so','surface.so']],*[ROOT/'out/density_ridge_lines'/f'{s}_ridge_grids.npz' for s in ['lego','chair','drums','ficus']]]],writable=['/tmp','/dev'])
    for trace_path in sorted((root/'setup').glob('full_suite*.strace')):
        audit=audit_policy(trace_path.read_text(),suite_policy,root/'setup',[str(ROOT),str(up)])
        audit['trace_sha256']=sha(trace_path);audits[trace_path.stem]=audit
    preserved=json.loads((art/'PRESERVED_FIXED_K.json').read_text())
    fixed_checks={p:sha(p)==h for p,h in preserved.items()}
    base=json.loads((art/'BASE_TRACKED.json').read_text());base_checks={p:sha(ROOT/p)==h for p,h in base.items()}
    journal=sorted([json.loads(line) for line in (art/'TDD.jsonl').read_text().splitlines()],key=lambda r:r['sequence'])
    journal_checks={r['output']:sha(ROOT/r['output'])==r['output_sha256'] and hashlib.sha256(json.dumps(r['command']).encode()).hexdigest()==r['command_sha256'] for r in journal}
    pairs={}
    for r in journal:
        if r['phase'] in ['RED','GREEN']:pairs.setdefault(r['label'],[]).append(r)
    tdd={}
    for label,records in pairs.items():
        # Retain an initial fixture syntax error in the journal; only the corrected
        # behavioral RED immediately before GREEN counts as prerequisite evidence.
        red=next(r for r in reversed(records) if r['phase']=='RED' and 'IndentationError' not in (ROOT/r['output']).read_text() and 'SyntaxError' not in (ROOT/r['output']).read_text())
        green=records[-1]
        log=(ROOT/red['output']).read_text()
        tdd[label]=red['phase']=='RED' and red['exit_code']!=0 and 'SyntaxError' not in log and 'IndentationError' not in log and green['phase']=='GREEN' and green['exit_code']==0 and red['finished_utc']<=green['started_utc']
    expected={'GATES.json'}|{f'{s}_{t}_{k}.{ext}' for s in cfg['scenes'] for t in [90,95] for k in [32,64,128] for ext in ['json','npz']}|{f'{s}_{kind}.png' for s in cfg['scenes'] for kind in ['coverage','diagnostics']}
    arrays_equal=all(semantics[f'run:{s}_{t}_{k}']['arrays']==semantics[f'rerun:{s}_{t}_{k}']['arrays'] for s in cfg['scenes'] for t in [90,95] for k in [32,64,128])
    access=dict(passed=all(r['passed'] for r in audits.values()),forbidden_successes=sum(len(r['forbidden_successes']) for r in audits.values()),unparsed_open_lines=sum(len(r['unparsed_open_lines']) for r in audits.values()),stages=audits,scope='Native-open traces of production run/rerun and full suite; Landlock before production asset decoding. TEST scientific data and photographs excluded.')
    gates=json.loads((root/'run/GATES.json').read_text())
    reconstructed=gate_summary({s:{f'{t}_{k}':json.loads((root/'run'/f'{s}_{t}_{k}.json').read_text()) for t in [90,95] for k in [32,64,128]} for s in cfg['scenes']})
    checks=dict(deterministic=comparison['passed'],array_hashes=arrays_equal,npz_semantics=all(r['passed'] for r in semantics.values()),access=access['passed'],prior_fixed_k_preserved=all(fixed_checks.values()),all_base_tracked_preserved=all(base_checks.values()),journal_integrity=all(journal_checks.values()),vertical_tdd=all(tdd.values()),expected_inventory=set(comparison['hashes']['run'])==expected,gate_recomputed=gates==reconstructed)
    result=dict(passed=all(checks.values()),checks=checks,comparison=comparison,semantics=semantics,preserved=fixed_checks,base=base_checks,tdd=tdd,journal=journal_checks,protocol_sha256=sha(art/'PROTOCOL.md'),video='NOT_APPLICABLE unless G2/G3 reached')
    (art/'ACCESS_AUDIT.json').write_text(json.dumps(access,sort_keys=True,indent=2)+'\n')
    (art/'VERIFICATION.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    gates['execution_audit']='PASS' if access['passed'] else 'INVALID';gates['verification_passed']=result['passed']
    (art/'GATES.json').write_text(json.dumps(gates,sort_keys=True,indent=2)+'\n')
    print(json.dumps(dict(passed=result['passed'],checks=checks,forbidden=access['forbidden_successes']),indent=2))
    sys.exit(0 if result['passed'] else 1)


if __name__=='__main__':main()
