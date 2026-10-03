#!/usr/bin/env python3
"""Read-only lineage verifier. Preflight readiness is not a trained checkpoint."""
import argparse
import datetime
import difflib
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import numpy as np

from verify_experiment import ROOT,ART,STAGE,SCENES,F,C,read,write,sha,canonical,require,audit_access

AART=ROOT/'artifacts'/STAGE/'acquisition'


def verify_source_bytes(relative,pinned,staged):
    """Independently reconstruct the exact predeclared acquisition-only patch."""
    allowed={
        'utils/general_utils.py': [('def safe_state(silent):','def safe_state(silent, seed=0):'),('    random.seed(0)','    random.seed(seed)'),('    np.random.seed(0)','    np.random.seed(seed)'),('    torch.manual_seed(0)','    torch.manual_seed(seed)')],
        'scene/dataset_readers.py': [('    print("Reading Test Transforms")\n    test_cam_infos = readCamerasFromTransforms(path, "transforms_test.json", white_background, extension)','    # Strict TRAIN-only acquisition: do not open any TEST/VAL metadata.\n    test_cam_infos = []')],
        'train.py': [('    args = parser.parse_args(sys.argv[1:])','    parser.add_argument("--seed", type=int, default=0)\n    args = parser.parse_args(sys.argv[1:])'),('safe_state(args.quiet)','safe_state(args.quiet, args.seed)'),('        (model_params, first_iter) = torch.load(checkpoint)','        (model_params, first_iter) = acquisition_runtime.load_checkpoint(checkpoint)'),('    viewpoint_stack = None\n    ema_loss_for_log = 0.0','    viewpoint_stack, ema_loss_for_log = acquisition_runtime.restore_loop(checkpoint, scene)'),('                torch.save((gaussians.capture(), iteration), scene.model_path + "/chkpnt" + str(iteration) + ".pth")','                acquisition_runtime.save_checkpoint(gaussians, iteration, scene, viewpoint_stack, ema_loss_for_log)'),('import os\n','import os\nimport acquisition_runtime\n')]
    }
    expected=pinned
    for old,new in allowed.get(relative,[]):
        require(expected.count(old)==1,'pinned patch context differs: '+relative)
        expected=expected.replace(old,new)
    require(expected==staged,'staged source differs from Git pin + exact approved patch: '+relative)
    return True


def inspect_checkpoint(path,expected_sha256):
    from plyfile import PlyData
    require(sha(path)==expected_sha256,'checkpoint hash differs')
    vertex=PlyData.read(path)['vertex'].data;names=vertex.dtype.names
    require(len(vertex)>0,'empty checkpoint')
    required={'x','y','z','opacity','scale_0','scale_1','scale_2','rot_0','rot_1','rot_2','rot_3','f_dc_0','f_dc_1','f_dc_2'}
    require(required<=set(names),'non-vanilla checkpoint schema')
    full_sh={f'f_rest_{i}' for i in range(45)}
    require({n for n in names if n.startswith('f_rest_')}==full_sh,'training SHdegree3 coefficient schema differs')
    for name in names:
        require(np.issubdtype(vertex.dtype[name],np.number) and np.isfinite(vertex[name]).all(),'nonfinite/nonnumeric PLY field: '+name)
    return dict(path=str(path),sha256=expected_sha256,gaussians=len(vertex),all_numeric_fields_finite=True,fields=list(names),ignored_by_NPR_fullSH_fields_finite=sorted(full_sh),full_SH_degree=3)


def acquisition_canonical(value):
    # Acquisition uses json default ensure_ascii=True, unlike NPR canonical.
    import hashlib
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def preflight():
    acquisition=read(AART/'ACQUISITION.json');sources=read(AART/'SOURCE_MANIFEST.json')
    require(acquisition['source_manifest_sha256']==sha(AART/'SOURCE_MANIFEST.json'),'acquisition source manifest digest differs')
    require(acquisition['upstream_commit']==sources['commit']=='472689c0dc70417448fb451bf529ae532d32c095','upstream pin differs')
    changed=set();checked=[];diff=[];provenance=[]
    prior_vendor=Path('/home/u00134/3dgs_line/tier1/out/multiscene_foundation/vendor/gaussian-splatting')
    for row in sources['files']:
        require(sha(row['path'])==row['sha256'],'isolated training source changed: '+row['relative_path'])
        pinned=subprocess.check_output(['git','show',sources['commit']+':'+row['relative_path']],cwd=sources['upstream'])
        pinned_sha=hashlib.sha256(pinned).hexdigest()
        require(pinned_sha==row['upstream_sha256'],'declared upstream digest differs from actual Git blob')
        staged=Path(row['path']).read_text();original=pinned.decode()
        verify_source_bytes(row['relative_path'],original,staged)
        working_sha=sha(Path(sources['upstream'])/row['relative_path'])
        if 'upstream_worktree_sha256' in row:require(working_sha==row['upstream_worktree_sha256'],'disclosed upstream working tree changed')
        require(row['modified']==(row['sha256']!=row['upstream_sha256']),'source modification flag differs')
        if row['modified']:
            changed.add(row['relative_path'])
            diff.extend(difflib.unified_diff(original.splitlines(True),staged.splitlines(True),fromfile='upstream/'+row['relative_path'],tofile='isolated/'+row['relative_path']))
        prior_sha=sha(prior_vendor/row['relative_path'])
        if row['relative_path'] not in ('train.py','utils/general_utils.py'):
            require(prior_sha==pinned_sha,'prior actual Lego vendor differs from pin outside known seed patch: '+row['relative_path'])
        provenance.append(dict(path=row['relative_path'],git_blob_sha256=pinned_sha,upstream_working_tree_sha256=working_sha,working_tree_matches_pin=working_sha==pinned_sha,prior_lego_vendor_sha256=prior_sha,prior_vendor_matches_pin=prior_sha==pinned_sha))
        checked.append(row['relative_path'])
    require(changed=={'train.py','scene/dataset_readers.py','utils/general_utils.py'},'unreviewed vanilla source modifications')
    require('LICENSE.md' in checked and sources['patch_sha256']==sha(AART/'UPSTREAM_PATCH.diff'),'license/patch pin missing')
    require(''.join(diff)==(AART/'UPSTREAM_PATCH.diff').read_text(),'recorded training patch differs from independently reconstructed Git-pin diff')
    for row in acquisition['binaries']+acquisition['prior_files']+acquisition['support_files']:
        require(sha(row['path'])==row['sha256'],'acquisition dependency hash changed: '+row['path'])
    central=read(ROOT/'artifacts'/STAGE/'INPUTS.json');scenes={}
    for scene in SCENES:
        item=acquisition['scenes'][scene];manifest=read(item['path'])
        require(sha(item['path'])==item['sha256'] and acquisition_canonical(manifest)==item['canonical_sha256'],'acquisition manifest digest differs')
        require(manifest['scene']==scene and manifest['seed']==1729 and manifest['iterations']==30000,'scene/seed/iteration changed')
        require(manifest['checkpoint_iterations']==[7000,30000],'checkpoint schedule changed')
        expected=dict(resolution=-1,sh_degree=3,lambda_dssim=.2,densification_interval=100,densify_from_iter=500,densify_until_iter=15000,densify_grad_threshold=.0002,opacity_reset_interval=3000,percent_dense=.01,position_lr_max_steps=30000)
        for k,v in expected.items():require(manifest['defaults'][k]==v,'vanilla default changed: '+k)
        args=manifest['arguments'];require('--white_background' in args and '--eval' not in args,'training background/eval changed')
        require(args[args.index('--iterations')+1]=='30000','CLI training iteration differs')
        require(manifest['diagnostic_train_indices']==[1,41,79],'in-sample diagnostic indices changed')
        require(manifest['source_manifest_sha256']==sha(AART/'SOURCE_MANIFEST.json'),'training source identity differs')
        data=Path(manifest['original_data']);require(data==Path('/home/u00134/cglib/data/full')/scene,'training data path differs')
        metadata=read(data/'transforms_train.json');require(len(metadata['frames'])==100,'TRAIN count differs')
        input_rows={str(Path(r['path'])):r['sha256'] for r in manifest['input_files']}
        require(len(input_rows)==101 and str(data/'transforms_train.json') in input_rows,'exact100 TRAIN files+metadata not declared')
        for i in range(100):
            require(str(data/'train'/f'r_{i}.png') in input_rows,'missing TRAIN image hash')
            require(Path(metadata['frames'][i]['file_path']).as_posix()==f'train/r_{i}','TRAIN frame index mismatch')
        require(input_rows[str(data/'transforms_train.json')]==sha(data/'transforms_train.json'),'TRAIN metadata changed')
        central_rows={r['path']:r['sha256'] for r in central['scenes'][scene]['train_images']}
        require(all(input_rows[k]==v for k,v in central_rows.items()) and len(central_rows)==100,'root/acquisition TRAIN hashes differ')
        for row in manifest['verified_files']:require(sha(row['path'])==row['sha256'],'verified file changed: '+row['path'])
        scenes[scene]=dict(passed=True,seed=1729,iterations=30000,train_cameras=100,C_used_photometrically=list(C),manifest_sha256=sha(item['path']),checkpoint_destination=item['checkpoint_destination'])
    return dict(passed=True,mode='PREFLIGHT_ONLY',source_files=checked,modified_files=sorted(changed),scenes=scenes,
                independent_git_pin_provenance=provenance,upstream_working_tree_is_not_trusted_as_git_pin=True,
                necessary_differences=acquisition['necessary_differences'],source_image_bytes_rehashed=False,
                input_hash_scope='TRAIN metadata rehashed; image digests crosschecked with root frozen bytehash manifest, no image decode',
                production_claim='No checkpoint/training/calibration claim from preflight')


def final_scene(scene):
    manifest_path=AART/'manifests'/f'{scene}.json';manifest=read(manifest_path);identity=acquisition_canonical(manifest)
    folder=Path(manifest['directory']);lock=read(folder/'CHECKPOINT_LOCK.json');status=read(folder/'STATUS.json')
    require(lock['state']==status['state']=='COMPLETE','training not complete')
    require(lock['scene']==scene and lock['seed']==1729 and lock['iterations']==30000,'checkpoint lineage scene/seed/iteration differs')
    require(lock['manifest_sha256']==status['manifest_sha256']==identity,'checkpoint lineage manifest differs')
    require(lock['source_manifest_sha256']==manifest['source_manifest_sha256'] and lock['source_commit']==manifest['source_commit'],'checkpoint training source differs')
    require(status['exit_code']==0 and not status['timed_out'] and status['wall_seconds']<=7200+60,'training exit/timeout/budget invalid')
    require(set(lock['checkpoints'])=={'7000','30000'},'checkpoint iterations incomplete')
    checkpoints={}
    for key,row in lock['checkpoints'].items():
        iteration=int(key);require(row['iteration']==iteration,'checkpoint iteration differs')
        require(sha(row['path'])==row['sha256'] and sha(row['snapshot'])==row['snapshot_sha256'],'checkpoint bytes differ')
        sidecar=read(row['snapshot_sidecar'])
        require(sidecar['sha256']==row['snapshot_sha256'] and sidecar['manifest_sha256']==identity and sidecar['iteration']==iteration,'resume sidecar differs')
        checkpoints[key]={**row,'independent_numeric_check':inspect_checkpoint(row['path'],row['sha256'])}
    losses=[json.loads(line) for line in (folder/'losses.jsonl').read_text().splitlines()]
    require([r['iteration'] for r in losses]==list(range(1,30001)),'loss history has missing/duplicate/restarted iteration')
    require(all(math.isfinite(r[k]) and r[k]>=0 for r in losses for k in ('l1','photometric_loss','cuda_iteration_ms')),'nonfinite/invalid photometric training losses')
    attempts=sorted(folder.glob('attempt_*'));require(attempts,'missing actual launch evidence')
    launches=[]
    for attempt in attempts:
        launch=read(attempt/'LAUNCH.json');guard=read(attempt/'GPU_GUARD.json');exit_status=read(attempt/'EXIT.json')
        require(launch['manifest_sha256']==identity,'launched manifest changed')
        require(launch['verified_remote_sha']==launch['freeze_commit'],'launch lacked matching remote freeze')
        frozen=subprocess.check_output(['git','show',launch['freeze_commit']+':'+str(manifest_path.relative_to(ROOT))],cwd=ROOT)
        require(json.loads(frozen)==manifest,'launched manifest not committed')
        for name in ('PROTOCOL.md','INPUTS.json'):
            subprocess.run(['git','cat-file','-e',launch['freeze_commit']+':artifacts/'+STAGE+'/'+name],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
        gpu=next(d for d in guard['devices'] if d['index']==launch['gpu'])
        require(not any(r['gpu_uuid']==gpu['uuid'] for r in guard['processes']),'selected GPU had process at launch')
        require(all(r['pid'] in guard['own_pids'] for r in guard['processes']),'foreign GPU process present at launch')
        trace=attempt/'training.strace';access=audit_access(trace.read_text(),ROOT,'acquisition',initial_cwd=folder)
        launches.append(dict(path=str(attempt),launch=launch,access=access,trace_sha256=sha(trace),exit_code=exit_status['exit_code']))
    require(sum(r['launch']['resume'] is None for r in launches)==1,'multiple fresh acquisitions')
    return dict(passed=True,checkpoint_lock_path=str(folder/'CHECKPOINT_LOCK.json'),checkpoint_lock_sha256=sha(folder/'CHECKPOINT_LOCK.json'),checkpoints=checkpoints,loss_iterations=len(losses),first_loss=losses[0],last_loss=losses[-1],launches=launches,
                training_qualification='All100 TRAIN including C used photometrically; diagnostics in-sample only, no generalization or NPR quality gate')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--final',action='store_true');parser.add_argument('--checkpoint-scene',choices=SCENES);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    require(ART in args.output.resolve().parents,'output outside independent directory')
    report=dict(passed=False,scientific_GO=False,errors=[])
    try:
        report['preflight']=preflight()
        if args.final:report['scenes']={s:final_scene(s) for s in SCENES}
        elif args.checkpoint_scene:report['scenes']={args.checkpoint_scene:final_scene(args.checkpoint_scene)}
        report['passed']=True;report['status']='PASS' if args.final else 'PREFLIGHT_ONLY_PASS'
        if args.checkpoint_scene:report['status']='SCENE_ACQUISITION_PASS'
    except Exception as exc:report['errors'].append(repr(exc));report['status']='INVALID_OR_INCOMPLETE'
    write(args.output,report);print(json.dumps(report,ensure_ascii=False));return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
