#!/usr/bin/env python3
"""Strict TRAIN-only entry; run only through the guarded, traced worker."""
import argparse
import importlib
import json
import os
from pathlib import Path
import sys
from acquisition_support import atomic_json,canonical_hash,read_train_metadata,sha256,utc


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--manifest',type=Path,required=True);parser.add_argument('--resume',type=Path)
    args=parser.parse_args();manifest=json.loads(args.manifest.read_text());root=Path(manifest['directory']);source=Path(manifest['source'])
    for row in manifest['verified_files']:
        if sha256(row['path'])!=row['sha256']: raise RuntimeError('frozen file changed: '+row['path'])
    data=Path(manifest['original_data']);metadata=read_train_metadata(data)
    for row in manifest['input_files']:
        if sha256(row['path'])!=row['sha256']: raise RuntimeError('TRAIN input changed: '+row['path'])
    staged=root/'data';staged.mkdir(parents=True,exist_ok=True)
    target=staged/'transforms_train.json'
    if target.exists():
        if sha256(target)!=sha256(data/'transforms_train.json'): raise RuntimeError('staged TRAIN metadata changed')
    else: target.write_bytes((data/'transforms_train.json').read_bytes())
    train=staged/'train'
    if train.exists():
        if train.resolve()!=(data/'train').resolve(): raise RuntimeError('wrong TRAIN symlink')
    else: train.symlink_to(data/'train',target_is_directory=True)
    if (staged/'points3d.ply').exists() and not args.resume: raise RuntimeError('fresh launch refuses existing initialization PLY')
    # Only imports occur before CUDA setup; GPU ownership was checked by worker.
    sys.path[:0]=[str(source),*manifest['site']]
    import torch
    torch.cuda.init()
    repo=Path(__file__).resolve().parents[3]
    sys.path.insert(0,str(repo))
    from src.foundation import restrict_filesystem
    allowed_read=[sys.prefix,'/usr','/lib','/lib64','/etc','/proc','/sys',str(source),str(Path(__file__).parent),str(data/'train'),str(data/'transforms_train.json'),*manifest['site']]
    restrict_filesystem([p for p in allowed_read if Path(p).exists()],[str(root),'/dev'])
    def dataset_audit(event,arguments):
        if event=='open' and arguments and isinstance(arguments[0],(str,bytes,os.PathLike)):
            raw=os.fsdecode(arguments[0]);path=Path(raw)
            lowered=raw.lower()
            if any(part in ('test','val','mesh','meshes') for part in path.parts) or 'transforms_test.json' in lowered or 'transforms_val.json' in lowered:
                raise PermissionError('forbidden dataset access: '+raw)
    sys.addaudithook(dataset_audit)
    import acquisition_runtime
    acquisition_runtime.configure(manifest)
    import train as vanilla
    from argparse import ArgumentParser
    from arguments import ModelParams,OptimizationParams,PipelineParams
    parser=ArgumentParser();lp=ModelParams(parser);op=OptimizationParams(parser);pp=PipelineParams(parser)
    parsed=parser.parse_args(manifest['arguments'])
    vanilla.training_report=acquisition_runtime.report
    vanilla.Scene.save=acquisition_runtime.atomic_scene_save
    # Logger output config is inherited; TensorBoard is disabled to avoid duplicate
    # image streams. Exact scalar losses and fixed in-sample diagnostics are explicit.
    vanilla.TENSORBOARD_FOUND=False
    vanilla.safe_state(False,manifest['seed'])
    # No viewer listener is opened; this affects I/O only, not optimizer work.
    vanilla.network_gui.try_connect=lambda:None
    atomic_json(root/'RUNTIME.json',dict(started_utc=utc(),pid=os.getpid(),manifest_sha256=canonical_hash(manifest),
        torch_version=torch.__version__,cuda=torch.version.cuda,device=torch.cuda.get_device_name(0),
        diff_gaussian_rasterization=importlib.import_module('diff_gaussian_rasterization').__file__,
        simple_knn=importlib.import_module('simple_knn').__file__,cuda_visible_devices=os.environ.get('CUDA_VISIBLE_DEVICES'),
        train_camera_count=len(metadata['frames']),eval=False,test_cameras=0))
    vanilla.training(lp.extract(parsed),op.extract(parsed),pp.extract(parsed),manifest.get('testing_iterations',[7000,30000]),manifest['save_iterations'],manifest['checkpoint_iterations'],str(args.resume) if args.resume else None,-1)
    acquisition_runtime.LOSS.close()

if __name__=='__main__': main()
