"""Pre-evaluation engineering adapter for a frozen copied identifier typo.

run_boundary.py is retained byte-exact. PATB_ARMS was an unintended textual
rename of PATH_ARMS in inherited reporting/evaluation loops. This alias changes
no arm, function body, scientific parameter or generated asset.
"""
import runtime
from runtime import ACTIVE_UNIT as UNIT,sha
import argparse,json
import run_boundary as frozen

def main():
    lock=json.loads((UNIT/'ENGINEERING_ADAPTER_LOCK.json').read_text())
    for path,digest in lock['files'].items():assert sha(path)==digest,path
    assert frozen.PATH_ARMS==('A','B','C') and not hasattr(frozen,'PATB_ARMS')
    frozen.PATB_ARMS=frozen.PATH_ARMS
    ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['evaluate','attribution']);args=ap.parse_args()
    getattr(frozen,args.stage)()

if __name__=='__main__':main()
