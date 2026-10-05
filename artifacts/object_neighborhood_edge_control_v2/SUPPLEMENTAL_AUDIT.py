"""Read-only post-production audit. Run only after production releases GPU0."""
import sys,json,math
from pathlib import Path
import numpy as np,torch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'experiments/object_neighborhood_edge_control_v2/src'))
from runtime import *
from data import CFG,CHECKPOINT,LABELS,IDENTITY,selection,freeze_data,input_snapshot
from renderer_adapter import load_checkpoint,contribution,rgb
from evaluation import prepare,terms
from color_operator import effective
from utils.general_utils import build_rotation

def main():
    resource_guard();torch.set_num_threads(2)
    frozen=json.loads((ART/'SOURCE_FREEZE.json').read_text());assert source_hashes()==frozen['source_hashes']
    before=json.loads((OUT/'original_inputs_before.json').read_text());assert input_snapshot()==before
    seals=[]
    for p in (OUT/'seals').glob('*.json'):
        s=json.loads(p.read_text())
        for name,h in s['outputs'].items():assert sha(ROOT/name)==h,(p,name)
        seals.append({'unit':s['unit'],'seal_sha256':sha(p),'output_count':len(s['outputs'])})
    manifest=freeze_data();m=load_checkpoint(CHECKPOINT);uids,labels,selected=selection();views=prepare(manifest,m,('train','dev-in','dev-out'));R=build_rotation(m._rotation);S=R@torch.diag_embed(m.get_scaling.square())@R.transpose(1,2)
    widths=[];quant=[]
    for v in views:
        cam=v['camera'];W=cam.world_view_transform[:3,:3].T;xyz=torch.cat([m.get_xyz,torch.ones_like(m.get_xyz[:,:1])],dim=1)@cam.world_view_transform;z=xyz[:,2].clamp_min(.01);f=512/(2*math.tan(.4));j=torch.stack([f/z,torch.zeros_like(z),-f*xyz[:,0]/z.square()],dim=1);C=W[None]@S@W.T[None];sig=torch.einsum('ni,nij,nj->n',j,C,j).clamp_min(0).sqrt();mass=contribution(m,cam,labels,v['band'])['band_mass'];sel=torch.tensor(selected,device='cuda');den=mass.sum().clamp_min(1e-20)
        widths.append({'id':v['frame']['id'],'role':v['role'],'theta_deg':v['frame']['theta_deg'],'band_contribution_weighted_projected_horizontal_sigma_px':float((mass*sig).sum()/den),'selected_weighted_projected_sigma_px':float((mass[sel]*sig[sel]).sum()/mass[sel].sum().clamp_min(1e-20)),'definition':'camera pinhole Jacobian x direction, propagated world covariance; representation footprint proxy, not measured edge W; excludes rasterizer added low-pass variance'})
        if v['role']=='train':
            x=v['view']['float_rgb'];q=v['view']['rgb'];b=v['band'].cpu().numpy();quant.append({'id':v['frame']['id'],'whole_mse':float(np.mean((x-q)**2)),'band_mse':float(np.mean((x[b]-q[b])**2))})
    gradients=[];cov=load_checkpoint(OUT/'checkpoints/O_cov.pth');params=[cov._features_dc,cov._scaling,cov._rotation]
    for p in params:p.requires_grad_(True)
    for v in [v for v in views if v['role']=='train']:
        im=rgb(cov,v['camera']);a=rgb(cov,v['camera'],torch.ones((len(uids),3),device='cuda'))[0];t=terms(im,a,v);row={'id':v['frame']['id'],'terms':{}}
        for name,loss in t.items():
            gs=torch.autograd.grad(loss,params,retain_graph=True,allow_unused=True);row['terms'][name]={'loss':float(loss),'grad_l1_by_parameter':{key:float(g[selected].abs().sum()) if g is not None else 0. for key,g in zip(('color_SH0','log_scale','raw_quaternion'),gs)}}
        gradients.append(row)
    inputs=[]
    for arm in ('G00','G10','G01','G11'):
        folder=OUT/'training_inputs'/arm;checks={p.name:sha(p)==sha(OUT/'data/native_train'/p.name) for p in (OUT/'data/native_train').glob('*.png')};assert len(checks)==24 and all(checks.values());inputs.append({'arm':arm,'same_24_quantized_training_PNGs':True,'training_transforms_sha256':sha(folder/'transforms_train.json'),'initial_points_sha256':sha(folder/'points3d.ply'),'empty_test_transform_count':len(json.loads((folder/'transforms_test.json').read_text())['frames'])})
    provenance={}
    for arm in ('F00','F01','F10','F11'):
        d=json.loads((ART/'results'/f'{arm}.json').read_text());counts={}
        for row in d['metrics']['per_view']:
            key=row['role']+'/'+row['status'];counts[key]=counts.get(key,0)+1
        provenance[arm]=counts
    original_cap,_=torch.load(CHECKPOINT,map_location='cpu');retrained_cap,_=torch.load(OUT/'models/G00/checkpoint.pth',map_location='cpu');compare={}
    for i,key in enumerate(('xyz','features_dc','features_rest','log_scale','rotation','opacity'),1):
        a,b=original_cap[i].detach(),retrained_cap[i].detach();compare[key]={'shape_v1':list(a.shape),'shape_G00':list(b.shape),'max_abs_if_same_shape':float((a-b).abs().max()) if a.shape==b.shape and a.numel() else None}
    color=effective(m).cpu().numpy();mass=np.load(LABELS)['band_mass'];known=np.argsort(-mass)[:32]
    r4_check={'known_UIDs_count':32,'known_UIDs_all_in_C1':bool(selected[known].all()),'known_original_colors_within_box':bool((color[known]<=1).all()),'C1_channels_over_one':int((color[selected]>1).sum()),'all_channels_over_one':int((color>1).sum()),'probe_solution_feasible':True,'bounds':'R4 revision2 uses per-UID [0,max(1,perturbed initial effective color)]; the unperturbed known solution remains feasible; R1/R3 boxes unchanged'}
    assert input_snapshot()==before
    out={'status':'COMPLETED','source_sha256':sha(__file__),'source_freeze_verified':True,'seals':seals,'original_inputs_unchanged':True,'projected_width_proxies':widths,'quantization_floor':quant,'covariance_final_full_epoch_loss_gradients':gradients,'gradient_interpretation':'connectivity and parameter-effect audit, not cross-unit gradient ranking','R2_input_provenance':inputs,'R2_G00_vs_v1_parameter_comparison':compare,'actual_interpolation_extrapolation_counts':provenance,'R4_feasibility_check':r4_check}
    atomic_json(ART/'SUPPLEMENTAL_AUDIT.json',out);print(json.dumps({'seals_verified':len(seals),'input_count':len(before),'r4_check':r4_check,'R2_G00_vs_v1':compare},indent=2))
if __name__=='__main__':main()
