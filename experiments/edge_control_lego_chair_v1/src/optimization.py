"""Selected original-row DC deltas, bounded covariance; full rest SH stays native."""
import copy,time
import numpy as np
import torch
from adapter import C0,render,alpha,snapshot,permission_audit
from runtime import result,event,OUT

class Editor:
    def __init__(self,base,ids,cov,cfg=None):
        self.base=base;self.ids=torch.as_tensor(ids,device='cuda',dtype=torch.long);self.cov=cov;self.cfg=cfg or {'dc_display_delta_bound':.15,'scale_ratio_bound':1.2,'rotation_relative_delta_norm_bound':.08}
        self.dc_delta=torch.nn.Parameter(torch.zeros((len(ids),1,3),device='cuda'))
        self.scale_delta=torch.nn.Parameter(torch.zeros((len(ids),3),device='cuda'),requires_grad=cov)
        self.rot_delta=torch.nn.Parameter(torch.zeros((len(ids),4),device='cuda'),requires_grad=cov)
    def model(self):
        m=copy.copy(self.base)
        m._features_dc=self.base._features_dc.index_copy(0,self.ids,self.base._features_dc[self.ids]+self.dc_delta)
        if self.cov:
            m._scaling=self.base._scaling.index_copy(0,self.ids,self.base._scaling[self.ids]+self.scale_delta)
            m._rotation=self.base._rotation.index_copy(0,self.ids,self.base._rotation[self.ids]+self.rot_delta)
        return m
    def project(self):
        with torch.no_grad():
            self.dc_delta.clamp_(-self.cfg['dc_display_delta_bound']/C0,self.cfg['dc_display_delta_bound']/C0)
            self.scale_delta.clamp_(-np.log(self.cfg['scale_ratio_bound']),np.log(self.cfg['scale_ratio_bound']))
            maximum=self.base._rotation[self.ids].norm(dim=1,keepdim=True)*self.cfg['rotation_relative_delta_norm_bound']
            self.rot_delta.mul_(torch.minimum(torch.ones_like(maximum),maximum/self.rot_delta.norm(dim=1,keepdim=True).clamp_min(1e-12)))
    def regularizer(self):return self.scale_delta.square().mean()+self.rot_delta.square().mean()
    def arrays(self):return {'ids':self.ids.detach().cpu().numpy(),'dc_delta':self.dc_delta.detach().cpu().numpy(),'scale_delta':self.scale_delta.detach().cpu().numpy(),'rot_delta':self.rot_delta.detach().cpu().numpy()}
    def restore(self,path):
        a=np.load(path)
        if not np.array_equal(a['ids'],self.ids.cpu().numpy()):raise ValueError('UID mismatch')
        with torch.no_grad():
            for k in ('dc_delta','scale_delta','rot_delta'):getattr(self,k).copy_(torch.as_tensor(a[k],device='cuda'))

def coverage_loss(pred,reference,outline):
    reliable=(reference>=.99).float()
    full=(torch.relu(reference-pred).square()*reliable).sum()/reliable.sum().clamp_min(1)
    aa=((pred-reference).square()*outline).sum()/outline.sum().clamp_min(1)
    return full+aa
def masked_mean(values,mask):return (values*mask).sum()/(mask.sum().clamp_min(1)*values.shape[0])
def objective(editor,view,cfg,ordinary=False):
    m=editor.model();im=render(m,view['camera']);gt=view['gt'];band=view['band'];out=view['nonband']
    a=alpha(m,view['camera']) if editor.cov else view['alpha0']
    cov=coverage_loss(a,view['aa'],view['outline'])
    if ordinary:
        from utils.loss_utils import ssim
        rgb=.8*(im-gt).abs().mean()+.2*(1-ssim(im,gt))
    else:rgb=masked_mean((im-gt).abs(),band)+cfg['outside_weight']*masked_mean((im-view['b0']).square(),out)
    reg=editor.regularizer() if editor.cov else im.new_zeros(())
    loss=rgb+cfg['coverage_weight']*cov+cfg['cov_regularizer']*reg
    metrics={'objective':loss.item(),'rgb_objective':rgb.item(),'band_mse':masked_mean((im-gt).square(),band).item(),'whole_mse':(im-gt).square().mean().item(),'outside_damage':masked_mean((im-view['b0']).square(),out).item(),'coverage':cov.item(),'cov_reg':reg.item()}
    return loss,metrics

def optimize(scene,name,base,ids,train,cfg,cov,ordinary,time_budget=None):
    start=time.perf_counter();e=Editor(base,ids,cov,cfg)
    groups=[{'params':[e.dc_delta],'lr':cfg['color_lr']}]
    if cov:groups.extend([{'params':[e.scale_delta],'lr':cfg['scale_lr']},{'params':[e.rot_delta],'lr':cfg['rotation_lr']}])
    opt=torch.optim.Adam(groups);torch.cuda.synchronize();initialization=time.perf_counter()-start
    path=OUT/scene/'edits'/f'{name}.npz';path.parent.mkdir(parents=True,exist_ok=True)
    before=snapshot(base);logs=[];epochs=[];start=time.perf_counter();steps=0
    maximum=cfg['steps'] if time_budget is None else cfg['steps']*4
    event(f'{scene}/{name}','OPTIMIZING',cov=cov,ordinary=ordinary,count=len(ids),time_budget=time_budget)
    for step in range(maximum):
        opt.zero_grad(set_to_none=True);loss,met=objective(e,train[step%len(train)],cfg,ordinary);loss.backward();opt.step();e.project();steps=step+1
        logs.append({'step':steps,'train_key':train[step%len(train)]['key'],**met})
        if steps%len(train)==0:
            with torch.no_grad():full=[objective(e,v,cfg,ordinary)[1] for v in train]
            avg={k:float(np.mean([v[k] for v in full])) for k in full[0]}
            epochs.append({'epoch':steps//len(train),'step':steps,'full_train_mean':avg,'all_train_views':full,'seconds':time.perf_counter()-start})
            np.savez_compressed(path,**e.arrays())
            if steps%64==0:event(f'{scene}/{name}','OPTIMIZING',step=steps,full_train_objective=avg['objective'],seconds=time.perf_counter()-start)
        torch.cuda.synchronize()
        if time_budget is not None and time.perf_counter()-start>=time_budget:break
    seconds=time.perf_counter()-start
    with torch.no_grad():final=[objective(e,v,cfg,ordinary)[1] for v in train]
    np.savez_compressed(path,**e.arrays())
    audit=permission_audit(before,snapshot(e.model()),ids,cov)
    audit.update({'max_dc_display_delta':float((e.dc_delta*C0).abs().max()),'max_scale_ratio':float(e.scale_delta.exp().max()),'min_scale_ratio':float(e.scale_delta.exp().min()),'max_rot_relative_delta':float((e.rot_delta.norm(dim=1)/base._rotation[e.ids].norm(dim=1)).max()),'degree':base.active_sh_degree,'all_original_rows_preserved':True})
    if not audit['pass']:raise AssertionError('parameter freeze failure')
    record={'scene':scene,'arm':name,'steps':steps,'selected_count':len(ids),'optimizer_seconds':seconds,'initialization_seconds':initialization,'matched_time_target':time_budget,'shared_3D_parameters':True,'permissions':audit,'online_steps':logs,'full_epochs':epochs,'final_full_train':final,'edit_path':str(path),'scope':'natural original TRAIN photo supervision; DC delta with full higher SH frozen; no constant-color linear claim'}
    result(f'{scene}_{name}_optimization',record);event(f'{scene}/{name}','OPTIMIZATION_COMPLETE',steps=steps,seconds=seconds)
    return e,record
