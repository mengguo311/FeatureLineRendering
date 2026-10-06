"""24 native Gaussian frames, with construction truth frozen before scoring."""
import time
import numpy as np
import torch
from runtime import ROOT,ART,OUT,sha,atomic_json,guard,event
from adapter import from_npz,make_camera,render,alpha,numpy_image,effective_colors,perturb,parameter_derivative
from evidence import signed_map,profile_vector,classify_contrast
from calibration import identity
from evaluation import analytic_rays
import legacy_evidence as legacy

def run(freeze):
    records=[];images=[];cfg=freeze['config']
    for case in freeze['synthetic']['cases']:
        guard('synthetic/'+case['id']);t=time.perf_counter()
        path=ROOT/case['model_path'];assert sha(path)==case['model_sha256']
        m=from_npz(path);c=make_camera(case['camera']);s=dict(case['sample'])
        with torch.no_grad():rgb=numpy_image(render(m,c));a=alpha(m,c).cpu().numpy()
        p=profile_vector(rgb,s,False);offs=np.linspace(-12,12,97)
        lo=p[offs<=-9.6].mean(0);hi=p[offs>=9.6].mean(0);delta=hi-lo
        contrast=float(np.linalg.norm(delta));s['u']=(delta/contrast).tolist() if contrast>.01 else [1,0,0]
        s['c_star']=((lo+hi)/2).tolist()
        ident,_,terms=identity(m,c,s,rgb,a);metrics=legacy.profile_metrics(rgb,[s])[0]
        decision=classify_contrast(contrast,case['expected_visible_rgb'])
        # Detail is not a structural target; instance IDs do not manufacture an RGB edge.
        accepted=decision=='clear_color_transition' and case['kind']!='texture_detail' and metrics['valid']
        truth=case['expected_accept']
        loc=abs(metrics.get('x50',99)) if metrics['valid'] else None
        presence_pass=(accepted==truth) and (not truth or (loc is not None and loc<=cfg['synthetic_localization_tolerance_px']))
        if case['kind']=='texture_detail':presence_pass=not accepted
        native_pass=ident['reconstruction_abs_residual']<cfg['identity_abs_tolerance'] and abs(ident['total_weight_identity_residual'])<cfg['identity_weight_tolerance']
        r=dict(id=case['id'],kind=case['kind'],construct_truth=case,sample=s,contrast=contrast,
               decision=decision,accepted=accepted,profile_metrics=metrics,localization_error_px=loc,
               presence_absence_pass=presence_pass,native_identity_pass=native_pass,signed=ident,
               class_name='texture_detail' if case['kind']=='texture_detail' else decision,
               seconds=time.perf_counter()-t,baseline_native_profile=p.tolist())
        records.append(r);images.append((case['id'],rgb))
        from media import save_png
        save_png(ART/'media/synthetic'/f'{case["id"]}.png',rgb)
        event('synthetic/'+case['id'],'COMPLETE',accepted=accepted,truth=truth,identity_residual=ident['reconstruction_abs_residual'])
        del m;torch.cuda.empty_cache()
    extras=[]
    for case in freeze['synthetic']['extras']:
        guard('synthetic_extra/'+case['id']);m=from_npz(ROOT/case['model_path']);c=make_camera(case['camera']);s=case['sample']
        with torch.no_grad():rgb=numpy_image(render(m,c));a=alpha(m,c).cpu().numpy();override=numpy_image(render(m,c,effective_colors(m,c)))
        ident,dw,terms=identity(m,c,s,rgb,a);ids=[0] if case['id']!='hidden' else [3,4]
        probe=signed_map(s,a.shape)[None,...]*np.array(s['u'])[:,None,None]
        responses={}
        for param,dr in [('dc',[1,0,0]),('scale',[1,1,1]),('opacity',[1])]:
            delta=.006;pred=parameter_derivative(m,c,ids,param,dr,probe)
            with torch.no_grad():
                plus=numpy_image(render(perturb(m,ids,param,delta,dr),c));minus=numpy_image(render(perturb(m,ids,param,-delta,dr),c))
                halfplus=numpy_image(render(perturb(m,ids,param,delta/2,dr),c));halfminus=numpy_image(render(perturb(m,ids,param,-delta/2,dr),c))
            calc=lambda im:float((im.transpose(2,0,1)*probe).sum())
            fd=(calc(plus)-calc(minus))/(2*delta);halffd=(calc(halfplus)-calc(halfminus))/delta
            responses[param]=dict(native_derivative=pred,fd=fd,half_fd=halffd,abs_error=abs(pred-fd),
                                   fullimage_max_delta=float(np.abs(plus-minus).max()),branch_sensitive=True)
        native_pass=ident['reconstruction_abs_residual']<3e-5 and abs(ident['total_weight_identity_residual'])<2e-5
        samepass=case['id']!='same_color_front_back' or responses['opacity']['fullimage_max_delta']<2e-5
        hiddenpass=case['id']!='hidden' or responses['dc']['fullimage_max_delta']<2e-5
        fdpass=all(abs(r['native_derivative']-r['fd'])<max(.0005,abs(r['fd'])*.3) for r in responses.values())
        extras.append(dict(id=case['id'],signed=ident,responses=responses,
                           native_override_max_abs=float(np.abs(rgb-override).max()),
                           same_color_rgb_response_pass=samepass,hidden_rgb_response_pass=hiddenpass,
                           finite_parameter_chain_rule_pass=fdpass,pass_all=native_pass and samepass and hiddenpass and fdpass,
                           clamped_channels=int((effective_colors(m,c,True)<0).sum())))
    from media import synthetic_sheet
    synthetic_sheet(images,ART/'media/synthetic_24.png')
    result=dict(frames=len(records),records=records,extras=extras,analytic=analytic_rays(),
                independent_construct_truth=True,score_derived_labels=False,all_native_renders=True,
                gate1_pass=all(r['presence_absence_pass'] and r['native_identity_pass'] for r in records) and all(r['pass_all'] for r in extras),
                sealed_files=[str(p.relative_to(ROOT)) for p in (ART/'media/synthetic').glob('*.png')]+[str((ART/'media/synthetic_24.png').relative_to(ROOT))])
    return result
