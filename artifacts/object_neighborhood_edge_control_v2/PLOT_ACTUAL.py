"""Plots use only saved real iterations, no synthetic/interpolated result series."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ART=Path(__file__).resolve().parent

def load(name):return json.loads((ART/'results'/f'{name}.json').read_text())
def main():
    fig,axes=plt.subplots(2,2,figsize=(10,7))
    for ax,name in zip(axes.ravel(),('F00','F01','F10','F11')):
        d=load(name);t=d['trace'];x=[p['iteration'] for p in t];ax.plot(x,[p['mse_upper'] for p in t],label='feasible upper');ax.plot(x,[p['mse_lower'] for p in t],label='dual lower minus margin');ax.set_title(name+' '+','.join(d['fit_roles']));ax.set_xlabel('Actual iteration');ax.set_ylabel('Matched band MSE');ax.legend(fontsize=8);ax.grid(alpha=.2)
    fig.tight_layout();fig.savefig(ART/'figures/R1_actual_convergence.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    for name in ('G00','G10','G01','G11'):
        t=load(name)['trace'];x=[p['iteration'] for p in t];axes[0].plot(x,[p['full_train_rgb_objective'] for p in t],label=name);axes[1].plot(x,[p['N'] for p in t],label=name)
    axes[0].set_yscale('log');axes[0].set_ylabel('Full epoch train RGB objective');axes[1].set_ylabel('Actual Gaussian count')
    for ax in axes:ax.set_xlabel('Actual training step');ax.legend();ax.grid(alpha=.2)
    fig.tight_layout();fig.savefig(ART/'figures/R2_actual_curves.png',dpi=150);plt.close(fig)
    d=load('C1_exact_convex');t=d['trace'];fig,ax=plt.subplots(figsize=(7,4));x=[p['iteration'] for p in t];ax.plot(x,[p['exact_v1_primal'] for p in t],label='convex feasible primal');ax.plot(x,[p['dual_lower'] for p in t],label='convex dual lower');ax.axhline(sum(d['v1_Adam_same_objective'].values()),color='gray',ls='--',label='v1 Adam same objective');ax.set_xlabel('Actual PDHG iteration');ax.set_ylabel('Band L1 + outside MSE');ax.legend();ax.grid(alpha=.2);fig.tight_layout();fig.savefig(ART/'figures/C1_exact_objective_actual.png',dpi=150);plt.close(fig)
if __name__=='__main__':main()
