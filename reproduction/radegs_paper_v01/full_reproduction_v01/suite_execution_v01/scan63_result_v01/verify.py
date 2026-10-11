"""Read-only CPU provenance, schedule and PLY opacity audit for scan63."""
import datetime,json,sys
from pathlib import Path
import numpy as np
from plyfile import PlyData
import torch
W=Path(__file__).resolve().parents[5];H=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');S=H/'full_reproduction_v01/suite_execution_v01';O=S/'scan63_result_v01'
sys.path.insert(0,str(W/'reproduction/radegs_paper_v01/stage2'))
from safety import sha256,verify_seal,atomic_json
state=S/'scan63_v01/state';cp=state/'runner_config.json';c=json.loads(cp.read_text());model=Path(c['model'])
assert sha256(cp)=='76e495e4f2b924e88d05a3a8f97e10a320c1a44c5811315f40b679054278758a'
for p,d in c['immutable_files'].items():assert sha256(p)==d,p
seals={s:verify_seal(state/(s+'.seal.json'),s,c['inputs']) for s in ['smoke','train','export','tsdf']};assert all(seals.values())
b=state.parent/'boundary_checkpoint/checkpoint_15000.seal.json';assert verify_seal(b,'boundary_checkpoint',c['inputs'])
logs=[json.loads(l) for l in (model/'iteration_loss.jsonl').read_text().splitlines()];assert len(logs)==30000 and {l['iteration'] for l in logs}==set(range(1,30001))
for r in logs:
 assert r['geometry_active']==(r['iteration']>15000)
 assert (r['wd'],r['wn'])==((100,5) if r['geometry_active'] else (0,0))
params=[]
for iteration in [15000,30000]:
 p=model/f'point_cloud/iteration_{iteration}/point_cloud.ply';v=PlyData.read(p)['vertex'].data
 fields={k:int((~np.isfinite(v[k])).sum()) for k in v.dtype.names if np.issubdtype(v[k].dtype,np.number)}
 raw=torch.sigmoid(torch.from_numpy(v['opacity'].copy())).numpy().astype(np.float64)
 scale=np.exp(np.stack([v['scale_'+str(k)] for k in range(3)],1).astype(np.float64));f=v['filter_3D'].astype(np.float64)
 effective=raw*np.sqrt(np.prod(scale**2,1)/np.prod(scale**2+f[:,None]**2,1))
 assert np.isfinite(effective).all()
 params.append({'iteration':iteration,'sha256':sha256(p),'gaussians':len(v),'nonfinite_fields':{k:x for k,x in fields.items() if x},'raw_opacity_quantiles':np.quantile(raw,[0,.01,.1,.5,.9,.99,1]).tolist(),'effective_opacity_quantiles':np.quantile(effective,[0,.01,.1,.5,.9,.99,1]).tolist(),'effective_below_1_over_255_fraction':float((effective<1/255).mean()),'effective_coefficient_calculation':'CPU float64 diagnostic; sigmoid uses torchCPU float32 source behavior','position_bounds':[[float(v[k].min()) for k in ['x','y','z']],[float(v[k].max()) for k in ['x','y','z']]]})
assert not torch.cuda.is_initialized()
result={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'config_sha256':sha256(cp),'immutable_inputs_verified':len(c['immutable_files']),'seals_verified':seals,'seal_hashes':{str(state/(s+'.seal.json')):sha256(state/(s+'.seal.json')) for s in seals},'boundary_checkpoint_verified':True,'boundary_seal_sha256':sha256(b),'unique_iteration_records':len(logs),'schedule_verified':True,'last_iteration':logs[-1],'parameters':params,'official_metric':None,'official_outer_eval_attempted':True,'official_inner_metric_executed':False,'current_failure':'author mask culling raised IndexError before official inner metric; cause being audited','torch_CUDA_initialized':False,'scientificdone':False}
atomic_json(O/'VERIFICATION.json',result);print(json.dumps(result,indent=2))
