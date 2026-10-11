"""Shared-admitted GPU regression, actual captured RED/GREEN and two-step replay.
No training beyond the bounded replay; full pipeline remains blocked until PASS.
"""
import argparse,json,os,subprocess,sys
from pathlib import Path
from safety import atomic_json,sha256
from repair_scope import validate

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--config',required=True);a=ap.parse_args();c=json.loads(Path(a.config).read_text());validate(c)
 assert os.environ['CUDA_VISIBLE_DEVICES']==c['allowed_gpu_uuids'][0]
 out=Path(c['validation_root'])/os.environ['RADEGS_ATTEMPT'];out.mkdir(parents=True,exist_ok=False)
 code=Path(__file__).resolve().parent;full=code.parents[1];base=full.parent
 def run(name,cmd,expected=0,env=None):
  with (out/(name+'.log')).open('w') as log:r=subprocess.run(list(map(str,cmd)),stdout=log,stderr=subprocess.STDOUT,env=env)
  atomic_json(out/(name+'.receipt.json'),{'command':list(map(str,cmd)),'exit':r.returncode,'expected_exit':expected})
  if r.returncode!=expected:raise RuntimeError(name+' failed; '+str(out/(name+'.log')))
  print(name,'PASS expected_exit',expected,flush=True)
 f=Path(c['failure_root']);captured=f/'captured_covariance.txt'
 run('eigen_actual_gpu_RED',[f/'eigen_gpu_old',captured],expected=1)
 run('eigen_actual_gpu_GREEN',[f/'eigen_gpu_candidate',captured])
 run('expanded_RGB_alpha',[sys.executable,full/'suite_execution_v01/scan69_cuda_failure_v01/rgb_vjp_validation_v02/expanded_reference.py','--output',out/'expanded_RGB_alpha.json'])
 env=os.environ.copy();env['PYTHONPATH']=c['baseline_python']+os.pathsep+env['PYTHONPATH']
 run('baseline',[sys.executable,base/'stage2/gpu_smoke.py','--mode','baseline','--output',out/'baseline.pt'],env=env)
 run('candidate',[sys.executable,base/'stage2/gpu_smoke.py','--mode','baseline','--output',out/'candidate.pt'])
 import torch,diff_gaussian_rasterization as raster
 from gpu_smoke import assert_close
 assert sha256(raster._C.__file__)==c['inputs']['native']
 b=torch.load(out/'baseline.pt',map_location='cpu',weights_only=False);v=torch.load(out/'candidate.pt',map_location='cpu',weights_only=False);reg={}
 for i,(x,y) in enumerate(zip(b['outputs'],v['outputs'])):
  assert_close(x.float(),y.float(),1e-6,1e-6,'baseline output '+str(i));reg[str(i)]=float((x.float()-y.float()).abs().max())
 for k,x in b['rgb_alpha_gradients'].items():
  y=v['rgb_alpha_gradients'][k];assert_close(x,y,2e-4,2e-5,'baseline RGBalpha backward '+k);reg['gradient_'+k]=float((x-y).abs().max())
 atomic_json(out/'baseline_regression.json',reg)
 run('normal_depth_backend',[sys.executable,base/'gradient_fix_v01/validate_eq24.py','--output',out/'normal_depth_backend.json'])
 run('official_losses',[sys.executable,full/'official_code_fix_v01/gpu_loss_check.py','--output',out/'official_losses.json'])
 run('capture_native',[sys.executable,code/'capture_native_green.py','--config',a.config,'--output',out])
 assert not torch.cuda.is_initialized(), 'Coordinator must remain CPU-only'
 # Fork original train.py with unchanged original loss/view selection, at most 2 updates.
 run('actual_two_steps',[sys.executable,code/'repair_replay_worker.py','--config',a.config])
 replay=Path(c['capture_dir'])/os.environ['RADEGS_ATTEMPT']/'REPLAY_NOT_REPRODUCED.json'
 assert replay.exists() and json.loads(replay.read_text())['status']=='TWO_STEPS_FINITE_ONLY'
 outputs={str(p):sha256(p) for p in out.iterdir() if p.is_file()};outputs[str(replay)]=sha256(replay)
 atomic_json(c['reports']['smoke'],{'status':'PASS','stage':'smoke','attempt':os.environ['RADEGS_ATTEMPT'],'inputs':c['inputs'],'outputs':outputs,'details':{'native':raster._C.__file__,'numerical_revision':'scan55_eigen_fallback_v01','formal_training_completed':False,'original_capture_RED_and_GREEN':True,'bounded_actual_training_steps':2},'scientificdone':False})
 print('NUMERICAL_VALIDATION_PASS; not full training',flush=True)
if __name__=='__main__':main()
