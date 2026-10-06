import json,time
from pathlib import Path
import numpy as np
import torch
from PIL import Image
from runtime import ART,OUT,guard,event,atomic_json,result,sha,digest
from adapter import load_model,make_camera,render,alpha,support,selected_contribution,C0
from data import load_reference,REP
from evidence import build_evidence

def save_png(path,im):
    if torch.is_tensor(im):im=im.detach().cpu().numpy().transpose(1,2,0)
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    Image.fromarray(np.round(np.clip(im,0,1)*255).astype(np.uint8)).save(path)
def view_data(entry,base,seal=None):
    gt,aa=load_reference(entry,seal);e=build_evidence(gt,aa);camera=make_camera(entry['camera'])
    with torch.no_grad():b0=render(base,camera).detach();a=alpha(base,camera).detach()
    def cuda(x):return torch.as_tensor(x,device='cuda',dtype=torch.float32)
    v={'key':entry['key'],'entry':entry,'camera':camera,'gt':cuda(gt.transpose(2,0,1)),'aa':cuda(aa),'evidence':e,'band':cuda(e['internal_band']),'nonband':cuda(e['nonband']),'outline':cuda(e['outline_band']),'b0':b0,'alpha0':a}
    return v
def calibration(scene,base,view):
    from scene.cameras import Camera
    spec=view['entry']['camera'];w=np.asarray(spec['w2c'])
    stock=Camera(0,w[:3,:3].T,w[:3,3],spec['FoVx'],spec['FoVy'],view['gt'],None,view['key'],0)
    with torch.no_grad():
        ref=render(base,stock);python=render(base,view['camera'],python_sh=True)
        degree=base.active_sh_degree;base.active_sh_degree=0;sh0=render(base,view['camera']);base.active_sh_degree=degree
    maps=[np.ones(view['aa'].shape,np.float32)]*3;full=support(base,view['camera'],maps)
    rel=abs(full[:,0].sum().item()-view['alpha0'].sum().item())/max(view['alpha0'].sum().item(),1)
    rng=np.random.default_rng(1729);ids=np.sort(rng.choice(len(base.get_xyz),min(1024,len(base.get_xyz)),replace=False))
    feat=torch.zeros((len(base.get_xyz),3),device='cuda');feat[ids]=1
    with torch.no_grad():selected=selected_contribution(base,view['camera'],ids)
    mask=rng.uniform(0,1,view['aa'].shape).astype(np.float32)
    adj=support(base,view['camera'],[mask,mask,mask])[:,0]
    lhs=float((selected*torch.as_tensor(mask,device='cuda')).sum());rhs=float(adj[ids].sum())
    record={'scene':scene,'camera_hash':view['entry']['camera_hash'],'degree':degree,'stock_official_Camera_max_abs':float((ref-view['b0']).abs().max()),'stock_official_Camera_mse':float((ref-view['b0']).square().mean()),'full_SH_python_conversion_max_abs':float((python-view['b0']).abs().max()),'full_SH_vs_SH0_mse':float((sh0-view['b0']).square().mean()),'full_alpha_Jacobian_sum_relative_residual':rel,'random_full_weight_adjoint_lhs':lhs,'random_full_weight_adjoint_rhs':rhs,'random_full_weight_adjoint_relative_residual':abs(lhs-rhs)/max(abs(lhs),1),'alpha_T_topk':None,'finite_precision_tolerance':{'RGB_max_abs':.0005,'alpha_mass_relative':2e-5,'adjoint_relative':2e-5},'historical_RaDe_SH0_cache_used':False,'background':[1,1,1],'camera_intrinsics':spec['K'],'AA':'unchanged stock projected covariance 0.3 floor'}
    record['pass']=record['stock_official_Camera_max_abs']<.0005 and record['full_SH_python_conversion_max_abs']<5e-5 and rel<2e-5 and record['random_full_weight_adjoint_relative_residual']<2e-5
    result(f'{scene}_native_calibration',record)
    if not record['pass']:raise AssertionError(record)
    return record

def select(scene,base,train,cfg):
    start=time.perf_counter();n=len(base.get_xyz);total=np.zeros(n,np.float64);band=np.zeros(n,np.float64);relative=np.zeros(n,np.float64);nonedge=np.zeros(n,np.float64);outline=np.zeros(n,np.float64);vis=np.zeros(n,int);per=[]
    for view in train:
        guard(f'{scene}/selector/{view["key"]}');e=view['evidence'];shape=e['internal_band'].shape
        maps=[e['internal_band'],e['outline_band'],np.ones(shape,np.float32)]
        mass=support(base,view['camera'],maps).cpu().numpy().astype(float)
        balanced=support(base,view['camera'],e['balanced_maps']).cpu().numpy().astype(float)
        m=mass[:,2];valid=m>.001
        total+=m;band+=mass[:,0];outline+=mass[:,1];nonedge+=np.maximum(m-mass[:,0],0);vis+=valid
        # Each target segment and each scale has equal mass; own visibility
        # density controls the denominator, not absolute edge contribution.
        relative+=balanced.mean(axis=1)/(m/np.prod(shape)+1e-8)
        per.append({'key':view['key'],'band_mass':float(mass[:,0].sum()),'outline_mass':float(mass[:,1].sum()),'all_mass':float(m.sum()),'alpha_sum':float(view['alpha0'].sum()),'balanced_map_sums':[float(x.sum()) for x in e['balanced_maps']],'evidence_metadata':e['metadata']})
    score=relative/len(train)*np.sqrt(vis/len(train));score[total<cfg['selector_floor_total_pixels']]=-1
    k=min(cfg['budget_cap'],int(np.ceil(n*cfg['budget_fraction'])));ids=np.argsort(-score,kind='stable')[:k];bandids=np.argsort(-band,kind='stable')[:k]
    # Match exact count in joint visibility-count/log-mass strata.
    rng=np.random.default_rng(cfg['seed']);bins=np.minimum(15,np.maximum(0,np.floor(np.log2(total+1e-6)+8).astype(int)));strata=vis*16+bins;chosen=[]
    for stratum in np.unique(strata[ids]):
        number=int(np.sum(strata[ids]==stratum));pool=np.flatnonzero(strata==stratum);chosen.extend(rng.choice(pool,number,replace=False).tolist())
    randomids=np.asarray(chosen,int);selections={'relative':np.sort(ids),'band2d':np.sort(bandids),'random':np.sort(randomids)}
    old=json.loads((REP/'assets'/scene/'selected_ids.json').read_text());legacy=[]
    # Old ranking has same source rows, but SH0/old target definition: reference only.
    if old['checkpoint_sha256']==json.loads((ART/'DATA_FREEZE.json').read_text())['scenes'][scene]['model_sha256']:
        for name,v in old['arms'].items():
            a=np.asarray(v.get('ordered_original_ids',[]),int)
            if len(a)>=k:legacy.append({'name':name,'selected_count':k,'coverage':float(band[a[:k]].sum()/max(band.sum(),1e-20)),'scope':'same PLY SHA but old SH0/top64 edge targets; reference only, incompatible primary ranking'})
            else:legacy.append({'name':name,'available_count':len(a),'requested_count':k,'scope':'cannot compare same count; shorter archived UID list, reference only'})
    coverage={name:{'count':len(a),'band_contribution_coverage':float(band[a].sum()/max(band.sum(),1e-20)),'outline_contribution_coverage':float(outline[a].sum()/max(outline.sum(),1e-20)),'selected_nonedge_own_fraction':float(nonedge[a].sum()/max(total[a].sum(),1e-20)),'selected_total_fraction':float(total[a].sum()/max(total.sum(),1e-20)),'visibility_counts':np.bincount(vis[a],minlength=len(train)+1).tolist()} for name,a in selections.items()}
    path=OUT/scene/'selection.npz';path.parent.mkdir(parents=True,exist_ok=True);np.savez_compressed(path,total=total,band=band,outline=outline,score=score,vis=vis,**selections)
    record={'scene':scene,'budget':k,'budget_rule':'ceil(0.10*N), cap 32768, frozen before dev','selectors':coverage,'legacy_ranking_reference':legacy,'per_train_view':per,'selection_seconds':time.perf_counter()-start,'score':'mean scale/segment-balanced edge alphaT divided by own full-image alphaT density; sqrt train visibility fraction; mass floor 0.1px','nonedge_definition':'own total alphaT minus internal-band alphaT','physical_contact_claim':False,'truncation':None,'selected_original_rows':{name:a.tolist() for name,a in selections.items()},'input_npz_sha256':sha(path)}
    atomic_json(ART/f'{scene}_SELECTION_FREEZE.json',record)
    return selections,record
