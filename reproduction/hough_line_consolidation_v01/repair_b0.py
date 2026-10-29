"""Engineering correction only: independent B0 fragments must not undergo line NMS."""
from pilotio import *
from core import run_backend
from synthetic import evaluate
from real import save_result

def main():
    history=OUT/'engineering_history/B0_independence';metrics=json.loads((OUT/'synthetic_metrics.json').read_text()); corrected={};changed=0
    for p in sorted((OUT/'synthetic').glob('seed_*/*/*/input.npz')):
        guard();data=load_np(p);ev=json.loads((p.parent/'EVALUATION_ONLY.json').read_text());ev.update(load_np(p.parent/'EVALUATION_ONLY.npz'))
        dst=history/p.parent.relative_to(OUT/'synthetic')/'B0';shutil.copytree(p.parent/'B0',dst)
        old=load_np(p.parent/'B0/geometry.npz');result=run_backend(data,'B0',ev['seed']);pr,row=evaluate(data,result,ev);row['input_sha256']=sha(p)
        changed+=int(not np.array_equal(old['xyz'],result['xyz']) or not np.array_equal(old['membership'],result['membership']))
        save_result(p.parent/'B0',result);js(p.parent/'B0/raw_PR.json',pr);js(p.parent/'B0/evaluation.json',row)
        corrected[(ev['seed'],ev['condition'],ev['case'])]=row
    metrics=[corrected[(r['seed'],r['condition'],r['case'])] if r['method']=='B0' else r for r in metrics];js(OUT/'synthetic_metrics.json',metrics)
    data=load_np(OUT/'real_budgeted/scan24/input.npz');checks=[]
    for seed in CFG['seeds']:
        result=run_backend(data,'B0',seed);folder=OUT/'real_budgeted/scan24'/('B0' if seed==0 else f'paired/seed_{seed}/B0');old=load_np(folder/'geometry.npz')
        for key in ['xyz','tangent','groups','membership']:assert np.array_equal(old[key],result[key]),key
        checks.append(dict(seed=seed,geometry_and_membership_bitexact=True))
    js(OUT/'B0_ENGINEERING_CORRECTION.json',dict(reason='B0 independent fragments must bypass shared inter-hypothesis line NMS',synthetic_B0_reruns=len(corrected),changed_geometry_or_membership_runs=changed,real_B0_bitexact_replay=checks,Hough_and_B1_B2_outputs_unchanged=True,parameters_unchanged=True,old_outputs_preserved=str(history)))
    status('B0_INDEPENDENCE_FIXED',runs=len(corrected),changed=changed)
if __name__=='__main__':main()
