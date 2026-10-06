"""Call unmodified pinned official training() with pilot parameters and seed 1729."""
import argparse
import json
import random
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from runtime import EXP, OUT, ART, atomic_json, code_identity, resource_guard, sha,assert_training_open

def train_scene(scene):
    assert_training_open(scene)
    guard=resource_guard()
    from native import install_stock
    install_stock()
    import numpy as np
    import torch
    import train as upstream
    from arguments import ModelParams,PipelineParams,OptimizationParams
    cfg=json.loads((EXP/'configs/pilot.json').read_text());settings=cfg['training']
    np.random.seed(cfg['seed']);random.seed(cfg['seed']);torch.manual_seed(cfg['seed'])
    torch.cuda.manual_seed_all(cfg['seed']);torch.set_num_threads(2)
    p=argparse.ArgumentParser();mp=ModelParams(p);op=OptimizationParams(p);pp=PipelineParams(p)
    args=p.parse_args([])
    args.source_path=str(OUT/'data'/scene/'native_train');args.model_path=str(OUT/'models'/scene)
    args.eval=True;args.sh_degree=settings['sh_degree'];args.resolution=1;args.data_device='cpu'
    for k in ('iterations','densify_from_iter','densify_until_iter','densification_interval',
              'opacity_reset_interval','position_lr_max_steps','lambda_dssim'):setattr(args,k,settings[k])
    Path(args.model_path).mkdir(parents=True,exist_ok=True)
    atomic_json(Path(args.model_path)/'actual_config.json',{'args':vars(args),'seed':cfg['seed'],
        'source':code_identity(),'guard':guard,'upstream_training_unmodified':True,
        'TEST_input_to_upstream':False,'initialization':'4096 random volume; not oracle objectwise'})
    torch.cuda.reset_peak_memory_stats();start=time.monotonic()
    upstream.training(mp.extract(args),op.extract(args),pp.extract(args),[],[settings['iterations']],
                      [settings['iterations']],None,-1)
    torch.cuda.synchronize()
    cap,step=torch.load(Path(args.model_path)/f'chkpnt{settings["iterations"]}.pth',map_location='cpu')
    result={'scene':scene,'seed':cfg['seed'],'iterations':step,'gaussians':len(cap[1]),
        'duration_seconds':time.monotonic()-start,'peak_allocated_bytes':torch.cuda.max_memory_allocated(),
        'checkpoint_sha256':sha(Path(args.model_path)/f'chkpnt{step}.pth'),'parameters':vars(args),
        'source':code_identity(),'guard':guard}
    atomic_json(EXP/f'results/manifests/train_{scene}.json',result)
    atomic_json(OUT/f'seals/train_{scene}.json',result)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('scene');train_scene(p.parse_args().scene)
