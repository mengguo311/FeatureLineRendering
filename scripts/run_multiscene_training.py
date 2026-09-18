#!/usr/bin/env python3
"""Run one frozen seed queue in a durable detached worker, without changing recipes."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.foundation import verified_json, freeze_json
from src.multiscene_training import run_job, sha256, utc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--gpu', type=int, choices=[0, 1], required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    cfg = verified_json(root / 'config.json', (root / 'config.json.sha256').read_text().strip())
    jobs = verified_json(root / 'training_jobs.json', (root / 'training_jobs.json.sha256').read_text().strip())
    with (root / 'setup' / f'gpu{args.gpu}.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        statuses = []
        for job in jobs:
            if job['gpu'] != args.gpu:
                continue
            directory = Path(job['directory'])
            env = dict(CUDA_VISIBLE_DEVICES=str(args.gpu), OMP_NUM_THREADS='4',
                OPENBLAS_NUM_THREADS='4', MKL_NUM_THREADS='4', PYTHONDONTWRITEBYTECODE='1',
                CUDA_CACHE_DISABLE='1', CUDA_MODULE_LOADING='EAGER')
            command = ['strace', '-f', '-qq', '-yy', '-s', '4096', '-e',
                'trace=open,openat,openat2,creat', '-o', str(directory/'training.strace'),
                sys.executable, str(ROOT/'scripts/multiscene_train_entry.py'),
                '--spec', str(directory/'entry.json')]
            print(json.dumps(dict(stage='launch',scene=job['scene'],seed=job['seed'],utc=utc())), flush=True)
            code = run_job(command, directory, env, args.gpu, cfg['training'])
            ply = Path(job['output'])/'point_cloud/iteration_30000/point_cloud.ply'
            complete = code == 0 and ply.exists()
            row = dict(scene=job['scene'], seed=job['seed'], exit_code=code, complete=complete)
            if complete:
                row.update(path=str(ply), bytes=ply.stat().st_size, sha256=sha256(ply))
            freeze_json(directory/'completion.json',row)
            statuses.append(row)
            print(json.dumps(row), flush=True)
        freeze_json(root/'setup'/f'worker_gpu{args.gpu}_exit.json',dict(finished_utc=utc(),jobs=statuses))


if __name__ == '__main__':
    main()
