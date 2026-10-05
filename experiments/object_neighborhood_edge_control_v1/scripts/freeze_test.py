"""Freeze actual validation-calibrated pilot evaluation; never derive gates from TEST."""
import argparse
import json
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from runtime import EXP,OUT,ART,atomic_json,sha,code_identity

def freeze(scenes):
    destination=EXP/'results/manifests/test_freeze.json'
    if destination.exists():raise RuntimeError('TEST freeze already exists; cannot replace')
    checkpoints={};validation={};comparisons=[]
    for scene in scenes:
        directory=OUT/'controls'/scene
        for p in sorted(directory.glob('*.pth')):
            method=p.stem;val=EXP/f'results/tables/{scene}_{method}_val_coverage_v2.json'
            if not val.exists():val=EXP/f'results/tables/{scene}_{method}_val.json'
            if not val.exists():continue
            checkpoints[scene+'/'+method]=sha(p);validation[scene+'/'+method]=sha(val)
        for method in ('B0','B1','B3_uniform','B6','C0_control','C1_control'):
            if scene+'/'+method not in checkpoints:raise RuntimeError('required method validation absent: '+method)
        b1path=EXP/f'results/tables/{scene}_B1_val_coverage_v2.json'
        if not b1path.exists():b1path=EXP/f'results/tables/{scene}_B1_val.json'
        b1=json.loads(b1path.read_text())['mean_metrics']
        for method in ('C0_control','C1_control'):
            score=json.loads((EXP/f'results/tables/{scene}_{method}_val.json').read_text())['mean_metrics']
            comparisons.append({'scene':scene,'method':method,'B1_edge_mse':b1['edge_mse_linear'],
                'edge_mse':score['edge_mse_linear'],'beats_simple_B1':score['edge_mse_linear']<b1['edge_mse_linear']})
    high=[c for c in comparisons if c['scene']=='panels_high']
    stop=len(high)==2 and all(not x['beats_simple_B1'] for x in high)
    result={'created_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'scope':'one-seed pilot, not formal',
        'checkpoints':checkpoints,'validation_sha256':validation,'data_sha256':sha(EXP/'data/manifests/data_freeze.json'),
        'cameras_sha256':sha(EXP/'data/manifests/cameras.json'),'config_sha256':sha(EXP/'configs/pilot.json'),
        'code':code_identity(),
        'evaluator_source_sha256':{str(p):sha(p) for p in list((EXP/'src').glob('*.py'))+
            [EXP/'scripts/evaluate.py',EXP/'scripts/temporal.py']},
        'thresholds':{'edge_MSE_relative_reduction_vs_B1':.10,'whole_image_psnr_drop_db_max':.2,
            'hole_rate_increase_max':.001,'temporal_increase_ratio_max':.05,
            'near_zero_width_absolute_error_px':.05,'width_absolute_reason':'validation B0 W error already ~0.004 pixels; relative width improvement unstable',
            'contrast_min':.02,'label_confidence':.85,'band_px':12},
        'decision_basis':'validation only; no TEST target pixels read','comparisons':comparisons,
        'stop_complexity':stop,'stop_rule':'two controlled candidate/loss ablations fail to beat same-budget ordinary B1',
        'P3':'PARTIAL: full10-condition MVP, B2/B5 and formal seeds not completed',
        'P4':None,'P5':None,'P6':None,'human_visual_GO':'PENDING_INDEPENDENT_HUMAN',
        'main_training_provenance':'native jointly RGB-trained model + fixed training-mask-supported UID labels; no surface geometry oracle input'}
    atomic_json(destination,result)
    atomic_json(ART/'STATUS.json',{'state':'FROZEN_FOR_READ_ONLY_TEST','P0':'EXECUTED','P1':'EXECUTED',
        'P2':'SINGLE_SCENE_VALIDATION_COMPLETE','P3':'PARTIAL','P4':None,'P5':None,'P6':None,
        'P7':'IN_PROGRESS','stop_complexity':stop,'TEST_opened':False,'freeze_sha256':sha(destination)})
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--scenes',nargs='+',default=['panels_high']);freeze(p.parse_args().scenes)
