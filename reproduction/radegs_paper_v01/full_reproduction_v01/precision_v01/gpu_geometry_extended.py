"""GPU geometry cases fixed from real covariance audits; gated worker only."""
import json
from pathlib import Path
import numpy as np
import torch
from diff_gaussian_rasterization import GaussianRasterizationSettings,GaussianRasterizer
from eigen_probe import rotation
from geometry_precision_audit import quantities
from safety import atomic_json


def render(means,packed,rotation_camera):
    view=torch.eye(4,device='cuda');view[:3,:3]=rotation_camera
    proj=torch.zeros(4,4,device='cuda');proj[0,0]=proj[1,1]=1500/16
    proj[2,2]=100/99.99;proj[2,3]=-1/99.99;proj[3,2]=1
    settings=GaussianRasterizationSettings(image_height=32,image_width=32,tanfovx=16/1500,tanfovy=16/1500,
        bg=torch.zeros(3,device='cuda'),scale_modifier=1.,viewmatrix=view.T.contiguous(),
        projmatrix=(proj@view).T.contiguous(),sh_degree=0,campos=torch.zeros(3,device='cuda'),prefiltered=False,debug=False)
    return GaussianRasterizer(settings)(means3D=means,means2D=torch.zeros_like(means,requires_grad=True),
        opacities=torch.full((1,1),.6,device='cuda'),colors_precomp=torch.full((1,3),.3,device='cuda'),cov3D_precomp=packed*1e-4)


def main(config):
    fixtures=json.loads(Path(config['extreme_fixtures']).read_text())
    r=rotation(np.array([[.9,-.1,.2,.3]],np.float32))[0].astype(float)
    u,_,v=np.linalg.svd(r)
    cameras={'identity':np.eye(3),'rotated':u@v}
    failures=[];rows=[]
    for fixture in fixtures:
        a=np.array(fixture['matrix'],np.float32)
        for cname,c in cameras.items():
            camera=torch.tensor(c,device='cuda',dtype=torch.float32)
            means=(camera.T@torch.tensor([.01,-.008,2.],device='cuda'))[None].detach().requires_grad_()
            packed=torch.tensor(a[[0,0,0,1,1,2],[0,1,2,1,2,2]][None]/1e-4,device='cuda',requires_grad=True)
            output=render(means,packed,camera);alpha=output[4][0,9,23]
            assert .02<float(alpha)<.98,'test fixture outside supported alpha branch'
            normal=output[5][:,9,23]/alpha;depth=output[3][0,9,23]
            adj=torch.tensor([.2,-.4,.7],device='cuda')
            loss=normal@adj+.3*depth
            grads=torch.autograd.grad(loss,(means,packed))
            mm=means[0].detach().cpu().double().requires_grad_()
            pp=packed[0].detach().cpu().double().requires_grad_();p=pp*1e-4
            matrix=torch.stack([p[0],p[1],p[2],p[1],p[3],p[4],p[2],p[4],p[5]]).reshape(3,3)
            truth_eigenvalues=torch.linalg.eigvalsh(matrix)
            assert float(truth_eigenvalues.min())>1e-8
            nr,dr=quantities(mm,torch.linalg.inv(matrix),camera.cpu().double())
            refs=torch.autograd.grad(nr@adj.cpu().double()+.3*dr,(mm,pp))
            row={'iteration':fixture['iteration'],'index':fixture['index'],'camera':cname,'alpha':float(alpha),
                 'normal':normal.detach().cpu().tolist(),'reference_normal':nr.detach().tolist(),
                 'normal_max_error':float((normal.cpu()-nr).abs().max()),'depth_error':abs(float(depth-dr.cuda())),
                 'eigenvalues_double':truth_eigenvalues.detach().tolist(),'gradients':{},'mean_x_eps_sweep':[]}
            for name,g,ref in zip(['means','scaled_covariance'],grads,refs):
                g=g[0].cpu().double()
                row['gradients'][name]={'analytic':g.tolist(),'oracle':ref.tolist(),'max_abs_error':float((g-ref).abs().max())}
                if not torch.allclose(g,ref,rtol=.003,atol=.001):failures.append([fixture['index'],cname,name])
            for eps in [1e-3,3e-4,1e-4,3e-5,1e-5]:
                vals=[];aa=[]
                for sign in [-1,1]:
                    m=means.detach().clone();m[0,0]+=sign*eps
                    oo=render(m,packed.detach(),camera);av=oo[4][0,9,23];nn=oo[5][:,9,23]/av
                    vals.append(float(nn@adj+.3*oo[3][0,9,23]));aa.append(float(av))
                row['mean_x_eps_sweep'].append({'eps':eps,'fd':(vals[1]-vals[0])/(2*eps),'alphas_pm':aa,
                    'analytic':float(grads[0][0,0]),'oracle':float(refs[0][0])})
            if row['normal_max_error']>.001 or row['depth_error']>1e-5:failures.append([fixture['index'],cname,'forward'])
            rows.append(row);print(json.dumps(row),flush=True)
    destination=Path(config['state_dir'])/'extended_geometry.json'
    atomic_json(destination,{'status':'FAIL' if failures else 'PASS','failures':failures,'rows':rows,
                            'optimizer_steps':0,'scope':'fixed trained covariance cases, not all inputs'})
    assert not failures,str(failures)
    return destination
