"""Actual original-fixture RED and scalar diagnostics; gated CUDA worker only.

Frozen intermediates below isolate VJPs for diagnosis, never change train loss.
"""
import argparse
import json
from pathlib import Path
import traceback
import torch
from gpu_smoke import fixture, render, normal_loss, worker
from paper_losses import median_depth_normal


def branch(p):
    singles=[render(p,j) for j in range(3)]
    a=torch.stack([s[4] for s in singles])
    t=torch.ones_like(a[0]);chosen=torch.full_like(t,-1,dtype=torch.long)
    before=[]
    for j in range(3):
        before.append(t)
        chosen=torch.where((t>.5)&(a[j]>=1/255),j,chosen)
        t=t*(1-a[j])
    region=(slice(None),slice(10,14),slice(14,18))
    return {'median_ids':chosen[region].cpu().tolist(),
            'alpha_min':float(a[:,:,10:14,14:18].min()),
            'alpha_max':float(a[:,:,10:14,14:18].max()),
            'T_half_margin':float((torch.stack(before)[:,:,10:14,14:18]-.5).abs().min()),
            'T_final_min':float(t[region].min()),
            'sort_order':p['means'][:,2].argsort().cpu().tolist(),
            'radii':[s[1].cpu().tolist() for s in singles]}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);args=ap.parse_args()
    outpath=Path(args.output);outpath.parent.mkdir(parents=True,exist_ok=True)
    torch.backends.cuda.matmul.allow_tf32=False
    result={'original_smoke':None,'diagnostic_detach':'component VJP isolation only; train loss unchanged'}
    try:
        worker('variant',outpath.with_suffix('.pt'))
        result['original_smoke']='PASS'
    except AssertionError as exc:
        result['original_smoke']=str(exc)
        traceback.print_exc()
    p=fixture();o=render(p);roi=torch.zeros_like(o[4]);roi[:,11:13,15:17]=1
    nd=median_depth_normal(o[3],16.,12.).detach();mix=o[5].detach()
    def components(output):
        alpha=(output[4]*roi).sum()/roi.sum()
        normal=-(output[5]*nd*roi).sum()/roi.sum()
        depth=-(mix*median_depth_normal(output[3],16.,12.)*roi).sum()/roi.sum()
        return {'full':normal_loss(output,roi),'alpha':alpha,'normal':normal,'depth':depth}
    losses=components(o)
    gradients={name:torch.autograd.grad(value,tuple(p.values()),retain_graph=True)
               for name,value in losses.items()}
    result['losses']={k:float(v) for k,v in losses.items()}
    result['branch_center']=branch(p)
    result['components']=[]
    for key in ('means','scales','rotations','opacity'):
        for idx in range(p[key].numel()):
            record={'key':key,'index':idx,'analytic':{k:float(v[list(p).index(key)].flatten()[idx]) for k,v in gradients.items()},'sweep':[]}
            for eps in (.03,.01,.003,.001,.0003,.0001,.00003):
                sides=[];branches=[]
                for sign in (-1,1):
                    pp={k:v.detach().clone() for k,v in p.items()}
                    pp[key].flatten()[idx]+=sign*eps
                    oo=render(pp)
                    sides.append({k:float(v) for k,v in components(oo).items()})
                    branches.append(branch(pp))
                fd={k:(sides[1][k]-sides[0][k])/(2*eps) for k in losses}
                record['sweep'].append({'eps':eps,'sides':sides,'fd':fd,'branches':branches,
                    'abs_error':{k:abs(record['analytic'][k]-fd[k]) for k in losses}})
            result['components'].append(record)
            print(json.dumps({'key':key,'idx':idx,'analytic':record['analytic'],
                              'fd_001':record['sweep'][3]['fd'],'error_001':record['sweep'][3]['abs_error']}),flush=True)
    outpath.write_text(json.dumps(result,indent=2)+'\n')
    print('DIAGNOSTICS_WRITTEN '+str(outpath),flush=True)
    # Real RED stays nonzero; no possible transition to training through this job.
    if result['original_smoke']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
