import json
import time
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from runtime import EXP,OUT,atomic_json,resource_guard,sha,code_identity,assert_training_open

def extract(scene):
    assert_training_open(scene)
    guard=resource_guard()
    import numpy as np
    import torch
    from renderer_adapter import load_checkpoint,make_camera,rgb,contribution
    from data_access import config,frames,training_view
    from metrics import visible_band,profiles
    from stable_ids import Identity
    from adjacency import center_pairs,ellipsoid_pairs,SOLVER_AUDIT
    from utils.general_utils import build_rotation
    cfg=config();checkpoint=OUT/'models'/scene/f'chkpnt{cfg["training"]["iterations"]}.pth'
    m=load_checkpoint(checkpoint);N=len(m.get_xyz)
    support=torch.zeros((N,3),device='cuda');band_mass=torch.zeros(N,device='cuda');total_mass=torch.zeros(N,device='cuda')
    observed=[];reference=[];timings=[]
    for frame in frames('train'):
        view=training_view(scene,frame);cam=make_camera(frame,cfg['resolution'],cfg['camera_angle_x'])
        c=torch.zeros((N,3),device='cuda',requires_grad=True)
        im=rgb(m,cam,c)
        masks=torch.stack([torch.tensor(view['coverage'][...,k]>.99,device='cuda') for k in (1,2,0)])
        support+=torch.autograd.grad((im*masks).sum(),c)[0]
        band,_=visible_band(view['instance'],cfg['selection']['band_px'])
        diag=contribution(m,cam,np.ones(N),torch.tensor(band,device='cuda'))
        band_mass+=diag['band_mass'];total_mass+=diag['total_mass']
        observed.extend(profiles(rgb(m,cam).detach().cpu().permute(1,2,0).numpy(),view['instance']))
        reference.extend(profiles(view['rgb'],view['instance']))
    prob=(support/support.sum(1,keepdim=True).clamp_min(1e-8)).cpu().numpy()
    maxp=prob.max(1);raw=prob.argmax(1);labels=np.array([1,2,0])[raw]
    labels[maxp<cfg['selection']['label_confidence']]=-1
    mu=m.get_xyz.detach().cpu().numpy()
    # IDs assigned once at the post-training checkpoint, never used as row indices.
    ids=Identity(np.arange(N)+1729000000,labels,mu)
    directory=OUT/'controls'/scene;directory.mkdir(parents=True,exist_ok=True)
    atomic_json(directory/'identity.json',ids.as_dict())
    np.savez_compressed(directory/'fixed_labels.npz',probability=prob,confidence=maxp,
                        band_mass=band_mass.cpu().numpy(),total_mass=total_mass.cpu().numpy())
    start=time.monotonic();p0=center_pairs(mu,labels,cfg['selection']['center_radius']);t0=time.monotonic()-start
    L=(build_rotation(m._rotation).detach()@torch.diag_embed(m.get_scaling.detach())).cpu().numpy()
    start=time.monotonic();p1=ellipsoid_pairs(mu,L,labels,cfg['selection']['ellipsoid_k'],cfg['selection']['ellipsoid_epsilon']);t1=time.monotonic()-start
    mass=band_mass.cpu().numpy();visible=mass>cfg['selection']['band_mass_min']
    selections={}
    for key,pairs in (('C0',p0),('C1',p1)):
        candidates=sorted(set(j for pair in pairs for j in pair));sel=[i for i in candidates if visible[i]]
        selections[key]={'uids':ids.uid[sel].tolist(),'spatial_uids':ids.uid[candidates].tolist(),
                         'hidden_uids':ids.uid[[i for i in candidates if not visible[i]]].tolist(),
                         'relation':'Gaussian_neighborhood_proxy_not_contact',
                         'visible_contribution_recall':float(mass[sel].sum()/max(mass.sum(),1e-8)),
                         'band_fraction_mean':float(np.mean(mass[sel]/np.maximum(total_mass.cpu().numpy()[sel],1e-8))) if sel else None}
    # Match 2D-only capacity to primary C1. No surface or TEST pixels used.
    budget=len(selections['C1']['uids']);order=np.argsort(-mass);only2d=order[visible[order]][:budget]
    selections['B6']={'uids':ids.uid[only2d].tolist(),'scope':'2D training mask band only','capacity':len(only2d)}
    low_ref=all(p['width_px'] is None and p['reason']=='low_contrast' for p in reference) if reference else False
    decision='no_op_low_contrast' if low_ref else 'no_op_spatially_separated' if not budget else 'hard_edge_color_only'
    result={'scene':scene,'N':N,'selections':selections,'decision':decision,'oracle_surface_used':False,
        'label_provenance':'argmax normalized exact native training-mask contributions; uncertain <0.85 kept unknown; not Gaussian Grouping learned identities',
        'label_counts':{str(k):int((labels==k).sum()) for k in (-1,0,1,2)},
        'identity_sha256':sha(directory/'identity.json'),'fixed_labels_sha256':sha(directory/'fixed_labels.npz'),
        'initial_checkpoint_sha256':sha(checkpoint),'C0_time_seconds':t0,'C1_time_seconds':t1,
        'C1_distance_certificate_count':len(SOLVER_AUDIT),
        'C1_uncertified_decisions':sum(not x['decision_certified'] for x in SOLVER_AUDIT),
        'C1_max_distance_interval':max((x['upper']-x['lower'] for x in SOLVER_AUDIT),default=0),
        'C1_scipy_unsuccessful_but_certified':sum(not x['scipy_success'] for x in SOLVER_AUDIT),
        'source':code_identity(),'guard':guard,'observed_profiles':observed,'reference_profiles':reference,
        'diagnosis_hypotheses':['native_training_reconstruction_error'] if decision=='hard_edge_color_only' else [],
        'explicit_target':{'task':'A','source':'training_reference_RGB','target_width':'measured per-view, not threshold backprop'}}
    atomic_json(directory/'selection.json',result)
    summary={k:v for k,v in result.items() if k not in ('observed_profiles','reference_profiles','selections')}
    summary['selections']={k:{'candidate_count':len(v['uids']),**{x:y for x,y in v.items() if not x.endswith('uids')}} for k,v in selections.items()}
    atomic_json(EXP/f'results/manifests/selection_{scene}.json',summary)
    atomic_json(OUT/f'seals/selection_{scene}.json',{'output_sha256':sha(directory/'selection.json'),'result':summary})
    return result

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('scene');extract(p.parse_args().scene)
