"""Only evaluate sealed inputs. No training mutation, no operation re-selection."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from runtime import EXP,ART,OUT,atomic_json
from runner import unit

def run():
    freeze=json.loads((EXP/'results/manifests/test_freeze.json').read_text());scripts=EXP/'scripts'
    for key in freeze['checkpoints']:
        scene,method=key.split('/')
        unit(scene+'_'+method+'_test',[str(scripts/'evaluate.py'),scene,method,'--split','test'],
             [EXP/f'results/tables/{scene}_{method}_test.json'])
    # Entire continuous heldout path for comparator and both actual ablations;
    # failed COB baseline receives the same path, no handpicked camera video.
    for method in ('B0','B1','C0_control','C1_control','B4_official'):
        key='panels_high/'+method
        if key not in freeze['checkpoints']:continue
        unit(method+'_path',[str(scripts/'evaluate.py'),'panels_high',method,'--split','path'],
             [EXP/f'results/tables/panels_high_{method}_path.json'])
        unit(method+'_temporal',[str(scripts/'temporal.py'),'panels_high',method],
             [EXP/f'results/tables/panels_high_{method}_temporal.json'])
        unit(method+'_video',[str(scripts/'make_video.py'),'panels_high',method],
             [EXP/f'results/manifests/panels_high_{method}_video.json'])
    atomic_json(ART/'STATUS.json',{'state':'SINGLE_SCENE_PILOT_CLOSED_LOOP_COMPLETE','P0':'EXECUTED',
        'P1':'EXECUTED','P2':'HIGH_CONTRAST_EXECUTED; NEGATIVES_PENDING','P3':'PARTIAL',
        'P4':None,'P5':None,'P6':None,'P7':'IN_PROGRESS','TEST_opened':True,
        'stop_complexity':freeze['stop_complexity'],'model_or_threshold_changes_after_TEST':False})

if __name__=='__main__':run()
