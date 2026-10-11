"""GPU geometry oracle in actual trained covariance range; gated runner only.

Single-Gaussian positive-definite fixture; no scene optimization or GT.
Normal/alpha is used ONLY to inspect the single Gaussian's normal, not training.
"""
import argparse
import json
import os
from pathlib import Path
import numpy as np
import torch
import torch.nn.functional as F
from diff_gaussian_rasterization import GaussianRasterizer,GaussianRasterizationSettings
from safety import atomic_json
from gpu_stages import report


def oracle(means,cov):
    x,y,z=means[0];u=x/z;v=y/z
    a,b,c,d,e,f=cov[0]*1e-4
    sigma=torch.stack([a,b,c,b,d,e,c,e,f]).reshape(3,3)
    ray=torch.stack([u,v,z*0+1]);precision=torch.linalg.solve(sigma,ray)
    normal=-F.normalize(precision,dim=0)
    zero=z*0
    ij=torch.stack([1+v*v,-u*v,-u,-u*v,1+u*u,-v,zero,zero,zero]).reshape(3,3)
    plane=ij@precision/(precision@ray)*z/(1+u*u+v*v)
    # H=W=32, f=1500, test pixel x=23,y=9.
    delta=torch.stack([1500*u+15.5-23,1500*v+15.5-9])
    depth=z+(plane[:2]*delta/1500).sum()
    return normal,depth


def render(means,cov):
    proj=torch.zeros(4,4,device='cuda');proj[0,0]=proj[1,1]=1500/16
    proj[2,2]=100/99.99;proj[2,3]=-1/99.99;proj[3,2]=1
    settings=GaussianRasterizationSettings(image_height=32,image_width=32,tanfovx=16/1500,tanfovy=16/1500,
        bg=torch.zeros(3,device='cuda'),scale_modifier=1.,viewmatrix=torch.eye(4,device='cuda'),
        projmatrix=proj.T.contiguous(),sh_degree=0,campos=torch.zeros(3,device='cuda'),prefiltered=False,debug=False)
    return GaussianRasterizer(settings)(means3D=means,means2D=torch.zeros_like(means,requires_grad=True),
        opacities=torch.full((1,1),.6,device='cuda'),colors_precomp=torch.full((1,3),.3,device='cuda'),cov3D_precomp=cov*1e-4)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--config',required=True);args=ap.parse_args()
    cfg=json.loads(Path(args.config).read_text());assert os.environ['CUDA_VISIBLE_DEVICES']==cfg['allowed_gpu_uuids'][0]
    torch.backends.cuda.matmul.allow_tf32=False
    audit=json.loads(Path(cfg['covariance_audit']).read_text())
    matrices=[np.array(audit['15000']['worst_matrix'])]
    # Fixed second covariance from the actual CPU RED, independent of outcome.
    from eigen_probe import rotation
    r=rotation(np.array([[.7,.2,-.3,.4]],np.float32))[0]
    matrices.append(r@np.diag([1e-7,4e-6,1e-5])@r.T)
    rows=[];failures=[]
    for index,a in enumerate(matrices):
        cov=torch.tensor([[a[0,0],a[0,1],a[0,2],a[1,1],a[1,2],a[2,2]]],device='cuda',dtype=torch.float32,requires_grad=True)/1e-4
        cov=cov.detach().requires_grad_();means=torch.tensor([[.01,-.008,2.]],device='cuda',requires_grad=True)
        out=render(means,cov);alpha=out[4][0,9,23]
        assert .02<float(alpha)<.98,'fixture unsupported or saturated'
        normal=out[5][:,9,23]/alpha;depth=out[3][0,9,23]
        m=means.detach().cpu().double().requires_grad_();v=cov.detach().cpu().double().requires_grad_()
        nref,dref=oracle(m,v);adj=torch.tensor([.2,-.4,.7],device='cuda')
        loss=(normal*adj).sum()+.3*depth;expected=(nref*adj.cpu().double()).sum()+.3*dref
        gradients=torch.autograd.grad(loss,(means,cov));reference=torch.autograd.grad(expected,(m,v))
        record={'fixture':index,'alpha':float(alpha),'normal':normal.detach().cpu().tolist(),'normal_oracle':nref.detach().tolist(),
            'normal_max_error':float((normal.cpu()-nref).abs().max()),'depth':float(depth),'depth_oracle':float(dref),
            'depth_error':abs(float(depth)-float(dref)),'gradients':{},'eps_sweep':[]}
        for name,g,ref in zip(['means','scaled_covariance'],gradients,reference):
            record['gradients'][name]={'analytic':g.detach().cpu().tolist(),'oracle':ref.tolist(),'max_abs_error':float((g.cpu()-ref).abs().max())}
            if not torch.allclose(g.cpu().double(),ref,rtol=.003,atol=.001):failures.append([index,name,'VJP'])
        for eps in [1e-4,3e-5,1e-5,3e-6,1e-6]:
            losses=[];normals=[];alphas=[];valid=[]
            for sign in [-1,1]:
                c=cov.detach().clone();c[0,1]+=sign*eps
                oo=render(means.detach(),c);aa=oo[4][0,9,23];nn=oo[5][:,9,23]/aa
                ll=(nn*adj).sum()+.3*oo[3][0,9,23]
                losses.append(float(ll));normals.append(nn.detach().cpu().tolist());alphas.append(float(aa))
                cc=c.detach().cpu().double()[0]*1e-4
                aa_,bb,cc_,dd,ee,ff=cc
                valid.append(float(torch.linalg.eigvalsh(torch.stack([aa_,bb,cc_,bb,dd,ee,cc_,ee,ff]).reshape(3,3)).min())>1e-8)
            record['eps_sweep'].append({'eps':eps,'fd_scaled_covariance_xy':(losses[1]-losses[0])/(2*eps),
                'analytic':float(gradients[1][0,1]),'oracle':float(reference[1][0,1]),'normals_pm':normals,'alphas_pm':alphas,'true_covariance_well_conditioned_pm':valid})
        if record['normal_max_error']>.001 or record['depth_error']>1e-5:failures.append([index,'forward'])
        rows.append(record);print(json.dumps(record),flush=True)
    output=Path(cfg['probe_output']);atomic_json(output,{'rows':rows,'failures':failures,'status':'FAIL' if failures else 'PASS','optimizer_steps':0})
    assert not failures,str(failures)
    report(cfg,'checkpoint_diagnostic',[output],{'operation':'trained-range single-Gaussian covariance oracle','optimizer_steps':0})


if __name__=='__main__':main()
