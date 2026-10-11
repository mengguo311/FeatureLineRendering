"""Fresh official C24 scan24, literal defaults, complete verified resume only."""
import argparse,json,os,sys
from pathlib import Path

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--config',required=True);a=ap.parse_args();c=json.loads(Path(a.config).read_text());sys.path.insert(0,c['runtime_module']);sys.path.insert(0,c['runtime_source'])
 import train,torch,diff_gaussian_rasterization as raster
 from safety import sha256
 from arguments import ModelParams,PipelineParams,OptimizationParams
 assert Path(train.__file__).resolve()==Path(c['runtime_source'])/'train.py';assert sha256(raster._C.__file__)==c['inputs']['native'];assert os.environ['CUDA_VISIBLE_DEVICES']==c['allowed_gpu_uuids'][0]
 p=argparse.ArgumentParser();mp=ModelParams(p);op=OptimizationParams(p);pp=PipelineParams(p);args=p.parse_args(['-s',c['data'],'-m',c['model'],'-r','2','--use_decoupled_appearance'])
 expected={'iterations':30000,'resolution':2,'lambda_distortion':100,'lambda_depth_normal':.05,'regularization_from_iter':15000,'use_decoupled_appearance':True,'eval':False,'white_background':False}
 assert all(getattr(args,k)==v for k,v in expected.items()),'C24 defaults changed'
 train.safe_state(False);train.training(mp.extract(args),op.extract(args),pp.extract(args),[],[15000,30000],[],None,-1,a.config)
if __name__=='__main__':main()
