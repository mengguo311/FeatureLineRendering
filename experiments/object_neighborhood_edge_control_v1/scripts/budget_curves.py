"""Pilot equal-time points at a single common Gaussian count cap, no extra capacity."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from runtime import OUT,EXP,atomic_json,assert_training_open
from runner import unit

def run():
    assert_training_open('panels_high');scripts=EXP/'scripts';methods=[]
    for budget in (1.,2.):
        for algorithm in ('B1','B6','C0_control','C1_control'):
            method=algorithm+'_time_'+str(int(budget))+'s';methods.append(method)
            unit(method,[str(scripts/'run_controls.py'),'panels_high',method,'--time-budget',str(budget)],
                 [OUT/f'controls/panels_high/{method}.pth'])
            unit(method+'_val',[str(scripts/'evaluate.py'),'panels_high',method,'--no-figures'],
                 [EXP/f'results/tables/panels_high_{method}_val.json'])
    atomic_json(EXP/'results/manifests/budget_curves.json',{'scene':'panels_high','methods':methods,
        'budgets_seconds':[1.,2.],'same_count_cap':10659,'scope':'single count cap; no count sweep, no formal seed statistics',
        'time_definition':'synchronized optimization loop, preprocessing and evaluation excluded',
        'overshoot_tolerance':'one native update iteration; actual seconds/iterations retained'})

if __name__=='__main__':run()
