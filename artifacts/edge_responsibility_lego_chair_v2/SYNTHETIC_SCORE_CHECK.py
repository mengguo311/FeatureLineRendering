"""Kernel-score/intervention appendix on the already frozen 24 constructs.

Two additional independently constructed fixtures cover truly full-frame
occlusion and large positive/negative cancellation. Existing failures remain.
All appendix models/targets/cameras/directions are frozen before ranking.
"""
import json,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'experiments/edge_responsibility_lego_chair_v2/src'))
from runtime import ART,OUT,sha,atomic_json,guard,event,unit
from adapter import C0,from_npz,make_camera,render,alpha,support,effective_colors,numpy_image,parameter_derivative,perturb
from evidence import signed_map,sample_band,profile_vector
from calibration import identity
from scoring import projected_area,match_random
from interventions import probe

def extra_models():
    out=[]
    for name in ['fully_occluded_full_frame','signed_cancellation']:
        if name=='fully_occluded_full_frame':
            xyz=np.array([[0,0,2.5],[0,0,2.55],[0,0,2.6],[0,0,2.65],[-.18,0,3],[.18,0,3.02]],np.float32)
            col=np.array([[.5]*3]*4+[[.1]*3,[.9]*3]);scales=np.array([[10,10,.02]]*4+[[.12,.3,.02]]*2)
            opacity=np.array([.99]*4+[.9,.9]);group=[4,5]
            truth='Four very wide .99 front Gaussians trigger native early stop before both rear Gaussians on every frame pixel.'
        else:
            xyz=np.array([[-.15,0,2.8],[.15,0,2.8],[-.15*3/2.8,0,3],[.15*3/2.8,0,3]],np.float32)
            col=np.array([[.1]*3,[.9]*3,[.9]*3,[.1]*3]);scales=np.array([[.10,.3,.02]]*2+[[.10*3/2.8,.3*3/2.8,.02]]*2)
            opacity=np.array([.4,.4,2/3,2/3]);group=[0,1]
            truth='Projected front dark/bright and rear bright/dark pairs have opposite signed color terms; front opacity .4 and conditional rear 2/3 match center weights.'
        n=len(xyz);path=OUT/'appendix_constructs'/f'{name}.npz';path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists():
            np.savez_compressed(path,_xyz=xyz,_features_dc=((col-.5)/C0).astype(np.float32)[:,None,:],
                 _features_rest=np.zeros((n,15,3),np.float32),_opacity=np.log(opacity/(1-opacity)).astype(np.float32)[:,None],
                 _scaling=np.log(scales).astype(np.float32),_rotation=np.tile([1,0,0,0],(n,1)).astype(np.float32))
        out.append(dict(id=name,path=str(path.relative_to(ROOT)),sha256=sha(path),group=group,
                        independent_construct_truth=truth,sample=dict(id=name,center=[63.5,63.5],normal=[1.,0.],radius=12.,samples=97,u=[1.,0,0],c_star=[.5]*3)))
    return out

def check(frozen,appendix):
    import torch
    results=[]
    for case in frozen['synthetic']['cases']:
        guard('synthetic_score/'+case['id']);start=time.perf_counter()
        assert sha(ROOT/case['model_path'])==case['model_sha256']
        m=from_npz(ROOT/case['model_path']);c=make_camera(case['camera']);s=dict(case['sample']);shape=(128,128)
        # A fixed construct color vector, independent of the score or gradients.
        if case['kind']=='material_step':u=np.array([.65,.45,.25]);center=np.array([.475,.425,.375])
        elif case['kind']=='fold_depth_step' and case['expected_visible_rgb']:u=np.ones(3);center=np.full(3,.45)
        else:u=np.array([1.,0,0]);center=np.full(3,.45)
        s['u']=(u/np.linalg.norm(u)).tolist();s['c_star']=center.tolist()
        with torch.no_grad():b0=numpy_image(render(m,c));a0=alpha(m,c).cpu().numpy()
        band=sample_band(s,shape,4);sm=signed_map(s,shape)
        mass=support(m,c,[np.ones(shape,np.float32),band,sm]).astype(float)
        col=effective_colors(m,c).cpu().numpy().astype(float)
        terms=mass[:,2]*((col-center)@np.array(s['u']))
        score={'old_relative':mass[:,1]/(mass[:,0]/np.prod(shape)+1e-8),'absolute':mass[:,1],'signed':terms}
        pool=np.flatnonzero(mass[:,0]>.001);k=min(64,len(pool))
        sets={name:np.sort(pool[np.argsort(-a[pool],kind='stable')[:k]]) for name,a in score.items()}
        ar=projected_area(m,c);vis=(mass[:,0]>.001).astype(int)
        sets['matched_random'],matching=match_random(sets['signed'],mass[:,0],ar,vis,1729)
        negative_patch=np.zeros(shape,np.float32);negative_patch[55:73,90:108]=1
        methods={}
        for method,ids in sets.items():
            probes={}
            for param in ['dc','scale']:
                delta=frozen['config']['independent_'+param+'_delta'];dr=frozen['config']['independent_'+param+'_direction']
                probes[param],_=probe(m,c,ids,param,delta,dr,b0,a0,b0,s,band,negative_patch)
            methods[method]=dict(rows=ids.tolist(),count=len(ids),current_signed_attribution=float(terms[ids].sum()),
                 current_absolute_signed_sum=float(np.abs(terms[ids]).sum()),position_band_fraction=float(mass[ids,1].sum()/max(mass[ids,0].sum(),1e-20)),
                 independent_fullmodel_probes=probes)
        ident,_,_=identity(m,c,s,b0,a0)
        results.append(dict(id=case['id'],construct_truth=case,current_native_signed=ident,methods=methods,matching=matching,
              actual_acceptance='EMPTY_NO_STRUCTURAL_TARGET' if not case['expected_accept'] else 'POSITION_DIAGNOSTIC_ONLY_ORIGINAL_GATE_FAILED',
              forced_top64_is_comparison_only=True,truth_not_gradient_or_score_derived=True,
              group_search_wall_seconds=time.perf_counter()-start,
              native_forward_calls_per_method=12,score_methods_have_equal_kernel_budget=True,
              no_causal_advantage_claim=True))
        event('synthetic_score/'+case['id'],'COMPLETE',seconds=time.perf_counter()-start)
        del m;torch.cuda.empty_cache()
    extras=[];cam=frozen['synthetic']['cases'][0]['camera']
    for item in appendix['extra_constructs']:
        guard('native_extra/'+item['id']);m=from_npz(ROOT/item['path']);c=make_camera(cam);s=item['sample'];ids=item['group']
        with torch.no_grad():rgb=numpy_image(render(m,c));a0=alpha(m,c).cpu().numpy()
        signed,dw,terms=identity(m,c,s,rgb,a0)
        sm=signed_map(s,a0.shape);probe_map=sm[None,...]*np.array(s['u'])[:,None,None]
        derivatives={}
        for param,dr in [('dc',[.5,-.75,.25]),('scale',[1,-.5,.25]),('opacity',[1])]:
            delta=.006;pred=parameter_derivative(m,c,ids,param,dr,probe_map)
            with torch.no_grad():
                plus=numpy_image(render(perturb(m,ids,param,delta,dr),c));minus=numpy_image(render(perturb(m,ids,param,-delta,dr),c))
                ph=numpy_image(render(perturb(m,ids,param,delta/2,dr),c));mh=numpy_image(render(perturb(m,ids,param,-delta/2,dr),c))
            e=lambda im:float((im.transpose(2,0,1)*probe_map).sum())
            fd=(e(plus)-e(minus))/(2*delta);half=(e(ph)-e(mh))/delta
            derivatives[param]=dict(native_param_derivative=pred,fd=fd,half_fd=half,max_fullimage_delta=float(np.abs(plus-minus).max()),
                 fd_error=abs(pred-fd),actual_chain_rule=True,opacity_diagnostic_only=param=='opacity')
        if item['id']=='fully_occluded_full_frame':passed=all(r['max_fullimage_delta']<=1e-6 for r in derivatives.values()) and float(np.abs(dw[ids]).sum())==0
        else:passed=signed['positive_sum']>0 and signed['negative_sum']<0 and signed['cancellation']>.5
        extras.append(dict(construct=item,signed=signed,parameter_derivatives=derivatives,pass_all=passed,
                           old_failed_hidden_fixture_preserved=True))
    return dict(frames=24,records=results,additional_native_fixtures=extras,
                original_synthetic_gate_still_failed=True,does_not_replace_original_failed_cases=True,
                scoring_comparison_is_not_a_new_formal_test=True)

if __name__=='__main__':
    assert (OUT/'RUNNER_COMPLETE.json').exists()
    frozen=json.loads((ART/'INPUT_FREEZE.json').read_text())
    path=ART/'SYNTHETIC_SCORE_INPUT_FREEZE.json'
    if path.exists():
        appendix=json.loads(path.read_text());assert appendix['source_sha256']==sha(__file__)
    else:
        appendix=dict(source_sha256=sha(__file__),original_input_freeze_sha256=sha(ART/'INPUT_FREEZE.json'),
                      extra_constructs=extra_models(),existing_constructs=frozen['synthetic']['cases'],
                      fixed_independent_directions_and_amplitudes=frozen['config'],group_budget=64,
                      freezes_before_score_or_fixture_probe=True,preserves_original_gate_failures=True)
        atomic_json(path,appendix)
    unit('synthetic_kernel_score_appendix',lambda:check(frozen,appendix),sha(path))
