"""One bounded, frozen real scene render per command."""
import runtime
from runtime import sha
from pathlib import Path
import argparse,json
from whole_asset import render_whole
from parts_asset import render_control

def verify(unit):
    lock=json.loads((unit/'PROTOCOL_LOCK.json').read_text())
    for key,name in [('decision','DECISION.json'),('protocol','PROTOCOL.json'),('source','SOURCE_LOCK.json')]:
        assert sha(unit/name)==lock[key],name
    seal=json.loads((unit/'INPUT_SEAL.json').read_text())
    assert sha(unit/'INPUT_LOCK.json')==seal['inputs'] and sha(unit/'PROTOCOL_LOCK.json')==seal['protocol_lock']
    for rel,h in json.loads((unit/'INPUT_LOCK.json').read_text()).items():assert sha(unit/rel)==h,rel
    for name,h in json.loads((unit/'SOURCE_LOCK.json').read_text()).items():
        assert sha(Path(__file__).parent/name)==h,name
        assert sha(unit/'source_snapshot'/name)==h,name

def main():
    p=argparse.ArgumentParser();p.add_argument('--unit',type=Path,required=True)
    p.add_argument('--kind',choices=['baseline','angle','highlight'],required=True);p.add_argument('--index',type=int,choices=[0,1,2],required=True)
    a=p.parse_args();verify(a.unit)
    c=json.loads((a.unit/'PROTOCOL.json').read_text())['cameras'][a.index]
    out=a.unit/'renders'/a.kind/c['view']
    if a.kind=='highlight':render_control(a.unit/'delivery/assets/angle',a.unit/'delivery/controls/upper_back',out,c)
    else:render_whole(a.unit/'delivery/assets'/a.kind,out,c)
    verify(a.unit)
if __name__=='__main__':main()
