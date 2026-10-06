"""Detached sequential GPU0 production with atomic, hash-verified unit seals."""
import sys,json,time,fcntl,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from runtime import *
from data import freeze_data,input_snapshot
from experiments import *
from delivery import report,media

def outputs(unit):
    ps=[ART/'results'/f'{unit}.json',OUT/'results'/f'{unit}.json']
    ps += list((OUT/'checkpoints').glob(unit+'.pth'))+list((OUT/'traces').glob(unit+'.*'))
    if unit.startswith('G'):ps+=list((OUT/'models'/unit).glob('checkpoint.pth'))
    ps+=list((ART/'figures').glob(unit+'_*'))
    if unit=='R0':ps+=list((ART/'figures').glob('R0_B0_*'))
    if unit=='MEDIA':ps+=list((ART/'videos').glob('*.mp4'))
    return [p for p in ps if p.is_file()]

def main():
    OUT.mkdir(parents=True,exist_ok=True);lock=(OUT/'production.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    freeze=json.loads((ART/'SOURCE_FREEZE.json').read_text());assert source_hashes()==freeze['source_hashes'],'production source changed'
    before=json.loads((OUT/'original_inputs_before.json').read_text());assert input_snapshot()==before,'original inputs changed'
    manifest=freeze_data();identity={'source_freeze_sha256':sha(ART/'SOURCE_FREEZE.json'),'data_manifest_sha256':sha(OUT/'data_manifest.json'),'inputs_manifest_sha256':sha(OUT/'original_inputs_before.json'),'config_sha256':sha(EXP/'configs/run.json')}
    completed=[]
    def unit(name,fn):
        assert source_hashes()==freeze['source_hashes'],'source changed during production'
        sealpath=OUT/'seals'/f'{name}.json'
        if sealpath.exists():
            sealed=json.loads(sealpath.read_text())
            if sealed['identity']!=identity:
                reuse=json.loads((ART/'VERIFIED_REUSE.json').read_text());assert name in reuse['units'];assert sealed['identity']==reuse['old_identity'];assert sha(sealpath)==reuse['seal_hashes'][name]
            else:assert sealed['identity']==identity
            for p,h in sealed['outputs'].items():assert sha(ROOT/p)==h,('sealed output modified',p)
            completed.append(name);print('VERIFIED_SKIP',name,flush=True);return get_result(name)
        while True:
            try:guard=resource_guard();break
            except RuntimeError as e:
                if 'WAIT_FOREIGN_GPU' not in str(e):raise
                status(name,'WAIT_FOREIGN_GPU',completed=completed);time.sleep(30)
        status(name,'RUNNING',completed=completed,guard=guard);print('START',name,flush=True);start=time.monotonic();r=fn()
        resource_guard(False);ps=outputs(name);assert ps
        atomic_json(sealpath,{'unit':name,'identity':identity,'duration_seconds':time.monotonic()-start,'outputs':{str(p.relative_to(ROOT)):sha(p) for p in ps},'status':'COMPLETED'});completed.append(name);status(name,'COMPLETED',completed=completed);print('DONE',name,flush=True);return r
    try:
        unit('R0',lambda:run_r0(manifest))
        for name in ('F00','F01','F10','F11'):
            fit=unit(name,lambda name=name:fit_r1(manifest,name))
            if fit['certificate']['mse_upper']<=CFG['r1_mse_tolerance']:
                outside=name+'_outside';unit(outside,lambda source=name,name=outside:fit_band_outside(manifest,source,name))
        unit('C1_exact_convex',lambda:fit_exact_v1(manifest))
        for name in ('G00','G10','G01','G11'):unit(name,lambda name=name:train_r2(manifest,name))
        for perm,label in (('color','O_color'),('cov','O_cov')):
            local=unit(label,lambda label=label,perm=perm:optimize_r3(manifest,label,perm))
            ordinary=label+'_ordinary';unit(ordinary,lambda name=ordinary,perm=perm:optimize_r3(manifest,name,perm,True))
            timed=ordinary+'_time';unit(timed,lambda name=timed,perm=perm,budget=local['optimizer_wall_seconds']:optimize_r3(manifest,name,perm,True,budget))
        # R4 only if natural local controls fail to show useful development potential.
        base=get_result('R0')['metrics']['summary']['dev-out']['edge_mse_linear'];potential=max(1-get_result(k)['metrics']['summary']['dev-out']['edge_mse_linear']/base for k in ('O_color','O_cov'))
        if potential<.1:
            make_recoverable_probe(manifest)
            for scope in ('C1','known','all'):
                for cov in (False,True):
                    name=f'R4_{scope}_{"scale" if cov else "color"}';unit(name,lambda name=name,scope=scope,cov=cov:solve_probe(manifest,name,scope,cov))
        atomic_json(ART/'R4_R5_DECISION.json',{'R4':'RUN' if potential<.1 else 'NOT_NEEDED_FIRST_PASS','R3_dev_band_potential':potential,'R5':'DEFERRED_PENDING_INDEPENDENT_CONTROL_ADVANTAGE','R5_epsilon':.02,'no_soft_edges_or_new_kernel':True})
        unit('MEDIA',lambda:media(manifest,['R0_B0','O_color','O_cov']))
        report(manifest);assert input_snapshot()==before
        status('ALL','COMPLETED_TEST_CLOSED',completed=completed,test_state='TEST_CLOSED');print('PRODUCTION_COMPLETED',flush=True)
    except Exception as e:
        status('FAILURE','FAILED',completed=completed,error_type=type(e).__name__,error=str(e));traceback.print_exc();
        try:report(manifest)
        except Exception:pass
        raise
from delivery import get_result
if __name__=='__main__':main()
