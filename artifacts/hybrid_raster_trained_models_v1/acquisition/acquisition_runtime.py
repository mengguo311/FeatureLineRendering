"""I/O-only hooks around the unchanged vanilla optimizer/loss/densification."""
import json
import os
from pathlib import Path
import random
import shutil
import time
import numpy as np
import torch
from acquisition_support import atomic_json, canonical_hash, check_resume, sha256, utc, validate_checkpoint_sidecar

MANIFEST=None
ROOT=None
START=None
LOSS=None
RESUME=None


def configure(manifest):
    global MANIFEST,ROOT,START,LOSS
    MANIFEST=manifest; ROOT=Path(manifest['directory']); START=time.monotonic()
    LOSS=(ROOT/'losses.jsonl').open('a',buffering=1)


def require_space(path,estimated_bytes):
    free=shutil.disk_usage(Path(path).parent).free
    if free < int(estimated_bytes*1.15)+2**30:
        raise RuntimeError(f"disk reserve: free={free}, estimated={estimated_bytes}, required 1GiB reserve")

def tensor_bytes(value):
    if isinstance(value,torch.Tensor): return value.numel()*value.element_size()
    if isinstance(value,dict): return sum(tensor_bytes(x) for x in value.values())
    if isinstance(value,(tuple,list)): return sum(tensor_bytes(x) for x in value)
    return 0

def save_checkpoint(gaussians,iteration,scene,viewpoint_stack,ema_loss):
    path=Path(scene.model_path)/f'chkpnt{iteration}.pth'
    if path.exists(): raise RuntimeError('refusing checkpoint overwrite: '+str(path))
    state=dict(model=gaussians.capture(),iteration=iteration,manifest_sha256=canonical_hash(MANIFEST),
               python_rng=random.getstate(),numpy_rng=np.random.get_state(),torch_rng=torch.get_rng_state(),
               cuda_rng=torch.cuda.get_rng_state_all(),train_camera_names=[c.image_name for c in scene.getTrainCameras()],viewpoint_names=[c.image_name for c in viewpoint_stack] if viewpoint_stack else [],
               ema_loss=ema_loss)
    require_space(path,tensor_bytes(state)+2**20)
    tmp=path.with_name(path.name+f'.tmp.{os.getpid()}')
    torch.save(state,tmp)
    with tmp.open('rb') as f: os.fsync(f.fileno())
    os.replace(tmp,path)
    atomic_json(path.with_suffix('.json'),dict(iteration=iteration,sha256=sha256(path),bytes=path.stat().st_size,
        manifest_sha256=canonical_hash(MANIFEST),utc=utc(),format='vanilla capture + exact RNG/viewpoint loop state'))


def load_checkpoint(path):
    global RESUME
    path=Path(path); sidecar=json.loads(path.with_suffix('.json').read_text())
    check_resume(MANIFEST,sidecar); validate_checkpoint_sidecar(path,sidecar)
    RESUME=torch.load(path)
    if RESUME['manifest_sha256']!=canonical_hash(MANIFEST): raise RuntimeError('snapshot internal identity mismatch')
    return RESUME['model'],RESUME['iteration']


def restore_loop(checkpoint,scene):
    if checkpoint is None: return None,0.0
    if RESUME is None: raise RuntimeError('missing exact resume state')
    random.setstate(RESUME['python_rng']); np.random.set_state(RESUME['numpy_rng'])
    torch.set_rng_state(RESUME['torch_rng']); torch.cuda.set_rng_state_all(RESUME['cuda_rng'])
    by_name={c.image_name:c for c in scene.getTrainCameras()}
    scene.train_cameras[1.0]=[by_name[name] for name in RESUME['train_camera_names']]
    return [by_name[name] for name in RESUME['viewpoint_names']],RESUME['ema_loss']


def atomic_scene_save(scene,iteration):
    destination=Path(scene.model_path)/'point_cloud'/f'iteration_{iteration}'
    if destination.exists(): raise RuntimeError('refusing PLY overwrite: '+str(destination))
    destination.parent.mkdir(parents=True,exist_ok=True)
    require_space(destination,scene.gaussians.get_xyz.shape[0]*248+2**20)
    temp=destination.with_name(destination.name+f'.partial.{os.getpid()}')
    scene.gaussians.save_ply(str(temp/'point_cloud.ply'))
    os.rename(temp,destination)


def report(tb_writer,iteration,Ll1,loss,l1_loss,elapsed,testing_iterations,scene,render_func,render_args):
    row=dict(iteration=iteration,l1=float(Ll1.item()),photometric_loss=float(loss.item()),cuda_iteration_ms=float(elapsed),
             gaussians=int(scene.gaussians.get_xyz.shape[0]))
    LOSS.write(json.dumps(row,sort_keys=True)+'\n')
    if iteration%100==0 or iteration==1:
        LOSS.flush()
        atomic_json(ROOT/'STATUS.json',dict(state='TRAINING',scene=MANIFEST['scene'],seed=1729,iteration=iteration,
            iterations=MANIFEST['iterations'],utc=utc(),elapsed_seconds=time.monotonic()-START,latest_loss=row,
            manifest_sha256=canonical_hash(MANIFEST)))
    if iteration in testing_iterations:
        from PIL import Image,ImageDraw
        diagnostics=ROOT/'diagnostics'/f'iteration_{iteration}'
        diagnostics.mkdir(parents=True,exist_ok=False)
        metrics=[]
        cams={cam.image_name:cam for cam in scene.getTrainCameras()}
        for index in MANIFEST['diagnostic_train_indices']:
            camera=cams[f'r_{index}']
            rendered=torch.clamp(render_func(camera,scene.gaussians,*render_args)['render'],0,1)
            reference=torch.clamp(camera.original_image.to('cuda'),0,1)
            mse=torch.mean((rendered-reference)**2)
            metric=dict(index=index,split='TRAIN',in_sample=True,generalization=False,l1=float(torch.mean(torch.abs(rendered-reference))),
                        psnr=float(-10*torch.log10(mse)),label='TRAIN in-sample fullSH RGB diagnostic; no quality gate')
            a=(reference.permute(1,2,0).cpu().numpy()*255).astype(np.uint8)
            b=(rendered.permute(1,2,0).cpu().numpy()*255).astype(np.uint8)
            canvas=Image.new('RGB',(a.shape[1]*2,a.shape[0]+40),'white')
            canvas.paste(Image.fromarray(a),(0,40));canvas.paste(Image.fromarray(b),(a.shape[1],40))
            ImageDraw.Draw(canvas).text((8,10),f"TRAIN r_{index} IN-SAMPLE SOURCE | VANILLA fullSH iter{iteration} (NOT generalization)",fill='black')
            path=diagnostics/f'train_{index:03d}.png';canvas.save(path)
            metric.update(path=str(path),sha256=sha256(path));metrics.append(metric)
        atomic_json(diagnostics/'METRICS.json',dict(scope='in-sample TRAIN photometric acquisition diagnostic only; no NPR tuning or quality gate',frames=metrics))
        torch.cuda.empty_cache()
