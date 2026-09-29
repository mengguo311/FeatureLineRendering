"""Detached verification trigger; never issues a scientific or visual verdict."""
import json,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];base=ROOT/'out/direct_curve_global_fit_probe/scheduler'/sys.argv[1]
while not all((base/r/'COMPLETE.json').exists() for r in ['run','rerun']):time.sleep(30)
py='/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python';output=base/'verification'
with (base/'verification.log').open('xb') as f:
 result=subprocess.run([py,'artifacts/direct_curve_global_fit_probe/verify_resume_delivery.py','--session',sys.argv[1],'--output',str(output)],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
with (base/'VERIFICATION_EXIT.json').open('x') as f:json.dump(dict(exit=result.returncode,output=str(output),independent_visual_review=False),f)
