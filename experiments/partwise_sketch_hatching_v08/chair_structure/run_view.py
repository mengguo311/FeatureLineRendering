import runtime
from runtime import sha
from pathlib import Path
import argparse,json
from whole_asset import render_whole
UNIT=runtime.ROOT/'units/unit_007';CODE=Path(__file__).parent
def main():
    p=argparse.ArgumentParser();p.add_argument('arm',choices=['off','on']);p.add_argument('view');a=p.parse_args()
    lock=json.loads((UNIT/'PROTOCOL_LOCK.json').read_text())
    for f,k in [('DECISION.json','decision'),('PROTOCOL.json','protocol'),('SOURCE_LOCK.json','source'),('INPUT_LOCK.json','inputs')]:assert sha(UNIT/f)==lock[k]
    for name,h in json.loads((UNIT/'SOURCE_LOCK.json').read_text()).items():assert sha(CODE/name)==h,name
    for name,h in json.loads((UNIT/'DERIVED_LOCK.json').read_text()).items():assert sha(UNIT/name)==h,name
    c=json.loads((UNIT/'delivery/cameras'/(a.view+'.json')).read_text())
    render_whole(UNIT/'delivery/assets'/a.arm,UNIT/'renders'/a.arm/a.view,c)
if __name__=='__main__':main()
