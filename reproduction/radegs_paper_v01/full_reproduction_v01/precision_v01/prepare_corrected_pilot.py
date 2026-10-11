"""Freeze corrected scan24 inputs after real GPU gates. No launch or CUDA."""
import datetime
import difflib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'reproduction/radegs_paper_v01/stage2'))
from safety import atomic_json,sha256,verify_seal,STAGES


def main():
    h=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01')
    prec=h/'full_reproduction_v01/precision_v01'
    art=ROOT/'artifacts/radegs_paper_reproduction_v01/full_reproduction_v01'
    part=art/'precision_v01';code=Path(__file__).resolve().parent
    source=h/'sources/paper_text_precision_v01';original=h/'sources/RaDe-GS'
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()=='00bb67c4ae39157906bcda6abc8760cc37679414'
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=original,text=True).strip()=='2d4bc087f1b4bd62c96054fbe89d273490526b81'
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=original,text=True).strip()
    stages=[]
    for directory in ['candidate_gpu_v01','expanded_gpu_v01','scene_regression_v01']:
        path=prec/directory/'state/runner_config.json';cfg=json.loads(path.read_text())
        state=json.loads((path.parent/'runner_state.json').read_text())
        assert state['status']=='DIAGNOSTIC_COMPLETE' and not Path('/proc',str(state['runner_pid'])).exists()
        seal=path.parent/'checkpoint_diagnostic.seal.json'
        assert verify_seal(seal,'checkpoint_diagnostic',cfg['inputs'])
        assert all(sha256(p)==digest for p,digest in cfg['immutable_files'].items())
        stages.append({'config':str(path),'config_sha256':sha256(path),'seal':str(seal),'seal_sha256':sha256(seal)})
    cpu=json.loads((prec/'CPU_final_v01/results.json').read_text());assert cpu['passed'] and cpu['test_count']==65
    assert all(x['returncode']==0 and sha256(x['log'])==x['sha256'] for x in cpu['suites'])
    assert 'Ran 3 tests' in (prec/'pilot_reserve_GREEN.log').read_text() and (prec/'pilot_reserve_GREEN.log').read_text().rstrip().endswith('OK')
    oldpath=h/'gradient_fix_v01/pilot/state/runner_config.json';c=json.loads(oldpath.read_text())
    assert all(sha256(p)==digest for p,digest in c['immutable_files'].items())
    for stage in ['smoke','train','export']:assert verify_seal(oldpath.parent/(stage+'.seal.json'),stage,c['inputs'])
    frozen=json.loads((prec/'candidate_source_frozen_v01.json').read_text())
    assert all(sha256(p)==digest for p,digest in frozen['files'].items())
    patch=[];changed=[]
    for name in sorted(frozen['files']):
        path=Path(name);relative=path.relative_to(source);before=original/relative
        if before.is_file() and sha256(before)==sha256(path):continue
        old=before.read_text().splitlines(True) if before.exists() else []
        new=path.read_text().splitlines(True)
        patch.extend(difflib.unified_diff(old,new,fromfile='C24/'+str(relative),tofile='paper_text_precision_v01/'+str(relative)))
        changed.append({'relative':str(relative),'before':sha256(before) if before.exists() else None,'after':sha256(path)})
    (part/'SOURCE_PATCH_FULL.diff').write_text(''.join(patch))
    shutil.copy2(prec/'CANDIDATE_PATCH.diff',part/'PRECISION_ONLY.diff')
    model=h/'models/scan24_paper_text_precision_v01_half_30k'
    state=prec/'pilot_v01/state';assert not state.exists() and not model.exists()
    reserve={'root_free_bytes':shutil.disk_usage('/').free,'HDD_free_bytes':shutil.disk_usage(h).free,
             'estimated_new_output_bytes':10*1024**3,'estimate_basis':'old scan24 model+export measured 2022188507 bytes; reserve 10 GiB for changed model/checkpoints/exports/eval, not a training-time estimate',
             'root_min_bytes':10*1024**3,'HDD_min_bytes':50*1024**3}
    assert reserve['root_free_bytes']>=reserve['root_min_bytes']
    assert reserve['HDD_free_bytes']-reserve['estimated_new_output_bytes']>=reserve['HDD_min_bytes']
    amendment={'parent_protocol':str(art/'FULL_SUITE_PROTOCOL.json'),'parent_protocol_sha256':sha256(art/'FULL_SUITE_PROTOCOL.json'),
               'scope':'scan24 half30k numerical implementation correction; no new scientific arm/ablation',
               'reason':'Actual trained-range GPU forward/VJP failure in absolute-tolerance GLM covariance eigensolver; same-scale normalization restores mathematical geometry',
               'GPU_gates':stages,'CPU_tests':65,'reserve_tests':3,'original_model_preserved':str(h/'models/scan24_paper_text_half_30k'),
               'new_model':str(model),'fresh_COLMAP_initialization':True,'resume_old_15k_or_30k':False,
               'losses_unchanged':{'wd':100,'wn':5,'photo_iterations':[1,15000],'geometry_iterations':[15001,30000],
                 'Eq23':'camera-z ordered double sum, detach alphaT only','Eq24':'alphaT unnormalized mixed normal consistency, no extra detach'},
               'remaining_method':'C24 median/Eq4 affine plane/Mip3D filter/GOF densification/DTU appearance unchanged',
               'not_bitexact_author_experiment':True,'collapse_causality_not_yet_proven':True,'storage':reserve}
    atomic_json(part/'PROTOCOL_AMENDMENT_PRECISION_V01.json',amendment)
    native=json.loads((prec/'build/native_provenance.json').read_text())
    receipt={'build_time_provenance':str(prec/'build/native_provenance.json'),'build_time_provenance_sha256':sha256(prec/'build/native_provenance.json'),
             'candidate_native':native['candidate_native'],'candidate_native_sha256':sha256(native['candidate_native']),
             'original_native_unchanged':sha256(native['original_native'])==native['original_native_sha256'],
             'actual_GPU_validation_seals':stages,'source_files':len(frozen['files']),'changed_from_C24':changed,
             'CPU_tests':65,'native_installed_in_original_env':False,'scientific_result_not_yet_known':True}
    atomic_json(part/'SOURCE_NATIVE_VALIDATION_RECEIPT.json',receipt)
    state.mkdir(parents=True);model.mkdir()
    cfgpath=state/'runner_config.json'
    c.update(state_dir=str(state),log_dir=str(prec/'pilot_v01/logs'),model=str(model),cwd=str(source),
             preflight_report=str(state/'preflight.json'),allowed_gpu_uuids=['GPU-d2d1e4fd-e246-0633-3343-ccc0a0bd981a'])
    c['runtime_env']['PYTHONPATH']=native['isolated_import_path']+':'+str(ROOT/'reproduction/radegs_paper_v01/stage2')+':'+str(source)
    c['stage_commands']={stage:[str(h/'envs/c24_py39/bin/python'),str(ROOT/'reproduction/radegs_paper_v01/stage2/gpu_stages.py'),
                                '--config',str(cfgpath),'--stage',stage] for stage in STAGES}
    c['reports']={stage:str(state/(stage+'.report.json')) for stage in STAGES}
    for key in ['train_command','tsdf_command','eval_command']:
        command=list(c[key]);command[command.index('-m')+1]=str(model)
        if key=='train_command':command[command.index('--pilot_config')+1]=str(cfgpath)
        c[key]=command
    c['inputs']=dict(c['inputs'],source_manifest=sha256(prec/'candidate_source_frozen_v01.json'),
                    native_build=sha256(part/'SOURCE_NATIVE_VALIDATION_RECEIPT.json'),
                    candidate_native=sha256(native['candidate_native']),
                    protocol_amendment=sha256(part/'PROTOCOL_AMENDMENT_PRECISION_V01.json'),
                    admission_policy=sha256(code/'strict_shared_policy.py'))
    c['immutable_files'].update(frozen['files'])
    extra=[Path(native['candidate_native']),Path(native['candidate_native']).parent/'__init__.py',prec/'candidate_source_frozen_v01.json',
           part/'PROTOCOL_AMENDMENT_PRECISION_V01.json',part/'SOURCE_NATIVE_VALIDATION_RECEIPT.json',part/'SOURCE_PATCH_FULL.diff',part/'PRECISION_ONLY.diff',
           prec/'CPU_final_v01/results.json',code/'strict_shared_policy.py',code/'strict_pilot_runner.py',code/'test_strict_pilot_runner.py',code/'prepare_corrected_pilot.py']
    for row in stages:extra.extend([Path(row['config']),Path(row['seal'])])
    for path in extra:c['immutable_files'][str(path)]=sha256(path)
    c['precision_parent_config']=str(oldpath);c['precision_parent_sha256']=sha256(oldpath)
    c['gpu_policy']='GPU0 shared low load; actual free>=12288MiB/util<=10 stable60s; stop own stage on new foreign context/actual free<2048/query failure'
    c['scientific_scope']='Corrected scan24 only; no automatic second scene. Full-suite objective retained in MASTER_STATUS.'
    atomic_json(cfgpath,c)
    atomic_json(state/'preflight.json',{'passed':True,'config_sha256':sha256(cfgpath),'actual_GPU_gates':stages,
                'CPU_tests':65,'reserve_tests':3,'storage':reserve,'fresh_output_empty_before_launch':True,
                'original_failure_preserved':True,'scientificdone':False})
    atomic_json(part/'MODEL_LAUNCH.json',{'config':str(cfgpath),'config_sha256':sha256(cfgpath),'model':str(model),
                 'train_command':c['train_command'],'cwd':str(source),'native':native['candidate_native'],
                 'native_sha256':sha256(native['candidate_native']),'status':'PREPARED_NOT_LAUNCHED',
                 'source_C24':'2d4bc087f1b4bd62c96054fbe89d273490526b81','workspace_HEAD':'00bb67c4ae39157906bcda6abc8760cc37679414'})
    print(json.dumps({'config':str(cfgpath),'config_sha256':sha256(cfgpath),'model':str(model),'immutable_files':len(c['immutable_files'])},indent=2))


if __name__=='__main__':main()
