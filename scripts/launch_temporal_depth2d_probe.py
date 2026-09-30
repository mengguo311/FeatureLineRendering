#!/usr/bin/env python3
"""Detach the sealed runner from the coding session; log PID, stdout and syscall trace."""
import argparse
import os
import subprocess
import sys
from pathlib import Path


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default='out/temporal_depth2d_video_probe/run')
    parser.add_argument('--rerun-kill',action='store_true')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1];output=(root/args.output).resolve()
    if not output.is_relative_to(root):raise ValueError('output outside this worktree')
    base=output.parent;base.mkdir(parents=True,exist_ok=True)
    prefix=output.name
    if os.fork():return
    os.setsid()
    if os.fork():os._exit(0)
    with open('/dev/null','rb') as inp,open(base/(prefix+'.log'),'ab',buffering=0) as log:
        for fd in [0,1,2]:os.dup2(inp.fileno() if fd==0 else log.fileno(),fd)
        env=os.environ.copy();env['OPENBLAS_NUM_THREADS']='1';env['OMP_NUM_THREADS']='1'
        cmd=['strace','-f','-qq','-e','trace=open,openat,creat,rename,renameat,unlink,unlinkat,mkdir,mkdirat',
             '-o',str(base/(prefix+'.strace')),sys.executable,'-u',str(root/'scripts/run_temporal_depth2d_probe.py'),
             '--output',str(output)]
        if args.rerun_kill:cmd.append('--rerun-kill')
        proc=subprocess.Popen(cmd,cwd=root,env=env)
        (base/(prefix+'.pid')).write_text(str(proc.pid)+'\n')
        os._exit(0)

if __name__=='__main__':main()
