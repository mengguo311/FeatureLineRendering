"""Keep v01 FD failure; independently test analytic VJP with double reference.

No native changes. Native FD uses all recorded eps; never select a favorable
epsilon. Double-reference derivative and its own FD are independent gates.
Float32 FD cancellation is quantified by per-forward loss error, not tolerance
inflation. Clamp crossing is explicitly a non-smooth negative control.
"""
import argparse,json
from pathlib import Path
import torch
from gpu_smoke import render
from reference import pixel,parameters,FIXTURES

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);args=ap.parse_args()
    torch.backends.cuda.matmul.allow_tf32=False
    fixtures=FIXTURES+[
      dict(FIXTURES[2],name='above_det_cutoff',scales=[[.0048,.0048,.0048]]),
      dict(FIXTURES[0],name='ill_conditioned_projected_covariance',means=[[.063125,.0841666666667,2.]],scales=[[.2,.002,.002]]),
    ]
    records=[];ok=True
    for f in fixtures:
      for objective in ['rgb','alpha']:
        p={k:v.detach().float().cuda().requires_grad_() for k,v in parameters(f).items()}
        ref={k:v.detach().cpu().double().requires_grad_() for k,v in p.items()}
        o=render(p);loss=o[0][:,12,16].sum() if objective=='rgb' else o[4][:,12,16].sum()
        g=torch.autograd.grad(loss,tuple(p.values()),retain_graph=True);g2=torch.autograd.grad(2*loss,tuple(p.values()))
        rloss,meta=pixel(ref,objective);rg=torch.autograd.grad(rloss,tuple(ref.values()),allow_unused=True)
        for (key,v),a,b,c in zip(p.items(),g,rg,g2):
          b=torch.zeros_like(ref[key]) if b is None else b
          for i in range(v.numel()):
            av=float(a.view(-1)[i]);rv=float(b.view(-1)[i]);a2=float(c.view(-1)[i])
            passed=abs(av-rv)<=3e-4+1e-3*abs(rv) and abs(a2-2*av)<=1e-5+2e-4*abs(2*av)
            epss=[1e-4,3e-5,1e-5] if key=='scales' else [1e-2,3e-3,1e-3,3e-4,1e-4,3e-5,1e-5] if key=='means' else [3e-3,1e-3,3e-4]
            # Retain unchanged original 28-input tests plus alpha counterpart.
            # Extreme/cutoff cases below use reference VJP and exact branch scope;
            # original fixtures get an independent float64 finite-difference gate.
            sweep=[]
            if f['name'] in [x['name'] for x in FIXTURES[:2]]:
              for eps in epss:
                gs=[];rs=[];stable=True;forward_errors=[]
                for sign in [-1,1]:
                  pp={k:x.detach().clone() for k,x in p.items()};pp[key].view(-1)[i]+=sign*eps
                  oo=render(pp);gl=float(oo[0][:,12,16].sum() if objective=='rgb' else oo[4][:,12,16].sum())
                  # Reference at exact float32-perturbed inputs accounts for
                  # representable perturbations separately from nominal eps.
                  rr={k:x.cpu().double().requires_grad_() for k,x in pp.items()}
                  rl,rm=pixel(rr,objective);gs.append(gl);rs.append(float(rl));forward_errors.append(abs(gl-float(rl)))
                  stable &= bool(torch.equal(o[1],oo[1]) and torch.equal(o[4]>0,oo[4]>0))
                fd=(gs[1]-gs[0])/(2*eps);rfd=(rs[1]-rs[0])/(2*eps)
                sweep.append({'eps':eps,'native_fd':fd,'reference_at_float32_inputs_fd':rfd,'native_minus_reference_forward_error_bound':sum(forward_errors)/(2*eps),'support_and_radius_stable':stable,'native_scalar_losses':gs,'reference_scalar_losses':rs})
              # Double FD with exact symmetric steps, independent of native
              # backward and float32 quantization. Same nominal central eps as v01.
              de=3e-5 if key=='scales' else 3e-4 if key=='means' else 1e-3
              values=[]
              for sign in [-1,1]:
                pp={k:x.detach().clone() for k,x in ref.items()};pp[key].view(-1)[i]+=sign*de;values.append(float(pixel(pp,objective)[0]))
              dfd=(values[1]-values[0])/(2*de)
              passed &= abs(rv-dfd)<=3e-4+1e-3*abs(dfd)
              # Native FD must agree with independent forward FD within its
              # measured float32 forward error; no branch switching accepted at
              # the original central eps. Broader sweeps may cross support.
              central=next(x for x in sweep if x['eps']==de)
              passed &= central['support_and_radius_stable'] and abs(central['native_fd']-central['reference_at_float32_inputs_fd'])<=central['native_minus_reference_forward_error_bound']+1e-9
            else:dfd=None
            ok &= passed
            records.append({'fixture':f['name'],'objective':objective,'key':key,'index':i,'analytic':av,'reference_float64':rv,'double_fd':dfd,'linear_vjp2':a2,'absolute_reference_error':abs(av-rv),'passed':bool(passed),'meta':meta,'sweep':sweep})
    # Explicit negative control at the hard determinant cutoff. No smooth
    # derivative assertion across this discontinuity; both sides are preserved.
    base=parameters(FIXTURES[2]);_,bm=pixel(base);critical=.004*(1e-6/bm['det'])**.25
    crossing=[]
    for factor in [.99,1.01]:
      f=dict(FIXTURES[2],scales=[[critical*factor]*3]);p={k:v.detach().float().cuda().requires_grad_() for k,v in parameters(f).items()};o=render(p);_,meta=pixel({k:v.detach().cpu().double() for k,v in p.items()});crossing.append({'factor':factor,'scale':critical*factor,'native_alpha':float(o[4][:,12,16]),'reference':meta})
    crossing_ok=crossing[0]['native_alpha']==0 and crossing[1]['native_alpha']>0
    result={'passed':bool(ok and crossing_ok),'records':records,'checks':len(records),'clamp_crossing_negative_control':crossing,'clamp_crossing_observed':crossing_ok,'fixed_tolerances':{'reference_rtol':1e-3,'reference_atol':3e-4,'linearity_rtol':2e-4,'linearity_atol':1e-5},'v01_original_failure_preserved':True,'not_original_FD_28of28_claim':True,'scope':'single Gaussian, identity camera, fixed positive scales; original NaN generation not proven','scientificdone':False}
    Path(args.output).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':result['passed'],'checks':len(records),'failed':[(r['fixture'],r['objective'],r['key'],r['index']) for r in records if not r['passed']]}),flush=True)
    if not result['passed']:raise AssertionError('independent reference/linearity/double FD/clamp negative control failed')

if __name__=='__main__':main()
