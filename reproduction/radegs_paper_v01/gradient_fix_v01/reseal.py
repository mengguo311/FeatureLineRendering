"""New audited config generation; old stage2 failure/config/seals stay untouched.

This supersedes, rather than relaxes, assemble_stage2.py's pre-commit HEAD gate.
No CUDA initialization; no launch; run only after private rebuild + CPU tests.
"""
import ast
import difflib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import zipfile

WORK=Path(__file__).resolve().parents[3]
CODE=WORK/'reproduction/radegs_paper_v01/stage2'
sys.path.insert(0,str(CODE))
from safety import atomic_json,sha256,STAGES

HDD=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01')
FIX=HDD/'gradient_fix_v01'
STATE=FIX/'pilot/state'
ART=WORK/'artifacts/radegs_paper_reproduction_v01/gradient_fix_v01'
VARIANT=HDD/'sources/paper_text_variant'
EXPECTED_HEAD='00bb67c4ae39157906bcda6abc8760cc37679414'
C24='2d4bc087f1b4bd62c96054fbe89d273490526b81'


def git(*args,cwd=WORK):
    return subprocess.check_output(['git',*args],cwd=cwd,text=True).strip()


def verify_changes(expected,allowed):
    changed=[]
    for name,digest in expected.items():
        current=sha256(name)
        if current!=digest:
            if name not in allowed:raise ValueError('unexpected parent-manifest change: '+name)
            changed.append({'path':name,'before_sha256':digest,'after_sha256':current})
    if {d['path'] for d in changed}!=allowed:raise ValueError('expected fix or new native binary missing')
    return changed


def main():
    assert not (STATE/'runner_state.json').exists(),'never reseal an active or previous runner'
    assert git('branch','--show-current')=='gaer-rade-depth-lift-v01'
    assert git('rev-parse','HEAD')==EXPECTED_HEAD,'review a new HEAD explicitly; do not reset commits'
    assert git('rev-parse','HEAD',cwd=HDD/'sources/RaDe-GS')==C24
    assert not git('status','--porcelain',cwd=HDD/'sources/RaDe-GS')
    for p in git('diff','--name-only').splitlines():
        assert p.startswith(('reproduction/radegs_paper_v01/','artifacts/radegs_paper_reproduction_v01/'))
    old=HDD/'stage2/state'
    parent_path=old/'runner_config.json'
    parent=json.loads(parent_path.read_text())
    previous=json.loads((old/'runner_state.json').read_text())
    assert previous['status']=='ENGINEERING_NOT_READY' and previous['child_pid'] is None
    original=FIX/'original_failure'
    snapshot=json.loads((original/'MANIFEST.json').read_text())
    for item in snapshot['files']:assert sha256(original/item['snapshot'])==item['sha256']
    tests=json.loads((FIX/'tests/results.json').read_text());assert tests['passed']
    for test in tests['suites']:assert test['returncode']==0 and sha256(test['log'])==test['sha256']
    native=HDD/'envs/c24_py39/lib/python3.9/site-packages/diff_gaussian_rasterization/_C.cpython-39-x86_64-linux-gnu.so'
    backward=VARIANT/'submodules/diff-gaussian-rasterization/cuda_rasterizer/backward.cu'
    changes=verify_changes(parent['immutable_files'],{str(native),str(backward),str(CODE/'gpu_stages.py')})
    wheel=next((FIX/'build/wheels').glob('*.whl'))
    with zipfile.ZipFile(wheel) as archive:
        binary=next(p for p in archive.namelist() if p.endswith('.so'))
        import hashlib
        assert hashlib.sha256(archive.read(binary)).hexdigest()==sha256(native)
    install=json.loads((FIX/'build/install.json').read_text());assert install['returncode']==0
    imports=json.loads((FIX/'build/import_check.json').read_text());assert imports['cuda_initialized'] is False
    assert imports['rasterizer_native']==str(native)
    source=json.loads((old/'stage2_source_manifest.json').read_text())
    source['variant_files']={p:sha256(p) for p in source['variant_files']}
    paths=[*CODE.glob('*.py'),*Path(__file__).parent.glob('*.py')]
    for path in paths:ast.parse(path.read_text())
    source['harness_files']={str(p):sha256(p) for p in paths}
    source['parent_manifest_sha256']=sha256(old/'stage2_source_manifest.json')
    source['workspace_head']=EXPECTED_HEAD
    source['gradient_fix_scope']='Jn third-column mean VJP: ray length and x/y cross terms; forward/loss/schedule unchanged'
    ART.mkdir(exist_ok=True,parents=True)
    patch=subprocess.check_output(['git','diff','--binary'],cwd=VARIANT)
    header=VARIANT/'submodules/diff-gaussian-rasterization/cuda_rasterizer/paper_distortion.cuh'
    extra=subprocess.run(['git','diff','--no-index','--','/dev/null',str(header.relative_to(VARIANT))],cwd=VARIANT,capture_output=True)
    assert extra.returncode==1;patch+=extra.stdout
    (ART/'SOURCE_PATCH.diff').write_bytes(patch)
    before=original/'HDD/sources/paper_text_variant/submodules/diff-gaussian-rasterization/cuda_rasterizer/backward.cu'
    (ART/'GRADIENT_ONLY.diff').write_text(''.join(difflib.unified_diff(before.read_text().splitlines(True),backward.read_text().splitlines(True),fromfile='before/backward.cu',tofile='after/backward.cu')))
    source['source_patch']=str(ART/'SOURCE_PATCH.diff');source['source_patch_sha256']=sha256(ART/'SOURCE_PATCH.diff')
    atomic_json(STATE/'source_manifest.json',source)
    build={'parent_native_build':parent['inputs']['native_build'],'source_manifest_sha256':sha256(STATE/'source_manifest.json'),
           'native_files':{p:sha256(p) for p in json.loads((old/'nativebuild_provenance.json').read_text())['native_files']},
           'wheel':str(wheel),'wheel_sha256':sha256(wheel),'installed_native_matches_wheel':True,
           'build_record':json.loads((FIX/'build/before_build.json').read_text()),
           'build_log':str(FIX/'build/build.log'),'build_log_sha256':sha256(FIX/'build/build.log'),
           'install_record':install,'CPU_import_check':imports,'GPU_verification':'mandatory smoke before train'}
    atomic_json(STATE/'nativebuild_provenance.json',build)
    inputs=dict(parent['inputs'],source_manifest=sha256(STATE/'source_manifest.json'),native_build=sha256(STATE/'nativebuild_provenance.json'))
    c=dict(parent);c['inputs']=inputs;c['state_dir']=str(STATE);c['log_dir']=str(FIX/'pilot/logs')
    c['allowed_gpu_uuids']=['GPU-d2d1e4fd-e246-0633-3343-ccc0a0bd981a']
    path=STATE/'runner_config.json'
    c['stage_commands']={s:[str(HDD/'envs/c24_py39/bin/python'),str(CODE/'gpu_stages.py'),'--config',str(path),'--stage',s] for s in STAGES}
    c['reports']={s:str(STATE/(s+'.report.json')) for s in STAGES}
    c['train_command']=list(parent['train_command']);c['train_command'][-1]=str(path)
    c['preflight_report']=str(STATE/'preflight.json')
    immutable={p:sha256(p) for p in parent['immutable_files']}
    immutable.update(source['harness_files'])
    for p in [STATE/'source_manifest.json',STATE/'nativebuild_provenance.json',
              ART/'SOURCE_PATCH.diff',ART/'GRADIENT_ONLY.diff',FIX/'tests/results.json',
              HDD/'stage2/shared/shared_runner.py',HDD/'stage2/shared/authorization.json']:
        immutable[str(p)]=sha256(p)
    c['immutable_files']=immutable
    c['gradient_fix_parent_config']=str(parent_path);c['gradient_fix_parent_sha256']=sha256(parent_path)
    c['previous_failure_preserved']=str(original/'MANIFEST.json')
    c['gpu_policy']='USER_AUTHORIZED_SHARED_GPU0; stable 60s util<=10 free>=12288; stop on new foreign context/free<2048/query failure'
    atomic_json(path,c)
    preflight={'passed':True,'utc_unix':time.time(),'CPU_tests':tests,'parent_config_sha256':sha256(parent_path),
               'config_sha256':sha256(path),'workspace_head':EXPECTED_HEAD,'changed_parent_files':changes,
               'old_ENGINEERING_NOT_READY_state_unchanged':True,'GPU_tests':'PENDING_ACTUAL_GPU_SMOKE',
               'scientificdone':False,'original_C24_clean':True,'snapshot_verified':True}
    atomic_json(STATE/'preflight.json',preflight)
    atomic_json(ART/'RESEAL_BEFORE_AFTER.json',preflight)
    print(json.dumps({'config':str(path),'sha256':sha256(path),'changed_parent_files':changes},indent=2))


if __name__=='__main__':main()
