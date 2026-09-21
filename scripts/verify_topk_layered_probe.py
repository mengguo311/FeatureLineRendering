#!/usr/bin/env python3
"""Decode and compare complete reached-stage scientific outputs."""
import hashlib
import json
from pathlib import Path
import sys
import cv2
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def compare_runs(first,second):
    inventory=lambda d:{p.name:p for p in d.iterdir() if p.suffix in ['.png','.npz','.json','.mp4'] and p.name!='allowlist.json'}
    a,b=inventory(first),inventory(second);checks={};arrays={};decoded_pngs=0;decoded_frames=0
    checks['same_inventory']=bool(a) and set(a)==set(b)
    for name in sorted(set(a)&set(b)):
        checks[name+':byte_equal']=sha(a[name])==sha(b[name])
        for run,path in [('run',a[name]),('rerun',b[name])]:
            key=run+':'+name
            try:
                if path.suffix=='.png':
                    im=cv2.imread(str(path),cv2.IMREAD_UNCHANGED);checks[key+':decode']=im is not None
                    decoded_pngs+=int(im is not None)
                elif path.suffix=='.npz':
                    with np.load(path,allow_pickle=False) as f:
                        arrays[key]={k:dict(shape=list(f[k].shape),dtype=str(f[k].dtype),sha256=hashlib.sha256(np.ascontiguousarray(f[k]).tobytes()).hexdigest()) for k in f.files}
                        checks[key+':finite']=all(np.isfinite(f[k]).all() for k in f.files)
                elif path.suffix=='.json':json.loads(path.read_text());checks[key+':decode']=True
                elif path.suffix=='.mp4':
                    cap=cv2.VideoCapture(str(path));expected=int(cap.get(cv2.CAP_PROP_FRAME_COUNT));count=0
                    while True:
                        ok,im=cap.read()
                        if not ok:break
                        count+=1
                    cap.release();checks[key+':decode']=count==expected and count>0;decoded_frames+=count
            except (ValueError,OSError,EOFError):checks[key+':decode']=False
    for name in sorted(set(a)&set(b)):
        if name.endswith('.npz'):checks[name+':array_equal']=arrays.get('run:'+name)==arrays.get('rerun:'+name)
    return dict(passed=all(checks.values()),checks=checks,arrays=arrays,decoded_pngs=decoded_pngs,decoded_video_frames=decoded_frames,hashes={run:{k:sha(p) for k,p in inv.items()} for run,inv in [('run',a),('rerun',b)]})


def npz_semantics(path,n):
    with np.load(path,allow_pickle=False) as f:
        ids=f['ids'];valid=ids>=0;w=f['w'];a=f['alpha'];T=f['T'];z=f['z']
        close=lambda x,y:bool(np.allclose(x,y,rtol=0,atol=2e-6))
        checks=dict(finite=all(np.isfinite(f[k]).all() for k in f.files),k16=ids.ndim==3 and ids.shape[-1]==16,
            ids=bool(np.all((ids==-1)|((ids>=0)&(ids<n)))),contiguous=bool(np.all(~valid[...,1:]|valid[...,:-1])),
            padding=all(np.all(f[k][~valid]==0) for k in ['w','alpha','T','z','rgb']),
            depths=bool(np.all(z[valid]>0) and np.all((~valid[...,1:])|(np.diff(z,axis=-1)>=-1e-6*np.maximum(1,np.abs(z[...,:-1]))))),
            unique_ids=all(not np.any((ids[...,i]==ids[...,j])&valid[...,i]&valid[...,j]) for i in range(16) for j in range(i)),
            weight_product=close(w,T*a),incoming_T=close(T[valid],np.concatenate([np.ones_like(a[...,:1]),np.cumprod(1-a[...,:-1],axis=-1)],axis=-1)[valid]),
            alpha_conservation=close(w.sum(-1)+f['tail_alpha']+f['final_T'],1),
            K=f['K'].shape==(3,3) and close(f['K'][2],[0,0,1]),w2c=f['w2c'].shape==(4,4))
        for k in [4,8,16]:
            checks[f'A{k}']=close(f[f'A{k}'],w[...,:k].sum(-1))
            checks[f'missing{k}']=close(f[f'missing{k}'],f['native_alpha']-f[f'A{k}'])
    return dict(passed=all(checks.values()),checks=checks)


def main():
    import argparse
    from src.corrected_audit import audit_policy,bootstrap_reads_before_policy,verified_source_exception
    from scripts.render_topk_layered_probe import frozen_inputs
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=ROOT/'out/topk_layered_probe')
    args=parser.parse_args();root=args.root.resolve();art=ROOT/'artifacts/topk_layered_probe'
    cfg=frozen_inputs(art);comparison=compare_runs(root/'run',root/'rerun');semantics={};audits={}
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
            metrics=json.loads((out/f'{scene}_g0.json').read_text())
            semantics[f'{name}:{scene}']=npz_semantics(out/f'{scene}_g0.npz',metrics['gaussian_count'])
    # Existing regression suite accesses explicitly identified historical density
    # fixtures and protocol metadata. They are not scientific inputs to G0.
    up=ROOT/'out/multiscene_foundation/vendor/gaussian-splatting'
    suite_policy=dict(readonly=[str(p) for p in [ROOT/'src',ROOT/'scripts',ROOT/'tests',Path(sys.prefix),Path('/usr'),Path('/lib'),Path('/lib64'),Path('/etc'),Path('/proc'),Path('/sys'),Path('/home/u00134/bin/miniconda3/envs/ts_diffusion/lib'),ROOT/'out/vrss/vendor/official_site',*[up/k for k in ['gaussian_renderer','scene','utils','arguments','.git']],Path('/home/u00134/.cache/matplotlib/fontlist-v390.json'),Path('/home/u00134/.gitconfig'),ROOT/'out/multiscene_foundation/config.json',ROOT/'out/point_feature_foundation/setup/composite.so',ROOT/'out/multiscene_foundation/setup/layers.so',*[ROOT/'out/multiscene_foundation_corrected/setup'/k for k in ['area_layers.so','fast_query.so','surface.so']],*[ROOT/'out/density_ridge_lines'/f'{s}_ridge_grids.npz' for s in ['lego','chair','drums','ficus']]]],writable=['/tmp','/dev'])
    for trace_path in sorted((root/'setup').glob('full_suite*.strace')):
        audit=audit_policy(trace_path.read_text(),suite_policy,root/'setup',[str(ROOT),str(up)])
        audit['trace_sha256']=sha(trace_path);audits[trace_path.stem]=audit
    base=json.loads((art/'BASE_SOURCES.json').read_text())
    source_checks={p:sha(ROOT/p)==h for p,h in base.items()}
    checkpoint_checks={s:sha(v['checkpoint']['path'])==v['checkpoint']['sha256'] for s,v in cfg['scenes'].items()}
    journal=[json.loads(line) for line in (art/'TDD.jsonl').read_text().splitlines()]
    journal_checks={r['output']:sha(ROOT/r['output'])==r['output_sha256'] and hashlib.sha256(json.dumps(r['command']).encode()).hexdigest()==r['command_sha256'] for r in journal}
    pairs={}
    for r in journal:
        if r['phase'] in ['RED','GREEN']:pairs.setdefault(r['label'],[]).append(r)
    tdd_checks={label:[r['phase'] for r in rows]==['RED','GREEN'] and rows[0]['exit_code']!=0 and rows[1]['exit_code']==0 and rows[0]['finished_utc']<=rows[1]['started_utc'] for label,rows in pairs.items()}
    access=dict(passed=all(r['passed'] for r in audits.values()),forbidden_successes=sum(len(r['forbidden_successes']) for r in audits.values()),unparsed_open_lines=sum(len(r['unparsed_open_lines']) for r in audits.values()),stages=audits,scope='All real-scene production workers kernel confined before asset decode; strace includes startup and native calls. Complete regression suites traced separately; temporary synthetic TEST-named fixtures and old density fixtures are not sealed TEST data. No TEST photography or TEST scientific output is permitted.')
    checks=dict(deterministic=comparison['passed'],npz_semantics=all(r['passed'] for r in semantics.values()),access=access['passed'],base_sources=all(source_checks.values()),checkpoints=all(checkpoint_checks.values()),journal_integrity=all(journal_checks.values()),vertical_tdd=all(tdd_checks.values()),expected_inventory=set(comparison['hashes']['run'])=={'GATES.json'}|{f'{s}_g0.{ext}' for s in ['lego','chair','drums','ficus'] for ext in ['json','npz','png']})
    result=dict(passed=all(checks.values()),checks=checks,comparison=comparison,npz_semantics=semantics,base_sources=source_checks,checkpoints=checkpoint_checks,journal=journal_checks,tdd_pairs=tdd_checks,protocol_sha256=sha(art/'PROTOCOL.md'),video='NOT_APPLICABLE: G0 failure; G2/G3 not reached')
    (art/'ACCESS_AUDIT.json').write_text(json.dumps(access,sort_keys=True,indent=2)+'\n')
    (art/'VERIFICATION.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    gates=json.loads((root/'run/GATES.json').read_text());gates['execution_audit']='PASS' if access['passed'] else 'INVALID';gates['verification_passed']=result['passed']
    (art/'GATES.json').write_text(json.dumps(gates,sort_keys=True,indent=2)+'\n')
    print(json.dumps(dict(passed=result['passed'],checks=checks,access_forbidden=access['forbidden_successes'],unparsed=access['unparsed_open_lines']),indent=2))
    sys.exit(0 if result['passed'] else 1)


if __name__=='__main__':main()
