"""Controlled backend observations. Evaluation labels never enter run_backend."""
from pilotio import *
from core import run_backend
from real import save_result
from scipy.spatial import cKDTree

def generate(case,condition,seed):
    rng=np.random.default_rng(seed); pieces=[]; curve_ids=[]; positives=[]
    def line(a,b,curve):
        n=int(round(np.linalg.norm(np.asarray(b)-a)))+1
        if condition=='density_1to4' and not pieces: n=4*(n-1)+1
        t=np.linspace(0,1,n); p=np.asarray(a)+(np.asarray(b)-a)*t[:,None]
        pieces.append(p);curve_ids.append(curve)
    if case in ['broken_collinear','collinear_distinct']:
        line([-40,0,0],[-4,0,0],0);line([4,0,0],[40,0,0],0 if case=='broken_collinear' else 1)
        if case=='broken_collinear': positives=[(0,1)]
    elif case=='sharp_corner':
        line([-40,0,0],[0,0,0],0);line([0,0,0],[0,40,0],1)
    elif case=='nearby_parallel':
        for j in range(2):
            line([-40,1.5*j,0],[-4,1.5*j,0],j);line([4,1.5*j,0],[40,1.5*j,0],j)
        positives=[(0,1),(2,3)]
    elif case=='depth_crossing':
        line([-40,0,0],[-4,0,0],0);line([4,0,0],[40,0,0],0)
        line([0,-40,4],[0,-4,4],1);line([0,4,4],[0,40,4],1);positives=[(0,1),(2,3)]
    elif case in ['T_junction','X_junction']:
        line([-40,0,0],[0,0,0],0);line([0,0,0],[40,0,0],0);line([0,0,0],[0,40,0],1)
        if case=='X_junction': line([0,-40,0],[0,0,0],1)
    elif case=='S_curve':
        t=np.linspace(-40,40,161 if condition!='density_1to4' else 641);pieces=[np.c_[t,12*np.sin(t/12),np.zeros(len(t))]];curve_ids=[0]
    # Random oblique rotation prevents axis-aligned tests from flattering Hough.
    Q,_=np.linalg.qr(rng.normal(size=(3,3)))
    if np.linalg.det(Q)<0:Q[:,0]*=-1
    truth=np.concatenate(pieces)@Q.T; tangent=np.concatenate([unit(np.gradient(p,axis=0)) for p in pieces])@Q.T
    fragment=np.concatenate([np.full(len(p),i,np.int32) for i,p in enumerate(pieces)])
    x=truth.copy()
    if condition=='position_0.5h': x+=rng.normal(0,.5,x.shape)
    if condition=='direction_15deg':
        perp=rng.normal(size=tangent.shape);perp-=np.sum(perp*tangent,axis=1)[:,None]*tangent;perp=unit(perp)
        angle=rng.normal(0,np.deg2rad(15),len(x));tangent=unit(tangent*np.cos(angle[:,None])+perp*np.sin(angle[:,None]))
    protected=np.zeros(len(x),bool)
    for i in range(len(pieces)):
        ids=np.flatnonzero(fragment==i);protected[ids[:2]]=True;protected[ids[-2:]]=True
    _,inv,cnt=np.unique(np.round(x,8),axis=0,return_inverse=True,return_counts=True);protected|=cnt[inv]>1
    data=dict(xyz=x,tangent=tangent,fragment_id=fragment,confidence=np.ones(len(x)),tangent_reliable=np.ones(len(x),bool),eligible=np.ones(len(x),bool),protected=protected)
    junction_ids=np.flatnonzero(np.linalg.norm(truth,axis=1)<1e-9) if case in ['T_junction','X_junction'] else np.array([],int)
    evaluation=dict(case=case,condition=condition,seed=seed,positive_pairs=positives,fragment_curve_ids=curve_ids,truth_xyz=truth,junction_sample_ids=junction_ids,synthetic=True,h_reference=1.,measurement='direct generated samples; no upstream GS reconstruction',visibility='UNKNOWN; no rendered edge evidence in this benchmark')
    return data,evaluation

def evaluate(data,result,evaluation):
    positives={tuple(p) for p in evaluation['positive_pairs']}; predictions={tuple(p['pair']):p['score'] for p in result['links']}
    rows=[dict(threshold=None,predictions=0,tp=0,fp=0,fn=len(positives),precision=None,recall=0. if positives else None)]
    for score in sorted(set(predictions.values()),reverse=True):
        chosen={p for p,s in predictions.items() if s>=score};tp=len(chosen&positives);fp=len(chosen-positives)
        rows.append(dict(threshold=score,predictions=len(chosen),tp=tp,fp=fp,fn=len(positives)-tp,precision=tp/len(chosen),recall=tp/len(positives) if positives else None))
    best=max([r['recall'] for r in rows if r['precision'] is not None and r['precision']>=.95 and r['recall'] is not None],default=0.) if positives else None
    wrong_groups=0
    for q in result['hypotheses']:
        if len({evaluation['fragment_curve_ids'][f] for f in q['fragment_ids']})>1: wrong_groups+=1
    junction_ids=evaluation['junction_sample_ids']; retained=int((np.linalg.norm(result['xyz'][junction_ids]-data['xyz'][junction_ids],axis=1)<1e-10).sum())
    truth=evaluation['truth_xyz'];dist=cKDTree(truth).query(result['xyz'])[0]; reverse=cKDTree(result['xyz']).query(truth)[0]
    metrics=dict(**result['stats'],case=evaluation['case'],condition=evaluation['condition'],positive_pairs=len(positives),predicted_pairs=len(predictions),true_candidate_pairs=len(set(predictions)&positives),false_candidate_pairs=len(set(predictions)-positives),candidate_recall_at_precision95=best,wrong_hypothesis_groups=wrong_groups,wrong_depth_candidate_pairs=len(set(predictions)-positives) if evaluation['case']=='depth_crossing' else 0,junction_denominator=len(junction_ids),junction_samples_retained=retained,junction_retention=retained/len(junction_ids) if len(junction_ids) else None,output_to_synthetic_truth_h=quant(dist),synthetic_truth_to_output_h=quant(reverse),curve_sample_count=len(data['xyz']),retained_sample_count=len(result['xyz']),confirmed_connection_metrics='NOT_EVALUATED: M2 verifier not implemented',original_to_synthetic_truth_h=quant(cKDTree(truth).query(data['xyz'])[0]))
    return rows,metrics

def main():
    guard();status('SYNTHETIC_RUNNING');all_metrics=[]
    for seed in CFG['seeds']:
        for condition in CFG['synthetic_conditions']:
            for case in CFG['synthetic_cases']:
                guard(); data,evaluation=generate(case,condition,seed); d=OUT/'synthetic'/f'seed_{seed}'/condition/case;d.mkdir(parents=True,exist_ok=True)
                np.savez_compressed(d/'input.npz',**data)
                np.savez_compressed(d/'EVALUATION_ONLY.npz',truth_xyz=evaluation['truth_xyz'],junction_sample_ids=evaluation['junction_sample_ids'])
                js(d/'EVALUATION_ONLY.json',{k:v for k,v in evaluation.items() if k not in ['truth_xyz','junction_sample_ids']})
                input_hash=sha(d/'input.npz')
                for method in CFG['methods']:
                    guard();result=run_backend(data,method,seed);pr,metrics=evaluate(data,result,evaluation);metrics['input_sha256']=input_hash
                    save_result(d/method,result);js(d/method/'raw_PR.json',pr);js(d/method/'evaluation.json',metrics);all_metrics.append(metrics)
                    assert result['stats']['refiner_calls']<=32
                    assert result['stats']['confirmed_links']==0
                js(OUT/'synthetic_metrics.json',all_metrics)
            status('SYNTHETIC_CONDITION_DONE',seed=seed,condition=condition,rows=len(all_metrics))
    # Bounded single-factor diagnostics; neutral confidence is deliberately reported
    # as a degenerate ablation instead of inventing a calibrated confidence signal.
    ablations=[]
    for case in CFG['synthetic_cases']:
        data,evaluation=generate(case,'density_1to4',0)
        for name,options in [('H1_no_density',dict(density=False)),('H1_no_tangent',dict(tangent_weight=False)),('H1_no_confidence',dict(confidence_weight=False))]:
            guard();result=run_backend(data,'H1',0,**options);pr,metrics=evaluate(data,result,evaluation);metrics['ablation']=name
            save_result(OUT/'ablations'/case/name,result);js(OUT/'ablations'/case/name/'raw_PR.json',pr);js(OUT/'ablations'/case/name/'evaluation.json',metrics);ablations.append(metrics)
    js(OUT/'ablation_metrics.json',ablations);status('SYNTHETIC_DONE',rows=len(all_metrics),ablations=len(ablations))
if __name__=='__main__':main()
