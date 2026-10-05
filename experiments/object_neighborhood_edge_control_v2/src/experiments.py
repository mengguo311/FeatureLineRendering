import json,time,random,shutil,argparse
from pathlib import Path
import numpy as np,torch
from runtime import OUT,ART,EXP,INPUT,atomic_json,sha,result,status,resource_guard
from data import CFG,CHECKPOINT,LABELS,IDENTITY,SELECTION,selection
from renderer_adapter import load_checkpoint,rgb,contribution
from color_operator import ColorOperator,effective,C0
from evaluation import prepare,assess,full_objective,terms
from utils.general_utils import build_rotation
PARAMS=('_xyz','_features_dc','_features_rest','_scaling','_rotation','_opacity')

def save_model(m,path,initial=CHECKPOINT):
    cap,step=torch.load(initial,map_location='cpu');cap=list(cap)
    for i,k in enumerate(PARAMS,1):cap[i]=getattr(m,k).detach().cpu()
    path.parent.mkdir(parents=True,exist_ok=True);tmp=Path(str(path)+'.tmp');torch.save((tuple(cap),step),tmp);tmp.replace(path)

def run_r0(manifest):
    resource_guard();m=load_checkpoint(CHECKPOINT);uids,labels,mask=selection();mask=torch.tensor(mask,device='cuda');views=prepare(manifest,m,('train','dev-in','dev-out'))
    ev=assess(m,views,labels,'R0_B0',[v['theta_deg'] for v in manifest['roles']['train']],True)
    trainmass=np.load(LABELS)['total_mass'];new=torch.tensor(trainmass<.05,device='cuda');unknown=torch.tensor(labels==-1,device='cuda')
    rows=[]
    R=build_rotation(m._rotation);var=(R[:,2,:].square()*m.get_scaling.square()).sum(1);distance=m._xyz[:,2].abs();candidate=effective(m)[mask]
    for v in views:
        d=contribution(m,v['camera'],labels,v['band']);mass=d['band_mass'];total=d['total_mass'];outside=total-mass;den=mass.sum().clamp_min(1e-20)
        rows.append({'id':v['frame']['id'],'role':v['role'],'selected_band_coverage':float(mass[mask].sum()/den),'unselected_band_fraction':float(mass[~mask].sum()/den),'newly_visible_band_fraction':float(mass[new].sum()/den),'unknown_band_fraction':float(mass[unknown].sum()/den),'selected_outside_mass_fraction':float(outside[mask].sum()/outside.sum().clamp_min(1e-20)),'selected_band_fraction_of_own_total':float(mass[mask].sum()/total[mask].sum().clamp_min(1e-20)),'oracle_center_abs_plane_distance':float((mass*distance).sum()/den),'oracle_normal_thickness':float((mass*var.sqrt()).sum()/den),'oracle_inplane_sigma_x':float((mass*(R[:,0,:].square()*m.get_scaling.square()).sum(1).sqrt()).sum()/den)})
    original={k:getattr(m,k).detach().clone() for k in PARAMS}
    with torch.no_grad():m._features_dc[mask,0,:]=(candidate.clamp(0,1)-.5)/C0
    projected=assess(m,views,labels,'R0_box_projection',[v['theta_deg'] for v in manifest['roles']['train']])
    pixelchanges=[]
    for v in views:
        im=rgb(m,v['camera']).detach();diff=(im-v['base']).abs();pixelchanges.append({'id':v['frame']['id'],'affected_pixels_gt_1e6':int((diff.max(0).values>1e-6).sum()),'max_abs':float(diff.max()),'mse':float(diff.square().mean())})
    for k in PARAMS:
        with torch.no_grad():getattr(m,k).copy_(original[k])
    base=full_objective(m,views);perturb=[];gen=torch.Generator(device='cuda');gen.manual_seed(1729)
    # Symmetric feasible directions use common band L1+outside MSE, actual native renders.
    for group,k,step in [('color','_features_dc',.01/C0),('scale','_scaling',.01),('rotation','_rotation',.01),('position','_xyz',.01*float(m.get_scaling[mask].median())),('opacity','_opacity',.01)]:
        source=original[k].clone();direction=torch.randn(source.shape,device='cuda',generator=gen);direction[~mask]=0;direction/=direction[mask].square().mean().sqrt().clamp_min(1e-20)
        center=source.clone()
        if group=='color':
            col=(center[mask]*C0+.5).clamp(0,1);center[mask]=(col-.5)/C0
            delta=direction[mask]*step*C0;limit=torch.minimum(col,1-col)
            direction[mask]*=torch.minimum(torch.ones_like(limit),limit/delta.abs().clamp_min(1e-20))
        if group=='rotation':
            center[mask]=center[mask]/torch.linalg.norm(center[mask],dim=1,keepdim=True);q=center[mask];direction[mask]-=(direction[mask]*q).sum(1,keepdim=True)*q
        vals={}
        for sign in (0,1,-1):
            change=center+sign*step*direction
            if group=='rotation':change[mask]=change[mask]/torch.linalg.norm(change[mask],dim=1,keepdim=True)
            with torch.no_grad():getattr(m,k).copy_(change)
            loss=full_objective(m,views);vals[str(sign)]={'loss':sum(loss.values()),'components':loss}
        perturb.append({'group':group,'normalized_step':.01,'parameter_step':step,'feasible_anchor':'box-projected only for color; original for other groups','rms_actual_parameter_delta':float((step*direction[mask]).square().mean().sqrt()),'losses':vals,'symmetric_difference':(vals['1']['loss']-vals['-1']['loss'])/2,'interpretation':'repair potential only, not unique physical cause'})
        with torch.no_grad():getattr(m,k).copy_(source)
    out={'status':'COMPLETED','checkpoint_sha256':sha(CHECKPOINT),'N':len(uids),'C1_count':int(mask.sum()),'color_min':float(effective(m).min()),'color_max':float(effective(m).max()),'candidate_color_min':float(candidate.min()),'candidate_color_max':float(candidate.max()),'candidate_channels_outside_box':int(((candidate<0)|(candidate>1)).sum()),'native_SH_preclamp_min':float((m._features_dc*C0+.5).min()),'fixed_contribution_rows':rows,'metrics':ev,'zero_step_box_projection':projected,'projection_pixels':pixelchanges,'common_objective_full_views':base,'perturbations':perturb,'oracle_proxy_note':'known z=0 plane; center distance and thickness are representation diagnostics only, not inferred physical surfaces','coverage_note':'selected alpha*T mass coverage, not error recall'}
    result('R0',out);return out

def fit_r1(manifest,name):
    selected=name in ('F00','F10');diag=name in ('F10','F11');m=load_checkpoint(CHECKPOINT);uids,labels,sel=selection();mask=torch.tensor(sel if selected else np.ones(len(uids),bool),device='cuda')
    allviews=prepare(manifest,m);fitviews=[v for v in allviews if v['role']=='train' or (diag and v['role']=='diagnostic-supervision')]
    op=ColorOperator(m,fitviews,mask);validation=op.validate();L=op.lipschitz();c=op.original[mask].clamp(0,1);z=c.clone();t=1.;trace=[];start=time.monotonic();best=None
    path=OUT/'checkpoints'/f'{name}.pth';tracepath=OUT/'traces'/f'{name}.jsonl';tracepath.parent.mkdir(parents=True,exist_ok=True)
    with tracepath.open('w') as log:
        for it in range(CFG['r1_iterations']):
            rr,g=op.objective_gradient(z);prev=c;c=(z-g.float()/L).clamp(0,1);tn=(1+np.sqrt(1+4*t*t))/2;z=c+(t-1)/tn*(c-prev);t=tn
            cert,gc=op.certificate(c,CFG['r1_margin_mse']);cert.update(iteration=it+1,seconds=time.monotonic()-start,lipschitz=L)
            trace.append(cert);log.write(json.dumps(cert)+'\n');log.flush()
            if best is None or cert['mse_upper']<best[0]:best=(cert['mse_upper'],c.clone(),cert)
            if (it+1)%25==0:
                status(name,'RUNNING',iteration=it+1,total=CFG['r1_iterations'],mse_upper=cert['mse_upper'],mse_lower=cert['mse_lower'],gap_mse=2*cert['gap']/op.M);op.install(best[1]);save_model(m,path)
            if 2*cert['gap']/op.M<CFG['r1_gap_tolerance']:break
    c=best[1];cert,gc=op.certificate(c,CFG['r1_margin_mse']);op.install(c);save_model(m,path)
    claim='UNDETERMINED_OPTIMIZATION' if 2*cert['gap']/op.M>=CFG['r1_gap_tolerance'] else ('NUMERICALLY_BOUNDED_UNREACHABLE' if cert['mse_lower']>CFG['r1_mse_tolerance'] else 'FEASIBLE_WITHIN_TOLERANCE' if cert['mse_upper']<=CFG['r1_mse_tolerance'] else 'UNDETERMINED_TOLERANCE')
    angles=[v['frame']['theta_deg'] for v in fitviews];ev=assess(m,allviews,labels,name,angles,True)
    out={'status':'COMPLETED','fit_roles':['train','diagnostic-supervision'] if diag else ['train'],'diagnostic_supervision':diag,'resource_arm':'all-Gaussian capacity reference, not fair-resource method' if not selected else 'fixed C1','validation':validation,'certificate':cert,'claim':claim,'iterations':len(trace),'duration_seconds':time.monotonic()-start,'checkpoint_sha256':sha(path),'trace_sha256':sha(tracepath),'trace':trace,'metrics':ev,'outside_constraint_status':'band-only; damage measured, not qualified repair','numerical_bound_note':'float32 native operator, float64 sums; fixed 3e-7 MSE downward margin; numerical certificate under tested operator tolerance, not a symbolic proof'}
    result(name,out);return out

def fit_exact_v1(manifest,iterations=800):
    # Chambolle-Pock for convex band L1 + outside MSE. Each view objective exactly mean(band L1)+mean(outside squared).
    m=load_checkpoint(CHECKPOINT);uids,labels,sel=selection();mask=torch.tensor(sel,device='cuda');views=[v for v in prepare(manifest,m) if v['role']=='train'];orig=effective(m);fixed=orig.clone();fixed[mask]=0
    with torch.no_grad():rs=[rgb(m,v['camera'],fixed).detach() for v in views]
    b=[torch.where(v['band'][None],v['target'],v['base'])-r for v,r in zip(views,rs)]
    # Objective scaling K rescales back to exact v1 normalization; identical minimizer.
    K=sum(int(v['band'].sum())*3 for v in views);a=[K/(len(views)*3*int(v['band'].sum())) for v in views];beta=[K/(len(views)*3*int((~v['band']).sum())) for v in views]
    mass=torch.zeros_like(orig)
    for v in views:
        color=torch.zeros_like(orig,requires_grad=True);im=rgb(m,v['camera'],color);mass+=torch.autograd.grad(im.sum(),color)[0]
    L=float(mass[mask].max())*1.05;step=1/np.sqrt(max(L,1));c=orig[mask].clamp(0,1);z=c.clone();ys=[torch.zeros_like(x) for x in b];trace=[];start=time.monotonic()
    for it in range(iterations):
        colors=torch.zeros_like(orig);colors[mask]=z
        with torch.no_grad():
            for i,v in enumerate(views):
                yy=ys[i]+step*(rgb(m,v['camera'],colors)-b[i]);ys[i]=torch.where(v['band'][None],yy.clamp(-a[i],a[i]),yy/(1+step/(2*beta[i])))
        grad=torch.zeros_like(c,dtype=torch.float64)
        for v,y in zip(views,ys):
            colors=torch.zeros_like(orig,requires_grad=True);im=rgb(m,v['camera'],colors);grad+=torch.autograd.grad((im*y).sum(),colors)[0][mask].double()
        prev=c;c=(c-step*grad.float()).clamp(0,1);z=2*c-prev
        if (it+1)%24==0 or it==iterations-1:
            with torch.no_grad():m._features_dc[mask,0,:]=(c-.5)/C0
            P=sum(full_objective(m,views).values());D=(-sum((bb.double()*yy.double()).sum().item()+yy[:,~v['band']].double().square().sum().item()/(4*be) for bb,yy,v,be in zip(b,ys,views,beta))+torch.minimum(grad,torch.zeros_like(grad)).sum().item())/K
            trace.append({'iteration':it+1,'exact_v1_primal':P,'dual_raw':D,'dual_margin':3e-7,'dual_lower':D-3e-7,'gap':P-D+3e-7,'seconds':time.monotonic()-start});status('C1_exact_convex','RUNNING',iteration=it+1,total=iterations)
            save_model(m,OUT/'checkpoints/C1_exact_convex.pth');atomic_json(OUT/'traces/C1_exact_convex.json',trace)
    original=load_checkpoint(INPUT/'controls/panels_high/C1_control.pth');old=full_objective(original,views)
    out={'status':'COMPLETED','objective':'per-view mean band absolute RGB to quantized train + outside MSE to B0; weight 1; box shared color; exactly v1','solver':'matrix-free Chambolle-Pock; finite-iteration convex solve, gap reported','iterations':iterations,'trace':trace,'v1_Adam_same_objective':old,'final_objective':trace[-1],'metrics':assess(m,prepare(manifest,load_checkpoint(CHECKPOINT)),labels,'C1_exact_convex',[f['theta_deg'] for f in manifest['roles']['train']]),'checkpoint_sha256':sha(OUT/'checkpoints/C1_exact_convex.pth'),'conclusion':'optimizer superiority requires sufficiently small same-objective gap; MSE arms do not prove L1 optimum'}
    result('C1_exact_convex',out);return out

def oracle_terms(m):
    R=build_rotation(m._rotation);normal_var=(R[:,2,:].square()*m.get_scaling.square()).sum(1)
    return (m._xyz[:,2]/CFG['scene_scale']).square().mean(),((normal_var-CFG['oracle_tau']**2)/CFG['scene_scale']**2).clamp_min(0).square().mean()

def train_r2(manifest,name):
    from arguments import ModelParams,PipelineParams,OptimizationParams
    from scene import Scene,GaussianModel
    from gaussian_renderer import render
    from utils.loss_utils import l1_loss,ssim
    from plyfile import PlyData,PlyElement
    surface=name in ('G10','G11');oracle=name in ('G01','G11')
    random.seed(CFG['seed']);np.random.seed(CFG['seed']);torch.manual_seed(CFG['seed']);torch.cuda.manual_seed_all(CFG['seed']);torch.set_num_threads(2)
    source=OUT/'training_inputs'/name;shutil.copytree(OUT/'data/native_train',source,dirs_exist_ok=True)
    if surface:
        rng=np.random.default_rng(CFG['seed']);xyz=np.column_stack([rng.uniform(-1,1,4096),rng.uniform(-.8,.8,4096),np.zeros(4096)]).astype(np.float32)
        verts=np.zeros(4096,dtype=[(k,'f4') for k in ('x','y','z','nx','ny','nz')]+[(k,'u1') for k in ('red','green','blue')])
        for j,k in enumerate(('x','y','z')):verts[k]=xyz[:,j]
        for k in ('red','green','blue'):verts[k]=127
        PlyData([PlyElement.describe(verts,'vertex')]).write(str(source/'points3d.ply'))
    directory=OUT/'models'/name;directory.mkdir(parents=True,exist_ok=True)
    p=argparse.ArgumentParser();mp=ModelParams(p);op=OptimizationParams(p);pp=PipelineParams(p);args=p.parse_args([])
    old=json.loads((INPUT/'models/panels_high/actual_config.json').read_text())['args']
    for k,v in old.items():setattr(args,k,v)
    args.source_path=str(source);args.model_path=str(directory);dataset=mp.extract(args);opt=op.extract(args);pipe=pp.extract(args)
    m=GaussianModel(0);scene=Scene(dataset,m);m.training_setup(opt);initial_scale=m.get_scaling.detach()
    init={'N':len(m.get_xyz),'scale_min':float(initial_scale.min()),'scale_median':float(initial_scale.median()),'scale_max':float(initial_scale.max()),'point_cloud_sha256':sha(source/'points3d.ply'),'colors':'constant 127/255; no oracle colors or Gaussian labels','regime':'uniform known z=0 panel surface; native nearest-neighbour scale' if surface else 'byte-exact original seeded random-volume point cloud; native nearest-neighbour scale'}
    trace=[];start=time.monotonic();stack=None;torch.cuda.reset_peak_memory_stats();background=torch.zeros(3,device='cuda')
    for iteration in range(1,7001):
        m.update_learning_rate(iteration)
        if iteration%1000==0:m.oneupSHdegree()
        if not stack:stack=scene.getTrainCameras().copy()
        cam=stack.pop(random.randint(0,len(stack)-1));pkg=render(cam,m,pipe,background);im=pkg['render'];target=cam.original_image.cuda();l1=l1_loss(im,target);loss=.8*l1+.2*(1-ssim(im,target));plane,thick=oracle_terms(m)
        if oracle:loss=loss+CFG['oracle_plane_weight']*plane+CFG['oracle_thickness_weight']*thick
        loss.backward()
        with torch.no_grad():
            if iteration<opt.densify_until_iter:
                vf=pkg['visibility_filter'];m.max_radii2D[vf]=torch.maximum(m.max_radii2D[vf],pkg['radii'][vf]);m.add_densification_stats(pkg['viewspace_points'],vf)
                if iteration>opt.densify_from_iter and iteration%opt.densification_interval==0:m.densify_and_prune(opt.densify_grad_threshold,.005,scene.cameras_extent,20 if iteration>opt.opacity_reset_interval else None)
                if iteration%opt.opacity_reset_interval==0:m.reset_opacity()
            if iteration<7000:m.optimizer.step();m.optimizer.zero_grad(set_to_none=True)
        if iteration%24==0 or iteration==7000:
            with torch.no_grad():
                losses=[]
                for camera in scene.getTrainCameras():
                    pic=render(camera,m,pipe,background)['render'];tar=camera.original_image.cuda();losses.append(float(.8*l1_loss(pic,tar)+.2*(1-ssim(pic,tar))))
                pl,th=oracle_terms(m)
            trace.append({'iteration':iteration,'full_train_rgb_objective':float(np.mean(losses)),'plane':float(pl),'thickness':float(th),'N':len(m.get_xyz),'seconds':time.monotonic()-start})
            if iteration%240==0 or iteration==7000:
                status(name,'RUNNING',iteration=iteration,total=7000,N=len(m.get_xyz));atomic_json(OUT/'traces'/f'{name}.json',trace)
        if iteration%1000==0:
            dest=directory/'checkpoint.pth';tmp=directory/'checkpoint.tmp';torch.save((m.capture(),iteration),tmp);tmp.replace(dest)
    torch.cuda.synchronize();duration=time.monotonic()-start;final=directory/'checkpoint.pth';count=sum(getattr(m,k).numel() for k in PARAMS)
    # Evaluate RGB/coverage without inventing true Gaussian object labels.
    views=prepare(manifest,load_checkpoint(CHECKPOINT));labels=np.full(len(m.get_xyz),-1)
    ev=assess(m,views,labels,name,[f['theta_deg'] for f in manifest['roles']['train']],True)
    out={'status':'COMPLETED','seed':CFG['seed'],'steps':7000,'SH':0,'init':init,'oracle_geometry':oracle,'oracle_source':'analytic known single plane z=0, tau=0.015 scene units, no depth proxy supervision' if oracle else None,'final_N':len(m.get_xyz),'parameters':count,'duration_seconds':duration,'peak_gpu_bytes':torch.cuda.max_memory_allocated(),'settings':{k:v for k,v in old.items() if k not in ('source_path','model_path')},'source_input_roles':['train'],'checkpoint_sha256':sha(final),'trace':trace,'metrics':ev,'label_note':'all labels unknown; segmentation/foreign contribution fields not method-quality scores','causal_limit':'if final N differs, quantity-matched confirmation required before formal causal/resource advantage'}
    result(name,out);return out

def project_parameters(m,original,mask,permission):
    allowed={'_features_dc'}|({'_scaling','_rotation'} if permission=='cov' else set())
    with torch.no_grad():
        for k in PARAMS:
            p=getattr(m,k)
            if k not in allowed:p.copy_(original[k])
            else:p[~mask]=original[k][~mask]
        c=(m._features_dc[mask]*C0+.5).clamp(0,1);m._features_dc[mask]=(c-.5)/C0
        if permission=='cov':
            m._scaling[mask]=torch.maximum(torch.minimum(m._scaling[mask],original['_scaling'][mask]+CFG['scale_log_bound']),original['_scaling'][mask]-CFG['scale_log_bound'])
            # Keep quaternion norm positive; upstream renderer normalizes rotation. Bound raw displacement, preserving original parameterization.
            q=m._rotation[mask];d=q-original['_rotation'][mask];bound=CFG['rotation_delta_bound'];d*=torch.minimum(torch.ones_like(d[:,:1]),bound/torch.linalg.norm(d,dim=1,keepdim=True).clamp_min(1e-20));m._rotation[mask]=original['_rotation'][mask]+d
            assert (torch.linalg.norm(m._rotation[mask],dim=1)>1e-6).all()

def optimize_r3(manifest,name,permission,ordinary=False,time_budget=None):
    from utils.loss_utils import l1_loss,ssim
    startprep=time.monotonic();m=load_checkpoint(CHECKPOINT);uids,labels,sel=selection();mask=torch.tensor(sel,device='cuda');views=prepare(manifest,m);train=[v for v in views if v['role']=='train']
    original={k:getattr(m,k).detach().clone() for k in PARAMS};allowed={'_features_dc'}|({'_scaling','_rotation'} if permission=='cov' else set())
    groups=[{'params':[m._features_dc],'lr':CFG['color_lr']}]
    if permission=='cov':groups += [{'params':[m._scaling],'lr':CFG['scale_lr']},{'params':[m._rotation],'lr':CFG['rotation_lr']}]
    for k in allowed:getattr(m,k).requires_grad_(True)
    opt=torch.optim.Adam(groups);prep=time.monotonic()-startprep;start=time.monotonic();trace=[];gradassert=None
    steps=CFG['r3_steps'] if time_budget is None else 10000
    for it in range(steps):
        v=train[it%len(train)];im=rgb(m,v['camera']);alpha=rgb(m,v['camera'],torch.ones((len(uids),3),device='cuda'))[0];t=terms(im,alpha,v)
        loss=(.8*l1_loss(im,v['target'])+.2*(1-ssim(im,v['target'])) if ordinary else t['band_l1']+CFG['outside_weight']*t['outside_mse'])+CFG['coverage_weight']*t['coverage']
        if permission=='cov' and gradassert is None:
            gs=torch.autograd.grad(t['coverage'],m._scaling,retain_graph=True)[0];gr=torch.autograd.grad(t['coverage'],m._rotation,retain_graph=True)[0];gradassert={'coverage_loss':float(t['coverage']),'scale_gradient_l1':float(gs[mask].abs().sum()),'rotation_gradient_l1':float(gr[mask].abs().sum())};assert gradassert['scale_gradient_l1']>1e-10,'coverage is not connected to geometry'
        opt.zero_grad(set_to_none=True);loss.backward()
        for k in allowed:getattr(m,k).grad[~mask]=0
        opt.step();project_parameters(m,original,mask,permission);torch.cuda.synchronize();elapsed=time.monotonic()-start
        if (it+1)%len(train)==0:
            full=full_objective(m,train,True);ordinaryloss=[]
            if ordinary:
                with torch.no_grad():
                    for vv in train:
                        pic=rgb(m,vv['camera']);ordinaryloss.append(float(.8*l1_loss(pic,vv['target'])+.2*(1-ssim(pic,vv['target']))))
            trace.append({'iteration':it+1,'full_train_components':full,'full_train_ordinary_rgb':float(np.mean(ordinaryloss)) if ordinary else None,'optimizer_wall_seconds':elapsed});status(name,'RUNNING',iteration=it+1,total=steps,time_budget=time_budget);save_model(m,OUT/'checkpoints'/f'{name}.pth');atomic_json(OUT/'traces'/f'{name}.json',trace)
        if time_budget is not None and elapsed>=time_budget:break
    torch.cuda.synchronize();duration=time.monotonic()-start;changes={}
    for k,o in original.items():
        if o.numel():
            assert torch.equal(getattr(m,k)[~mask],o[~mask]);changes[k]={'rows':int((getattr(m,k)!=o).reshape(len(uids),-1).any(1).sum()),'max_abs':float((getattr(m,k)-o).abs().max())}
        if k not in allowed:assert torch.equal(getattr(m,k),o)
    path=OUT/'checkpoints'/f'{name}.pth';save_model(m,path)
    out={'status':'COMPLETED','checkpoint_base_sha256':sha(CHECKPOINT),'candidate_count':int(mask.sum()),'permission':permission,'ordinary_same_permission':ordinary,'loss':'full-image 0.8 L1+0.2 SSIM + same coverage' if ordinary else 'band L1 + outside MSE + coverage','coverage':'reliable AA coverage>0.99 hinge alpha<0.95 + continuous edge AA support MSE, fixed reference ROI, opacity fixed','coverage_gradient_assertion':gradassert,'steps':it+1,'time_budget_seconds':time_budget,'optimizer_wall_seconds':duration,'preprocessing_seconds':prep,'total_seconds':duration+prep,'trace':trace,'changed':changes,'fixed_labels_sha256':sha(IDENTITY),'scale_bound_factor':[.8,1.25],'quaternion_displacement_bound':CFG['rotation_delta_bound'],'checkpoint_sha256':sha(path),'metrics':assess(m,views,labels,name,[f['theta_deg'] for f in manifest['roles']['train']],True),'scope':'original B0 only; no split, no center or opacity edits'}
    result(name,out);return out

def make_recoverable_probe(manifest):
    # Injector is separate from solver. Only injector reads original, amplitude and oracle UID record.
    m=load_checkpoint(CHECKPOINT);uids,labels,sel=selection();train=[v for v in prepare(manifest,m,('train',))]
    mass=np.load(LABELS)['band_mass'];chosen=np.argsort(-mass)[:32];path=OUT/'probe/perturbed.pth';path.parent.mkdir(parents=True,exist_ok=True)
    for v in train:
        reference=rgb(m,v['camera']).detach();dest=OUT/'probe/targets'/(v['frame']['id']+'.npy');dest.parent.mkdir(parents=True,exist_ok=True);np.save(dest,reference.cpu().numpy())
    with torch.no_grad():m._scaling[chosen]+=np.log(1.5)
    save_model(m,path)
    atomic_json(OUT/'probe/injector_oracle.json',{'UIDs':uids[chosen].tolist(),'original_checkpoint_sha256':sha(CHECKPOINT),'amplitude':1.5,'original_scale':load_checkpoint(CHECKPOINT)._scaling[chosen].detach().cpu().tolist(),'solver_forbidden_inputs':['injector_oracle.json','original_checkpoint','actual_amplitude'],'target_source':'unperturbed B0 native render, recoverable original scales exist'})
    atomic_json(OUT/'probe/known_uids.json',{'uids':uids[chosen].tolist()})
    return {'known_count':32,'perturbed_sha256':sha(path)}

def solve_probe(manifest,name,scope,cov):
    # Only perturbed checkpoint, UID set and target images enter solver; original scales/amplitude unavailable here.
    initial=OUT/'probe/perturbed.pth';m=load_checkpoint(initial);uids,labels,sel=selection()
    known=json.loads((OUT/'probe/known_uids.json').read_text())['uids'];mask=torch.tensor(sel if scope=='C1' else np.isin(uids,known) if scope=='known' else np.ones(len(uids),bool),device='cuda')
    views=prepare(manifest,m,('train',))
    for v in views:
        target=torch.tensor(np.load(OUT/'probe/targets'/(v['frame']['id']+'.npy')),device='cuda');v['target']=target;v['base']=target
    original={k:getattr(m,k).detach().clone() for k in PARAMS};params=[m._features_dc];m._features_dc.requires_grad_(True)
    if cov:m._scaling.requires_grad_(True);params.append(m._scaling)
    opt=torch.optim.Adam([{'params':[params[0]],'lr':.0025}]+([{'params':[params[1]],'lr':.001}] if cov else []));before=full_objective(m,views);trace=[];start=time.monotonic()
    for it in range(336):
        v=views[it%24];im=rgb(m,v['camera']);loss=(im[:,v['band']]-v['target'][:,v['band']]).abs().mean()+(im[:,~v['band']]-v['base'][:,~v['band']]).square().mean();opt.zero_grad(set_to_none=True);loss.backward()
        for p in params:p.grad[~mask]=0
        opt.step()
        with torch.no_grad():
            for k in PARAMS:
                p=getattr(m,k)
                if k not in ('_features_dc','_scaling') or (k=='_scaling' and not cov):p.copy_(original[k])
                else:p[~mask]=original[k][~mask]
            colors=(m._features_dc[mask]*C0+.5).clamp(0,1);m._features_dc[mask]=(colors-.5)/C0
            if cov:m._scaling[mask]=torch.maximum(torch.minimum(m._scaling[mask],original['_scaling'][mask]+np.log(2)),original['_scaling'][mask]-np.log(2))
        if (it+1)%24==0:trace.append({'iteration':it+1,'full_train':full_objective(m,views),'seconds':time.monotonic()-start});status(name,'RUNNING',iteration=it+1,total=336);atomic_json(OUT/'traces'/f'{name}.json',trace)
    final=full_objective(m,views);save_model(m,OUT/'checkpoints'/f'{name}.pth',initial)
    out={'status':'COMPLETED','scope':scope,'permission':'color+scale' if cov else 'color','steps':336,'before':before,'after':final,'relative_improvement':1-sum(final.values())/max(sum(before.values()),1e-20),'perturb_valid':sum(before.values())>1e-5,'duration_seconds':time.monotonic()-start,'trace':trace,'solver_read_original_parameters':False,'solver_read_amplitude':False,'capacity_reference':scope=='all','interpretation':'controlled recoverability only, not natural-error cause; finite short optimizer budget, failure does not establish unattainability'}
    result(name,out);return out

def fit_band_outside(manifest,source_name,name):
    # Conditional matched band-MSE + outside-MSE follow-up. Same colors, views, weights and fixed contributions.
    m=load_checkpoint(OUT/'checkpoints'/f'{source_name}.pth');uids,labels,sel=selection();mask=torch.tensor(sel if source_name in ('F00','F10') else np.ones(len(uids),bool),device='cuda')
    views=prepare(manifest,load_checkpoint(CHECKPOINT));fit=[v for v in views if v['role']=='train' or (source_name in ('F10','F11') and v['role']=='diagnostic-supervision')]
    orig=effective(m);c=orig[mask].clamp(0,1);M=sum(3*int(v['band'].sum()) for v in fit)
    weights=[torch.where(v['band'],torch.tensor(M/(len(fit)*3*int(v['band'].sum())),device='cuda'),torch.tensor(M/(len(fit)*3*int((~v['band']).sum())),device='cuda')) for v in fit]
    target=[torch.where(v['band'][None],v['target'],v['base']) for v in fit]
    mass=torch.zeros_like(orig)
    for v,w in zip(fit,weights):
        color=torch.zeros_like(orig,requires_grad=True);im=rgb(m,v['camera'],color);mass+=torch.autograd.grad((im*w).sum(),color)[0]
    L=max(float(mass[mask].max())*1.05,1e-6);trace=[];start=time.monotonic();z=c.clone();t=1.
    for it in range(300):
        grad=torch.zeros_like(c,dtype=torch.float64)
        for v,w,tar in zip(fit,weights,target):
            colors=orig.clone();colors[mask]=z;colors.requires_grad_(True);im=rgb(m,v['camera'],colors);loss=.5*((im-tar).square()*w).sum();grad+=torch.autograd.grad(loss,colors)[0][mask].double()
        prev=c;c=(z-grad.float()/L).clamp(0,1);tn=(1+np.sqrt(1+4*t*t))/2;z=c+(t-1)/tn*(c-prev);t=tn
        if (it+1)%24==0 or it==299:
            with torch.no_grad():m._features_dc[mask,0,:]=(c-.5)/C0
            vals=[]
            with torch.no_grad():
                for v in fit:
                    im=rgb(m,v['camera']);vals.append({'band_mse':float((im[:,v['band']]-v['target'][:,v['band']]).square().mean()),'outside_mse':float((im[:,~v['band']]-v['base'][:,~v['band']]).square().mean())})
            trace.append({'iteration':it+1,'band_mse':float(np.mean([x['band_mse'] for x in vals])),'outside_mse':float(np.mean([x['outside_mse'] for x in vals])),'seconds':time.monotonic()-start});status(name,'RUNNING',iteration=it+1,total=300);save_model(m,OUT/'checkpoints'/f'{name}.pth');atomic_json(OUT/'traces'/f'{name}.json',trace)
    out={'status':'COMPLETED','trigger':'source arm band-only feasible upper MSE <= fixed 1e-4','source_arm':source_name,'loss':'equal-view mean band MSE + equal-view mean outside MSE to original B0','fit_roles':sorted(set(v['role'] for v in fit)),'steps':300,'trace':trace,'optimizer':'native matrix-free FISTA with nonnegative row/column mass Lipschitz bound','checkpoint_sha256':sha(OUT/'checkpoints'/f'{name}.pth'),'metrics':assess(m,views,labels,name,[v['frame']['theta_deg'] for v in fit],True),'claim':'finite feasible error only; outside constraint introduces additional coupling, no new lower-bound claim'}
    result(name,out);return out
