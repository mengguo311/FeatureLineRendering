#!/usr/bin/env python3
"""Read-only post-run audit and deterministic replay comparison."""
import sys,json,re,ast
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from src.temporal_depth2d import sha,atomic_json,verify_seal
from scripts.run_temporal_depth2d_probe import science_metadata
ART=ROOT/'artifacts/temporal_depth2d_video_probe'


def trace_audit(path,manifest):
    allow={r['path'] for s in manifest['scenes'].values() for r in s['files']}
    pending={};failed=0;success=0;signals=0;science=[];forbidden=[];writes=[];unparsed=[]
    for raw in path.read_text().splitlines():
        match=re.match(r'^\s*(\d+)\s+(.*)$',raw)
        if not match:unparsed.append(raw);continue
        pid,line=match.groups()
        if line.startswith('--- SIG') and line.endswith('---'):
            signals+=1;continue
        if '<unfinished ...>' in line:pending[pid]=line.split('<unfinished ...>')[0];continue
        if line.startswith('<...') and 'resumed>' in line:
            old=pending.pop(pid,None)
            if old is None:unparsed.append(raw);continue
            line=old+line.split('resumed>',1)[1].lstrip()
        result=re.search(r'\)\s+=\s+(-?\d+)',line)
        if not result:unparsed.append(raw);continue
        if int(result.group(1))<0:failed+=1;continue
        paths=re.findall(r'"((?:[^"\\]|\\.)*)"',line)
        if not paths:unparsed.append(raw);continue
        success+=1
        mutation=not line.startswith(('open(', 'openat(')) or any(k in line for k in ['O_WRONLY','O_RDWR','O_CREAT','O_TRUNC'])
        for rawpath in paths[:2 if mutation and line.startswith('rename') else 1]:
            p=Path(ast.literal_eval('"'+rawpath+'"'));p=p if p.is_absolute() else ROOT/p
            p=p.resolve()
            if p.is_relative_to(Path('/home/u00134/3dgs_line')) and not p.is_relative_to(ROOT):
                science.append(str(p))
                if str(p) not in allow or mutation:forbidden.append({'path':str(p),'syscall':line})
            if mutation and not p.is_relative_to(ROOT) and str(p)!='/dev/null':writes.append({'path':str(p),'syscall':line})
    unparsed += [f'unfinished pid{p}: {s}' for p,s in pending.items()]
    return {'ignored_signal_records':signals,'successful_file_syscalls':success,'failed_file_syscalls':failed,'scientific_unique_paths':sorted(set(science)),
            'forbidden_successful_access':forbidden,'writes_outside_worktree':writes,'unparsed':unparsed,
            'pass':not(forbidden or writes or unparsed),'strace_sha256':sha(path)}


def rerun_compare(run,rerun):
    rows=[]
    for scene in ['F_construction','C_reserved','lego_arc0']:
        a=run/scene;b=rerun/scene
        for p in sorted(a.rglob('*')):
            if p.suffix not in ['.png','.npz','.mp4']:continue
            q=b/p.relative_to(a)
            same=q.exists() and sha(p)==sha(q)
            if p.suffix=='.npz' and q.exists():
                with np.load(p) as x,np.load(q) as y:same=x.files==y.files and all(np.array_equal(x[k],y[k]) for k in x.files)
            rows.append({'path':str(p.relative_to(run)),'identical':bool(same)})
    metrics_a=json.loads((run/'lego_arc0/RESULTS.json').read_text());metrics_b=json.loads((rerun/'lego_arc0/RESULTS.json').read_text())
    metrics_a.pop('elapsed_seconds');metrics_b.pop('elapsed_seconds')
    return {'assets':rows,'identical_assets':sum(r['identical'] for r in rows),'total_assets':len(rows),
            'metrics_identical':metrics_a==metrics_b,'pass':all(r['identical'] for r in rows) and metrics_a==metrics_b}


def main():
    run=ROOT/'out/temporal_depth2d_video_probe/run';manifest=json.loads((ART/'INPUTS.json').read_text());meta=science_metadata()
    units=[]
    for p in run.iterdir():
        if p.is_dir() and (p/'SEAL.json').exists():verify_seal(p,meta);units.append(p.name)
    sources=all(sha(r['path'])==r['sha256'] for s in manifest['scenes'].values() for r in s['files'])
    audit=trace_audit(run.parent/'run.strace',manifest)
    audit.update(sealed_units=sorted(units),sources_unchanged=sources)
    atomic_json(ART/'AUDIT.json',audit)
    rerun=run.parent/'rerun'
    if (rerun/'STATE.json').exists() and json.loads((rerun/'STATE.json').read_text())['status']=='COMPLETE':
        atomic_json(ART/'RERUN.json',rerun_compare(run,rerun))
        atomic_json(ART/'RERUN_ACCESS_AUDIT.json',trace_audit(run.parent/'rerun.strace',manifest))
    print(json.dumps({k:v for k,v in audit.items() if k not in ['scientific_unique_paths']},indent=2))

if __name__=='__main__':main()
