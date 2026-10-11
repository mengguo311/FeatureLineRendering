"""CPU-only figure of measured GPU FD precision; no generated/model imagery."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

H=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01')
O=H/'full_reproduction_v01/suite_execution_v01/scan69_cuda_failure_v01'
A=Path(__file__).resolve().parents[5]/'artifacts/radegs_paper_reproduction_v01/full_reproduction_v01/suite_execution_v01/scan69_cuda_failure_v01'
r=json.loads((O/'rgb_vjp_validation_v02/outputs/1791544934857119807/expanded_reference.json').read_text())
rows=[x for x in r['records'] if x['objective']=='rgb' and x['key']=='means' and x['index']==2 and x['fixture'].startswith('thin_')]
fig,axs=plt.subplots(1,2,figsize=(11,4.2),layout='constrained')
for ax,row in zip(axs,rows):
    s=row['sweep'];eps=[x['eps'] for x in s]
    ax.semilogx(eps,[x['native_fd'] for x in s],'o-',label='Native float32 FD')
    ax.semilogx(eps,[x['reference_at_float32_inputs_fd'] for x in s],'s--',label='Float64 forward FD at same inputs')
    ax.axhline(row['analytic'],color='tab:green',label='Native backward')
    ax.axhline(row['reference_float64'],color='black',ls=':',label='Independent float64 autograd')
    ax.axvline(3e-4,color='red',ls=':',alpha=.6,label='Original failed epsilon')
    ax.set(title=row['fixture'],xlabel='Camera-z perturbation epsilon',ylabel='RGB loss derivative')
    ax.grid(alpha=.2);ax.legend(fontsize=7)
fig.suptitle('Actual GPU derivative measurements; original float32 FD failures retained',fontsize=11)
fig.savefig(A/'RGB_Z_FD_PRECISION.png',dpi=170)
summary={'passed_reference_checks':sum(x['passed'] for x in r['records']),'max_covariance_condition':max(x['meta']['condition'] for x in r['records']),'negative_clamp_control':r['clamp_crossing_negative_control'],'z_rows':rows,'scientificdone':False}
(A/'RGB_Z_PRECISION_DETAILS.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({'figure':str(A/'RGB_Z_FD_PRECISION.png'),'checks':summary['passed_reference_checks'],'max_covariance_condition':summary['max_covariance_condition']}))
