"""Gated initial-COLMAP full-resolution forward/backward; zero optimizer steps."""
import argparse,json,os,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'full_resolution_runtime_v01'))
from smoke_runner import validate_probe
import gpu_stages
from safety import atomic_json,sha256

def main():
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);args=p.parse_args();c=json.loads(Path(args.config).read_text());validate_probe(c)
 assert os.environ.get('CUDA_VISIBLE_DEVICES')=='GPU-d2d1e4fd-e246-0633-3343-ccc0a0bd981a'
 import torch
 torch.cuda.init();torch.cuda.reset_peak_memory_stats();begin=time.time()
 gpu_stages.smoke(c)
 memory={'torch_parent_peak_allocated_bytes':torch.cuda.max_memory_allocated(),'torch_parent_peak_reserved_bytes':torch.cuda.max_memory_reserved(),'device_name':torch.cuda.get_device_name(0),'total_device_bytes':torch.cuda.get_device_properties(0).total_memory,'scope':'parent process containing full-resolution all-camera loading and one real data forward/backward; subprocess baseline probes not included','elapsed_seconds_diagnostic_only':time.time()-begin,'optimizer_steps':0,'resolution_pixels':c['expected_scene']['image_resolution'],'scientificdone':False}
 assert 0<memory['torch_parent_peak_allocated_bytes']<=memory['torch_parent_peak_reserved_bytes']<=memory['total_device_bytes']
 output=Path(c['state_dir'])/'gpu_validation/full_resolution_memory.json';atomic_json(output,memory)
 report_path=Path(c['reports']['smoke']);report=json.loads(report_path.read_text());report['outputs'][str(output)]=sha256(output);report['details']['full_resolution_memory']=memory;report['details']['validation_only']=True;atomic_json(report_path,report)
 print(json.dumps(memory),flush=True)
if __name__=='__main__':main()
