"""Wrong-model CLI edits must fail before creating any output; genuine saved input."""
import runtime
from runtime import OUTPUT_ROOT, js, now
from pathlib import Path
import argparse, subprocess, sys

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    a.output.mkdir(parents=True)
    asset=OUTPUT_ROOT/'units/unit_008/catalog_assets/chair'
    dest=a.output/'wrong_scene'
    command=[sys.executable,str(Path(__file__).with_name('demo.py')),'edit','--scene','ficus',
             '--asset',str(asset),'--output',str(dest),'--region','2','--angle','95']
    r=subprocess.run(command,capture_output=True,text=True,timeout=30)
    js(a.output/'RESULT.json',dict(utc=now(),command=command,returncode=r.returncode,
        stdout=r.stdout,stderr=r.stderr,output_created=dest.exists(),actual_input_scene='chair'))
    assert r.returncode!=0, 'wrong-scene edit was accepted on genuine Chair asset'
    assert 'scene/asset mismatch' in r.stderr
    assert not dest.exists(), 'invalid edit created output'
    print('PASS: wrong-scene edit rejected before output')
