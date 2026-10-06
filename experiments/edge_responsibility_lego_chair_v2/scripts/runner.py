#!/usr/bin/env python
import sys, json, fcntl, time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from runtime import OUT,ART,sha,event,unit,atomic_json,guard,source_hashes
from inputs import freeze
from adapter import load_model
from calibration import native_calibration
from reporting import update
import synthetic,scoring,interventions

def main():
    lock=(OUT/'RUNNER.lock').open('w')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    frozen=freeze();fh=sha(ART/'INPUT_FREEZE.json');cfg=frozen['config'];results={}
    if source_hashes()!=frozen['source_hashes']:raise RuntimeError('source freeze changed')
    results['synthetic']=unit('synthetic',lambda:synthetic.run(frozen),fh);update(frozen,results)
    # Independent per-scene exception handling preserves a failed Lego unit and still runs Chair.
    for scene in ['lego','chair']:
        data=frozen['scenes'][scene]
        try:
            guard(scene+'/model_load');assert sha(data['model'])==data['model_sha256'];m=load_model(data['model'])
            dev=[v for v in data['views'] if v['entry']['role']=='dev']
            def calibrate():
                records=[]
                for v in dev:
                    guard(scene+'/dev_calibration/'+v['entry']['key'])
                    records.append(native_calibration(m,v,cfg));event(scene+'/dev_calibration/'+v['entry']['key'],'COMPLETE',passed=records[-1]['pass'])
                return dict(scene=scene,views=records,pass_all=all(r['pass'] for r in records),pass_=all(r['pass'] for r in records),
                            **{'pass':all(r['pass'] for r in records)},absolute_action_minimum=max(r['absolute_action_minimum'] for r in records))
            results[scene+'_calibration']=unit(scene+'_calibration',calibrate,fh);update(frozen,results)
            results[scene+'_scores']=unit(scene+'_scores',lambda:scoring.run(scene,m,data,cfg),fh);update(frozen,results)
            score=results[scene+'_scores']
            if 'aggregate_path' not in score:raise RuntimeError('score engineering not ready; scene preserved')
            def train_groups():
                groups=interventions.build_groups(scene,m,data,score,cfg)
                return interventions.training(scene,m,data,score,groups,results[scene+'_calibration'],cfg)
            results[scene+'_construction']=unit(scene+'_construction',train_groups,fh);update(frozen,results)
            if 'groups' not in results[scene+'_construction']:raise RuntimeError('construction engineering not ready')
            results[scene+'_independent']=unit(scene+'_independent',lambda:interventions.independent(scene,m,data,score,results[scene+'_construction'],cfg),fh);update(frozen,results)
            val=results[scene+'_independent']
            if 'accepted_rows' not in val:raise RuntimeError('independent engineering not ready')
            results[scene+'_media']=unit(scene+'_media',lambda:interventions.deliver_media(scene,m,data,score,val,cfg),fh);update(frozen,results)
        except Exception as e:
            import traceback
            atomic_json(ART/'failures'/f'{scene}_scene_{time.time_ns()}.json',dict(error=str(e),traceback=traceback.format_exc()))
            event(scene,'SCENE_FAILED_CONTINUING',error=str(e))
        finally:
            if 'm' in locals():del m
            import torch
            torch.cuda.empty_cache()
    final=update(frozen,results,complete=True)
    atomic_json(OUT/'RUNNER_COMPLETE.json',dict(status=final['status'],units=list(results),optimization='NOT_RUN'))
    event('campaign','COMPLETE',status=final['status'],optimization='NOT_RUN')

if __name__=='__main__':main()
