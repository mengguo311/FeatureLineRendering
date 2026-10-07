"""Create immutable CPU-preflight/config manifests. Does not launch a GPU job."""
import ast
import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from safety import atomic_json,sha256,STAGES,query_gpus

WORK=Path(__file__).resolve().parents[3]
ART=WORK/'artifacts/radegs_paper_reproduction_v01'
CODE=Path(__file__).resolve().parent
HDD=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01')
ORIGINAL=HDD/'sources/RaDe-GS'
VARIANT=HDD/'sources/paper_text_variant'
STATE=HDD/'stage2/state'
PYTHON=HDD/'envs/c24_py39/bin/python'
C24='2d4bc087f1b4bd62c96054fbe89d273490526b81'


def command(argv,cwd=None):
    return subprocess.check_output([str(x) for x in argv],cwd=cwd,text=True).strip()


def main():
    assert not (STATE/'runner_state.json').exists(),'do not regenerate a live runner config'
    assert command(['git','branch','--show-current'],WORK)=='gaer-rade-depth-lift-v01'
    assert command(['git','rev-parse','HEAD'],WORK)=='52a409b806fd5d326ccce0d5657e25336beb68d5'
    frozen=ART/'stage1_frozen'
    for item in json.loads((frozen/'SEAL.json').read_text())['files']:
        assert sha256(frozen/item['path'])==item['sha256']
    assert json.loads((frozen/'STATUS.json').read_text())['stage1completed']
    assert json.loads((frozen/'evidence/document_validation.json').read_text())['passed']
    assert command(['git','rev-parse','HEAD'],ORIGINAL)==C24
    assert not command(['git','status','--porcelain'],ORIGINAL)
    subprocess.run(['git','diff','--check'],cwd=VARIANT,check=True)
    data=json.loads((STATE/'DATA_STATUS.json').read_text());assert data['passed']
    for path,digest in {**data['training_file_hashes'],**data['eval_file_hashes']}.items():
        assert sha256(path)==digest
    environment=json.loads((STATE/'environment_import_check.json').read_text())
    assert environment['cuda_initialized'] is False
    env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES='',TMPDIR=str(HDD/'tmp'),
        MPLCONFIGDIR=str(HDD/'cache/matplotlib'),XDG_CACHE_HOME=str(HDD/'cache'),PYTHONDONTWRITEBYTECODE='1')
    tests=[]
    for name in ['safety','paper_math','restart','train_contract','runner']:
        log=HDD/'stage2/tests'/f'{name}_FINAL_GREEN.log'
        with open(log,'w') as f:
            result=subprocess.run([str(PYTHON),str(CODE/f'test_{name}.py')],env=env,stdout=f,stderr=subprocess.STDOUT)
        tests.append({'name':name,'returncode':result.returncode,'log':str(log),'sha256':sha256(log)})
        assert result.returncode==0,log
    for path in CODE.glob('*.py'):ast.parse(path.read_text())
    # Store exact complete resolved environment, rather than pretending the
    # unpinned 2024 README specified today's resolution.
    freeze=command([PYTHON,'-m','pip','freeze','--all'])+'\n'
    (STATE/'pip-freeze.txt').write_text(freeze)
    conda=command(['/home/u00134/bin/miniconda3/bin/conda','list','--prefix',HDD/'envs/c24_py39','--explicit'])+'\n'
    (STATE/'conda-explicit.txt').write_text(conda)
    lock={**environment,'pip_freeze_path':str(STATE/'pip-freeze.txt'),
          'pip_freeze_sha256':sha256(STATE/'pip-freeze.txt'),
          'conda_explicit_path':str(STATE/'conda-explicit.txt'),
          'conda_explicit_sha256':sha256(STATE/'conda-explicit.txt'),
          'not_author_historical_environment':True}
    atomic_json(STATE/'environment_lock.json',lock)
    tracked=command(['git','ls-files'],ORIGINAL).splitlines()
    source_files={str(VARIANT/p):sha256(VARIANT/p) for p in tracked if (VARIANT/p).is_file()}
    header=VARIANT/'submodules/diff-gaussian-rasterization/cuda_rasterizer/paper_distortion.cuh'
    source_files[str(header)]=sha256(header)
    # Include checked-out gitlink contents needed to rebuild, not .git stores.
    for base in [VARIANT/'submodules/simple-knn',VARIANT/'submodules/diff-gaussian-rasterization/third_party/glm']:
        for rel in command(['git','ls-files'],base).splitlines():
            path=base/rel
            if path.is_file():source_files[str(path)]=sha256(path)
    code_hashes={str(p):sha256(p) for p in sorted(CODE.glob('*.py'))}
    patch=subprocess.check_output(['git','diff','--binary'],cwd=VARIANT)
    extra=subprocess.run(['git','diff','--no-index','--','/dev/null',str(header.relative_to(VARIANT))],cwd=VARIANT,capture_output=True)
    assert extra.returncode==1
    patch+=extra.stdout
    (ART/'SOURCE_PATCH.diff').write_bytes(patch)
    source={'upstream_head':C24,'original_path':str(ORIGINAL),'variant_path':str(VARIANT),
            'upstream_url':'https://github.com/HKUST-SAIL/RaDe-GS.git',
            'gitlinks':command(['git','submodule','status'],ORIGINAL).splitlines(),
            'source_patch':str(ART/'SOURCE_PATCH.diff'),'source_patch_sha256':sha256(ART/'SOURCE_PATCH.diff'),
            'variant_files':source_files,'harness_files':code_hashes,
            'claim':'paper_text_variant on C24; not the authors experiment commit or bit-exact reproduction'}
    atomic_json(STATE/'stage2_source_manifest.json',source)
    native_files={environment['rasterizer']:sha256(environment['rasterizer']),
                  environment['simple_knn']:sha256(environment['simple_knn'])}
    baseline_so=next((HDD/'build/baseline_python').rglob('*.so'))
    native_files[str(baseline_so)]=sha256(baseline_so)
    wheels={str(p):sha256(p) for p in (HDD/'build').rglob('*.whl')}
    baseline_hashes={}
    original_rasterizer=ORIGINAL/'submodules/diff-gaussian-rasterization'
    for src in original_rasterizer.rglob('*'):
        if src.is_file() and src.suffix in ('.cpp','.cu','.h','.cuh','.hpp','.inl','.py'):
            relative=src.relative_to(original_rasterizer)
            other=HDD/'sources/c24_validation_baseline'/relative
            assert sha256(src)==sha256(other),other
            baseline_hashes[str(other)]=sha256(other)
    build={'source_manifest_sha256':sha256(STATE/'stage2_source_manifest.json'),
           'native_files':native_files,'wheels':wheels,'CUDA_HOME':str(HDD/'envs/c24_py39'),
           'TORCH_CUDA_ARCH_LIST':'8.6','compiler':environment['compiler'],'nvcc':environment['nvcc'],
           'build_logs':{str(p):sha256(p) for p in (HDD/'stage2/logs').glob('build_*.log')},
           'cpu_import_passed_without_cuda_init':True,'GPU_forward_backward':'PENDING_IDLE_GPU',
           'baseline_source_checked_identical_to_C24':baseline_hashes,
           'baseline_purpose':'smoke RGB/alpha regression only, never a default-weight training arm'}
    atomic_json(STATE/'nativebuild_provenance.json',build)
    protocol={'scene':'scan24','resolution_divisor':2,'actual_half_image':[777,581],
              'iterations':30000,'photometric_iterations':[1,15000],'geometry_iterations':[15001,30000],
              'wd':100,'wn':5,'eq23':'camera-z double sum; detach alpha*T weights only',
              'eq24':'alpha minus blended_normal dot median_depth_normal; no normalization of blended_normal',
              'appearance':True,'Mip3D_filter':True,'GOF_densification':'inherited C24',
              'training_views':49,'test_views':0,'GT_role':'evaluation only',
              'automatic_scene_limit':1,'followup':'stop after scan24 chain; retain full-suite future objective'}
    atomic_json(STATE/'pilot_protocol.json',protocol)
    inputs={key:sha256(STATE/file) for key,file in [
        ('source_manifest','stage2_source_manifest.json'),('data_manifest','DATA_STATUS.json'),
        ('environment_lock','environment_lock.json'),('native_build','nativebuild_provenance.json'),
        ('protocol','pilot_protocol.json')]}
    immutable={**source_files,**code_hashes,**native_files,**data['training_file_hashes'],**data['eval_file_hashes']}
    for name in ['stage2_source_manifest.json','DATA_STATUS.json','environment_lock.json','nativebuild_provenance.json','pilot_protocol.json','pip-freeze.txt','conda-explicit.txt']:
        immutable[str(STATE/name)]=sha256(STATE/name)
    config_path=STATE/'runner_config.json';model=HDD/'models/scan24_paper_text_half_30k'
    model.mkdir(parents=True,exist_ok=True)
    train_command=[str(PYTHON),'train.py','-s',data['pilot']['prepared'],'-m',str(model),'-r','2',
       '--use_decoupled_appearance','--iterations','30000','--lambda_distortion','100',
       '--lambda_depth_normal','5','--regularization_from_iter','15001','--test_iterations','-1',
       '--save_iterations','15000','30000','--pilot_config',str(config_path)]
    runtime_env={'PATH':str(HDD/'envs/c24_py39/bin')+':/usr/bin:/bin',
       'PYTHONPATH':str(CODE)+':'+str(VARIANT),'PYTHONDONTWRITEBYTECODE':'1',
       'TMPDIR':str(HDD/'tmp'),'XDG_CACHE_HOME':str(HDD/'cache'),
       'MPLCONFIGDIR':str(HDD/'cache/matplotlib'),'TORCH_HOME':str(HDD/'cache/torch'),
       'OMP_NUM_THREADS':'4','OPENBLAS_NUM_THREADS':'4','MKL_NUM_THREADS':'4','CUDA_DEVICE_ORDER':'PCI_BUS_ID'}
    config={'schema':1,'scene':'scan24','automatic_scene_limit':1,'engineering_ready':True,
       'engineering_ready_means':'CPU preflight passed; GPU smoke is mandatory before train',
       'cwd':str(VARIANT),'data':data['pilot']['prepared'],'gt':data['evaluation']['path'],'model':str(model),
       'state_dir':str(STATE),'log_dir':str(HDD/'stage2/logs/runner'),'inputs':inputs,
       'preflight_report':str(STATE/'preflight.json'),'immutable_files':immutable,
       'poll_seconds':60,'stable_seconds':60,'active_monitor_seconds':5,
       'allowed_gpu_uuids':['GPU-d2d1e4fd-e246-0633-3343-ccc0a0bd981a','GPU-fedc3ced-16db-8c9b-fbc4-eec90f51bb55'],
       'runtime_env':runtime_env,'baseline_python':str(HDD/'build/baseline_python'),
       'stage_commands':{s:[str(PYTHON),str(CODE/'gpu_stages.py'),'--config',str(config_path),'--stage',s] for s in STAGES},
       'reports':{s:str(STATE/(s+'.report.json')) for s in STAGES},'train_command':train_command,
       'tsdf_command':[str(PYTHON),'mesh_extract.py','-s',data['pilot']['prepared'],'-m',str(model),'-r','2'],
       'eval_command':[str(PYTHON),'evaluate_dtu_mesh.py','-s',data['pilot']['prepared'],'-m',str(model),
                       '-r','2','--iteration','30000','--DTU',data['evaluation']['path']]}
    atomic_json(config_path,config)
    preflight={'passed':True,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
       'stage1_frozen_verified':True,'source_C24_clean':True,'data_verified':True,
       'CPU_tests':tests,'GPU_tests':'NOT_RUN_WAITING_FOR_IDLE_GPU','CUDA_initialized':False,
       'root_free_bytes':shutil.disk_usage('/').free,'hdd_free_bytes':shutil.disk_usage(HDD).free,
       'config_sha256':sha256(config_path),'not_scientific_completion':True}
    assert preflight['root_free_bytes']>=10*1024**3 and preflight['hdd_free_bytes']>=30*1024**3
    atomic_json(STATE/'preflight.json',preflight)
    evidence=ART/'stage2_evidence';evidence.mkdir(exist_ok=True)
    for name in ['DATA_STATUS.json','stage2_source_manifest.json','environment_lock.json','nativebuild_provenance.json','pilot_protocol.json','preflight.json','pip-freeze.txt','conda-explicit.txt','environment_import_check.json']:
        shutil.copyfile(STATE/name,evidence/name)
    (evidence/'tests').mkdir(exist_ok=True)
    for path in (HDD/'stage2/tests').glob('*.log'):
        shutil.copyfile(path,evidence/'tests'/path.name)
    atomic_json(STATE/'prelaunch_gpu_snapshot.json',{'unix':__import__('time').time(),'gpus':query_gpus()})
    print(json.dumps({'passed':True,'config':str(config_path),'config_sha256':sha256(config_path),
                       'CPU_suites':len(tests),'source_files':len(source_files),'immutable_files':len(immutable)},indent=2))


if __name__=='__main__':main()
