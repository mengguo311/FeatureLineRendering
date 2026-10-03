#!/usr/bin/env python3
"""CPU-only deterministic acquisition source/manifests, before freeze."""
import argparse
import difflib
import json
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
from acquisition_support import atomic_json,canonical_hash,patch_sources,sha256

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
OUT=REPO/'out/hybrid_raster_trained_models_v1'
UPSTREAM=Path('/home/u00134/3dgs_line/ext/gaussian-splatting')
SOURCE=OUT/'vendor/vanilla'
PYTHON='/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python'
SITES=['/home/u00134/3dgs_line/tier1/out/multiscene_foundation/vendor/training_site','/home/u00134/3dgs_line/tier1/out/vrss/vendor/official_site']

def main():
    source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=UPSTREAM,text=True).strip()
    if source_commit!='472689c0dc70417448fb451bf529ae532d32c095':raise RuntimeError('upstream pin mismatch')
    tracked=subprocess.check_output(['git','ls-tree','-r','--name-only',source_commit],cwd=UPSTREAM,text=True).splitlines()
    files=sorted(p for p in tracked if p in ['LICENSE.md','train.py'] or (len(Path(p).parts)==2 and Path(p).parts[0] in ['arguments','gaussian_renderer','scene','utils'] and p.endswith('.py')))
    blobs={p:subprocess.check_output(['git','show',source_commit+':'+p],cwd=UPSTREAM) for p in files}
    originals={p:blob.decode() for p,blob in blobs.items()}
    (HERE/'EXTERNAL_WORKTREE_READONLY.diff').write_bytes(subprocess.check_output(['git','diff','--',*files],cwd=UPSTREAM))
    patches=patch_sources({p:originals[p] for p in ['train.py','utils/general_utils.py','scene/dataset_readers.py']})
    records=[];diff=[]
    SOURCE.mkdir(parents=True,exist_ok=True)
    for name in files:
        target=SOURCE/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(patches.get(name,originals[name]))
        records.append(dict(relative_path=name,path=str(target),upstream_sha256=hashlib.sha256(blobs[name]).hexdigest(),upstream_worktree_sha256=sha256(UPSTREAM/name),sha256=sha256(target),modified=name in patches))
        if name in patches:diff.extend(difflib.unified_diff(originals[name].splitlines(True),patches[name].splitlines(True),fromfile='upstream/'+name,tofile='isolated/'+name))
    (HERE/'UPSTREAM_PATCH.diff').write_text(''.join(diff))
    source_manifest=dict(upstream=str(UPSTREAM),commit=source_commit,materialization='git show immutable commit blobs; never working-tree content',license='LICENSE.md',files=records,patch_sha256=sha256(HERE/'UPSTREAM_PATCH.diff'),external_worktree_diff_sha256=sha256(HERE/'EXTERNAL_WORKTREE_READONLY.diff'))
    atomic_json(HERE/'SOURCE_MANIFEST.json',source_manifest)
    binaries=[]
    for site in SITES:
        for path in sorted(Path(site).rglob('*')):
            if path.is_file() and path.suffix in ('.py','.so'):
                binaries.append(dict(path=str(path),sha256=sha256(path)))
    # Resolve defaults from pinned parser without importing GPU code.
    sys.path.insert(0,str(SOURCE));from arguments import ModelParams,OptimizationParams,PipelineParams
    parser=argparse.ArgumentParser();lp=ModelParams(parser);op=OptimizationParams(parser);pp=PipelineParams(parser)
    defaults=vars(parser.parse_args([]))
    inputs=json.loads((HERE.parent/'INPUTS.json').read_text())
    support=[dict(path=str(p),sha256=sha256(p)) for p in sorted(HERE.glob('*.py'))]
    verified=[dict(path=r['path'],sha256=r['sha256']) for r in records]+binaries+support
    manifests={}
    for scene,row in inputs['scenes'].items():
        directory=OUT/'training'/scene/'seed_1729';output=directory/'checkpoints'
        input_files=[dict(path=item['path'],sha256=item['sha256']) for item in row['train_images']]
        metadata=row['metadata'];input_files.append(dict(path=metadata['path'],sha256=metadata['sha256']))
        arguments=['-s',str(directory/'data'),'-m',str(output),'--white_background','--iterations','30000']
        manifest=dict(schema=1,scene=scene,seed=1729,iterations=30000,timeout_seconds=7200,python=PYTHON,source=str(SOURCE),site=SITES,
            directory=str(directory),output=str(output),original_data=str(Path(metadata['path']).parent),source_commit=source_commit,
            source_manifest_sha256=sha256(HERE/'SOURCE_MANIFEST.json'),verified_files=verified,input_files=input_files,
            arguments=arguments,defaults=defaults,diagnostic_train_indices=[1,41,79],save_iterations=[7000,30000],checkpoint_iterations=[7000,30000],
            evaluation='all100TRAIN incl C used photometrically; diagnostics in-sample; no TEST/VAL or mesh',
            initialization='official per-seed random100000 xyz=random*2.6-1.3; SH2RGB(random/255); local points3d.ply',
            resume='only matching manifest+snapshot SHA; model/optimizer+python/numpy/torch/CUDA RNG+remaining viewpoint stack restored')
        path=HERE/'manifests'/f'{scene}.json';atomic_json(path,manifest)
        manifests[scene]=dict(path=str(path),sha256=sha256(path),canonical_sha256=canonical_hash(manifest),checkpoint_destination=str(output/'point_cloud/iteration_30000/point_cloud.ply'))
    # Freeze a separate two-step synthetic infrastructure fixture before any GPU.
    # It never counts as a requested scene acquisition or NPR output.
    from PIL import Image
    toy=OUT/'training/synthetic_gpu_input_round3';(toy/'train').mkdir(parents=True,exist_ok=True)
    for index,color in [(0,(100,80,40,128)),(1,(40,80,100,255))]: Image.new('RGBA',(8,8),color).save(toy/'train'/f'r_{index}.png')
    toy_metadata={'camera_angle_x':.69,'frames':[{'file_path':'./train/r_0','transform_matrix':[[1,0,0,0],[0,1,0,0],[0,0,1,4],[0,0,0,1]]},{'file_path':'./train/r_1','transform_matrix':[[1,0,0,1],[0,1,0,0],[0,0,1,4],[0,0,0,1]]}]}
    atomic_json(toy/'transforms_train.json',toy_metadata)
    toy_directory=OUT/'training/synthetic_gpu_preflight_round3';toy_output=toy_directory/'checkpoints'
    toy_manifest=dict(manifest,scene='SYNTHETIC_INFRASTRUCTURE_ONLY',iterations=2,directory=str(toy_directory),output=str(toy_output),original_data=str(toy),
        arguments=['-s',str(toy_directory/'data'),'-m',str(toy_output),'--white_background','--iterations','2'],
        input_files=[{'path':str(p),'sha256':sha256(p)} for p in [toy/'transforms_train.json',toy/'train/r_0.png',toy/'train/r_1.png']],
        diagnostic_train_indices=[0,1],testing_iterations=[2],save_iterations=[2],checkpoint_iterations=[2],evaluation='synthetic infrastructure only; not requested-scene evidence')
    atomic_json(HERE/'SYNTHETIC_PREFLIGHT.json',toy_manifest)
    prior=Path('/home/u00134/3dgs_line/tier1/out/multiscene_foundation/training/lego/seed_1729')
    old=json.loads((prior/'manifest.json').read_text())
    provenance=[dict(path=str(p),sha256=sha256(p)) for p in [prior/'entry.json',prior/'manifest.json',prior/'checkpoints/cfg_args',Path('/home/u00134/3dgs_line/tier1/scripts/multiscene_train_entry.py'),Path('/home/u00134/3dgs_line/tier1/scripts/run_multiscene_training.py')]]
    atomic_json(HERE/'ACQUISITION.json',dict(schema=1,upstream_commit=source_commit,source_manifest_sha256=sha256(HERE/'SOURCE_MANIFEST.json'),prior_files=provenance,
        prior_train_count=sum(x['path'].startswith('train/') for x in old['staged_data']['files']),prior_val_diagnostic_count=sum(x['path'].startswith('val/') for x in old['staged_data']['files']),
        same_recipe=dict(seed=1729,iterations=30000,resolution=-1,SH_degree=3,white_background=True,loss='0.8L1+0.2(1-SSIM)',default_densification=True,initialization='official random100k'),
        necessary_differences=['all100 TRAIN versus prior86 TRAIN','no VAL/TEST metadata or pixels; eval=False and strict TRAIN-only reader','in-sample fixed TRAIN diagnostic only','I/O hooks for atomic PLY/snapshot/status+exact RNG resume; GUI off; TensorBoard replaced by explicit scalar log'],
        support_files=support,binaries=binaries,scenes=manifests))
    print(json.dumps({'scenes':list(manifests),'source_files':len(records),'binary_files':len(binaries),'source_manifest_sha256':sha256(HERE/'SOURCE_MANIFEST.json')}))

if __name__=='__main__':main()
