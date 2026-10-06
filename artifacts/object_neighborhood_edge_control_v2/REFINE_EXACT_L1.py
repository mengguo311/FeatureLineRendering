"""Same v1 convex objective with native row/column CP diagonal steps."""
import sys,json,time,os
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'experiments/object_neighborhood_edge_control_v2/src'))
def cp_norm_bound(A):
    A=np.asarray(A,float)
    if (A<0).any():raise ValueError('requires nonnegative weights')
    row=A.sum(1).clip(1e-10);col=A.sum(0).clip(1e-10);B=.99*A/np.sqrt(row[:,None]*col[None,:]);return float(np.linalg.norm(B,2)**2)
def main():
    from runtime import OUT,ART,EXP,atomic_json,sha,resource_guard,result
    freeze=json.loads((ART/'L1_REFINEMENT_FREEZE.json').read_text());assert sha(__file__)==freeze['script_sha256'];assert sha(ART/'SOURCE_FREEZE.json')==freeze['core_source_freeze_sha256']
    while True:
        state=json.loads((OUT/'REFINEMENT_STATUS.json').read_text()) if (OUT/'REFINEMENT_STATUS.json').exists() else {}
        if state.get('phase')=='COMPLETED':break
        atomic_json(OUT/'L1_REFINEMENT_STATUS.json',{'phase':'WAIT_COLOR_REFINEMENT','pid':os.getpid()});time.sleep(30)
    while True:
        try:resource_guard();break
        except RuntimeError as e:
            if 'WAIT_FOREIGN_GPU' not in str(e):raise
            time.sleep(30)
    import torch
    from data import CHECKPOINT,CFG,selection,freeze_data,input_snapshot
    from renderer_adapter import load_checkpoint,rgb
    from color_operator import effective,C0
    from evaluation import prepare,assess,full_objective
    from experiments import save_model
    torch.set_num_threads(2);before=json.loads((OUT/'original_inputs_before.json').read_text());assert input_snapshot()==before;manifest=freeze_data();name='C1_exact_convex_refined';identity={'script_sha256':sha(__file__),'source_freeze_sha256':sha(ART/'SOURCE_FREEZE.json'),'data_manifest_sha256':sha(OUT/'data_manifest.json'),'input_manifest_sha256':sha(OUT/'original_inputs_before.json'),'max_iterations':4000,'objective_gap_tolerance':1e-6}
    seal=OUT/'seals'/f'{name}.json'
    if seal.exists():
        s=json.loads(seal.read_text());assert s['identity']==identity
        for p,h in s['outputs'].items():assert sha(ROOT/p)==h
        atomic_json(OUT/'L1_REFINEMENT_STATUS.json',{'phase':'COMPLETED','verified_skip':True});return
    m=load_checkpoint(CHECKPOINT);warm=load_checkpoint(OUT/'checkpoints/C1_exact_convex.pth');uids,labels,sel=selection();mask=torch.tensor(sel,device='cuda');views=prepare(manifest,m);fit=[v for v in views if v['role']=='train'];orig=effective(m);zero=orig.clone();zero[mask]=0;ones=torch.zeros_like(orig);ones[mask]=1
    with torch.no_grad():fixed=[rgb(m,v['camera'],zero).detach() for v in fit];row=[rgb(m,v['camera'],ones)[0].detach().clamp_min(1e-10) for v in fit]
    b=[torch.where(v['band'][None],v['target'],v['base'])-r for v,r in zip(fit,fixed)];K=sum(int(v['band'].sum())*3 for v in fit);ab=[K/(len(fit)*3*int(v['band'].sum())) for v in fit];beta=[K/(len(fit)*3*int((~v['band']).sum())) for v in fit]
    col=torch.zeros_like(orig,dtype=torch.float64)
    for v in fit:
        color=torch.zeros_like(orig,requires_grad=True);im=rgb(m,v['camera'],color);col+=torch.autograd.grad(im.sum(),color)[0].double()
    tau=.99/col[mask].float().clamp_min(1e-10);sigma=[.99/r for r in row];c=effective(warm)[mask].clamp(0,1);z=c.clone();ys=[torch.zeros_like(x) for x in b];trace=[];bestP=float('inf');bestD=-float('inf');bestc=c.clone();besty=None;start=time.monotonic()
    for it in range(4000):
        colors=torch.zeros_like(orig);colors[mask]=z
        with torch.no_grad():
            for i,(v,si) in enumerate(zip(fit,sigma)):
                yy=ys[i]+si[None]*(rgb(m,v['camera'],colors)-b[i]);ys[i]=torch.where(v['band'][None],yy.clamp(-ab[i],ab[i]),yy/(1+si[None]/(2*beta[i])))
        g=torch.zeros_like(c,dtype=torch.float64)
        for v,y in zip(fit,ys):
            color=torch.zeros_like(orig,requires_grad=True);im=rgb(m,v['camera'],color);g+=torch.autograd.grad((im*y).sum(),color)[0][mask].double()
        prev=c;c=(c-tau*g.float()).clamp(0,1);z=2*c-prev
        if (it+1)%24==0 or it==3999:
            with torch.no_grad():m._features_dc[mask,0,:]=(c-.5)/C0
            P=sum(full_objective(m,fit).values());D=(-sum((bb.double()*yy.double()).sum().item()+yy[:,~v['band']].double().square().sum().item()/(4*be) for bb,yy,v,be in zip(b,ys,fit,beta))+torch.minimum(g,torch.zeros_like(g)).sum().item())/K
            if P<bestP:bestP=P;bestc=c.clone()
            if D>bestD:bestD=D;besty=[yy.detach().cpu().clone() for yy in ys]
            gap=bestP-bestD+3e-7;trace.append({'iteration':it+1,'P_current':P,'D_current_raw':D,'exact_v1_primal':bestP,'dual_lower':bestD-3e-7,'dual_margin':3e-7,'gap':gap,'seconds':time.monotonic()-start});atomic_json(OUT/'L1_REFINEMENT_STATUS.json',{'phase':'RUNNING','pid':os.getpid(),'iteration':it+1,'total':4000,'gap':gap});atomic_json(OUT/'traces'/f'{name}.json',trace)
            with torch.no_grad():m._features_dc[mask,0,:]=(bestc-.5)/C0
            save_model(m,OUT/'checkpoints'/f'{name}.pth')
            if gap<=1e-6:break
    with torch.no_grad():m._features_dc[mask,0,:]=(bestc-.5)/C0
    cp=OUT/'checkpoints'/f'{name}.pth';save_model(m,cp);dual=OUT/'checkpoints'/f'{name}_dual.pth';torch.save({'y':besty,'objective_scaling_K':K},dual);old=json.loads((ART/'results/C1_exact_convex.json').read_text())['v1_Adam_same_objective']
    out={'status':'COMPLETED','same_v1_objective':True,'target_precision':'byte-exact quantized native train PNG','solver':'matrix-free diagonally preconditioned Chambolle-Pock; primal .99/column mass, dual .99/row mass; operator step norm <= .99','iterations':it+1,'duration_seconds':time.monotonic()-start,'trace':trace,'certificate':trace[-1],'v1_Adam_same_objective':old,'checkpoint_sha256':sha(cp),'dual_y_sha256':sha(dual),'metrics':assess(m,views,labels,name,[f['theta_deg'] for f in manifest['roles']['train']]),'claim':'finite feasible objective and valid dual bound with engineering finite precision margin; optimum certified to stated tolerance only if gap <= 1e-6'}
    result(name,out);ps=[ART/'results'/f'{name}.json',OUT/'results'/f'{name}.json',OUT/'traces'/f'{name}.json',cp,dual];atomic_json(seal,{'unit':name,'identity':identity,'status':'COMPLETED','outputs':{str(p.relative_to(ROOT)):sha(p) for p in ps}});assert input_snapshot()==before;atomic_json(OUT/'L1_REFINEMENT_STATUS.json',{'phase':'COMPLETED','iterations':it+1,'gap':gap,'inputs_unchanged':True,'pid':os.getpid()});print('L1_REFINEMENT_COMPLETED',flush=True)
if __name__=='__main__':main()
