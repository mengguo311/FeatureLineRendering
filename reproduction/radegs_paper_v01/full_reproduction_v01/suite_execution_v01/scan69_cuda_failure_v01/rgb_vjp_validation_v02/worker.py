"""Actual baseline/Eq23/Eq24/scene smoke plus every RGB input FD; one admitted GPU process group."""
import argparse,json,os,sys,time,subprocess
from pathlib import Path

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--config',required=True);args=ap.parse_args();c=json.loads(Path(args.config).read_text());assert os.environ['CUDA_VISIBLE_DEVICES']==c['allowed_gpu_uuids'][0]
 from safety import atomic_json,sha256
 import gpu_stages
 out=Path(c['diagnostic_output'])/os.environ['RADEGS_ATTEMPT'];out.mkdir(parents=True,exist_ok=False)
 fd=out/'expanded_reference.json';subprocess.run([sys.executable,str(Path(__file__).with_name('expanded_reference.py')),'--output',str(fd)],check=True)
 # Keep existing baseline RGB/alpha, Eq23/Eq24, normal independent reference,
 # eps sweep, and actual scan69 appearance/filter forward/backward checks intact.
 gpu_stages.smoke(c)
 r=Path(c['reports']['smoke']);report=json.loads(r.read_text());report['outputs'][str(fd)]=sha256(fd);report['details'].update(backward_candidate_only=True,expanded_RGB_fd=str(fd),production_training_approved=False,original_scan69_NaN_cause_proven=False);atomic_json(r,report)
if __name__=='__main__':main()
