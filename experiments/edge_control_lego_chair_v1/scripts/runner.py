#!/usr/bin/env python
import sys,os,json,copy,time,traceback,fcntl
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from runtime import ROOT,EXP,ART,OUT,guard,event,result,sha,source_hashes,atomic_json,digest
import torch,numpy as np
from data import config
from adapter import load_model,snapshot,dc_project,permission_audit
from preparation import view_data,calibration,select,save_png
from optimization import optimize
from evaluation import evaluate,common_profiles
from media import montage,videos
from reporting import finish
torch.set_num_threads(2)

def freeze_targets(scene,train,dev):
    targets=[]
    for v in train+dev:
        e=v['evidence'];arrays={k:__import__('hashlib').sha256(e[k].tobytes()).hexdigest() for k in ('internal_band','outline_band','foreground','nonband','reliable')}
        targets.append({'key':v['key'],'role':v['entry']['role'],'camera_hash':v['entry']['camera_hash'],'photo_sha256':v['entry']['expected_photo_sha256'],'mask_array_sha256':arrays,'profiles':e['profiles'],'roi':e['roi'],'metadata':e['metadata']})
    atomic_json(ART/f'{scene}_TARGET_FREEZE.json',{'targets':targets,'holdout_target_rule':'same frozen evidence.py and DATA_FREEZE expected photo SHA; holdout bytes remain closed until DEV_MODEL_SEAL','source_sha256':sha(EXP/'src/evidence.py')})

def source_check(seal):
    if source_hashes()!=seal['source_hashes']:raise RuntimeError('source changed after production seal')

def run_scene(scene,s,cfg,seal):
    start=time.perf_counter();guard(f'{scene}/prepare');source_check(seal)
    base=load_model(s['model'],s['ply']['degree']);train=[view_data(e,base) for e in s['roles']['edit-train']]
    calibration(scene,base,train[0]);selections,selection=select(scene,base,train,cfg)
    dev=[view_data(e,base) for e in s['roles']['dev']];freeze_targets(scene,train,dev)
    prepared=time.perf_counter()-start
    models={'B0':base};oprecords={};train_scores={};dev_scores={}
    projected=copy.copy(base);projected._features_dc=dc_project(base._features_dc,selections['relative'])
    if not permission_audit(snapshot(base),snapshot(projected),selections['relative'],False)['pass']:raise AssertionError('projection freeze')
    models['zero_step_dc_projection']=projected
    for name in list(models):
        train_scores[name]=evaluate(scene,name,models[name],train,selections['relative'],'edit-train');dev_scores[name]=evaluate(scene,name,models[name],dev,selections['relative'],'dev')
    units=[('relative_color','relative',False,False,None),('relative_color_ordinary','relative',False,True,None),('relative_cov','relative',True,False,None),('relative_cov_ordinary','relative',True,True,None),('relative_color_ordinary_time','relative',False,True,'relative_color'),('relative_cov_ordinary_time','relative',True,True,'relative_cov'),('band2d_cov','band2d',True,False,None),('random_cov','random',True,False,None)]
    for name,selection_name,cov,ordinary,timeref in units:
        guard(f'{scene}/{name}');source_check(seal)
        edit,record=optimize(scene,name,base,selections[selection_name],train,cfg,cov,ordinary,oprecords[timeref]['optimizer_seconds'] if timeref else None)
        models[name]=edit.model();oprecords[name]=record
        train_scores[name]=evaluate(scene,name,models[name],train,selections[selection_name],'edit-train');dev_scores[name]=evaluate(scene,name,models[name],dev,selections[selection_name],'dev')
        atomic_json(ART/f'{scene}_PROGRESS.json',{'phase':'EDITING_DEV','completed_arms':list(models),'source_model_sha256':sha(s['model']),'preparation_seconds':prepared})
    common_profiles(scene,'dev',dev_scores)
    # All choices/edits are final before opening a single edit-holdout PNG.
    devseal=ART/f'{scene}_DEV_MODEL_SEAL.json'
    atomic_json(devseal,{'scene':scene,'primary_arm':'relative_cov, fixed config before dev','configuration_sha256':sha(EXP/'configs/pilot.json'),'source_hashes':seal['source_hashes'],'data_freeze_sha256':sha(ART/'DATA_FREEZE.json'),'selection_freeze_sha256':sha(ART/f'{scene}_SELECTION_FREEZE.json'),'target_freeze_sha256':sha(ART/f'{scene}_TARGET_FREEZE.json'),'edit_sha256':{p.name:sha(p) for p in (OUT/scene/'edits').glob('*.npz')},'dev_summary':{n:r['mean_per_view'] for n,r in dev_scores.items()},'decisions':'No dev tuning; evaluate all fixed arms; human visual GO pending; no independent TEST claim','utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())})
    guard(f'{scene}/holdout-readonly');source_check(seal);event(scene,'DEV_FROZEN_HOLDOUT_READONLY')
    heldout=[view_data(e,base,devseal) for e in s['roles']['edit-holdout']]
    holdout_scores={}
    for name,m in models.items():
        selector='band2d' if name=='band2d_cov' else ('random' if name=='random_cov' else 'relative')
        holdout_scores[name]=evaluate(scene,name,m,heldout,selections[selector],'edit-holdout')
    common_profiles(scene,'edit-holdout',holdout_scores)
    montage(scene,dev,'dev');montage(scene,heldout,'edit-holdout')
    media=[]
    display_models={n:models[n] for n in ('B0','relative_color','relative_cov','relative_cov_ordinary')}
    for name,cameras in [('arc0',s['arc']),('orbit',s['orbit'])]:media.extend(videos(scene,cameras,display_models,selections['relative'],name))
    modelafter=sha(s['model'])
    if modelafter!=s['model_sha256']:raise AssertionError('original model changed')
    record={'phase':'COMPLETE','scene':scene,'source_model_sha256_before':s['model_sha256'],'source_model_sha256_after':modelafter,'selection':selection,'optimization':{n:{k:v for k,v in r.items() if k not in ('online_steps','full_epochs','final_full_train')} for n,r in oprecords.items()},'train':train_scores,'dev':dev_scores,'holdout':holdout_scores,'media':media,'scene_seconds':time.perf_counter()-start,'preparation_seconds':prepared,'source_model_integrity':True,'holdout_readonly_after_seal':True,'independent_human_visual_GO':'PENDING'}
    atomic_json(ART/f'{scene}_FINAL.json',record);event(scene,'SCENE_COMPLETE',seconds=record['scene_seconds'])
    del models,base,train,dev,heldout;torch.cuda.empty_cache()

def main():
    lock=(OUT/'PRODUCTION.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    seal=json.loads((ART/'SOURCE_FREEZE.json').read_text());data=json.loads((ART/'DATA_FREEZE.json').read_text());cfg=config();source_check(seal)
    for p,h in data['read_only_dependencies'].items():
        if sha(p)!=h:raise ValueError('read-only dependency changed before production')
    event('production','STARTED',source_seal_sha256=sha(ART/'SOURCE_FREEZE.json'))
    # Both actual original models are rendered before any optimization starts.
    for scene,s in data['scenes'].items():
        try:
            guard(f'{scene}/initial_native_B0');base=load_model(s['model'],3);v=view_data(s['roles']['edit-train'][0],base);cal=calibration(scene,base,v)
            save_png(ART/'figures'/f'{scene}_initial_native_B0.png',v['b0']);save_png(ART/'figures'/f'{scene}_initial_TRAIN_reference.png',v['gt']);event(scene,'ACTUAL_NATIVE_B0_COMPLETE',calibration_pass=cal['pass']);del base,v;torch.cuda.empty_cache()
        except Exception as error:
            event(scene,'INITIAL_FAILED',error=str(error));(OUT/'logs'/f'{scene}_initial_failure.txt').write_text(traceback.format_exc())
    for scene,s in data['scenes'].items():
        if (ART/f'{scene}_FINAL.json').exists():raise RuntimeError('existing finalized scene; explicit verified resume required')
        try:run_scene(scene,s,cfg,seal)
        except Exception as error:
            atomic_json(ART/f'{scene}_FINAL.json',{'phase':'FAILED','scene':scene,'error':str(error),'traceback':traceback.format_exc(),'remaining':'inspect scene logs, preserve source/target/selection seals and resume verified units; other scene continues'})
            event(scene,'SCENE_FAILED',error=str(error));torch.cuda.empty_cache()
    final=finish();atomic_json(OUT/'FINAL.json',final);event('production',final['phase'])

if __name__=='__main__':main()
