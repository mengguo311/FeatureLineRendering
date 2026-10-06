"""Same R1 objective, diagonally preconditioned matrix-free convergence refinement."""
import sys,json,time,os,hashlib
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'experiments/object_neighborhood_edge_control_v2/src'))

def validate_majorizer_dense(A):
    # Tiny mathematical unit-test only; production never constructs dense pixel/Gaussian A.
    A=np.asarray(A,dtype=float)
    if (A<0).any():raise ValueError('native contribution weights must be nonnegative')
    H=A.T@A;d=H@np.ones(A.shape[1]);return bool(np.linalg.eigvalsh(np.diag(d)-H).min()>-1e-12)

def main():
    from runtime import OUT,ART,EXP,atomic_json,sha,source_hashes,resource_guard,result
    freeze=json.loads((ART/'REFINEMENT_FREEZE.json').read_text());assert sha(__file__)==freeze['script_sha256'];assert sha(ART/'SOURCE_FREEZE.json')==freeze['core_source_freeze_sha256']
    # Wait for the first production process and then wait for any foreign GPU0 job.
    while True:
        state=json.loads((OUT/'STATUS.json').read_text())
        if state['phase']=='COMPLETED_TEST_CLOSED':break
        if state['phase']=='FAILED':raise RuntimeError('main production failed; refinement not started')
        atomic_json(OUT/'REFINEMENT_STATUS.json',{'phase':'WAIT_MAIN_PRODUCTION','pid':os.getpid(),'main_unit':state['unit']});time.sleep(30)
    while True:
        try:resource_guard();break
        except RuntimeError as e:
            if 'WAIT_FOREIGN_GPU' not in str(e):raise
            atomic_json(OUT/'REFINEMENT_STATUS.json',{'phase':'WAIT_FOREIGN_GPU','pid':os.getpid()});time.sleep(30)
    import torch
    from data import CHECKPOINT,CFG,selection,freeze_data,input_snapshot
    from renderer_adapter import load_checkpoint
    from color_operator import ColorOperator,effective
    from evaluation import prepare,assess
    from experiments import save_model
    torch.set_num_threads(2);before=json.loads((OUT/'original_inputs_before.json').read_text());assert input_snapshot()==before;manifest=freeze_data()
    identity={'script_sha256':sha(__file__),'core_source_freeze_sha256':sha(ART/'SOURCE_FREEZE.json'),'data_manifest_sha256':sha(OUT/'data_manifest.json'),'input_manifest_sha256':sha(OUT/'original_inputs_before.json'),'max_iterations':2000,'gap_mse_tolerance':CFG['r1_gap_tolerance'],'margin_mse':CFG['r1_margin_mse']}
    completed=[]
    for arm in ('F00','F01','F10','F11'):
        name=arm+'_refined';seal=OUT/'seals'/f'{name}.json'
        if seal.exists():
            s=json.loads(seal.read_text());assert s['identity']==identity
            for p,h in s['outputs'].items():assert sha(ROOT/p)==h
            completed.append(name);continue
        resource_guard();atomic_json(OUT/'REFINEMENT_STATUS.json',{'unit':name,'phase':'RUNNING','pid':os.getpid(),'completed':completed})
        m=load_checkpoint(CHECKPOINT);warm=load_checkpoint(OUT/'checkpoints'/f'{arm}.pth');uids,labels,sel=selection();mask=torch.tensor(sel if arm in ('F00','F10') else np.ones(len(uids),bool),device='cuda');allviews=prepare(manifest,m);fit=[v for v in allviews if v['role']=='train' or (arm in ('F10','F11') and v['role']=='diagnostic-supervision')];op=ColorOperator(m,fit,mask);validation=op.validate()
        ones=torch.ones((op.k,3),device='cuda');d=op.adjoint(op.forward(ones)).float().clamp_min(1e-10)*1.01
        torch.manual_seed(672);delta=torch.randn_like(ones);ad=op.forward(delta);lhs=sum(x.double().square().sum().item() for x in ad);rhs=(d.double()*delta.double().square()).sum().item();assert lhs<=rhs*(1+2e-5)
        c=effective(warm)[mask].clamp(0,1);z=c.clone();t=1.;trace=[];bestP=float('inf');bestD=-float('inf');bestc=c.clone();besty=None;start=time.monotonic();tr=OUT/'traces'/f'{name}.jsonl';tr.parent.mkdir(parents=True,exist_ok=True)
        with tr.open('w') as log:
            for it in range(2000):
                rr,g=op.objective_gradient(z);prev=c;c=(z-g.float()/d).clamp(0,1);tn=(1+np.sqrt(1+4*t*t))/2;z=c+(t-1)/tn*(c-prev);t=tn
                residual,gc=op.objective_gradient(c);P=sum(.5*r.double().square().sum().item() for r in residual);D=-P-sum((b.double()*r.double()).sum().item() for b,r in zip(op.b,residual))+torch.minimum(gc,torch.zeros_like(gc)).sum().item();margin=op.M*CFG['r1_margin_mse']/2
                if P<bestP:bestP=P;bestc=c.clone()
                if D>bestD:bestD=D;besty=[r.detach().cpu().clone() for r in residual];dual_iteration=it+1
                gap=2*(bestP-bestD+margin)/op.M;row={'iteration':it+1,'P_current':P,'D_current_raw':D,'P_best':bestP,'D_best':bestD-margin,'mse_upper':2*bestP/op.M,'mse_lower':2*(bestD-margin)/op.M,'gap_mse':gap,'seconds':time.monotonic()-start};trace.append(row);log.write(json.dumps(row)+'\n');log.flush()
                if (it+1)%25==0 or gap<=CFG['r1_gap_tolerance']:
                    atomic_json(OUT/'REFINEMENT_STATUS.json',{'unit':name,'phase':'RUNNING','pid':os.getpid(),'iteration':it+1,'total':2000,'gap_mse':gap,'completed':completed});op.install(bestc);save_model(m,OUT/'checkpoints'/f'{name}.pth')
                if gap<=CFG['r1_gap_tolerance']:break
        op.install(bestc);cp=OUT/'checkpoints'/f'{name}.pth';save_model(m,cp);dual=OUT/'checkpoints'/f'{name}_dual.pth';torch.save({'y':besty,'dual_iteration':dual_iteration,'scalar_observations':op.M,'margin':margin},dual)
        cert={'P':bestP,'D_raw':bestD,'D':bestD-margin,'gap':bestP-bestD+margin,'mse_upper':2*bestP/op.M,'mse_lower':2*(bestD-margin)/op.M,'numerical_margin':margin,'scalar_observations':op.M,'primal_and_dual_may_come_from_different_iterations':True,'saved_dual_y_sha256':sha(dual)}
        claim='UNDETERMINED_OPTIMIZATION' if gap>CFG['r1_gap_tolerance'] else 'NUMERICALLY_BOUNDED_UNREACHABLE' if cert['mse_lower']>CFG['r1_mse_tolerance'] else 'FEASIBLE_WITHIN_TOLERANCE' if cert['mse_upper']<CFG['r1_mse_tolerance'] else 'UNDETERMINED_TOLERANCE'
        res={'status':'COMPLETED','source_arm':arm,'fit_roles':['train','diagnostic-supervision'] if arm in ('F10','F11') else ['train'],'same_objective_and_box_as_primary_R1':True,'initial_checkpoint_sha256':sha(OUT/'checkpoints'/f'{arm}.pth'),'solver':'diagonal metric FISTA; d=A^T A1 from native operator, Jensen proves diag(d)-A^T A PSD for nonnegative weights; 1% safety factor','native_majorizer_test':{'lhs_A_delta_norm_squared':lhs,'rhs_diagonal_quadratic':rhs,'passed':True},'validation':validation,'certificate':cert,'claim':claim,'iterations':len(trace),'duration_seconds':time.monotonic()-start,'trace':trace,'metrics':assess(m,allviews,labels,name,[v['frame']['theta_deg'] for v in fit]),'numerical_bound_note':'same fixed float32/native and 3e-7 MSE finite-precision engineering margin; no claim about general 3DGS limit'}
        result(name,res);paths=[ART/'results'/f'{name}.json',OUT/'results'/f'{name}.json',cp,dual,tr];atomic_json(seal,{'unit':name,'status':'COMPLETED','identity':identity,'outputs':{str(p.relative_to(ROOT)):sha(p) for p in paths}});completed.append(name)
    assert input_snapshot()==before;atomic_json(OUT/'REFINEMENT_STATUS.json',{'phase':'COMPLETED','pid':os.getpid(),'completed':completed,'inputs_unchanged':True});print('REFINEMENT_COMPLETED',flush=True)
if __name__=='__main__':main()
