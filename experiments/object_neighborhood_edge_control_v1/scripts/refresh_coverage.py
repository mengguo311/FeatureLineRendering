"""Pre-TEST metric correction only, preserving original validation tables/seals."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from runtime import EXP,OUT,atomic_json,assert_training_open
from runner import unit

if __name__=='__main__':
    assert_training_open('panels_high')
    for path in sorted((OUT/'controls/panels_high').glob('*.pth')):
        method=path.stem
        if not (EXP/f'results/tables/panels_high_{method}_val.json').exists():continue
        unit(method+'_coverage_validation_v2',[str(EXP/'scripts/evaluate.py'),'panels_high',method,
             '--split','val','--no-figures','--tag','coverage_v2'],
             [EXP/f'results/tables/panels_high_{method}_val_coverage_v2.json'])
    atomic_json(EXP/'results/manifests/coverage_metric_correction.json',{
        'time':'before TEST freeze','model_changes':False,'old_tables_preserved':True,
        'reason':'old alpha hole ROI excluded target colour band; add all reliable foreground and target band hole metrics',
        'RGB_edge_metrics_unchanged':True,'parameter_selection_unchanged':True})
