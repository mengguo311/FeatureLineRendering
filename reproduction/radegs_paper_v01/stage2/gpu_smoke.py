"""GPU-only validation worker. Invoke only inside runner's exclusive-idle gate.

Baseline and variant run in separate Python processes; the baseline is never a
training arm. Finite differences hold Eq.23 weights fixed, as the paper asks.
"""
import argparse
import json
from pathlib import Path

import torch
from diff_gaussian_rasterization import GaussianRasterizer, GaussianRasterizationSettings
from paper_losses import median_depth_normal


def fixture():
    values={
        'means':[[.03,-.02,1.8],[-.07,.04,2.6],[.06,.01,3.2]],
        'scales':[[.38,.31,.08],[.48,.36,.10],[.56,.47,.12]],
        'rotations':[[1.,.08,.13,.03],[1.,-.11,.07,.02],[1.,.04,-.12,.03]],
        'opacity':[[.35],[.50],[.65]],
        'colors':[[.8,.2,.1],[.1,.7,.3],[.2,.3,.9]],
    }
    return {k:torch.tensor(v,dtype=torch.float32,device='cuda',requires_grad=True) for k,v in values.items()}


def render(params,index=None):
    projection=torch.zeros((4,4),device='cuda')
    projection[0,0]=projection[1,1]=1.
    projection[2,2]=100./99.99;projection[2,3]=-1./99.99;projection[3,2]=1.
    settings=GaussianRasterizationSettings(image_height=24,image_width=32,tanfovx=1.,tanfovy=1.,
        bg=torch.tensor([.1,.2,.3],device='cuda'),scale_modifier=1.,
        viewmatrix=torch.eye(4,device='cuda'),projmatrix=projection.T.contiguous(),
        sh_degree=0,campos=torch.zeros(3,device='cuda'),prefiltered=False,debug=False)
    p=params if index is None else {k:v[index:index+1] for k,v in params.items()}
    screenspace=torch.zeros_like(p['means'],requires_grad=True)
    return GaussianRasterizer(settings)(means3D=p['means'],means2D=screenspace,
        opacities=p['opacity'],colors_precomp=p['colors'],scales=p['scales'],
        rotations=torch.nn.functional.normalize(p['rotations'],dim=-1))


def assert_close(a,b,rtol,atol,label):
    if not torch.isfinite(a).all() or not torch.isfinite(b).all():
        raise AssertionError(label+': nonfinite')
    if not torch.allclose(a,b,rtol=rtol,atol=atol):
        raise AssertionError(f'{label}: max absolute error {float((a-b).abs().max())}, tolerances {rtol}/{atol}')


def weighted_oracle(single,weights):
    depths=torch.stack([x[3] for x in single])
    return (weights[:,None]*weights[None,:]*(depths[:,None]-depths[None,:]).square()).sum((0,1))


def normal_loss(output,roi):
    target=median_depth_normal(output[3],16.,12.)
    return ((output[4]-(output[5]*target).sum(0,keepdim=True))*roi).sum()/roi.sum()


def worker(mode,output):
    torch.manual_seed(0)
    torch.backends.cuda.matmul.allow_tf32=False
    p=fixture();out=render(p)
    rgb_alpha=out[0].square().mean()+.37*out[4].square().mean()
    gradients=torch.autograd.grad(rgb_alpha,tuple(p.values()))
    result={'outputs':[x.detach().cpu() for x in out],
            'rgb_alpha_gradients':{k:g.detach().cpu() for k,g in zip(p,gradients)},
            'mode':mode,'checks':{}}
    if mode=='variant':
        p=fixture();out=render(p);single=[render(p,i) for i in range(3)]
        trans=torch.ones_like(single[0][4]);weights=[]
        for one in single:
            weights.append((trans*one[4]).detach());trans=trans*(1-one[4])
        weights=torch.stack(weights)
        expected=weighted_oracle(single,weights)
        assert_close(out[6],expected,3e-4,8e-6,'Eq23 camera-z double sum forward')
        roi=torch.zeros_like(out[4]);roi[:,11:13,15:17]=1
        if any(float(x[4][:,10:14,14:18].min())<.02 for x in single):
            raise AssertionError('fixture crosses support boundary')
        actual_loss=(out[6]*roi).sum()/roi.sum()
        oracle_loss=(expected*roi).sum()/roi.sum()
        actual_grad=torch.autograd.grad(actual_loss,tuple(p.values()),retain_graph=True)
        oracle_grad=torch.autograd.grad(oracle_loss,tuple(p.values()),allow_unused=True)
        for key,a,b in zip(p,actual_grad,oracle_grad):
            b=torch.zeros_like(a) if b is None else b
            assert_close(a,b,2e-3,3e-4,'Eq23 native backward '+key)
        # Independent finite differences use native forward depths only and
        # frozen alpha*T from the unperturbed scene; gradients do not reuse the
        # native backward. Avoid branch/culling boundaries by the central ROI.
        errors={}
        for key in ('means','scales','rotations','opacity'):
            maximum=0.
            for i in range(p[key].numel()):
                epsilon=1e-3
                vals=[]
                for sign in (-1,1):
                    pp={k:v.detach().clone() for k,v in p.items()}
                    pp[key].view(-1)[i]+=sign*epsilon
                    one=[render(pp,j) for j in range(3)]
                    vals.append((weighted_oracle(one,weights)*roi).sum()/roi.sum())
                fd=(vals[1]-vals[0])/(2*epsilon)
                analytic=actual_grad[list(p).index(key)].view(-1)[i]
                assert_close(analytic,fd,.035,.003,'Eq23 finite difference '+key+str(i))
                maximum=max(maximum,float((analytic-fd).abs()))
            errors['eq23_'+key]=maximum
        p=fixture();out=render(p)
        ln=normal_loss(out,roi)
        grads=torch.autograd.grad(ln,tuple(p.values()))
        for key in ('means','scales','rotations','opacity'):
            maximum=0.
            for i in range(p[key].numel()):
                vals=[];epsilon=1e-3
                for sign in (-1,1):
                    pp={k:v.detach().clone() for k,v in p.items()}
                    pp[key].view(-1)[i]+=sign*epsilon
                    vals.append(normal_loss(render(pp),roi))
                fd=(vals[1]-vals[0])/(2*epsilon)
                analytic=grads[list(p).index(key)].view(-1)[i]
                assert_close(analytic,fd,.05,.003,'Eq24 finite difference '+key+str(i))
                maximum=max(maximum,float((analytic-fd).abs()))
            errors['eq24_'+key]=maximum
        # GPU autograd checks of the depth-normal function itself (double).
        depth=torch.full((1,5,5),2.,dtype=torch.double,device='cuda',requires_grad=True)
        assert torch.autograd.gradcheck(lambda x:median_depth_normal(x,10.,11.),(depth,))
        result['checks']={'eq23_forward':True,'eq23_backward':True,'eq24_backward':True,
                          'median_depth_normal_gradcheck':True,'finite_difference_max_abs':errors}
    torch.cuda.synchronize()
    torch.save(result,output)
    print(json.dumps({'mode':mode,'checks':result['checks'],'output':str(output)},indent=2),flush=True)


def compare(baseline,variant,output):
    # Called inside the gated stage; data are CPU tensors.
    a=torch.load(baseline,map_location='cpu');b=torch.load(variant,map_location='cpu')
    errors={}
    for i,label in enumerate(('rgb','radii','expected_depth_sum','median_depth','alpha','blended_normal')):
        x,y=a['outputs'][i],b['outputs'][i]
        assert_close(x.float(),y.float(),1e-6,1e-6,'baseline '+label)
        errors[label]=float((x-y).abs().max())
    for k,x in a['rgb_alpha_gradients'].items():
        y=b['rgb_alpha_gradients'][k]
        assert_close(x,y,2e-4,2e-5,'baseline RGB/alpha backward '+k)
        errors['rgb_alpha_grad_'+k]=float((x-y).abs().max())
    assert b['checks'] and all(b['checks'][k] for k in ('eq23_forward','eq23_backward','eq24_backward','median_depth_normal_gradcheck'))
    Path(output).write_text(json.dumps({'status':'PASS','baseline_max_abs':errors,
                                     'paper_checks':b['checks'],'scope':'fixtures; not a proof for all inputs'},indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=['baseline','variant','compare'],required=True)
    parser.add_argument('--output',required=True);parser.add_argument('--baseline');parser.add_argument('--variant')
    args=parser.parse_args()
    if args.mode=='compare':compare(args.baseline,args.variant,args.output)
    else:worker(args.mode,args.output)
