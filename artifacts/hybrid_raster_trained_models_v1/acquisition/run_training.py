#!/usr/bin/env python3
"""One scene, device-exclusive guard, full strace, hard timeout, atomic lineage."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from acquisition_support import atomic_json,audit_trace,canonical_hash,check_resume,gpu_guard,sha256,utc,validate_checkpoint_sidecar


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--manifest',type=Path,required=True);parser.add_argument('--gpu',type=int,choices=[0,1],required=True)
    parser.add_argument('--freeze-commit',required=True);parser.add_argument('--resume',type=Path)
    args=parser.parse_args();manifest=json.loads(args.manifest.read_text());directory=Path(manifest['directory']);directory.mkdir(parents=True,exist_ok=True)
    repo=Path(__file__).resolve().parents[3];runroot=repo/'out/hybrid_raster_trained_models_v1'
    relative=str(args.manifest.resolve().relative_to(repo))
    frozen=subprocess.check_output(['git','show',args.freeze_commit+':'+relative],cwd=repo)
    if json.loads(frozen)!=manifest: raise RuntimeError('manifest does not equal committed freeze')
    subprocess.run(['git','merge-base','--is-ancestor',args.freeze_commit,'HEAD'],cwd=repo,check=True)
    remote=subprocess.check_output(['git','ls-remote','origin','refs/heads/hybrid-raster-trained-models-v1'],cwd=repo,text=True).split()[0]
    if remote!=args.freeze_commit: raise RuntimeError('remote freeze SHA differs at launch')
    if args.resume:
        sidecar=json.loads(args.resume.with_suffix('.json').read_text());check_resume(manifest,sidecar);validate_checkpoint_sidecar(args.resume,sidecar)
    elif (directory/'launch_claim.json').exists(): raise RuntimeError('refusing second fresh acquisition')
    previous_seconds=0.0
    for previous in sorted(directory.glob('attempt_*')):
        if not (previous/'EXIT.json').exists(): raise RuntimeError('unresolved previous attempt; no budget-safe automatic resume')
        previous_seconds+=float(json.loads((previous/'EXIT.json').read_text())['wall_seconds'])
    remaining_seconds=manifest['timeout_seconds']-previous_seconds
    if remaining_seconds<=0: raise RuntimeError('aggregate per-scene training budget exhausted')
    lock=(runroot/f'training/gpu{args.gpu}.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    guard=gpu_guard(args.gpu,runroot)
    attempt=directory/f'attempt_{len(list(directory.glob("attempt_*"))):03d}';attempt.mkdir()
    atomic_json(attempt/'GPU_GUARD.json',guard)
    command=['strace','-f','-q','-yy','-s','4096','-e','trace=open,openat,openat2,creat','-o',str(attempt/'training.strace'),
             manifest['python'],str(Path(__file__).parent/'train_entry.py'),'--manifest',str(args.manifest.resolve())]
    if args.resume: command.extend(['--resume',str(args.resume.resolve())])
    started=utc();started_clock=time.monotonic()
    claim=dict(utc=started,worker_pid=os.getpid(),gpu=args.gpu,command=command,manifest_sha256=canonical_hash(manifest),freeze_commit=args.freeze_commit,verified_remote_sha=remote,resume=str(args.resume) if args.resume else None)
    atomic_json(attempt/'LAUNCH.json',claim)
    if not args.resume:
        with (directory/'launch_claim.json').open('x') as f: json.dump(claim,f,indent=2)
    cache=directory/'cache';cache.mkdir(exist_ok=True);(cache/'tmp').mkdir(exist_ok=True)
    env=dict(os.environ,CUDA_VISIBLE_DEVICES=str(args.gpu),OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',MKL_NUM_THREADS='4',PYTHONDONTWRITEBYTECODE='1',
             CUDA_CACHE_DISABLE='1',CUDA_MODULE_LOADING='EAGER',XDG_CACHE_HOME=str(cache),TMPDIR=str(cache/'tmp'))
    atomic_json(directory/'STATUS.json',dict(state='STARTING',scene=manifest['scene'],utc=started,manifest_sha256=canonical_hash(manifest),attempt=str(attempt)))
    timed_out=False
    with (attempt/'train.log').open('x') as log, (attempt/'resources.jsonl').open('x') as resources:
        process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,env=env,cwd=directory,start_new_session=True)
        while process.poll() is None:
            elapsed=time.monotonic()-started_clock
            if elapsed>remaining_seconds:
                timed_out=True;os.killpg(process.pid,signal.SIGTERM)
                try: process.wait(timeout=20)
                except subprocess.TimeoutExpired: os.killpg(process.pid,signal.SIGKILL);process.wait()
                break
            sample=dict(utc=utc(),elapsed_seconds=elapsed,pid=process.pid,gpu=args.gpu,
                        nvidia_smi=subprocess.check_output(['nvidia-smi',f'--id={args.gpu}','--query-gpu=memory.used,memory.free,utilization.gpu,temperature.gpu','--format=csv,noheader,nounits'],text=True).strip())
            resources.write(json.dumps(sample)+'\n');resources.flush();time.sleep(10)
        code=process.returncode
    audit=audit_trace(attempt/'training.strace',manifest['original_data']);atomic_json(attempt/'ACCESS_AUDIT.json',audit)
    checkpoints={}
    for iteration in [7000,30000]:
        ply=Path(manifest['output'])/'point_cloud'/f'iteration_{iteration}'/'point_cloud.ply'
        snapshot=Path(manifest['output'])/f'chkpnt{iteration}.pth'
        if ply.exists() and snapshot.exists() and snapshot.with_suffix('.json').exists():
            sidecar=json.loads(snapshot.with_suffix('.json').read_text())
            check_resume(manifest,sidecar);validate_checkpoint_sidecar(snapshot,sidecar)
            if int(sidecar['iteration'])!=iteration: raise RuntimeError('snapshot sidecar iteration mismatch')
            checkpoints[str(iteration)]=dict(iteration=iteration,path=str(ply),sha256=sha256(ply),bytes=ply.stat().st_size,
                snapshot=str(snapshot),snapshot_sha256=sha256(snapshot),snapshot_sidecar=str(snapshot.with_suffix('.json')))
    complete=code==0 and not timed_out and audit['passed'] and len(checkpoints)==2
    status=dict(state='COMPLETE' if complete else 'FAILED',scene=manifest['scene'],seed=1729,iteration=30000 if complete else None,
                started_utc=started,finished_utc=utc(),wall_seconds=time.monotonic()-started_clock,prior_attempt_seconds=previous_seconds,aggregate_seconds=previous_seconds+time.monotonic()-started_clock,exit_code=code,timed_out=timed_out,
                manifest_sha256=canonical_hash(manifest),attempt=str(attempt),audit_passed=audit['passed'],checkpoints=checkpoints)
    atomic_json(attempt/'EXIT.json',status);atomic_json(directory/'STATUS.json',status)
    if complete:
        atomic_json(directory/'CHECKPOINT_LOCK.json',dict(schema=1,scene=manifest['scene'],seed=1729,iterations=30000,state='COMPLETE',
            frozen_utc=utc(),manifest_sha256=canonical_hash(manifest),manifest_path=str(args.manifest.resolve()),freeze_commit=args.freeze_commit,
            source_commit=manifest['source_commit'],source_manifest_sha256=manifest['source_manifest_sha256'],checkpoints=checkpoints,
            training_access='all100 TRAIN cameras including NPR C; in-sample, not blind evaluation',audit=str(attempt/'ACCESS_AUDIT.json')))
    return 0 if complete else 1

if __name__=='__main__': sys.exit(main())
