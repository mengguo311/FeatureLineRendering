"""Extra GPU gate: independent double oracle, branch checks and negative control.

Run only as a child of the authorized GPU0 shared supervisor. The unchanged
original gpu_smoke remains a separate mandatory check with its old tolerances.
"""
import argparse
import json
from pathlib import Path
import torch
from gpu_smoke import fixture,render,normal_loss,assert_close
from paper_losses import median_depth_normal
from probe_eq24 import branch
from reference_renderer import reference


def loss_parts(alpha,normal,depth,roi,nd,mix):
    return {'full':((alpha-(normal*median_depth_normal(depth,16.,12.)).sum(0,keepdim=True))*roi).sum()/roi.sum(),
            'alpha':(alpha*roi).sum()/roi.sum(),
            'normal':-(normal*nd*roi).sum()/roi.sum(),
            'depth':-(mix*median_depth_normal(depth,16.,12.)*roi).sum()/roi.sum()}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);args=ap.parse_args()
    torch.backends.cuda.matmul.allow_tf32=False
    p=fixture();o=render(p)
    q={k:v.detach().cpu().double().requires_grad_() for k,v in p.items()}
    ref=reference(q)
    roi=torch.zeros_like(o[4]);roi[:,11:13,15:17]=1
    nd=median_depth_normal(o[3],16.,12.).detach();mix=o[5].detach()
    native=loss_parts(o[4],o[5],o[3],roi,nd,mix)
    oracle=loss_parts(ref['alpha'],ref['normal'],ref['median'],roi.cpu().double(),nd.cpu().double(),mix.cpu().double())
    errors={};gradients={}
    keys=('means','scales','rotations','opacity')
    for name in native:
        gn=torch.autograd.grad(native[name],tuple(p[k] for k in keys),retain_graph=True)
        gr=torch.autograd.grad(oracle[name],tuple(q[k] for k in keys),retain_graph=True,allow_unused=True)
        gradients[name]={}
        for key,a,b in zip(keys,gn,gr):
            a=a.detach().cpu().double();b=torch.zeros_like(a) if b is None else b
            assert_close(a,b,2e-3,2e-5,'independent float64 oracle '+name+' '+key)
            errors[name+'_'+key]=float((a-b).abs().max())
            gradients[name][key]={'native':a.tolist(),'reference':b.tolist()}
    center=branch(p);branches=[]
    for key in keys:
        for idx in range(p[key].numel()):
            for sign in (-1,1):
                pp={k:v.detach().clone() for k,v in p.items()};pp[key].flatten()[idx]+=sign*.001
                b=branch(pp)
                assert b['median_ids']==center['median_ids']
                assert b['sort_order']==center['sort_order']
                assert b['alpha_min']>.02 and b['alpha_max']<.98
                assert b['T_final_min']>.01 and b['T_half_margin']>.005
                # Verify inferred selector with actual native forward depths.
                one=[render(pp,j) for j in range(3)]
                ids=torch.tensor(b['median_ids'],device='cuda')
                depths=torch.stack([v[3][:,10:14,14:18] for v in one])
                inferred=depths.gather(0,ids.unsqueeze(0)).squeeze(0)
                assert_close(render(pp)[3][:,10:14,14:18],inferred,1e-6,1e-6,'native median selector')
                branches.append({'key':key,'index':idx,'sign':sign,**b})
    # Deliberate non-differentiable median threshold. Record as negative control,
    # without using it to excuse or remove the original smooth-fixture checks.
    n={k:v.detach().clone() for k,v in p.items()}
    coefficient=float(render(n,0)[4][0,11,15]/n['opacity'][0,0])
    n['opacity'][0,0]=.5/coefficient
    center_out=render({k:v.requires_grad_() for k,v in n.items()})
    negative_gradient=torch.autograd.grad(normal_loss(center_out,roi),n['opacity'])[0][0,0]
    negative=[]
    for sign in (-1,1):
        pp={k:v.detach().clone() for k,v in n.items()};pp['opacity'][0,0]+=sign*1e-4
        oo=render(pp)
        negative.append({'sign':sign,'branch':branch(pp),'selected_depth':float(oo[3][0,11,15]),'loss':float(normal_loss(oo,roi))})
    assert negative[0]['branch']['median_ids']!=negative[1]['branch']['median_ids']
    assert abs(negative[1]['selected_depth']-negative[0]['selected_depth'])>.5
    result={'status':'PASS','independent_double_vjp_max_abs':errors,'gradients':gradients,
            'smooth_branch_checks':branches,
            'negative_control':{'purpose':'deliberate median T=0.5 discontinuity; not a differentiable oracle',
                'analytic_local_branch':float(negative_gradient),'fd_crossing':(negative[1]['loss']-negative[0]['loss'])/2e-4,
                'opacity_at_boundary':float(n['opacity'][0,0]),'sides':negative},
            'scope':'original fixture; well-conditioned covariance, identity camera, unclipped interior; not all possible scenes'}
    Path(args.output).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':'PASS','independent_double_vjp_max_abs':errors,
                      'branch_checks':len(branches),'negative_control':result['negative_control']},indent=2),flush=True)


if __name__=='__main__':main()
