"""Frozen-label, frozen-nondesignated, native color-only edit on checkpoint copies."""
import json
import time
import numpy as np
import torch
from pathlib import Path
from runtime import OUT,EXP,atomic_json,sha,code_identity
from renderer_adapter import load_checkpoint,make_camera,rgb
from data_access import config,frames,training_view
from metrics import visible_band,evaluate_frame

def save_edit(m,initial,ids,path):
    cap,step=torch.load(initial,map_location='cpu');cap=list(cap)
    for j,name in enumerate(('_xyz','_features_dc','_features_rest','_scaling','_rotation','_opacity'),1):
        cap[j]=getattr(m,name).detach().cpu()
    tmp=Path(str(path)+'.tmp');torch.save((tuple(cap),step),tmp);tmp.replace(path)

def optimize(scene,method,time_budget=None):
    algorithm=method.split('_time_')[0]
    cfg=config();directory=OUT/'controls'/scene
    selection=json.loads((directory/'selection.json').read_text());identity=json.loads((directory/'identity.json').read_text())
    initial=OUT/'models'/scene/f'chkpnt{cfg["training"]["iterations"]}.pth'
    m=load_checkpoint(initial);uids=np.asarray(identity['uid']);labels=np.asarray(identity['label'])
    key='B6' if algorithm=='B6' else 'C0' if algorithm=='C0_control' else 'C1'
    chosen=np.asarray(selection['selections'][key]['uids']);mask=torch.tensor(np.isin(uids,chosen),device='cuda')
    original={n:getattr(m,n).detach().clone() for n in ('_xyz','_features_dc','_features_rest','_scaling','_rotation','_opacity')}
    if algorithm=='B3_uniform':
        with torch.no_grad():m._scaling[mask]+=np.log(cfg['controls']['uniform_scale_factor'])
    no_op=algorithm=='B0' or algorithm=='reliable_no_op' or (algorithm in ('C0_control','C1_control') and selection['decision'].startswith('no_op'))
    m._features_dc.requires_grad_(not no_op)
    opt=torch.optim.Adam([m._features_dc],lr=cfg['controls']['color_lr']) if not no_op else None
    trainframes=frames('train');views=[]
    for f in trainframes:
        v=training_view(scene,f);camera=make_camera(f,cfg['resolution'],cfg['camera_angle_x'])
        band,_=visible_band(v['instance'],cfg['selection']['band_px'])
        target=torch.tensor(v['rgb'].transpose(2,0,1),device='cuda')
        with torch.no_grad():base=rgb(load_checkpoint(initial),camera).detach()
        views.append((camera,target,torch.tensor(band,device='cuda'),base))
    from utils.loss_utils import l1_loss,ssim
    trace=[];start=time.monotonic();torch.cuda.reset_peak_memory_stats()
    steps=0 if no_op else cfg['controls']['iterations']
    for it in range(steps):
        camera,target,band,base=views[it%len(views)]
        image=rgb(m,camera)
        if algorithm in ('B1','B3_uniform'):
            loss=.8*l1_loss(image,target)+.2*(1-ssim(image,target))
        else:
            # Pixels of fixed reference profiles; W is measurement only.
            loss=(image[:,band]-target[:,band]).abs().mean() if band.any() else image.sum()*0
            loss+=cfg['controls']['outside_weight']*((image[:,~band]-base[:,~band])**2).mean()
        opt.zero_grad(set_to_none=True);loss.backward()
        m._features_dc.grad[~mask]=0;opt.step()
        with torch.no_grad():
            m._features_dc[~mask]=original['_features_dc'][~mask]
            # Colour support constraint. No opacity or label update.
            c=(m._features_dc[mask]*.28209479177387814+.5).clamp(0,1)
            m._features_dc[mask]=(c-.5)/.28209479177387814
        torch.cuda.synchronize();elapsed=time.monotonic()-start
        if (it+1)%24==0:trace.append({'iteration':it+1,'seconds':elapsed,'loss':float(loss)})
        if time_budget is not None and elapsed>=time_budget:
            steps=it+1;break
    torch.cuda.synchronize();duration=time.monotonic()-start
    path=directory/f'{method}.pth';save_edit(m,initial,identity,path)
    changed={n:int((getattr(m,n).detach()!=v).reshape(len(uids),-1).any(1).sum()) for n,v in original.items() if v.numel()}
    for n,v in original.items():
        if n!='_features_dc' and n!='_scaling':assert torch.equal(getattr(m,n),v)
        if v.numel():assert torch.equal(getattr(m,n)[~mask],v[~mask])
    result={'scene':scene,'method':method,'algorithm':algorithm,'seed':cfg['seed'],'task':'A','initial_sha256':sha(initial),'output_sha256':sha(path),
        'candidate_count':int(mask.sum()),'gaussian_count':len(uids),'iterations':steps,'duration_seconds':duration,
        'peak_allocated_bytes':torch.cuda.max_memory_allocated(),'time_budget_seconds':time_budget,
        'changed_rows':changed,'labels_sha256':sha(directory/'fixed_labels.npz'),'identity_sha256':sha(directory/'identity.json'),
        'no_op':no_op,'trace':trace,'source':code_identity()}
    atomic_json(directory/f'{method}_edit.json',result)
    atomic_json(EXP/f'results/manifests/{scene}_{method}_edit.json',result)
    return result
