import numpy as np
import torch
from adapter import render,alpha,support,effective_colors,make_camera,parameter_derivative,perturb,numpy_image
from evidence import signed_map,profile_vector
from evaluation import centered_identity

def identity(m,c,s,baseline=None,a=None):
    baseline=numpy_image(render(m,c)) if baseline is None else baseline
    a=alpha(m,c).detach().cpu().numpy() if a is None else a
    sm=signed_map(s,a.shape);dw=support(m,c,[sm])[:,0].astype(np.float64)
    colors=effective_colors(m,c).detach().cpu().numpy().astype(np.float64)
    u=np.asarray(s.get('u') or [1.,0,0]);center=np.asarray(s.get('c_star',[.5]*3))
    dtbg=float((sm*(1-a)).sum(dtype=np.float64))
    terms,bg,wi=centered_identity(dw,colors,dtbg,np.ones(3),u,center)
    measured=float(((baseline*sm[...,None]).sum((0,1)))@u)
    summation=float(terms.sum(dtype=np.float64)+bg)
    absolute=float(np.abs(terms).sum(dtype=np.float64))
    record=dict(sample_id=s['id'],native_E=measured,signed_sum=summation,
                primitive_signed_sum=float(terms.sum()),background_term=bg,background_delta_T=dtbg,
                total_weight_identity_residual=wi,reconstruction_abs_residual=abs(summation-measured),
                absolute_sum=absolute,positive_sum=float(terms[terms>0].sum()),negative_sum=float(terms[terms<0].sum()),
                cancellation=1-abs(float(terms.sum()))/max(absolute,1e-20),
                c_star=center.tolist(),u=u.tolist(),precision='float32 native atomic backward, float64 streamed accounting',
                nonzero_terms=int((dw!=0).sum()),no_NxHxW_tensor=True)
    return record,dw,terms

def native_calibration(m,view,cfg):
    camera=make_camera(view['entry']['camera']);shape=(camera.image_height,camera.image_width)
    with torch.no_grad():
        baseline=numpy_image(render(m,camera));repeat=numpy_image(render(m,camera));python=numpy_image(render(m,camera,python_sh=True))
        override=numpy_image(render(m,camera,effective_colors(m,camera)))
        a=alpha(m,camera).cpu().numpy()
    total=support(m,camera,[np.ones(shape,np.float32)])[:,0].astype(float)
    samples=view['reference']['samples'];s=samples[0] if samples else dict(id='calibration',center=[shape[1]/2,shape[0]/2],normal=[1,0],radius=12,samples=97,u=[1,0,0],c_star=[.5]*3)
    signed,_,_=identity(m,camera,s,baseline,a)
    target=support(m,camera,[np.abs(signed_map(s,shape))])[:,0]
    ids=np.argsort(-target,kind='stable')[:64]
    sm=signed_map(s,shape);probe=sm[None,...]*np.array(s.get('u') or [1,0,0])[:,None,None]
    derivatives={}
    for param,direction,delta in [('dc',[.5,-.75,.25],.006),('scale',[1,-.5,.25],.006),('opacity',[1.],.006)]:
        analytic=parameter_derivative(m,camera,ids,param,direction,probe)
        with torch.no_grad():
            p=numpy_image(render(perturb(m,ids,param,delta,direction),camera));q=numpy_image(render(perturb(m,ids,param,-delta,direction),camera))
            ph=numpy_image(render(perturb(m,ids,param,delta/2,direction),camera));qh=numpy_image(render(perturb(m,ids,param,-delta/2,direction),camera))
        def e(im):return float((im.transpose(2,0,1)*probe).sum())
        fd=(e(p)-e(q))/(2*delta);half=(e(ph)-e(qh))/delta
        derivatives[param]=dict(native_parameter_derivative=analytic,finite_difference=fd,half_delta_fd=half,
             abs_residual=abs(fd-analytic),half_abs_residual=abs(half-analytic),parameter='opacity_logit' if param=='opacity' else param,
             includes_chain_rule=True,branch_changes_possible=True)
    raw=effective_colors(m,camera,unclamped=True).detach().cpu().numpy()
    noise=float(np.max(np.abs(baseline-repeat)));action_min=max(cfg['minimum_action_floor'],noise*cfg['noise_multiplier'])
    result=dict(noise_max_abs=noise,absolute_action_minimum=action_min,outside_rms_budget=cfg['outside_rms_budget'],
         flat_rms_budget=cfg['flat_rms_budget'],full_SH_native_vs_python_max_abs=float(np.max(np.abs(baseline-python))),
         effective_override_max_abs=float(np.max(np.abs(baseline-override))),full_alpha_mass_relative_residual=abs(total.sum()-a.sum())/max(a.sum(),1),
         signed=signed,parameter_derivatives=derivatives,clamped_channels=int((raw<0).sum()),
         native_clamp='clamp_min(SH3(direction)+0.5,0); no upper clamp',geometry_centers_frozen=True)
    result['pass']=result['full_SH_native_vs_python_max_abs']<5e-5 and result['effective_override_max_abs']<5e-5 and result['full_alpha_mass_relative_residual']<2e-5 and signed['reconstruction_abs_residual']<cfg['identity_abs_tolerance'] and abs(signed['total_weight_identity_residual'])<cfg['identity_weight_tolerance']
    return result
