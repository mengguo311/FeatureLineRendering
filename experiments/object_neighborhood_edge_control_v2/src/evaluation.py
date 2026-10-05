"""Fixed reference ROI and common profiles; surface proxies evaluation only."""
import numpy as np,torch
from scipy.ndimage import binary_erosion,binary_dilation
from PIL import Image
from runtime import OUT,ART
from data import CFG,view
from renderer_adapter import make_camera,rgb,contribution
from metrics import visible_band,evaluate_frame
from edge_profiles import linear_to_srgb
from contracts import angle_status

def prepare(manifest,m,roles=('train','dev-in','dev-out','diagnostic-supervision')):
    views=[]
    for role in roles:
        for f in manifest['roles'][role]:
            v=view(f,role);cam=make_camera(f,CFG['resolution'],CFG['camera_angle_x']);band,_=visible_band(v['instance'])
            b=torch.tensor(band,device='cuda');target=torch.tensor(v['rgb'].transpose(2,0,1),device='cuda')
            with torch.no_grad():base=rgb(m,cam).detach()
            cov=v['coverage'][...,1:].sum(-1);reliable=cov>.99
            views.append({'frame':f,'role':role,'view':v,'camera':cam,'band':b,'target':target,'base':base,'reliable':torch.tensor(reliable,device='cuda'),'coverage':torch.tensor(cov,device='cuda')})
    return views

def terms(im,alpha,v):
    b=v['band'];r=v['reliable'];target=v['target'];base=v['base']
    band=(im[:,b]-target[:,b]).abs().mean();outside=(im[:,~b]-base[:,~b]).square().mean()
    coverage=(.95-alpha[r]).clamp_min(0).square().mean()
    # Preserve AA support continuously, reference alpha may be strictly between 0 and 1.
    aa=(v['coverage']>0)&(v['coverage']<.99)
    coverage=coverage+(alpha[aa]-v['coverage'][aa]).square().mean() if aa.any() else coverage
    return {'band_l1':band,'outside_mse':outside,'coverage':coverage}

def full_objective(m,views,coverage=False):
    vals=[]
    with torch.no_grad():
        for v in views:
            im=rgb(m,v['camera']);a=rgb(m,v['camera'],torch.ones((len(m.get_xyz),3),device='cuda'))[0] if coverage else torch.zeros_like(v['band'],dtype=torch.float)
            t=terms(im,a,v);vals.append({k:float(x) for k,x in t.items() if coverage or k!='coverage'})
    return {k:float(np.mean([x[k] for x in vals])) for k in vals[0]}

def assess(m,views,labels,name,train_angles,save_images=False):
    rows=[]
    for v in views:
        f=v['frame'];base=v['base'].cpu().permute(1,2,0).numpy();im=rgb(m,v['camera']).detach().cpu().permute(1,2,0).numpy()
        diag=contribution(m,v['camera'],labels,v['band']);obj=diag['objects'].cpu().permute(1,2,0).numpy();alpha=diag['alpha'].cpu().numpy()
        met,p,q=evaluate_frame(im,v['view']['float_rgb'],v['view']['instance'],obj,alpha,diag['depth_center_proxy'].cpu().numpy(),v['view']['depth_ray_parameter'],base)
        met['depth_center_proxy_abs_error']=None
        common=[i for i,(a,b) in enumerate(zip(p,q)) if a['width_px'] is not None and b['width_px'] is not None]
        centers=[abs(p[i]['center_px']-q[i]['center_px']) for i in common if p[i]['center_px'] is not None and q[i]['center_px'] is not None]
        fg=v['view']['coverage'][...,1:].sum(-1)>.99;band=v['band'].cpu().numpy();contour=binary_dilation(v['view']['instance']>0,iterations=3)^binary_erosion(v['view']['instance']>0,iterations=3)
        met.update(boundary_position_abs_error_px=float(np.mean(centers)) if centers else None,common_profile_indices=common,common_profile_count=len(common),profile_total=len(p),band_mse_quantized=float(np.mean((im[band]-v['view']['rgb'][band])**2)),outer_contour_mse=float(np.mean((im[contour]-v['view']['float_rgb'][contour])**2)),full_foreground_holes=float(np.mean(alpha[fg]<.95)),nonband_foreground_holes=float(np.mean(alpha[fg&~band]<.95)),band_foreground_holes=float(np.mean(alpha[fg&band]<.95)),AA_coverage_mse=float(np.mean((alpha-v['view']['coverage'][...,1:].sum(-1))**2)))
        rows.append({'id':f['id'],'role':v['role'],'theta_deg':f['theta_deg'],**angle_status(f['theta_deg'],train_angles),'metrics':met,'profiles':p,'reference_profiles':q})
        if save_images and v['role'] in ('dev-in','dev-out','dev-path'):
            dest=OUT/'renders'/name/v['role'];dest.mkdir(parents=True,exist_ok=True)
            disp=np.round(linear_to_srgb(im)*255).astype(np.uint8);Image.fromarray(disp).save(dest/(f['id']+'.png'))
            if v['role']=='dev-out':
                panels=[v['view']['float_rgb'],base,im]
                full=np.concatenate([np.round(linear_to_srgb(x)*255).astype(np.uint8) for x in panels],axis=1)
                Image.fromarray(full).save(ART/'figures'/f'{name}_{f["id"]}_full.png')
                # Fixed same-camera x centre crop, never model-dependent crop.
                Image.fromarray(np.concatenate([x[160:352,220:292] for x in np.split(full,3,axis=1)],axis=1)).resize((648,576)).save(ART/'figures'/f'{name}_{f["id"]}_edge.png')
    summary={}
    for role in set(x['role'] for x in rows):
        rr=[x['metrics'] for x in rows if x['role']==role];keys=[k for k,v in rr[0].items() if isinstance(v,(int,float)) and not isinstance(v,bool)]
        summary[role]={k:float(np.mean([r[k] for r in rr if r.get(k) is not None])) if any(r.get(k) is not None for r in rr) else None for k in keys}
    return {'name':name,'per_view':rows,'summary':summary,'width_aggregation':'per-view macro mean with measurable/common profiles; refused profiles remain null','depth_note':'centre camera-z proxy versus ray parameter is not scored as surface accuracy; legacy proxy field retained only as non-comparable diagnostic'}
