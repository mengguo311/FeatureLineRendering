"""Gated, read-only real-scene gradient audit. Zero optimizer steps.

49views x two existing checkpoints. Decomposition detach is diagnostic only;
full loss and production/native implementations remain unchanged.
"""
import argparse,json,os,math
from pathlib import Path
import torch
from safety import atomic_json,sha256,verify_seal
from gpu_stages import load_scene,report
from gaussian_renderer import render
from gradient_decomposition import eq24_diagnostic_parts

def stat(g):
    x=g.detach().float();flat=x.flatten();q=torch.quantile(flat,torch.tensor([0.,.01,.5,.99,1.],device=x.device))
    return {'sum':float(x.double().sum()),'l2':float(torch.linalg.vector_norm(x)), 'positive_fraction':float((x>0).float().mean()),'negative_fraction':float((x<0).float().mean()),'quantiles':q.cpu().tolist()}

def main():
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);args=p.parse_args();c=json.loads(Path(args.config).read_text())
    assert os.environ['CUDA_VISIBLE_DEVICES']==c['allowed_gpu_uuids'][0]
    from diff_gaussian_rasterization import _C
    assert sha256(_C.__file__)==c['inputs']['candidate_native']
    parent=json.loads(Path(c['parent_config']).read_text())
    for stage in ['train','export']:assert verify_seal(Path(parent['state_dir'])/(stage+'.seal.json'),stage,parent['inputs'])
    out=Path(c['diagnostic_output'])/os.environ['RADEGS_ATTEMPT'];out.mkdir(parents=True,exist_ok=False)
    model,cameras,pipe,_=load_scene(c,c['model'],False);rows=[]
    for it in [15000,30000]:
        model.load_ply(str(Path(c['model'])/f'point_cloud/iteration_{it}/point_cloud.ply'))
        keys=['_opacity','_scaling','_rotation','_xyz'];params=[getattr(model,k) for k in keys]
        for cam in cameras:
            r=render(cam,model,pipe,torch.zeros(3,device='cuda'))
            fx=cam.image_width/(2*math.tan(cam.FoVx/2));fy=cam.image_height/(2*math.tan(cam.FoVy/2))
            parts=eq24_diagnostic_parts(r['mask'],r['normal'],r['middepth'],fx,fy)
            grads={k:torch.autograd.grad(v*5,params,retain_graph=True) for k,v in parts.items()}
            distortion=r['depth_distortion'].mean()*100
            gd=torch.autograd.grad(distortion,params)
            row={'iteration':it,'view':cam.image_name,'values':{k:float(v) for k,v in parts.items()},'Eq23_weighted':float(distortion),'gradients':{},'chain_rule_error':{}}
            for j,key in enumerate(keys):
                full=grads['full'][j];summed=sum(grads[k][j] for k in ['alpha','normal','depth'])
                assert torch.isfinite(full).all() and torch.isfinite(gd[j]).all()
                error=full-summed;relative=float(torch.linalg.vector_norm(error)/torch.linalg.vector_norm(full).clamp_min(1e-20))
                maximum=float(error.abs().max())
                row['chain_rule_error'][key]={'relative_l2':relative,'max_abs':maximum}
                assert relative<1e-4 or maximum<1e-7, row['chain_rule_error']
                row['gradients'][key]={k:stat(g[j]) for k,g in grads.items()};row['gradients'][key]['Eq23']=stat(gd[j])
                row['gradients'][key]['Eq23_Eq24_cosine']=float((gd[j]*full).sum()/(torch.linalg.vector_norm(gd[j])*torch.linalg.vector_norm(full)).clamp_min(1e-20))
            assert torch.count_nonzero(gd[0])==0,'Eq23 detached weights must not send opacity gradient'
            rows.append(row);atomic_json(out/'progress.json',{'rows':rows,'expected_rows':98,'optimizer_steps':0,'production_changed':False})
            print(json.dumps({'iteration':it,'view':cam.image_name,'Eq24':row['values']['full'],'Eq24_opacity_gradient':row['gradients']['_opacity']['full'],'chain_rule_error':row['chain_rule_error']}),flush=True)
            del r,parts,grads,gd,full,summed,error
    path=out/'gradient_audit.json';atomic_json(path,{'rows':rows,'optimizer_steps':0,'expected_rows':98,'scientificdone':False,'interpretation':'per-view instantaneous derivatives, not proof of complete optimization causality; no finite-difference across changing median branches'})
    report(c,'checkpoint_diagnostic',[path],{'views_per_checkpoint':49,'checkpoints':[15000,30000],'optimizer_steps':0,'result':str(path)})
if __name__=='__main__':main()
