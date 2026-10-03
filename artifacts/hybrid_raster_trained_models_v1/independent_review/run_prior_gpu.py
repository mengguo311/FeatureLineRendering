#!/usr/bin/env python3
"""Seven inherited synthetic CUDA regressions; no scene assets or old writes."""
import argparse
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest

ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')];sys.dont_write_bytecode=True
from verify_experiment import ART,OUT,PRIOR,sha,require,verify_inheritance,write

GROUPS={
 'native_v2': ['tests.test_hybrid_raster_native.NativeContractTest.'+name for name in (
   'test_01_vertical_export_and_unpatched_calibration',
   'test_02_more_than_four_contributors_keeps_full_moment',
   'test_03_empty_rays_and_dimensions')],
 'legacy_patched':['tests.test_rade_native_f1'],
 'legacy_unpatched':['tests.test_rade_state_calibration'],
}


def setup(group):
    from src import hybrid_raster_native as native
    native.NATIVE=PRIOR/'out/hybrid_raster_evidence_v2/native'
    native.STAGE=OUT/'gpu_regression'/group;native.STAGE.mkdir(parents=True,exist_ok=True)
    if group.startswith('legacy_'):
        variant='patched' if group=='legacy_patched' else 'unpatched'
        sys.path.insert(0,str(native.NATIVE/variant))
    return native


def worker(group):
    verify_inheritance();native=setup(group);guard=native.gpu_guard()
    write(ART/('GPU_GUARD_'+group+'.json'),guard)
    start=time.monotonic();result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(GROUPS[group]))
    report=dict(group=group,passed=result.wasSuccessful(),tests_run=result.testsRun,errors=len(result.errors),failures=len(result.failures),skipped=len(result.skipped),
        seconds=time.monotonic()-start,gpu_guard=guard,tests=GROUPS[group],native_binary_root=str(native.NATIVE),write_root=str(native.STAGE))
    write(ART/('GPU_'+group+'.json'),report);return 0 if result.wasSuccessful() else 1


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--freeze-commit');parser.add_argument('--worker',choices=GROUPS);args=parser.parse_args()
    if args.worker:return worker(args.worker)
    require(args.freeze_commit,'explicit protocol freeze commit required before GPU launch')
    remote=subprocess.check_output(['git','ls-remote','origin','refs/heads/hybrid-raster-trained-models-v1'],cwd=ROOT,text=True).split()[0]
    require(remote==args.freeze_commit,'remote freeze SHA differs')
    for name in ('PROTOCOL.md','INPUTS.json'):
        subprocess.run(['git','cat-file','-e',args.freeze_commit+':artifacts/hybrid_raster_trained_models_v1/'+name],cwd=ROOT,check=True)
    verify_inheritance();cache=OUT/'gpu_regression/cache';(cache/'tmp').mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES='0',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
        CUDA_CACHE_DISABLE='1',XDG_CACHE_HOME=str(cache),TMPDIR=str(cache/'tmp'))
    reports=[]
    for group in GROUPS:
        native=setup(group);guard=native.gpu_guard()
        command=[sys.executable,'-B',str(Path(__file__).resolve()),'--worker',group]
        trace=OUT/'gpu_regression'/f'{group}.strace'
        full=['strace','-f','-q','-yy','-s','4096','-e','trace=open,openat,openat2,creat','-o',str(trace)]+command
        log=ART/'logs'/f'GPU_{group}.log'
        with log.open('x') as stream:process=subprocess.run(full,cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT)
        report=read_report= json.loads((ART/('GPU_'+group+'.json')).read_text()) if (ART/('GPU_'+group+'.json')).exists() else {'passed':False,'tests_run':0}
        reports.append(dict(**report,command=full,exit_code=process.returncode,log=str(log),log_sha256=sha(log),trace=str(trace),trace_sha256=sha(trace),parent_guard=guard))
        if process.returncode:break
    result=dict(passed=len(reports)==3 and all(r['passed'] and r['exit_code']==0 for r in reports),tests_run=sum(r['tests_run'] for r in reports),groups=reports,
        freeze_commit=args.freeze_commit,verified_remote_sha=remote,qualification='Seven unchanged inherited synthetic GPU regressions only; no new-scene output or calibration evidence')
    write(ART/'PRIOR_GPU_TESTS.json',result);print(json.dumps(result));return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
