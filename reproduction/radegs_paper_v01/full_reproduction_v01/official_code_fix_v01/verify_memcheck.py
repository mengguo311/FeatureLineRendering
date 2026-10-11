"""Read-only verification of the completed, owned 1000-step diagnostic."""
import hashlib,json,os,time
from pathlib import Path
import torch
H=Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01');O=H/'full_reproduction_v01/suite_execution_v01/scan69_cuda_failure_v01/rgb_vjp_memcheck_v01'
assert not torch.cuda.is_initialized() and os.environ['CUDA_VISIBLE_DEVICES']==''
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(8*1024**2),b''):h.update(b)
 return h.hexdigest()
cpath=O/'state/runner_config.json';c=json.loads(cpath.read_text());seal=json.loads((O/'state/smoke.seal.json').read_text())
assert sha(cpath)=='c33016b83753b0d89e436a1fe3d427db15b414734c15666dd2a2e9c780c13595'
assert seal['inputs']==c['inputs']
for p,h in {**c['immutable_files'],**seal['outputs']}.items():assert sha(p)==h,p
model=H/'models/scan69_rgb_vjp_memcheck_v01';desc=json.loads((model/'restart.json').read_text());assert sha(desc['path'])==desc['sha256']
state=torch.load(desc['path'],map_location='cpu');assert state['completed_iteration']==desc['completed_iteration']==1000
assert state['provenance']==desc['provenance'];checks=[]
def walk(obj,name):
 if isinstance(obj,torch.Tensor):
  assert torch.isfinite(obj).all(),name
  checks.append({'name':name,'shape':list(obj.shape),'elements':obj.numel()})
 elif isinstance(obj,dict):
  for k,v in obj.items():walk(v,name+'/'+str(k))
 elif isinstance(obj,(list,tuple)):
  for k,v in enumerate(obj):walk(v,name+'/'+str(k))
for key in ('parameters','buffers','appearance_network','optimizer'):walk(state[key],key)
rows=[json.loads(x) for x in (model/'iteration_loss.jsonl').read_text().splitlines()];ids=[r['iteration'] for r in rows];assert ids==list(range(1,1001))
result=json.loads((O/'outputs/1791545275251099185/result.json').read_text());assert result['status']=='NO_NONFINITE_FOUND_THROUGH1000' and result['native_sha256']=='b9f110c97644cdc7b67300214dd14da18b7d9867b20493299f16baf7a6730252'
log=O/'sanitizer_logs/1791545275251099185.log';assert log.read_text().count('ERROR SUMMARY: 0 errors')==1
out={'status':'VERIFIED_BOUNDED_DIAGNOSTIC','utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'config_sha256':sha(cpath),'immutable_files_verified':len(c['immutable_files']),'sealed_outputs_verified':len(seal['outputs']),'seal_sha256':sha(O/'state/smoke.seal.json'),'checkpoint':desc,'checkpoint_finite_checks':checks,'iteration_count':len(ids),'iterations_unique_contiguous':True,'iteration_log_sha256':sha(model/'iteration_loss.jsonl'),'sanitizer_sha256':sha(log),'result':result,'original_NaN_cause_proven':False,'scientificdone':False}
f=H/'official_code_fix_v01/MEMCHECK_VERIFIED.json';assert not f.exists();f.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ('checkpoint_finite_checks','checkpoint')},indent=2));print('finite tensors',len(checks))
