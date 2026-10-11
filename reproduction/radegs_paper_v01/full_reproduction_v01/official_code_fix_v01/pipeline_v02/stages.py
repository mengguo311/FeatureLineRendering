"""Official-method chain; reports are sealed by the independent supervisor."""
import argparse,json,os,signal,subprocess,sys
from pathlib import Path
from safety import atomic_json,sha256
from postprocess import report

def train(c):
 signal.signal(signal.SIGTERM,lambda *args:None);signal.signal(signal.SIGINT,lambda *args:None)
 r=subprocess.run(c['train_command'])
 if r.returncode:raise SystemExit(r.returncode if r.returncode>0 else 75)
 from checkpointing import checkpoint_descriptor
 from train_records import validate_records
 from plyfile import PlyData
 import numpy as np
 model=Path(c['model']);desc=checkpoint_descriptor(model/'restart.json',c['inputs']);assert desc['completed_iteration']==30000
 log=model/'iteration_loss.jsonl';counts=validate_records([json.loads(x) for x in log.read_text().splitlines()]);complete=model/'train_complete.json';assert json.loads(complete.read_text())['inputs']==c['inputs']
 ply=model/'point_cloud/iteration_30000/point_cloud.ply';v=PlyData.read(ply)['vertex'].data;assert len(v) and 'filter_3D' in v.dtype.names;assert all(np.isfinite(v[k]).all() for k in v.dtype.names if k!='opacity');assert not np.isnan(v['opacity']).any()
 outputs=[complete,model/'restart.json',Path(desc['path']),ply,log]
 for i in (14999,15000,30000):
  p=model/('checkpoint_'+str(i)+'.json');d=checkpoint_descriptor(p,c['inputs']);assert d['completed_iteration']==i;outputs.extend([p,Path(d['path']),model/'completed_step_ply'/str(i)/'point_cloud.ply'])
 report(c,'train',outputs,{'method_variant':'official_code_fix_v01',**counts,'gaussians':len(v),'geometry_quality_pending':True})

def main():
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--stage',required=True,choices=['smoke','train','export','tsdf','eval']);a=p.parse_args();c=json.loads(Path(a.config).read_text());sys.path.insert(0,str(Path(__file__).parent))
 from pipeline_scope import validate_scope
 validate_scope(c);assert os.environ['CUDA_VISIBLE_DEVICES']==c['allowed_gpu_uuids'][0]
 import postprocess
 {'smoke':__import__('scene_smoke').smoke,'train':train,'export':postprocess.export,'tsdf':postprocess.tsdf,'eval':postprocess.evaluate}[a.stage](c)
if __name__=='__main__':main()
